"""简历诊断服务 — Rules 提取 + AI 诊断（JSON）+ 结果存储 + 幂等缓存"""

import json
import time

from adapters.ai_client import AIClient
from repositories.resumes import ResumeRepository
from repositories.diagnoses import DiagnosisRepository
from domain.rules import count_digits, count_self_claims, format_rules_stats, clean_resume_text
from domain.prompts import build_diagnosis_prompt
from utils.exceptions import AppError, ExternalServiceError, ValidationError
from utils.file_utils import get_text_hash
from utils.logger import get_logger, mask_openid
from config import Config

logger = get_logger(__name__)

# ── 诊断幂等缓存：同一用户+同一简历内容 MD5，24h 内跳过 AI 调用 ──
_DIAG_CACHE_TTL = 86400  # 24 小时
_DIAG_CACHE_MAX_SIZE = 1000
_diag_cache: dict[str, dict] = {}


class ResumeDiagnoseService:
    """简历诊断编排。注入 AI client（依赖注入）。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    async def diagnose(self, openid: str, resume_id: str) -> dict:
        """完整诊断流程（JSON 输出 + 覆盖旧诊断 + 幂等缓存）。

        1. 读简历（校验归属）→ 清洗文本 → 缓存检查
        2. 缓存命中 → 跳过 AI，upsert 缓存结果直接返回
        3. Rules 提取（纯正则）
        4. 拼 Prompt + 调 AI（chat_json）
        5. 重连 DB + upsert 覆盖旧诊断
        6. 写入缓存 → 返回 {diagnosis_id, result, is_rediagnosis}

        Raises:
            ResourceNotFoundError: 简历不存在
            AuthorizationError: 简历不属于当前用户
            ExternalServiceError: AI 调用失败
        """
        # ── ① 读简历（Repository 内校验归属）────────
        resume = await ResumeRepository.get_by_id(resume_id, openid)
        raw_text = resume["raw_text"]

        if not raw_text or not raw_text.strip():
            raise ValidationError(message="简历文本为空")

        logger.info(
            f"DIAGNOSE_START resume_id={resume_id} "
            f"openid={mask_openid(openid)} text_len={len(raw_text)}"
        )

        # ── ② 清洗传输噪声（乱码碎片、编码断裂）───
        clean_text = clean_resume_text(raw_text)

        # ── ②.5 幂等缓存：同一份简历 24h 内不重复调 AI ──
        cache_key = f"{openid}:{get_text_hash(clean_text)}"
        cached = _diag_cache.get(cache_key)
        if cached and (time.time() - cached["ts"]) < _DIAG_CACHE_TTL:
            logger.info(
                f"DIAGNOSE_CACHE_HIT resume_id={resume_id} "
                f"openid={mask_openid(openid)} "
                f"cached_diag_id={cached['diagnosis_id']}"
            )
            ai_result = json.loads(cached["diagnose_result"])
            # 不调 AI，不 upsert，直接返回已有 diagnosis
            return {
                "diagnosis_id": cached["diagnosis_id"],
                "result": ai_result,
                "is_cached": True,
            }

        # ── ③ Rules 提取（纯正则，毫秒级）─────────
        numbers = count_digits(clean_text)
        claims = count_self_claims(clean_text)
        stats_text = format_rules_stats(numbers, claims)

        logger.debug(
            f"DIAGNOSE_RULES numbers={numbers} claims={claims}"
        )

        # ── ③ 释放 DB 连接 ⚠️ 铁律 ─────────────────
        # AI 调用 30-120s，不能占着连接。连接已在 Repository 的 finally 中释放。

        # ── ④ 拼 Prompt ─────────────────────────
        messages = build_diagnosis_prompt(clean_text, stats_text)

        # ── ⑤ 调 AI（JSON 模式，两层防御）─────────
        try:
            ai_result = await self.ai.chat_json(
                messages=messages,
                temperature=0.0,
                max_tokens=Config.AI_MAX_TOKENS,
            )
        except AppError:
            raise  # Adapter 已包装，原样透传
        except Exception as e:
            logger.error(
                f"DIAGNOSE_AI_ERROR resume_id={resume_id} error={type(e).__name__}: {e}"
            )
            raise ExternalServiceError(service_name="AI诊断") from e

        result_len = len(json.dumps(ai_result, ensure_ascii=False))
        logger.info(
            f"DIAGNOSE_AI_DONE resume_id={resume_id} result_len={result_len}"
        )

        # ── ⑥ 重连 DB + upsert 覆盖旧诊断 ──────────
        diagnose_json = json.dumps(ai_result, ensure_ascii=False)
        diagnosis_id, is_rediagnosis = await DiagnosisRepository.upsert(
            openid=openid,
            resume_id=resume_id,
            diagnose_result=diagnose_json,
        )

        # ── ⑦ 写入缓存 + 过期淘汰 ─────
        _diag_cache[cache_key] = {
            "diagnose_result": diagnose_json,
            "ts": time.time(),
            "diagnosis_id": diagnosis_id,
        }
        _sweep_cache()

        logger.info(
            f"DIAGNOSE_COMPLETE diagnosis_id={diagnosis_id} "
            f"resume_id={resume_id} openid={mask_openid(openid)} "
            f"rediagnosis={is_rediagnosis}"
        )

        return {
            "diagnosis_id": diagnosis_id,
            "result": ai_result,
            "is_rediagnosis": is_rediagnosis,
        }


def _sweep_cache() -> None:
    """淘汰过期条目；超上限时淘汰最旧条目"""
    now = time.time()
    expired = [k for k, v in _diag_cache.items() if (now - v["ts"]) > _DIAG_CACHE_TTL]
    for k in expired:
        del _diag_cache[k]
    if len(_diag_cache) > _DIAG_CACHE_MAX_SIZE:
        sorted_keys = sorted(_diag_cache.items(), key=lambda x: x[1]["ts"])
        for k, _ in sorted_keys[:len(_diag_cache) - _DIAG_CACHE_MAX_SIZE]:
            del _diag_cache[k]
