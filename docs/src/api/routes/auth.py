"""认证路由：微信 OAuth 登录 + JWT 签发 + 用户信息"""

from urllib.parse import quote, urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from adapters.wechat_auth import WechatAuthAdapter
from services.auth import AuthService
from repositories.members import MemberRepository
from models import TokenExchangeRequest
from config import Config
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ── 依赖注入 ──────────────────────────────────────
_wechat = WechatAuthAdapter(
    appid=Config.WECHAT_APPID,
    secret=Config.WECHAT_SECRET,
    login_url=Config.WECHAT_LOGIN_URL,
)
_auth_service = AuthService(wechat=_wechat)


@router.post("/exchange")
async def exchange(req: TokenExchangeRequest):
    """用微信授权码换取 JWT。不包装，直接返回 {access_token, token_type, ...}。"""
    result = await _auth_service.exchange_code(req.code)
    return result


@router.get("/info")
async def get_info(request: Request):
    """获取当前用户配额信息。需 JWT。"""
    openid = request.state.openid
    member = await MemberRepository.get_by_openid(openid)
    if not member:
        logger.error(f"AUTH_INFO_USER_NOT_FOUND openid={mask_openid(openid)}")
        return JSONResponse(
            status_code=404,
            content={"code": 404, "data": None, "message": "用户不存在"},
        )
    return {
        "preview_remain": member["preview_remain"],
        "optimize_remain": member["optimize_remain"],
    }


@router.get("/wechat-login")
async def wechat_login(request: Request):
    """重定向到微信 OAuth 授权页面。统一用公众号 snsapi_base，全场景兼容。"""
    redirect_uri = f"{Config.DOMAIN}/auth/callback/wechat"
    state = "login"

    wechat_url = (
        "https://open.weixin.qq.com/connect/oauth2/authorize"
        f"?appid={Config.WECHAT_APPID}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        f"&response_type=code"
        f"&scope=snsapi_base"
        f"&state={state}"
        "#wechat_redirect"
    )
    logger.info("AUTH_REDIRECT_TO_WECHAT")
    return RedirectResponse(url=wechat_url)


@router.get("/callback/wechat")
async def wechat_callback(code: str = "", state: str = ""):
    """微信 OAuth 回调——重定向到前端中转页完成 token 交换。"""
    params = urlencode({"code": code, "state": state})
    return RedirectResponse(url=f"/auth-callback.html?{params}")
