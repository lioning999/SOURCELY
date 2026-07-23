"""微信 OAuth 登录 API 封装。

职责：纯 HTTP 调用 — 用 code 换 openid。
禁止：业务逻辑、数据库操作、FastAPI 类型依赖。
"""

import json
from typing import Any

import aiohttp

from utils.exceptions import ExternalServiceError
from utils.logger import get_logger

logger = get_logger(__name__)


class WechatAuthAdapter:
    """微信 OAuth 2.0 适配器。

    Usage:
        adapter = WechatAuthAdapter(appid="...", secret="...")
        openid = await adapter.exchange_code("auth_code_xxx")
    """

    def __init__(self, appid: str, secret: str, login_url: str):
        self.appid = appid
        self.secret = secret
        self.login_url = login_url

    async def exchange_code(self, code: str) -> str:
        """用授权码换取 openid。

        Raises:
            ExternalServiceError: 微信 API 调用失败
        """
        params = {
            "appid": self.appid,
            "secret": self.secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.login_url, params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    content = await resp.read()
                    try:
                        data: dict[str, Any] = json.loads(content.decode("utf-8"))
                    except json.JSONDecodeError:
                        raise ExternalServiceError(
                            service_name="微信登录",
                            details={"error": "接口返回格式错误"},
                        )

                    if "openid" not in data:
                        error_msg = data.get(
                            "errmsg",
                            data.get("error_description", "未知错误"),
                        )
                        raise ExternalServiceError(
                            service_name="微信登录",
                            details={"wechat_error": error_msg},
                        )

                    return data["openid"]

        except aiohttp.ClientError as e:
            raise ExternalServiceError(
                service_name="微信登录",
                details={"network_error": str(e)},
            ) from e
