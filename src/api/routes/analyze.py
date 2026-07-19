"""1688 商品分析 API — 接收 1688 链接，返回分析数据。"""

import re
import time
from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator
from config import Config
from services.analyze_service import analyze_service
from utils.exceptions import ValidationError, InsufficientQuotaError
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 简单内存计数器（按 IP）
_daily_counter: dict[str, tuple[int, float]] = {}  # {ip: (count, first_request_ts)}


class AnalyzeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def must_be_1688_detail(cls, v: str) -> str:
        if not re.search(r"1688\.com/offer/\d{8,}", v):
            raise ValueError("请输入有效的 1688 商品链接（detail.1688.com/offer/...）")
        return v.strip()


@router.post("/api/analyze")
async def analyze_product(body: AnalyzeRequest, request: Request):
    """分析 1688 商品。

    流程：
    1. 提取 offerId
    2. 检查每日配额（Demo: 每 IP 3 次/天）
    3. 调 Apify 抓取并映射
    4. 返回标准化数据
    """
    # ---- 0. 提取 offerId ----
    offer_id_match = re.search(r"offer/(\d+)", body.url)
    offer_id = offer_id_match.group(1) if offer_id_match else None

    # ---- 1. 每日配额检查 ----
    ip = request.client.host if request.client else "unknown"
    if not _check_quota(ip):
        raise InsufficientQuotaError(
            resource_type="今日免费分析次数",
            details={
                "daily_limit": Config.APIFY_DAILY_FREE_LIMIT,
                "whatsapp": "+86 138-xxxx-xxxx",
            },
        )

    # ---- 2. 调用分析服务 ----
    t0 = time.time()
    try:
        data = await analyze_service.analyze(body.url)
    except Exception:
        logger.exception(f"Analyze failed for {body.url}")
        raise

    elapsed = time.time() - t0
    logger.info(f"Analyzed {offer_id} in {elapsed:.1f}s")

    return {
        "code": 200,
        "data": data,
        "message": "ok",
        "meta": {"offerId": offer_id, "elapsed": f"{elapsed:.1f}s"},
    }


def _check_quota(ip: str) -> bool:
    """检查 IP 是否在每日配额内。超过限制返回 False。"""
    now = time.time()
    entry = _daily_counter.get(ip)

    # 无记录或已过 24h → 重置
    if entry is None or (now - entry[1]) > 86400:
        _daily_counter[ip] = (1, now)
        return True

    count, first_ts = entry
    if count >= Config.APIFY_DAILY_FREE_LIMIT:
        return False

    _daily_counter[ip] = (count + 1, first_ts)
    return True
