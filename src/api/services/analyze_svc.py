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
from typing import Any, cast

from config import Config
from adapters.apify_adapter import apify_adapter
from domain import cache as analysis_cache
from domain.cache import cache as _cache_store  # 只读过期缓存（风险 #3 #7 降级数据源）
from domain import rate_limiter
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
            mapped = _map_raw(raw, raw_url, offer_id)

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
                       for s in _as_dict_list(mapped.get("specs"))],
            "skus": [{"sku_name": s.get("name") or s.get("sku_name", ""),
                       "sku_image": s.get("imgUrl") or s.get("sku_image", "")}
                      for s in _as_dict_list(mapped.get("skus"))],
            "price_tiers": mapped.get("price_tiers", []) or [],
        }


# ---- 单例 ----
analyze_service = AnalyzeService(repo=AnalysisRepository())


# ====================================================================
# 数据映射（原 analyze_service._map 逻辑）
# ====================================================================

def _map_raw(raw: dict[str, Any], original_url: str, offer_id: str) -> dict[str, Any]:
    """Apify 原始 JSON → 标准化数据（字段级容错，风险 #8）。

    所有字段取值前检查存在性，缺字段不崩溃。
    """
    price_data: dict[str, Any] = raw.get("price") or {}
    supplier: dict[str, Any] = raw.get("supplier") or {}
    flags: dict[str, Any] = supplier.get("flags", {}) or {}
    stats: dict[str, Any] = supplier.get("stats", {}) or {}
    shipping: dict[str, Any] = raw.get("shipping") or {}

    price_low_cny = price_data.get("min") or 0
    price_high_cny = price_data.get("max") or price_low_cny
    location = shipping.get("location", "")

    # SKU 变体（Apify 键名: skuImages，字段: name/imgUrl）
    sku_list: list[dict[str, Any]] = raw.get("skuImages") or raw.get("skuList") or raw.get("skus") or []

    # 阶梯价格
    price_tiers = _extract_price_tiers(raw)

    # 数据完整度信号（三层金字塔：认证 + 年限）
    _tier, _tier_reason = _data_tier(flags, supplier.get("tpYear"))

    return {
        # 产品信息
        "title": raw.get("title", ""),
        "image": (raw.get("images") or [""])[0] if raw.get("images") else "",
        "images": (raw.get("images") or [])[:5],
        "priceLow": round(float(price_low_cny) / Config.CNY_USD_RATE, 2) if price_low_cny else None,
        "priceHigh": round(float(price_high_cny) / Config.CNY_USD_RATE, 2) if price_high_cny else None,
        "priceCNY": {"low": price_low_cny, "high": price_high_cny},
        "moq": raw.get("minOrderQuantity"),
        "itemUrl": original_url or raw.get("detailUrl", ""),
        "specs": _filter_specs(raw.get("specs", []) or []),
        "unit": raw.get("unit", ""),
        "offerId": offer_id,

        # 产品指标
        "return7day": "OK" if _has_tag(raw.get("serviceLabels", []) or [], "7天")
                            or _has_tag(raw.get("serviceLabels", []) or [], "退货") else "NO",
        "sold": raw.get("saledCount"),
        "wantBuyCount": raw.get("wantBuyCount", 0),

        # 产品标签（Badge 行）
        "badgeLabels": _build_badge_labels(
            raw.get("productFlags", {}) or {},
            raw.get("serviceLabels", []) or [],
        ),

        # 工厂信息
        "supplierName": supplier.get("companyName", ""),
        "shop_rate": _parse_pct(
            stats.get("positiveReviewRate")
            or _raw_card_value(stats, "goodRate")
            or supplier.get("positiveReviewRate")
        ),
        "shop_years": supplier.get("tpYear"),
        "repurchase": _parse_pct(
            stats.get("repeatRate")
            or _raw_card_value(stats, "byrRepeatRate")
            or _factory_tag_value(supplier, "回头率")
            or supplier.get("repeatRate")
        ),
        "shippingLocation": location,
        "industryCluster": _industry_cluster(location),
        "deliveryDays": shipping.get("deliveryDays"),
        "freeSample": _has_tag(raw.get("serviceLabels", []) or [], "免费拿样"),

        # 工厂身份 + 认证 + 排名
        "sellerType": supplier.get("sellerType", ""),
        "sellerTypeLabel": _SELLER_TYPE_MAP.get(supplier.get("sellerType", ""), ""),
        "factoryFlags": _build_factory_flags(flags),
        "certType": _safe_cert_type(supplier.get("certification")),
        "certReportUrl": _safe_cert_url(supplier.get("certification")),
        "shopUrl": supplier.get("shopUrl", ""),
        "rankText": (supplier.get("rank") or {}).get("text", ""),
        "sellerTierLabel": _trust_bar_label(flags),

        # 数据完整度信号（三层金字塔）
        "dataTier": _tier,
        "dataTierReason": _tier_reason,

        # 回头客 / 跨境买家
        "repeatBuyers": stats.get("repeatBuyers") or _raw_card_value(stats, "byrRepeatCustomer") or "",
        "crossBorderBuyers": stats.get("crossBorderBuyers") or _raw_card_value(stats, "kjByrNum90D") or "",

        # SKU + 阶梯价（供前端渲染）
        "skus": sku_list[:6] if sku_list else [],
        "price_tiers": price_tiers,
    }


