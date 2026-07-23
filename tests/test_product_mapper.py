"""product_mapper 单元测试 — map_raw() + as_dict_list() 纯函数。

覆盖：正常映射、字段缺失容错、空输入、as_dict_list 类型收窄。
"""

import json
from pathlib import Path

import pytest

# 从项目根目录导入 domain 模块
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "api"))

from domain.product_mapper import map_raw, as_dict_list  # noqa: E402

# ---- 测试夹具 ----
FIXTURE_DIR = Path(__file__).resolve().parent


def _load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def apify_raw() -> dict:
    """真实 Apify 返回数据 — 蒲扇商品（源头旗舰 + SGS 认证）。"""
    return _load_fixture("apify_raw_sample.json")


# ====================================================================
# map_raw — 正常映射
# ====================================================================

def test_map_raw_basic_fields(apify_raw):
    """基本字段正确映射。"""
    result = map_raw(apify_raw, "https://detail.1688.com/offer/1038913113865.html", "1038913113865")

    assert result["title"], "title 不应为空"
    assert result["offerId"] == "1038913113865"
    assert result["priceCNY"] == {"low": 7.5, "high": 7.8}
    assert result["priceLow"] == pytest.approx(1.04, abs=0.1)   # 7.5 / 7.2
    assert result["priceHigh"] == pytest.approx(1.08, abs=0.1)  # 7.8 / 7.2
    assert result["moq"] == 2
    assert result["unit"] != ""
    assert result["sold"] == 4944
    assert result["images"]  # 至少 1 张图片


def test_map_raw_supplier_fields(apify_raw):
    """工厂/供应商字段正确提取。"""
    result = map_raw(apify_raw, "", "1038913113865")

    assert result["supplierName"], "公司名称不应为空"
    assert result["shop_years"] == 6
    assert result["sellerType"] == "yuantou_flagship"
    assert result["sellerTypeLabel"] == "源头旗舰"
    assert result["certType"], "认证类型不应为空"
    assert result["certReportUrl"], "认证报告 URL 不应为空"
    assert result["sellerTierLabel"] in ("源头工厂", "贸易商")


def test_map_raw_specs_and_skus(apify_raw):
    """规格 + SKU + 阶梯价正确提取。"""
    result = map_raw(apify_raw, "", "1038913113865")

    assert isinstance(result["specs"], list)
    assert len(result["specs"]) > 0
    for s in result["specs"]:
        assert "name" in s
        assert "value" in s

    assert isinstance(result["skus"], list)
    assert len(result["skus"]) <= 6  # 上限 6 个

    assert isinstance(result["price_tiers"], list)
    for t in result["price_tiers"]:
        assert "qty_min" in t
        assert "unit_price" in t


def test_map_raw_badge_labels(apify_raw):
    """Badge 标签数组格式正确。"""
    result = map_raw(apify_raw, "", "1038913113865")

    badges = result["badgeLabels"]
    assert isinstance(badges, list)
    for b in badges:
        assert "label" in b
        assert "class" in b
        assert b["class"] in ("green", "blue", "gold")


def test_map_raw_data_tier(apify_raw):
    """数据完整度信号输出。"""
    result = map_raw(apify_raw, "", "1038913113865")

    assert result["dataTier"] in ("sufficient", "partial", "limited")
    assert result["dataTierReason"]


# ====================================================================
# map_raw — 字段缺失容错（风险 #8）
# ====================================================================

def test_map_raw_empty_input():
    """空 dict 不崩溃，返回默认值。"""
    result = map_raw({}, "", "1234567890")

    assert result["title"] == ""
    assert result["priceCNY"] == {"low": 0, "high": 0}
    assert result["priceLow"] is None
    assert result["sold"] is None
    assert result["moq"] is None
    assert result["supplierName"] == ""
    assert result["sellerType"] == ""
    assert result["sellerTypeLabel"] == ""
    assert result["certType"] == ""
    assert result["images"] == []
    assert result["specs"] == []
    assert result["skus"] == []
    assert result["price_tiers"] == []
    assert result["badgeLabels"] == []


def test_map_raw_partial_supplier():
    """supplier 为空时工厂字段不崩溃。"""
    raw = {"title": "test", "price": {"min": 10}}
    result = map_raw(raw, "", "123")

    assert result["supplierName"] == ""
    assert result["shop_years"] is None
    assert result["factoryFlags"] == "非生产厂家"  # flags 为空 → isFactory 不存在 → 非生产厂家
    assert result["certType"] == ""
    assert result["dataTier"] == "limited"


def test_map_raw_missing_price():
    """price 为 None 时价格字段不崩溃。"""
    raw = {"title": "test", "price": None}
    result = map_raw(raw, "", "123")

    assert result["priceCNY"] == {"low": 0, "high": 0}


# ====================================================================
# as_dict_list — 类型收窄
# ====================================================================

def test_as_dict_list_with_list():
    assert as_dict_list([{"a": 1}]) == [{"a": 1}]


def test_as_dict_list_with_none():
    assert as_dict_list(None) == []


def test_as_dict_list_with_string():
    assert as_dict_list("not a list") == []


def test_as_dict_list_with_int():
    assert as_dict_list(42) == []
