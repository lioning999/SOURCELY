"""JWT 认证中间件 — 对 /resume/ /pay/ /auth/ 前缀强制认证（auth 公共路径豁免）"""

from fastapi import Request
from fastapi.responses import JSONResponse
from utils.jwt import verify_jwt
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)

# 需 JWT 认证的路径前缀
PROTECTED_PREFIXES = ["/resume/", "/pay/", "/auth/"]

# 在这些前缀下但免认证的路径
EXEMPT_PATHS = [
    "/pay/notify",
    "/auth/exchange",
    "/auth/wechat-login",
    "/auth/callback/wechat",
]


async def jwt_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path

    # 只对受保护前缀强制 JWT
    needs_auth = any(path.startswith(p) for p in PROTECTED_PREFIXES)
    if not needs_auth:
        return await call_next(request)

    # 受保护前缀下的免认证路径
    if any(path.startswith(p) for p in EXEMPT_PATHS):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "data": None, "message": "未提供认证令牌"},
        )

    try:
        scheme, token = auth_header.split(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except (ValueError, AttributeError):
        return JSONResponse(
            status_code=401,
            content={"code": 401, "data": None, "message": "无效的认证头格式"},
        )

    try:
        openid = verify_jwt(token)
        request.state.openid = openid
        return await call_next(request)
    except Exception as e:
        logger.warning(f"JWT_AUTH_FAIL path={path} error={type(e).__name__}")
        return JSONResponse(
            status_code=401,
            content={"code": 401, "data": None, "message": "认证失败，请重新登录"},
        )
