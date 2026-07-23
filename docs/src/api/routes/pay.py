"""支付路由：POST /pay/create-order /pay/notify"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Union

from adapters.wechat_pay import WeChatPayAdapter
from services.payment import PaymentService
from utils.exceptions import AppError
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pay", tags=["支付"])

# 延迟初始化：TEST_MODE 缺证书时不崩，仅在首次请求时初始化
_pay_adapter = None
_payment_service = None


def _get_payment_service():
    global _pay_adapter, _payment_service
    if _payment_service is None:
        _pay_adapter = WeChatPayAdapter()
        _payment_service = PaymentService(_pay_adapter)
    return _payment_service


class CreateOrderRequest(BaseModel):
    plan: int = Field(..., ge=1, le=2, description="套餐 1=体验装")
    diagnosis_id: str | None = Field(default=None, min_length=36, max_length=36,
                                     description="关联诊断ID，用于支付回调标记已付")


@router.post("/create-order")
async def create_order(request: Request, body: CreateOrderRequest) -> dict:
    """创建支付订单。

    需 JWT（openid 来自 request.state.openid）。
    返回: {qr_code_url, out_trade_no, amount, plan}
    （不包装在 {code, data, message} 中，参考 CLAUDE.md §响应格式）
    """
    openid = request.state.openid
    try:
        result = await _get_payment_service().create_order(
            openid=openid,
            plan=body.plan,
            diagnosis_id=body.diagnosis_id,
        )
        return result
    except AppError:
        raise


@router.get("/order-status/{out_trade_no}")
async def get_order_status(request: Request, out_trade_no: str) -> dict:
    """查询订单支付状态。需 JWT。返回: {status, out_trade_no}"""
    openid = request.state.openid
    return await _get_payment_service().get_order_status(openid, out_trade_no)


@router.post("/notify", response_model=None)
async def pay_notify(request: Request) -> Union[dict, JSONResponse]:
    """微信支付回调通知。

    无需 JWT（微信服务器回调）。
    返回: {code: "SUCCESS" / "FAIL"}
    """
    body = await request.body()
    try:
        success = await _get_payment_service().process_callback(
            headers=dict(request.headers),
            body=body,
        )
        if success:
            return {"code": "SUCCESS"}
        return JSONResponse(
            status_code=400, content={"code": "FAIL", "message": "验签失败"}
        )
    except AppError:
        return JSONResponse(
            status_code=500, content={"code": "FAIL", "message": "处理失败"}
        )
    except Exception:
        return JSONResponse(
            status_code=500, content={"code": "FAIL", "message": "服务器错误"}
        )
