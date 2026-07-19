"""JWT 工具 — 令牌生成 + 验证。"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

# TODO: 从 config.py 读取密钥和有效期
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT access token。

    Args:
        data: 要编码的数据（必须包含 sub 等标识字段）
        expires_delta: 过期时间，默认 24h

    Returns:
        encoded JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> Optional[dict[str, Any]]:
    """验证 JWT token。

    Args:
        token: Bearer token 字符串

    Returns:
        解码后的 payload，无效返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
