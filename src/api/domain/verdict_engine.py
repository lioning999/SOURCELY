"""V1 规则引擎 — 三层判词金字塔（L1 精确 + L2 区间 + L3 兜底）。

覆盖风险清单：
  #4  判词覆盖率不足 → 三层金字塔 L1+L2+L3，目标 80%
  #5  判词闪烁 → 滞回区间（Hysteresis）
  #6  核心字段缺失 → 检查字段存在性，缺字段降级 L3

判词文案从 verdict_templates.json 加载（风险 #14*：新增品类只需改配置，不动代码）。
"""

import json
from pathlib import Path
from typing import Any

# ---- 加载判词模板 ----
_TEMPLATES_PATH = Path(__file__).parent / "verdict_templates.json"
with open(_TEMPLATES_PATH, "r", encoding="utf-8") as _f:
    T = json.load(_f)

# ---- 滞回区间配置 ----
# 触发阈值 vs 回落阈值，防止阈值附近判词抖动
HYSTERESIS: dict[str, tuple[float, float]] = {
    "high_repurchase":  (0.70, 0.65),  # 触发 >70%, 回落 <65%
    "high_rate":        (0.95, 0.90),  # 触发 >95%, 回落 <90%
    "high_sales":       (5000, 3000),  # 触发 >5000, 回落 <3000
}


def _hysteresis_check(key: str, value: int | float) -> bool:
    """滞回区间检查：用触发阈值判断（回落阈值用于后续查询）。"""
    if key not in HYSTERESIS:
        return False
    trigger, _ = HYSTERESIS[key]
    return value > trigger


# ====================================================================
# 公开接口
# ====================================================================


def judge_product(data: dict[str, Any]) -> str:
    """产品维度的判词。

    依赖字段：moq, sold, return7day
    """
    L1 = T["product"]["L1"]
    L2 = T["product"]["L2_parts"]

    moq = data.get("moq")
    sold = data.get("sold")
    return_ok = data.get("return7day") == "OK"

    # L1 精确匹配
    if isinstance(moq, (int, float)) and isinstance(sold, (int, float)) and return_ok:
        if moq <= 5 and sold >= 1000:
            return L1["small_order_sales_return"]

    if isinstance(moq, (int, float)) and return_ok and moq <= 5:
        return L1["small_order_return"]

    # L2 区间匹配
    parts: list[str] = []

    if isinstance(sold, (int, float)):
        if _hysteresis_check("high_sales", sold):
            parts.append(L2["hot_sale"])
        elif sold >= 1000:
            parts.append(L2["good_sales"])

    if isinstance(moq, (int, float)):
        if moq <= 5:
            parts.append(L2["low_moq"])
        elif moq <= 20:
            parts.append(L2["mid_moq"])

    if return_ok:
        parts.append(L2["return_ok"])

    if parts:
        return " · ".join(parts)

    # L3 兜底
    return T["product"]["L3"]


def judge_factory(data: dict[str, Any]) -> str:
    """工厂维度的判词。

    依赖字段：shop_years, shop_rate, repurchase, flags
    """
    L1 = T["factory"]["L1"]
    L2 = T["factory"]["L2_parts"]

    years = data.get("shop_years")
    rate = data.get("shop_rate")
    rep = data.get("repurchase")
    flags: dict[str, Any] = data.get("flags", {}) or {}

    # L1: trader detection（sellerTierLabel="贸易商" → 非工厂，不输出工厂推荐）
    if data.get("sellerTierLabel") == "贸易商":
        return T["factory"]["L1"].get("agent_company", "贸易商，建议确认货源")

    # L1 精确匹配
    if isinstance(years, (int, float)) and isinstance(rate, (int, float)) and isinstance(rep, (int, float)):
        if years >= 5 and rate >= 95 and rep >= 70:
            return L1["trusted_old_shop"]

    if flags.get("isSuperFactory"):
        return L1["super_factory"]

    if isinstance(years, (int, float)) and isinstance(rate, (int, float)):
        if years >= 3 and rate >= 98:
            return L1["high_praise_old_shop"]

    # L2 区间匹配
    parts: list[str] = []

    if isinstance(years, (int, float)):
        if years >= 8:
            parts.append(L2["years_source_shop"].format(years=years))
        elif years >= 3:
            parts.append(L2["years_old_shop"].format(years=years))

    if isinstance(rate, (int, float)):
        if _hysteresis_check("high_rate", rate):
            parts.append(L2["rate_pct"].format(rate=rate))
        elif rate >= 95:
            parts.append(L2["rate_pct"].format(rate=rate))

    if isinstance(rep, (int, float)):
        if _hysteresis_check("high_repurchase", rep):
            parts.append(L2["repurchase_pct"].format(rep=rep))

    if flags.get("isFactory"):
        parts.append(L2["factory"])
    if flags.get("isChtMember"):
        parts.append(L2["cht_member"])

    if parts:
        return " · ".join(parts)

    # L3 兜底
    return T["factory"]["L3"]


def judge_sample(data: dict[str, Any]) -> str:
    """拿样维度的判词。

    依赖字段：moq, return7day, free_sample, delivery_days
    """
    L1 = T["sample"]["L1"]
    L2 = T["sample"]["L2_parts"]

    moq = data.get("moq")
    return_ok = data.get("return7day") == "OK"
    free_sample = data.get("freeSample", False)
    delivery = data.get("deliveryDays")

    # L1
    if isinstance(moq, (int, float)) and return_ok and moq <= 5:
        return L1["small_order_no_risk"]

    if free_sample:
        return L1["free_sample"]

    # L2
    parts: list[str] = []

    if isinstance(moq, (int, float)):
        if moq <= 5:
            parts.append(L2["low_barrier_sample"])
        elif moq <= 20:
            parts.append(L2["small_order_trial"])

    if isinstance(delivery, (int, float)) and delivery <= 2:
        parts.append(L2["flash_delivery"])

    if return_ok:
        parts.append(L2["return_ok"])

    if parts:
        return " · ".join(parts)

    # L3
    return T["sample"]["L3"]


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
