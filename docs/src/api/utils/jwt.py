"""JWT 令牌生成、验证与吊销。

生产上线前审计 (TODO-PRODUCTION):
  [ ] HS256 → RS256/ES256 非对称密钥（密钥轮换不中断服务）
  [ ] 有效期从 24h 缩短到 2h + refresh token 机制
  [ ] jti 黑名单从内存 → Redis SET（多进程共享 + 持久化）
  [ ] 加 issuer/audience claims 防跨服务滥用
  [ ] 密钥轮换策略（kid header + JWKS endpoint）
  [ ] 登录限流从内存 → Redis（多节点共享计数）
  [ ] access_token 从 sessionStorage → httpOnly cookie（防 XSS）
"""

import uuid
import time
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from .logger import get_logger, mask_openid, mask_token
from config import Config

SECRET_KEY = Config.JWT_SECRET_KEY
ALGORITHM = Config.JWT_ALGORITHM

logger = get_logger(__name__)

logger.info(f"JWT_UTILS_INIT SECRET_KEY={SECRET_KEY[:10]}... ALGORITHM={ALGORITHM} SECRET_KEY_exists={SECRET_KEY is not None}")

# ── Token 黑名单（内存，进程重启清空，上线前迁 Redis）──
# key: jti (JWT ID), value: 过期时间戳（过期后自动清理）
_revoked_tokens: dict[str, float] = {}


def _cleanup_revoked() -> None:
    """清理已过期的黑名单条目。"""
    now = time.time()
    expired = [jti for jti, exp in _revoked_tokens.items() if exp < now]
    for jti in expired:
        del _revoked_tokens[jti]


def revoke_token(jti: str, ttl_seconds: int = 86400) -> None:
    """吊销指定 jti 的 token（加入黑名单）。

    黑名单条目在 token 原定过期时间后自动清理。
    """
    _revoked_tokens[jti] = time.time() + ttl_seconds
    _cleanup_revoked()
    logger.info(f"JWT_REVOKED jti={jti[:8]}...")


def is_token_revoked(jti: str) -> bool:
    """检查 token 是否已被吊销。"""
    _cleanup_revoked()
    return jti in _revoked_tokens


def create_jwt(openid: str, expires_minutes: int = 1440) -> str:
    logger.info(f"JWT_CREATE_START openid={mask_openid(openid)} expires={expires_minutes}min")
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": openid,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": uuid.uuid4().hex,  # 唯一 token ID，用于吊销
    }
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"JWT_CREATE_SUCCESS openid={mask_openid(openid)} token_length={len(encoded_jwt)}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"JWT_CREATE_ERROR openid={mask_openid(openid)} error={str(e)}")
        raise


def verify_jwt(token: str) -> str:
    """验证 JWT 签名 + 过期 + 吊销状态。返回 openid。"""
    logger.debug(f"JWT_VERIFY_START token_length={len(token)} token_prefix={mask_token(token)}")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        openid = payload.get("sub") or payload.get("openid")
        if openid is None:
            logger.error("JWT_VERIFY_ERROR missing_sub_field")
            raise JWTError("无效的令牌：载荷中无用户标识")

        # 检查吊销
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            logger.warning(f"JWT_REVOKED_TOKEN jti={jti[:8]}... openid={mask_openid(openid)}")
            raise JWTError("令牌已被吊销")

        logger.debug(f"JWT_VERIFY_SUCCESS openid={mask_openid(openid)}")
        return openid
    except JWTError as e:
        logger.error(f"JWT_VERIFY_ERROR error={str(e)} token_prefix={mask_token(token)}")
        raise JWTError(f"令牌验证失败：{str(e)}")
    except Exception as e:
        logger.error(f"JWT_VERIFY_UNKNOWN_ERROR error={str(e)} token_prefix={mask_token(token)}")
        raise


def decode_jwt_payload(token: str) -> dict | None:
    """解码 JWT payload（不验证签名），用于获取 jti 等信息。"""
    try:
        # 不验证签名，仅解析 payload
        return jwt.get_unverified_claims(token)
    except Exception:
        return None


