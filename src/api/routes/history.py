"""历史记录 API — 登录用户查看过往分析记录（只读 DB，不调 Apify）。"""

from typing import Any

from fastapi import APIRouter, Request

from services.analyze_svc import analyze_service
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["history"])


@router.get("/api/history")
async def list_history(request: Request) -> dict[str, Any]:
    """返回当前用户最近 20 条分析记录。

    需 JWT 认证（/api/ 前缀自动拦截）。
    只读 analysis 表，不调任何外部服务。
    """
    user_id: int = getattr(request.state, "user_id", 0) or 0
    if not user_id:
        return {"code": 401, "data": None, "message": "请先登录"}

    items = await analyze_service.get_history(user_id)
    return {"code": 200, "data": {"items": items}, "message": "ok"}
