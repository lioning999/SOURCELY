"""支付服务：订单创建 + 微信支付回调 + 诊断按次付费标记。

职责：支付业务编排——创建订单、处理回调、标记诊断已付。
禁止：直接处理 HTTP Request 对象、手写 SQL、手管连接。
"""

import hashlib
import time
import uuid

from adapters.wechat_pay import WeChatPayAdapter
from repositories.orders import OrderRepository
from repositories.diagnoses import DiagnosisRepository
from utils.exceptions import (
    AppError,
    ExternalServiceError,
    ValidationError,
)
from utils.logger import get_logger, mask_openid
from config import Config

logger = get_logger("payment")

# 套餐定义：plan → {price, times, description}
PLANS = {
    1: {
        "price": Config.PLAN_1_PRICE,
        "times": Config.PLAN_1_TIMES,
        "description": "AI 简历优化 — 全流程通关",
    },
}


class PaymentService:
    """支付编排。注入 WeChatPayAdapter（依赖注入）。"""

    def __init__(self, pay_adapter: WeChatPayAdapter):
        self.pay = pay_adapter

    async def create_order(self, openid: str, plan: int,
                           diagnosis_id: str | None = None) -> dict:
        """创建支付订单。

        Args:
            openid: 用户 openid
            plan: 套餐类型 1=体验装
            diagnosis_id: 关联的诊断 ID（用于支付回调标记 is_paid）

        Returns:
            {qr_code_url, out_trade_no, amount, plan}

        Raises:
            ValidationError: 无效套餐
            ExternalServiceError: 微信下单失败
        """
        if plan not in PLANS:
            raise ValidationError(message=f"无效套餐: {plan}")

        plan_info = PLANS[plan]
        amount = plan_info["price"]
        times = plan_info["times"]
        description = plan_info["description"]

        # 生成订单号：ORDER + openid_hash8 + timestamp + 6randomhex，≤32 字符
        openid_hash = hashlib.md5(openid.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        random_suffix = uuid.uuid4().hex[:6]
        out_trade_no = f"ORDER{openid_hash}{timestamp}{random_suffix}"
        if len(out_trade_no) > 32:
            out_trade_no = out_trade_no[:32]

        logger.info(
            f"PAYMENT_CREATE_ORDER openid={mask_openid(openid)} "
            f"plan={plan} amount={amount} times={times}"
        )

        # ① 微信下单
        try:
            code_url = self.pay.create_native_order(
                description=description,
                out_trade_no=out_trade_no,
                amount=amount,
            )
        except AppError:
            raise  # Adapter 已包装，原样透传
        except Exception as e:
            logger.error(f"PAYMENT_WECHAT_ORDER_FAILED {e}")
            raise ExternalServiceError(service_name="微信支付下单") from e

        # ② 本地记录订单
        await OrderRepository.create(
            openid=openid,
            out_trade_no=out_trade_no,
            plan=plan,
            amount=amount,
            times=times,
            diagnosis_id=diagnosis_id,
        )

        logger.info(
            f"PAYMENT_ORDER_CREATED out_trade_no={out_trade_no} "
            f"openid={mask_openid(openid)} plan={plan}"
        )

        return {
            "qr_code_url": code_url,
            "out_trade_no": out_trade_no,
            "amount": amount,
            "plan": plan,
        }

    async def process_callback(self, headers: dict, body: bytes) -> bool:
        """处理微信支付回调。

        1. 验签 + 解密
        2. 过滤非支付成功事件
        3. 更新订单状态 + 发放优化次数（事务内）

        Returns:
            True=处理成功，False=验签失败
        """
        try:
            result = self.pay.verify_callback(headers, body)
            if result is None:
                logger.error("PAYMENT_CALLBACK_VERIFY_FAILED")
                return False

            event_type = result.get("event_type", "")
            if event_type != "TRANSACTION.SUCCESS":
                logger.info(f"PAYMENT_CALLBACK_IGNORED event_type={event_type}")
                return True  # 非支付成功事件，不重试

            resource = result.get("resource", {})
            out_trade_no = resource.get("out_trade_no")
            transaction_id = resource.get("transaction_id")

            if not out_trade_no or not transaction_id:
                logger.error(
                    f"PAYMENT_CALLBACK_MISSING_FIELDS "
                    f"out_trade_no={out_trade_no} transaction_id={transaction_id}"
                )
                return False

            logger.info(
                f"PAYMENT_CALLBACK_SUCCESS out_trade_no={out_trade_no} "
                f"transaction_id={transaction_id}"
            )

            # 事务内：标记订单已支付 + 发放次数
            paid = await OrderRepository.mark_paid(out_trade_no, transaction_id)

            if paid is None:
                # 幂等：同 transaction_id 已处理过
                logger.info(
                    f"PAYMENT_IDEMPOTENT out_trade_no={out_trade_no}"
                )
                return True

            # 标记关联诊断已付费（按次付费模型）
            diagnosis_id = paid.get("diagnosis_id")
            if diagnosis_id:
                await DiagnosisRepository.mark_paid(diagnosis_id, paid["openid"])

            logger.info(
                f"PAYMENT_DONE out_trade_no={out_trade_no} "
                f"openid={mask_openid(paid['openid'])} "
                f"diagnosis_id={diagnosis_id}"
            )
            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"PAYMENT_CALLBACK_ERROR {type(e).__name__}: {e}")
            raise ExternalServiceError(service_name="支付回调处理") from e

    async def get_order_status(self, openid: str, out_trade_no: str) -> dict:
        """查询订单支付状态。校验归属。

        Returns:
            {status, out_trade_no}
        Raises:
            ResourceNotFoundError: 订单不存在
            AuthorizationError: 订单不属于当前用户
        """
        from utils.exceptions import ResourceNotFoundError, AuthorizationError

        order = await OrderRepository.get_by_out_trade_no(out_trade_no)
        if not order:
            raise ResourceNotFoundError(
                resource_type="订单", resource_id=out_trade_no)
        if order["openid"] != openid:
            raise AuthorizationError(message="订单不属于当前用户")
        return {"status": order["status"], "out_trade_no": out_trade_no}
