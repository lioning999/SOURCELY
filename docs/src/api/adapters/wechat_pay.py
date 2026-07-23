"""微信支付 API v3 封装 — Native 扫码支付 + 回调验签。

职责：封装 WeChatPay SDK 的初始化和调用，对外暴露 create_native_order / verify_callback。
禁止：业务逻辑、数据库操作、FastAPI 类型依赖。
"""

import json
from typing import Optional

from wechatpayv3 import WeChatPay, WeChatPayType

from config import Config
from utils.logger import get_logger

logger = get_logger("wechat_pay")


class WeChatPayAdapter:
    """微信支付 API v3 Adapter — 封装 wechatpayv3 SDK。

    Usage:
        pay = WeChatPayAdapter()
        code_url = pay.create_native_order("简历优化套餐1：1次", "ORDERxxx", 990)
        result = pay.verify_callback(headers, body)
    """

    def __init__(self):
        with open(Config.WXPAY_PRIVATE_KEY_PATH, "r") as f:
            private_key = f.read()

        with open(Config.WXPAY_PUBLIC_KEY_PATH, "r") as f:
            public_key = f.read()

        self._client = WeChatPay(
            wechatpay_type=WeChatPayType.NATIVE,
            mchid=Config.WECHAT_PAY_MCH_ID,
            private_key=private_key,
            cert_serial_no=Config.WXPAY_CERT_SERIAL_NO,
            apiv3_key=Config.WXPAY_APIV3_KEY,
            appid=Config.WECHAT_PAY_APPID,
            notify_url=Config.WECHAT_PAY_NOTIFY_URL,
            logger=logger,
            partner_mode=False,
            proxy=None,
            timeout=(10, 30),
            public_key=public_key,
            public_key_id=Config.WXPAY_PUBLIC_KEY_ID,
        )

    def create_native_order(self, description: str, out_trade_no: str, amount: int) -> str:
        """创建 Native 支付订单，返回 code_url（二维码链接）。

        Args:
            description: 商品描述，如 "简历优化套餐1：1次"
            out_trade_no: 商户订单号，≤32 字符
            amount: 金额（分），如 990 = ¥9.90

        Returns:
            二维码链接（code_url），前端渲染为扫码支付二维码

        Raises:
            RuntimeError: 微信 API 返回非 200
        """
        code, message = self._client.pay(
            description=description,
            out_trade_no=out_trade_no,
            amount={"total": amount},
            pay_type=WeChatPayType.NATIVE,
        )
        if code != 200:
            logger.error(f"WECHAT_PAY_ORDER_FAILED code={code} message={message}")
            raise RuntimeError(f"微信下单失败: {message}")

        resp = json.loads(message)
        code_url = resp.get("code_url")
        logger.info(f"WECHAT_PAY_ORDER_CREATED out_trade_no={out_trade_no} amount={amount}")
        return code_url

    def verify_callback(self, headers: dict, body: bytes) -> Optional[dict]:
        """验签 + AES-GCM 解密回调数据。

        Args:
            headers: 请求头 dict，需包含 Wechatpay-Signature 等字段
            body: 回调请求体 bytes

        Returns:
            解密后的交易数据 dict，验签失败返回 None
        """
        # 构建 SDK 要求的 headers dict（大小写不敏感，但 key 需精确匹配 SDK 预期）
        sdk_headers = {
            "Wechatpay-Signature": str(headers.get("wechatpay-signature", "")),
            "Wechatpay-Signature-Type": str(headers.get("wechatpay-signature-type", "")),
            "Wechatpay-Nonce": str(headers.get("wechatpay-nonce", "")),
            "Wechatpay-Timestamp": str(headers.get("wechatpay-timestamp", "")),
            "Wechatpay-Serial": str(headers.get("wechatpay-serial", "")),
        }

        result = self._client.callback(sdk_headers, body)
        if result is None:
            logger.error("WECHAT_PAY_CALLBACK_VERIFY_FAILED")
            return None

        if isinstance(result, bytes):
            result = json.loads(result.decode("utf-8"))

        if not isinstance(result, dict):
            logger.error(f"WECHAT_PAY_CALLBACK_UNEXPECTED_TYPE type={type(result)}")
            return None

        return result
