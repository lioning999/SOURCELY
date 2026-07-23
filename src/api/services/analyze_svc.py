"""1688 商品分析服务 — 缓存→限流→Apify→判词→入库 全流程编排。

覆盖风险清单：
  #2  请求合并（Coalescing） → _pending 字典
  #3  90s 超时 + 过期缓存兜底
  #7  三级降级响应
  #8  字段级容错（判词引擎 + 映射层均检查字段存在性）
"""

import asyncio
import time
import uuid
from typing import Any

from config import Config
from adapters.apify_adapter import apify_adapter
from domain import cache as analysis_cache
from domain.cache import cache as _cache_store  # 只读过期缓存（风险 #3 #7 降级数据源）
from domain import rate_limiter
from domain.product_mapper import map_raw, as_dict_list
from domain.verdict_engine import judge_all
from repositories.analysis_repo import AnalysisRepository
from utils.exceptions import ExternalServiceError
from utils.logger import get_logger

logger = get_logger(__name__)

# ---- 异步任务管理 ----
_pending: dict[str, asyncio.Task[dict[str, Any]]] = {}  # {offer_id: Task}  请求合并（风险 #2）
_tasks: dict[str, dict[str, Any]] = {}        # {task_id: {status, result, ...}}  异步轮询（风险 #10）
TASK_TTL = Config.TASK_TTL  # 任务结果保留时长（秒）


