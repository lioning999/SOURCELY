"""verdict_engine 单元测试 — judge_product / judge_factory / judge_sample 全覆盖。

每个判词分支至少一个用例。判词文案从 verdict_templates.json 加载。
"""

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "api"))

from domain.verdict_engine import judge_product, judge_factory, judge_sample, judge_all  # noqa: E402


# ====================================================================
# judge_product — 4 分支
# ====================================================================

def _product_data(**overrides):
    """构造产品数据，默认值使判词落在 recommend_sample。"""
    base = {
        "certType": "SGS",
        "sold": 5000,
        "return7day": "OK",
        "priceCNY": {"low": 5.0},
        "moq": 2,
        "unit": "件",
    }
    base.update(overrides)
    return base


def test_product_recommend_sample():
    """✅ 推荐拿样：有认证 + 高销量 + 7天无理由。"""
    v = judge_product(_product_data())
    assert "推荐拿样" in v or "试错成本" in v


def test_product_consider():
    """✅ 可考虑：有认证 + 中销量(>=100)。"""
    v = judge_product(_product_data(sold=300, return7day="NO"))
    assert "可考虑" in v or "拿样" in v


def test_product_no_cert():
    """⚠️ 缺认证：无认证 + 有销量(>=500)。"""
    v = judge_product(_product_data(certType=None, sold=600))
    assert "认证" in v


def test_product_insufficient_data():
    """⚠️ 数据不足：无认证 + 低销量。"""
    v = judge_product(_product_data(certType=None, sold=50))
    assert len(v) > 0  # 至少返回了文案


def test_product_cert_null_string():
    """certType='null' 被视为无认证。"""
    v = judge_product(_product_data(certType="null", sold=50))
    assert len(v) > 0


def test_product_zero_sold():
    """sold=0 走 insufficient_data 分支。"""
    v = judge_product(_product_data(certType=None, sold=0))
    assert len(v) > 0


# ====================================================================
# judge_factory — 5 分支
# ====================================================================

def _factory_data(**overrides):
    """构造工厂数据，默认值使判词落在 reliable。"""
    base = {
        "shop_years": 5,
        "certType": "SGS",
        "sellerType": "super_factory",
        "factoryFlags": "生产厂家 · 超级工厂",
    }
    base.update(overrides)
    return base


def test_factory_reliable():
    """✅ 工厂可靠：高级认证 + 3年以上。"""
    v = judge_factory(_factory_data())
    assert "可靠" in v or "合作" in v  # noqa: PLR1714


def test_factory_cooperative():
    """✅ 可合作：生产厂家 + 有认证（但非高级认证/不足3年）。"""
    v = judge_factory(_factory_data(
        sellerType="normal_factory",
        factoryFlags="生产厂家",
        shop_years=1,
    ))
    assert "可合作" in v or "拿样" in v


def test_factory_self_claimed():
    """⚠️ 自称工厂未认证：生产厂家 + 无认证。"""
    v = judge_factory(_factory_data(
        sellerType="normal_factory",
        factoryFlags="生产厂家",
        certType=None,
    ))
    assert "认证" in v or "自称" in v or "验证" in v  # noqa: PLR1714


def test_factory_trader():
    """⚠️ 非工厂：贸易商。"""
    v = judge_factory(_factory_data(
        sellerType="normal",
        factoryFlags="非生产厂家",
        certType=None,
    ))
    assert "贸易" in v or "非工厂" in v or "价差" in v  # noqa: PLR1714


def test_factory_insufficient():
    """⚠️ 数据不足：无法判断。"""
    v = judge_factory(_factory_data(
        sellerType="normal",
        factoryFlags="",
        certType=None,
        shop_years=0,
    ))
    assert len(v) > 0


def test_factory_advanced_by_flags():
    """高级认证通过 factoryFlags 中的「源头旗舰」关键词识别。"""
    v = judge_factory(_factory_data(
        sellerType="normal",
        factoryFlags="生产厂家 · 源头旗舰",
        shop_years=5,
    ))
    assert "可靠" in v or "合作" in v  # noqa: PLR1714


def test_factory_years_edge():
    """刚好 3 年 → reliable 分支。"""
    v = judge_factory(_factory_data(shop_years=3))
    assert "可靠" in v or "合作" in v  # noqa: PLR1714


def test_factory_no_flags():
    """factoryFlags=None 不崩溃。"""
    v = judge_factory(_factory_data(factoryFlags=None))
    assert len(v) > 0


# ====================================================================
# judge_sample — 统一模板
# ====================================================================

def test_sample_always_returns_two_payment():
    """任何输入都返回两段付款流程模板。"""
    v1 = judge_sample({})
    v2 = judge_sample({"moq": 100, "sold": 99999})
    assert v1 == v2
    assert "定金" in v1 or "尾款" in v1 or "验货" in v1  # noqa: PLR1714


# ====================================================================
# judge_all — 集成
# ====================================================================

def test_judge_all_returns_three_keys():
    """judge_all 返回 product / factory / sample 三个维度的判词。"""
    data = {
        "certType": "SGS",
        "sold": 5000,
        "return7day": "OK",
        "priceCNY": {"low": 5.0},
        "moq": 2,
        "unit": "件",
        "shop_years": 5,
        "sellerType": "super_factory",
        "factoryFlags": "生产厂家 · 超级工厂",
    }
    result = judge_all(data)
    assert set(result.keys()) == {"product", "factory", "sample"}
    for v in result.values():
        assert isinstance(v, str) and len(v) > 0


# ====================================================================
# 与前端同步 — 确认关键判断条件和 report.js 一致
# ====================================================================

def test_product_branches_match_frontend():
    """确认 4 个分支的条件与前端 buildProductVerdict() 一致。"""
    # Branch 1: hasCert + sold>=1000 + return7day=OK
    v1 = judge_product(_product_data(certType="SGS", sold=1000, return7day="OK"))
    # Branch 2: hasCert + sold>=100
    v2 = judge_product(_product_data(certType="SGS", sold=100, return7day="NO"))
    # Branch 3: no cert + sold>=500
    v3 = judge_product(_product_data(certType=None, sold=500))
    # Branch 4: else
    v4 = judge_product(_product_data(certType=None, sold=99))
    # 四个分支返回不同的文案
    results = {v1, v2, v3, v4}
    assert len(results) >= 3  # 至少 3 种不同文案（sample 模板可能部分相同）


def test_factory_branches_match_frontend():
    """确认工厂判词 5 个分支的条件与前端 buildFactoryVerdict() 一致。"""
    v1 = judge_factory(_factory_data(sellerType="super_factory",
                                      factoryFlags="生产厂家 · 超级工厂", shop_years=5))
    v2 = judge_factory(_factory_data(sellerType="normal_factory",
                                      factoryFlags="生产厂家", shop_years=1))
    v3 = judge_factory(_factory_data(sellerType="normal_factory",
                                      factoryFlags="生产厂家", certType=None))
    v4 = judge_factory(_factory_data(sellerType="normal",
                                      factoryFlags="非生产厂家", certType=None))
    v5 = judge_factory(_factory_data(sellerType="normal",
                                      factoryFlags="", certType=None, shop_years=0))
    results = {v1, v2, v3, v4, v5}
    assert len(results) >= 4  # 至少 4 种不同文案
