"""V1.1 规则引擎 — 判词改直接建议，不给数据摘要。

判词文案从 verdict_templates.json 加载。

⚠️ 同步铁律：本文件的 judge_product() / judge_factory() 判断条件 + 关键数据
   必须与 src/web/static/js/pages/report.js 的 buildProductVerdict() /
   buildFactoryVerdict() 完全一致。改任何一处，必须同步改另一处。
   验证方式：grep 两端 hasCert / isAdvanced / isFactory / isTrader 判断条件是否一致。
"""

import json
from pathlib import Path
from typing import Any, cast

# ---- 加载判词模板 ----
_TEMPLATES_PATH = Path(__file__).parent / "verdict_templates.json"
with open(_TEMPLATES_PATH, "r", encoding="utf-8") as _f:
    T = json.load(_f)


# ====================================================================
# 公开接口
# ====================================================================


def judge_product(data: dict[str, Any]) -> str:
    """产品维度的判词（V1.1 改直接建议，不给数据摘要）。

    依赖字段：certType, sold, return7day, priceCNY.low, moq, unit
    注：前端 report.js 的 buildProductVerdict() 以相同逻辑覆盖此值。
    """
    L1 = T["product"]["L1"]

    cert = data.get("certType")
    sold = data.get("sold", 0)
    return_ok = data.get("return7day") == "OK"
    price_cny_raw: Any = data.get("priceCNY") or {}
    price_cny: dict[str, Any] = cast(dict[str, Any], price_cny_raw) if isinstance(price_cny_raw, dict) else {}  # type: ignore[reportUnnecessaryIsInstance]
    price: Any = price_cny.get("low", 0)  # type: ignore[reportUnknownMemberType]
    moq = data.get("moq", 2)
    unit = data.get("unit", "件")
    deposit = int(float(price) * int(moq) + 10)

    has_cert = bool(cert and cert != "null")
    sold_str = f"{sold/1000:.1f}k+" if sold >= 1000 else str(sold)

    if has_cert and sold >= 1000 and return_ok:
        return L1["recommend_sample"].format(price=price, moq=moq, unit=unit, sold=sold_str)
    if has_cert and sold >= 100:
        return L1["consider"].format(price=price, moq=moq, unit=unit, sold=sold_str)
    if not has_cert and sold >= 500:
        return L1["no_cert"].format(sold=sold_str, deposit=deposit)
    return L1["insufficient_data"].format(deposit=deposit)


def judge_factory(data: dict[str, Any]) -> str:
    """工厂维度的判词（V1.1 改直接建议）。

    依赖字段：shop_years, certType, sellerType, factoryFlags
    注：前端 report.js 的 buildFactoryVerdict() 以相同逻辑覆盖此值。
    """
    L1 = T["factory"]["L1"]

    years = data.get("shop_years", 0) or 0
    cert = data.get("certType")
    has_cert = bool(cert and cert != "null")
    cert_name: str = str(cert).upper() if has_cert else ""
    flags: str = str(data.get("factoryFlags", "")) if data.get("factoryFlags") else ""

    # 高级认证
    is_advanced = data.get("sellerType") in ("super_factory", "flagship") \
        or any(kw in flags for kw in ("超级工厂", "源头旗舰", "实力工厂"))
    # 生产厂家
    is_factory = "非生产厂家" not in flags and \
        ("生产厂家" in flags or data.get("sellerType") in ("normal_factory", "super_factory"))
    # 贸易商
    is_trader = "非生产厂家" in flags

    if is_advanced and years >= 3:
        return L1["reliable"].format(years=years, cert=cert_name)
    if is_factory and has_cert:
        return L1["cooperative"].format(years=years)
    if is_factory and not has_cert:
        return L1["self_claimed"]
    if is_trader:
        return L1["trader"]
    return L1["insufficient"]


def judge_sample(data: dict[str, Any]) -> str:
    """拿样维度的判词 — 统一为两段付款流程。

    依赖字段：无特殊要求，所有商品走同一流程。
    """
    return T["sample"]["L1"]["two_payment"]


def judge_all(data: dict[str, Any]) -> dict[str, str]:
    """一次调用，返回三个维度的判词。

    Args:
        data: Apify 映射后的标准化数据，包含 moq, sold, shop_years, shop_rate,
              repurchase, return7day, flags, deliveryDays, freeSample 等字段

    Returns:
        {"product": "...", "factory": "...", "sample": "..."}
    """
    return {
        "product": judge_product(data),
        "factory": judge_factory(data),
        "sample":  judge_sample(data),
    }