# ---- 标签映射常量 ----

_SELLER_TYPE_MAP: dict[str, str] = {
    "yuantou_flagship": "源头旗舰",
    "shili_factory": "实力工厂",
    "super_factory": "超级工厂",
    "tp_factory": "通品工厂",
    "normal": "普通商家",
}

_FACTORY_FLAG_MAP: dict[str, str] = {
    "isFactory": "生产厂家",
    "isTpFactory": "通品工厂",
    "isShiliFactory": "实力工厂",
    "isSuperFactory": "超级工厂",
    "isYuantouFlagship": "源头旗舰",
    "isEaseBuyDealer": "工厂直供",
}

_BADGE_FLAG_MAP: dict[str, tuple[str, str]] = {
    # key → (label, css_class)
    "isFreeSample": ("免费拿样", "green"),
    "isBuyerProtection": ("买家保障", "gold"),
    "isCrossBorder": ("跨境专供", "blue"),
    "isWholesale": ("批发价", "green"),
    "isSupportMix": ("支持混批", "green"),
}

_SERVICE_BADGE_MAP: dict[str, str] = {
    "7天": "7天无理由退货",
    "退货": "7天无理由退货",
    "免费拿样": "免费拿样",
    "包邮": "包邮",
}


def _build_badge_labels(product_flags: dict[str, Any], service_labels: list[str]) -> list[dict[str, str]]:
    """从 productFlags + serviceLabels 构建 Badge 标签数组。"""
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for key, (label, cls) in _BADGE_FLAG_MAP.items():
        if product_flags.get(key) and label not in seen:
            result.append({"label": label, "class": cls})
            seen.add(label)
    for tag in service_labels:
        label = _SERVICE_BADGE_MAP.get(tag, tag)
        if label not in seen:
            result.append({"label": label, "class": "green"})
            seen.add(label)
    return result


def _trust_bar_label(flags: dict[str, Any]) -> str:
    """trust-bar 简化标签：isFactory=True→源头工厂, False→贸易商。

    详细等级（旗舰/超级/实力/普通）在工厂 Tab 展示。
    """
    return "源头工厂" if flags.get('isFactory') else "贸易商"


def _data_tier(flags: dict[str, Any], shop_years: Any) -> tuple[str, str]:
    """数据完整度信号：三层金字塔（认证 + 年限）。

    Returns:
        (tier, reason) — tier: "sufficient" | "partial" | "limited"
    """
    # 高级认证：平台花钱验证过的（超级工厂/实力工厂/源头旗舰等），不含自声称 isFactory
    has_advanced_cert: bool = bool(
        flags.get('isYuantouFlagship') or flags.get('isSuperFactory')
        or flags.get('isShiliFactory') or flags.get('isHyper')
        or flags.get('isChtMember')
    )
    is_factory: bool = bool(flags.get('isFactory'))
    years: float = float(shop_years) if shop_years else 0

    if has_advanced_cert and years >= 2:
        return 'sufficient', '平台验厂认证 + 经营 2 年以上 · 拿样风险低'
    elif has_advanced_cert:
        return 'partial', '有平台验厂认证，经营不足 2 年 · 建议验货'
    elif is_factory and years >= 1:
        return 'partial', '生产厂家，经营 1 年以上 · 建议拿样验证'
    elif years >= 1:
        return 'partial', '无工厂认证，经营 1 年以上 · 建议拿样验证'
    else:
        return 'limited', '无官方认证，经营不足 1 年 · 建议人工核实'


