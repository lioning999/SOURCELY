"""认证服务 — 微信 OAuth 登录 + JWT 签发"""

from adapters.wechat_auth import WechatAuthAdapter
from repositories.members import MemberRepository
from utils.jwt import create_jwt
from utils.exceptions import ExternalServiceError, ValidationError
from utils.logger import get_logger, mask_openid
from config import Config

logger = get_logger(__name__)


class AuthService:
    """微信登录 → 用户初始化 → JWT 签发。"""

    def __init__(self, wechat: WechatAuthAdapter):
        self.wechat = wechat

    async def exchange_code(self, code: str) -> dict:
        """用微信授权码换取 JWT token。

        TEST_MODE: code 以 test_ 开头 → openid = mock_openid_{code[5:]}
        生产模式: 调微信 API 换 openid
        """
        if not code or not code.strip():
            raise ValidationError(message="授权码不能为空")

        # ── 获取 openid ──────────────────────
        if Config.TEST_MODE and code.startswith("test_"):
            openid = f"mock_openid_{code[5:]}"
            logger.info(f"AUTH_MOCK openid={mask_openid(openid)}")
        else:
            try:
                openid = await self.wechat.exchange_code(code)
            except ExternalServiceError:
                raise  # Adapter 已包装，原样透传
            except Exception:
                raise ExternalServiceError(service_name="微信登录")
            logger.info(f"AUTH_WECHAT openid={mask_openid(openid)}")

        # ── 初始化用户（幂等）─────────────────
        await MemberRepository.init_member(openid)

        # ── 查配额 ──────────────────────────
        member = await MemberRepository.get_by_openid(openid)
        preview_remain = member["preview_remain"] if member else 0
        optimize_remain = member["optimize_remain"] if member else 0

        # ── 签发 JWT ────────────────────────
        token = create_jwt(openid)
        logger.info(f"AUTH_JWT_ISSUED openid={mask_openid(openid)}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "preview_remain": preview_remain,
            "optimize_remain": optimize_remain,
        }
