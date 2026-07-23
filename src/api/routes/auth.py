"""认证 API — Google OAuth 登录。"""

import json

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from adapters.google_auth import google_auth_adapter
from repositories.user_repo import UserRepository
from services.auth_svc import AuthService
from utils.exceptions import ExternalServiceError
from utils.logger import get_logger

logger = get_logger(__name__)

# ---- 依赖 ----
user_repo = UserRepository()
auth_service = AuthService(google_auth=google_auth_adapter, user_repo=user_repo)

# ---- 路由 ----
# /api/auth/* 路由（JWT 中间件豁免登录检查）
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# /google-callback 路由（无前缀，Google 回调固定路径）
callback_router = APIRouter(tags=["auth-callback"])


@auth_router.get("/google/login")
async def google_login():
    """跳转到 Google OAuth 授权页。"""
    url = google_auth_adapter.get_auth_url()
    return RedirectResponse(url=url, status_code=302)


@callback_router.get("/google-callback")
async def google_callback(code: str):
    """Google OAuth 回调。

    Google 授权后回调此端点，附带一次性 authorization code。
    后端用 code 换 id_token → upsert user → 签发 JWT → 重定向到首页。
    """
    try:
        result = await auth_service.login_with_google(code)
    except ExternalServiceError:
        # 登录失败 → 重定向到首页，前端不显示登录态
        return RedirectResponse(url="/", status_code=302)

    # 登录成功 → token 通过 URL hash 传给前端
    # 前端 checkAuth() 从 hash 读取并保存到 sessionStorage
    token = result["access_token"]
    user_json = json.dumps(result["user"])
    redirect_url = f"/?token={token}&user={user_json}"
    return RedirectResponse(url=redirect_url, status_code=302)
