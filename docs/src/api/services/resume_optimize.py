"""简历优化服务 — preview（全文优化）+ result（DB 秒开）+ interview_qa（追问异步）"""

import json

from adapters.ai_client import AIClient
from repositories.resumes import ResumeRepository
from repositories.diagnoses import DiagnosisRepository
from domain.prompts import (
    build_optimize_prompt,
    build_interview_qa_prompt,
    build_interview_mock_prompt,
)
from domain.rules import sanitize_self_evaluation
from utils.exceptions import (
    AppError,
    AuthorizationError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)
from utils.logger import get_logger, mask_openid
from config import Config

logger = get_logger(__name__)


class QuotaExhaustedError(AppError):
    """次数不足 → 402。"""
    def __init__(self, quota_type: str, message: str):
        super().__init__(message=message, http_status=402)
        self.quota_type = quota_type  # "preview" | "optimize"


class ResumeOptimizeService:
    """简历优化编排。注入 AI client（依赖注入）。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    # ── 内部 ──────────────────────────────────────────

    async def _get_diag(self, diagnosis_id: str, openid: str) -> dict:
        diag = await DiagnosisRepository.get_by_id(diagnosis_id)
        if not diag:
            raise ResourceNotFoundError(resource_type="诊断", resource_id=diagnosis_id)
        if diag["openid"] != openid:
            raise AuthorizationError(message="诊断不属于当前用户")
        return diag

    @staticmethod
    def _parse_result(diag: dict) -> dict:
        r = diag["diagnose_result"]
        return json.loads(r) if isinstance(r, str) else r

    @staticmethod
    async def _ensure_paid(openid: str, diagnosis_id: str) -> None:
        """检查该诊断是否已付费。未付 → QuotaExhaustedError(402)。"""
        diag = await DiagnosisRepository.get_by_id(diagnosis_id)
        if not diag or not diag.get("is_paid"):
            raise QuotaExhaustedError("optimize",
                "请先打赏 ¥1 解锁完整优化结果、追问预判与模拟面试。")

    # ── POST /resume/preview ──────────────────────────

    async def preview(self, openid: str, diagnosis_id: str) -> dict:
        """全文 AI 优化（免费）→ 入库 → 返回 Top 2 before/after 对。"""
        diag = await self._get_diag(diagnosis_id, openid)

        # 幂等：已有优化结果直接返回
        if diag.get("optimized_text"):
            logger.info(f"PREVIEW_CACHED diagnosis_id={diagnosis_id}")
            return self._cached_response(diag)

        # 调 AI 全文优化
        diagnose_result = self._parse_result(diag)
        resume = await ResumeRepository.get_by_id(diag["resume_id"], openid)
        raw_text = resume["raw_text"]

        logger.info(f"PREVIEW_START diagnosis_id={diagnosis_id} text_len={len(raw_text)}")
        ai_result = await self._call_ai(
            build_optimize_prompt(raw_text, diagnose_result),
            diagnosis_id, "AI优化",
        )

        # 入库
        optimized_text = ai_result.get("optimized_text", "")
        before_after = ai_result.get("before_after_pairs", [])

        # 代码层安全网：修复权力升级
        before_after, fixed_count = self._sanitize_pairs(before_after)
        if fixed_count > 0:
            logger.info(f"SANITIZE_FIXED diagnosis_id={diagnosis_id} fixed={fixed_count}")

        # 代码层后处理：T5c 非标准段落删除
        optimized_text, before_after, post_fixed = self._post_process(
            optimized_text, before_after)

        # 出口安全网：自评权力词扫描
        optimized_text = sanitize_self_evaluation(optimized_text)

        if post_fixed > 0:
            logger.info(f"POST_PROCESS diagnosis_id={diagnosis_id} fixed={post_fixed}")

        pairs_json = json.dumps(before_after, ensure_ascii=False)
        await DiagnosisRepository.update_optimized_text(
            diagnosis_id=diagnosis_id, openid=openid,
            optimized_text=optimized_text, before_after_pairs=pairs_json,
        )

        total_issues = len(diagnose_result.get("fatal_issues", []))

        return {
            "preview": self._top2_pairs(before_after, diagnose_result),
            "total_issues": total_issues,
            "diagnosis_id": diagnosis_id,
            "is_paid": bool(diag.get("is_paid")),
        }

    # ── GET /resume/result ────────────────────────────

    async def get_result(self, openid: str, diagnosis_id: str) -> dict:
        """查看完整优化结果。需已打赏 ¥1。"""
        diag = await self._get_diag(diagnosis_id, openid)
        optimized_text = diag.get("optimized_text")
        if not optimized_text:
            raise ValidationError(message="该诊断尚未优化，请先预览")

        await self._ensure_paid(openid, diagnosis_id)

        diagnose_result = self._parse_result(diag)
        optimized_text = sanitize_self_evaluation(optimized_text)
        return {
            "optimized_text": optimized_text,
            "before_after_pairs": diag.get("before_after_pairs") or [],
            "diagnose_summary": {
                "overall_impression": diagnose_result.get("overall_impression", ""),
                "fatal_count": len(diagnose_result.get("fatal_issues", [])),
            },
            "interview_qa": diag.get("interview_qa"),
            "diagnosis_id": diagnosis_id,
        }

    # ── POST /resume/interview-qa ─────────────────────

    async def get_interview_qa(self, openid: str, diagnosis_id: str) -> dict:
        """调 AI 生成追问预判 + resolved 标注，入库后返回。

        需已完成优化（optimized_text 存在）且已打赏。
        """
        diag = await self._get_diag(diagnosis_id, openid)

        # 未优化 → 引导先预览
        if not diag.get("optimized_text"):
            raise ValidationError(message="该诊断尚未优化，请先预览")

        # 付费判断
        await self._ensure_paid(openid, diagnosis_id)

        # 幂等
        cached = diag.get("interview_qa")
        if cached:
            logger.info(f"QA_CACHED diagnosis_id={diagnosis_id}")
            return cached if isinstance(cached, dict) else json.loads(cached)

        diagnose_result = self._parse_result(diag)
        optimized_text = diag.get("optimized_text", "")
        resume = await ResumeRepository.get_by_id(diag["resume_id"], openid)

        logger.info(f"QA_START diagnosis_id={diagnosis_id}")
        ai_result = await self._call_ai(
            build_interview_qa_prompt(
                resume["raw_text"], diagnose_result, optimized_text
            ),
            diagnosis_id, "AI追问预判",
        )

        await DiagnosisRepository.update_interview_qa(
            diagnosis_id=diagnosis_id, openid=openid,
            interview_qa=json.dumps(ai_result, ensure_ascii=False),
        )
        logger.info(f"QA_DONE diagnosis_id={diagnosis_id}")
        return ai_result

    # ── POST /resume/interview-questions ──────────────

    async def get_interview_questions(self, openid: str, diagnosis_id: str) -> dict:
        """调 AI 生成模拟面试题 + 入库，返回 5 道面试题。

        需已完成优化（optimized_text 存在）且已打赏。
        """
        diag = await self._get_diag(diagnosis_id, openid)

        # 未优化 → 引导先预览
        if not diag.get("optimized_text"):
            raise ValidationError(message="该诊断尚未优化，请先预览")

        # 付费判断
        await self._ensure_paid(openid, diagnosis_id)

        # 幂等
        cached = diag.get("interview_questions")
        if cached:
            logger.info(f"INTERVIEW_QUESTIONS_CACHED diagnosis_id={diagnosis_id}")
            return cached if isinstance(cached, dict) else json.loads(cached)

        diagnose_result = self._parse_result(diag)
        optimized_text = diag.get("optimized_text", "")
        resume = await ResumeRepository.get_by_id(diag["resume_id"], openid)

        logger.info(f"INTERVIEW_QUESTIONS_START diagnosis_id={diagnosis_id}")
        ai_result = await self._call_ai(
            build_interview_mock_prompt(
                resume["raw_text"], diagnose_result, optimized_text
            ),
            diagnosis_id, "AI模拟面试",
        )

        await DiagnosisRepository.update_interview_questions(
            diagnosis_id=diagnosis_id, openid=openid,
            interview_questions=json.dumps(ai_result, ensure_ascii=False),
        )
        # 流程走完 → 清理该用户其他诊断记录，保留当前
        await DiagnosisRepository.delete_other_diagnoses(openid, diagnosis_id)
        logger.info(f"INTERVIEW_QUESTIONS_DONE diagnosis_id={diagnosis_id}")
        return ai_result

    # ── GET /resume/latest ───────────────────────────

    async def get_latest(self, openid: str) -> dict | None:
        """查询最近一次诊断的摘要 + 各环节完成状态。"""
        row = await DiagnosisRepository.get_latest_by_openid(openid)
        if not row:
            return None

        diag = row["diagnose_result"]
        fatal_count = len(diag.get("fatal_issues", [])) if isinstance(diag, dict) else 0

        return {
            "diagnosis_id": row["id"],
            "created_at": str(row["created_at"]),
            "fatal_count": fatal_count,
            "steps": {
                "diagnose": True,
                "optimize": bool(row["optimized_text"]),
                "interview_qa": bool(row["interview_qa"]),
                "interview_questions": bool(row["interview_questions"]),
            },
        }

    # ── 安全网：代码层修复 AI 输出 ─────────────────

    @staticmethod
    def _sanitize_pairs(pairs: list[dict]) -> tuple[list[dict], int]:
        """检测并修复权力升级。返回 (修复后的 pairs, 修复数)。"""
        ALWAYS_FIX = [
            ("独立完成", "完成"),
            ("独立负责", "承担"),
            ("主导", "参与"),
            ("牵头", "配合"),
        ]
        fixed = 0
        reasons = []
        for pair in pairs:
            before = pair.get("before", "")
            after = pair.get("after", "")
            pair_reasons = []
            for forbidden, safe in ALWAYS_FIX:
                if forbidden in after:
                    after = after.replace(forbidden, safe)
                    pair_reasons.append(f'"{forbidden}"表述夸大，改为"{safe}"')
                    fixed += 1
            # 帮忙 → 负责：只在原文是"帮忙"时替换
            if "帮忙" in before and "负责" in after:
                after = after.replace("负责", "参与")
                pair_reasons.append('原文为"帮忙"，应保留参与角色')
                fixed += 1
            # 参与 → 独立完成：只在原文是"参与"时替换
            if "参与" in before and "独立完成" in after:
                after = after.replace("独立完成", "完成")
                pair_reasons.append('原文为"参与"，不应升为"独立完成"')
                fixed += 1
            # 参与 → 独立负责：只在原文是"参与"时替换
            if "参与" in before and "独立负责" in after:
                after = after.replace("独立负责", "承担")
                pair_reasons.append('原文为"参与"，不应升为"独立负责"')
                fixed += 1
            pair["after"] = after
            if pair_reasons:
                pair["reason"] = "；".join(pair_reasons)
        return pairs, fixed

    @staticmethod
    def _post_process(optimized_text: str, before_after: list[dict]) -> tuple[str, list[dict], int]:
        """T5c 非标准简历段落删除。返回 (text, pairs, fixed)。"""
        import re
        fixed = 0

        for keyword in ['岗位匹配说明', '求职信', '推荐语']:
            idx = optimized_text.find(keyword)
            if idx == -1:
                continue
            line_start = optimized_text.rfind('\n', 0, idx) + 1
            next_sec = re.search(
                r'\n[（(]?[一二三四五六七八九十\d]+[）)、]',
                optimized_text[line_start + len(keyword):])
            sec_end = line_start + len(keyword) + next_sec.start() if next_sec else len(optimized_text)
            para_start = line_start
            if para_start > 0 and optimized_text[para_start - 1] == '\n':
                para_start -= 1
            deleted = optimized_text[para_start:sec_end].strip()
            if len(deleted) > 20:
                optimized_text = (optimized_text[:para_start]
                                  + optimized_text[sec_end:].lstrip('\n'))
                before_after.append({
                    "section": keyword, "based_on_issue_id": None,
                    "before": deleted[:500], "after": "",
                    "reason": f"这是{keyword}类非标准简历段落，与正文内容重复，已删除",
                })
                fixed += 1
            break

        return optimized_text, before_after, fixed

    # ── 内部 ──────────────────────────────────────────

    async def _call_ai(self, messages: list[dict], diagnosis_id: str, label: str) -> dict:
        try:
            return await self.ai.chat_json(
                messages=messages, temperature=0.0, max_tokens=Config.AI_MAX_TOKENS)
        except AppError:
            raise
        except Exception as e:
            logger.error(f"{label}_ERROR diagnosis_id={diagnosis_id} {type(e).__name__}: {e}")
            raise ExternalServiceError(service_name=label) from e

    @staticmethod
    def _top2_pairs(before_after: list[dict], diagnose_result: dict) -> list[dict]:
        """取 Top 2（按 severity 排序），补 issue_title。"""
        if not before_after:
            return []
        sev = {i.get("id"): i.get("severity", "medium")
               for i in diagnose_result.get("fatal_issues", [])}
        pairs = sorted(before_after,
                       key=lambda p: 0 if sev.get(p.get("based_on_issue_id")) == "high" else 1)
        titles = {i.get("id"): i.get("title", "")
                  for i in diagnose_result.get("fatal_issues", [])}
        return [{"issue_title": titles.get(p.get("based_on_issue_id"), ""),
                 "before": p.get("before", ""), "after": p.get("after", "")}
                for p in pairs[:2]]

    @staticmethod
    def _cached_response(diag: dict) -> dict:
        """幂等：已有优化结果，从 DB 取 before_after_pairs 返回 Top 2。"""
        r = diag["diagnose_result"]
        if isinstance(r, str):
            r = json.loads(r)
        pairs = diag.get("before_after_pairs") or []
        return {
            "preview": ResumeOptimizeService._top2_pairs(pairs, r),
            "total_issues": len(r.get("fatal_issues", [])),
            "diagnosis_id": diag["id"], "cached": True,
            "is_paid": bool(diag.get("is_paid")),
        }