class AnalyzeService:
    """商品分析编排。依赖注入。"""

    def __init__(self, repo: AnalysisRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # 公开接口：异步轮询模式（风险 #10）
    # ------------------------------------------------------------------

    async def start(self, offer_id: str, user_id: int = 0, raw_url: str = "") -> str:
        """启动分析，立即返回 task_id。

        后台执行：缓存检查 → 限流 → Apify → 判词 → 入库。
        前端每 2s 轮询 GET /api/analyze/{task_id}。
        """
        # 请求合并（风险 #2）：同一 offer_id 正在分析中 → 等现有结果
        if offer_id in _pending:
            logger.info(f"Request coalesced: offer_id={offer_id}")
            existing_task = _pending[offer_id]
            task_id = str(uuid.uuid4())[:8]
            _tasks[task_id] = {"status": "pending", "result": None, "created_at": time.time()}

            async def _wait_existing():
                try:
                    result = await existing_task
                    _tasks[task_id] = {"status": "done", "result": result, "created_at": time.time()}
                except Exception as e:
                    _tasks[task_id] = {"status": "failed", "error": str(e), "created_at": time.time()}

            asyncio.create_task(_wait_existing())
            return task_id

        task_id = str(uuid.uuid4())[:8]
        _tasks[task_id] = {"status": "pending", "result": None, "created_at": time.time()}
        _pending[offer_id] = asyncio.create_task(self._run(task_id, offer_id, user_id, raw_url))
        return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """查询任务状态。None = 不存在或已过期。"""
        task = _tasks.get(task_id)
        if task and time.time() - task["created_at"] > TASK_TTL:
            del _tasks[task_id]
            return None
        return task

    async def get_history(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """查用户最近的分析记录（只读 DB，不调 Apify）。"""
        return await self.repo.get_history(user_id, limit)

    async def save_report(self, user_id: int, offer_id: str) -> dict[str, Any] | None:
        """用户手动保存分析报告到 DB。

        从内存缓存取数据 → 调用 repo.upsert() 写入。
        缓存不存在返回 None。
        """
        cached = analysis_cache.get(offer_id)
        if cached is None:
            return None
        await self._save_to_db_upsert(cached, user_id, offer_id)
        return cached

    # ------------------------------------------------------------------
    # 后台分析流水线
    # ------------------------------------------------------------------

    async def _run(self, task_id: str, offer_id: str, user_id: int, raw_url: str) -> dict[str, Any]:
        """完整分析流水线（在后天 asyncio.Task 中执行）。"""
        try:
            _tasks[task_id]["status"] = "running"

            # ---- 1. 缓存检查（风险 #1） ----
            cached = analysis_cache.get(offer_id)
            if cached:
                logger.info(f"Cache hit: offer_id={offer_id}")
                # 异步写入 DB（不阻塞返回）
                if user_id:
                    asyncio.create_task(self._save_to_db(cached, user_id, offer_id))
                _tasks[task_id] = {"status": "done", "result": cached, "created_at": time.time()}
                return cached

            # ---- 2. 全局限流（风险 #14 L3） ----
            if not rate_limiter.check():
                logger.warning(f"Global rate limit hit")
                # 有过期缓存 → 降级返回（风险 #7 一级降级）
                expired = _get_expired_cache(offer_id)
                if expired:
                    _tasks[task_id] = {
                        "status": "done", "result": expired,
                        "warning": "数据可能不是最新，系统繁忙中",
                        "created_at": time.time(),
                    }
                    return expired
                # 无缓存 → 明确拒绝
                _tasks[task_id] = {"status": "failed", "error": "系统繁忙，请稍后重试", "created_at": time.time()}
                raise ExternalServiceError(service_name="系统", details={"reason": "global_rate_limit"})

            # ---- 3. Apify 抓取（风险 #3：90s 超时） ----
            try:
                raw = await apify_adapter.fetch_product_by_url(raw_url or Config.URL_1688_DETAIL.format(offer_id=offer_id))
            except Exception as e:
                logger.error(f"Apify fetch failed: {e}")
                # 过期缓存兜底（风险 #3 + #7 一级降级）
                expired = _get_expired_cache(offer_id)
                if expired:
                    _tasks[task_id] = {
                        "status": "done", "result": expired,
                        "warning": "数据可能不是最新，该链接当前无法获取",
                        "created_at": time.time(),
                    }
                    return expired
                # 无缓存（风险 #7 三级降级）
                _tasks[task_id] = {"status": "failed", "error": "获取失败，请稍后重试。如持续失败请联系客服", "created_at": time.time()}
                raise ExternalServiceError(service_name="Apify", details={"reason": "fetch_failed"}) from e

            if raw is None:
                expired = _get_expired_cache(offer_id)
                if expired:
                    _tasks[task_id] = {
                        "status": "done", "result": expired,
                        "warning": "数据可能不是最新，该链接当前无法获取",
                        "created_at": time.time(),
                    }
                    return expired
                _tasks[task_id] = {
                    "status": "failed",
                    "error": "该链接可能已下架，请检查后重试",
                    "created_at": time.time(),
                }
                raise ExternalServiceError(service_name="Apify", details={"reason": "empty_result"})

            # ---- 4. 映射 + 判词 ----
            mapped = map_raw(raw, raw_url, offer_id)

            # 判词（风险 #4 #5 #6）
            verdicts = judge_all(mapped)
            mapped["verdict_product"] = verdicts["product"]
            mapped["verdict_factory"] = verdicts["factory"]
            mapped["verdict_sample"] = verdicts["sample"]

            # ---- 5. 写缓存（风险 #1 #14 L2） ----
            analysis_cache.set(offer_id, mapped)

            # ---- 6. 异步入库（风险 #12） ----
            if user_id:
                asyncio.create_task(self._save_to_db(mapped, user_id, offer_id))

            _tasks[task_id] = {"status": "done", "result": mapped, "created_at": time.time()}
            logger.info(f"Analysis done: offer_id={offer_id} task={task_id}")
            return mapped

        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception(f"Analysis failed: offer_id={offer_id}")
            _tasks[task_id] = {"status": "failed", "error": "服务器内部错误，请稍后重试", "created_at": time.time()}
            raise ExternalServiceError(service_name="分析引擎") from e
        finally:
            _pending.pop(offer_id, None)

    async def _save_to_db(self, mapped: dict[str, Any], user_id: int, offer_id: str) -> None:
        """异步写入 analysis 表（不阻塞主流程）。"""
        try:
            await self.repo.create(self._db_data(mapped, user_id, offer_id))
        except Exception:
            logger.exception(f"DB save failed for offer_id={offer_id}")

    async def _save_to_db_upsert(self, mapped: dict[str, Any], user_id: int, offer_id: str) -> None:
        """同步写入 analysis 表（用户手动保存，跑 upsert 不报重复键错误）。"""
        await self.repo.upsert(self._db_data(mapped, user_id, offer_id))

    def _db_data(self, mapped: dict[str, Any], user_id: int, offer_id: str) -> dict[str, Any]:
        """提取 DB 写入所需字段（_save_to_db 和 _save_to_db_upsert 共用）。"""
        return {
            "user_id": user_id,
            "offer_id": offer_id,
            "status": "done",
            "title": mapped.get("title"),
            "image_url": mapped.get("image"),
            "price_min": mapped.get("priceCNY", {}).get("low") if mapped.get("priceCNY") else None,  # type: ignore[reportUnknownMemberType]
            "price_max": mapped.get("priceCNY", {}).get("high") if mapped.get("priceCNY") else None,  # type: ignore[reportUnknownMemberType]
            "moq": mapped.get("moq"),
            "unit": mapped.get("unit"),
            "shop_name": mapped.get("supplierName"),
            "shop_years": mapped.get("shop_years"),
            "shop_rate": mapped.get("shop_rate"),
            "repurchase": mapped.get("repurchase"),
            "sold": mapped.get("sold"),
            "verdict_product": mapped.get("verdict_product"),
            "verdict_factory": mapped.get("verdict_factory"),
            "verdict_sample": mapped.get("verdict_sample"),
            "specs": [{"spec_key": s.get("name", s.get("spec_key", "")), "spec_value": s.get("value", s.get("spec_value", ""))}
                       for s in as_dict_list(mapped.get("specs"))],
            "skus": [{"sku_name": s.get("name") or s.get("sku_name", ""),
                       "sku_image": s.get("imgUrl") or s.get("sku_image", "")}
                      for s in as_dict_list(mapped.get("skus"))],
            "price_tiers": mapped.get("price_tiers", []) or [],
        }


# ---- 单例 ----
analyze_service = AnalyzeService(repo=AnalysisRepository())


def _get_expired_cache(offer_id: str) -> dict[str, Any] | None:
    """读取过期缓存（风险 #3 #7：超时/失败时的降级数据源）。"""
    entry = _cache_store.get(offer_id)
    if entry:
        return entry[1]
    return None