def _build_factory_flags(flags: dict[str, Any]) -> str:
    """从 supplier.flags 提取工厂实力描述文字。

    isFactory=False 时不输出工厂标签。
    """
    if not flags.get('isFactory'):
        return "非生产厂家"

    parts = []
    for key, label in _FACTORY_FLAG_MAP.items():
        if flags.get(key):
            parts.append(label)
    return " · ".join(parts) if parts else ""


def _safe_cert_type(cert: Any) -> str:
    if isinstance(cert, dict):
        return cert.get("type", "")
    return ""


def _safe_cert_url(cert: Any) -> str:
    if isinstance(cert, dict):
        return cert.get("reportUrl", "")
    return ""


def _extract_price_tiers(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """提取阶梯价格。Apify 返回格式：[{quantityMin, quantityMax, price}, ...]"""
    tiers: list[dict[str, Any]] = raw.get("quantityPrices") or raw.get("priceRanges") or raw.get("priceRange") or []
    result: list[dict[str, Any]] = []
    for t in tiers:
        result.append({
            "qty_min": t.get("quantityMin") or t.get("begin") or t.get("qty_min"),
            "qty_max": t.get("quantityMax") or t.get("end") or t.get("qty_max"),
            "unit_price": t.get("price") or t.get("unit_price"),
        })
    return result


def _filter_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """过滤关键规格（风险 #8：字段级容错）。"""
    KEYS = {"材质", "品牌", "颜色", "规格", "尺寸", "风格", "货号", "重量", "包装", "工艺", "类别", "骨架"}
    result: list[dict[str, str]] = []
    for s in specs:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name", "")).strip()
        value = str(s.get("value", "")).strip()
        if name in KEYS and value and value != "咨询客服" and len(value) < 30:
            result.append({"name": name, "value": value})
    result.sort(key=lambda x: 0 if x["name"] in ("材质", "工艺", "类别") else 1)
    return result[:8]


def _as_dict_list(val: Any) -> list[dict[str, Any]]:
    """类型收窄：Any → list[dict]。非列表时返回空列表。"""
    return cast(list[dict[str, Any]], val) if isinstance(val, list) else []


def _has_tag(tags: list[str], keyword: str) -> bool:
    return any(keyword in str(t) for t in tags)


def _parse_pct(val: Any) -> float | None:
    """解析百分比字段。支持 '95.3%' / 0.953 / 95.3 多种格式。"""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.replace("%", "").strip()
    try:
        v = float(val)
        return round(v * 100 if v < 1 else v, 1)
    except (ValueError, TypeError):
        return None


def _raw_card_value(stats: dict[str, Any], code: str) -> Any:
    """从 stats.rawCardDetail 数组中按 code 取值。"""
    for item in (stats.get('rawCardDetail') or []):
        if isinstance(item, dict) and item.get('code') == code:
            return item.get('value')
    return None


def _factory_tag_value(supplier: dict[str, Any], keyword: str) -> Any:
    """从 supplier.factoryTags 数组中按 text 关键词模糊匹配取值。"""
    for item in (supplier.get('factoryTags') or []):
        if isinstance(item, dict) and keyword in str(item.get('text', '')):
            return item.get('value')
    return None


def _industry_cluster(location: str) -> str:
    if not location:
        return ""
    MAP = {
        "义乌": "中国小商品集散中心", "广州": "服装/箱包/皮具产业带",
        "深圳": "3C 电子/跨境电商货源地", "晋江": "运动鞋服产业带",
        "南通": "家纺产业带", "泉州": "鞋服箱包产业带",
        "东莞": "电子/玩具/模具产业带", "佛山": "家具/陶瓷产业带",
        "杭州": "女装/电商供应链中心", "温州": "鞋革/五金/眼镜产业带",
        "宁波": "小家电/文具产业带", "绍兴": "纺织面料产业带",
        "澄海": "玩具产业带", "永康": "五金/杯壶产业带",
        "诸暨": "袜子/珍珠产业带", "潮州": "陶瓷/卫浴产业带",
    }
    for key, desc in MAP.items():
        if key in location:
            return desc
    return ""


def _get_expired_cache(offer_id: str) -> dict[str, Any] | None:
    """读取过期缓存（风险 #3 #7：超时/失败时的降级数据源）。"""
    entry = _cache_store.get(offer_id)
    if entry:
        return entry[1]
    return None
