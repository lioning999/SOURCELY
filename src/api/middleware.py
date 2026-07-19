"""JWT 认证中间件 — PROTECTED_PREFIXES + EXEMPT_PATHS 模式。"""

from typing import Awaitable, Callable
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.jwt import verify_access_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件。

    特性：
    - PROTECTED_PREFIXES: 需要认证的路径前缀
    - EXEMPT_PATHS: 保护前缀下的免认证路径
    - 认证成功 → 注入 request.state.user_id
    - 认证失败 → 返回 401 JSON
    """

    # TODO: 按项目实际路径修改
    PROTECTED_PREFIXES = ["/api/", "/admin/"]
    EXEMPT_PATHS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/analyze",
        "/docs",
        "/openapi.json",
        "/health",
    ]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ):
        path = request.url.path

        # 检查是否需要认证
        if self._needs_auth(path):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "data": None, "message": "缺少认证信息"},
                )

            token = auth_header.removeprefix("Bearer ")
            payload = verify_access_token(token)
            if payload is None:
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "data": None, "message": "token无效或已过期"},
                )

            # 注入用户身份
            request.state.user_id = payload.get("sub")

        return await call_next(request)

    def _needs_auth(self, path: str) -> bool:
        if path in self.EXEMPT_PATHS:
            return False
        return any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
