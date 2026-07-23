"""简历诊断路由"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models import DiagnoseRequest
from services.resume_diagnose import ResumeDiagnoseService
from repositories.diagnoses import DiagnosisRepository
from adapters.ai_client import AIClient
from config import Config
from utils.exceptions import AppError, AuthorizationError, ResourceNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/resume", tags=["简历"])

# ── 依赖注入 ──────────────────────────────────────
_ai_client = AIClient(
    api_key=Config.DASHSCOPE_API_KEY,
    base_url=Config.DASHSCOPE_BASE_URL,
    model=Config.AI_MODEL_NAME,
    timeout=Config.AI_DIAGNOSE_TIMEOUT,
    connect_timeout=Config.AI_CONNECT_TIMEOUT,
    max_retries=Config.AI_MAX_RETRIES,
    temperature=0.0,
    max_tokens=Config.AI_MAX_TOKENS,
)
_diagnose_service = ResumeDiagnoseService(ai_client=_ai_client)

# ── 防重：同用户同简历的并发诊断只跑一次 ──────────────
_pending: dict[str, asyncio.Event] = {}


@router.post("/diagnose")
async def diagnose_resume(
    request: Request,
    body: DiagnoseRequest,
) -> JSONResponse:
    """诊断简历。返回结构化 JSON 诊断结果。JWT 认证。

    防重：同 openid + resume_id 并发请求返回 409。
    """
    openid = request.state.openid
    key = f"{openid}:{body.resume_id}"

    if key in _pending:
        logger.warning(f"DIAGNOSE_DUP key={key}")
        return JSONResponse(
            status_code=409,
            content={"code": 409, "data": None, "message": "诊断进行中，请勿重复提交"},
        )

    done = asyncio.Event()
    _pending[key] = done

    try:
        logger.info(f"DIAGNOSE_REQUEST resume_id={body.resume_id}")
        result = await _diagnose_service.diagnose(openid, body.resume_id)
        # 打平嵌套：将 AI result 字段提升到顶层，前端直接读 overall_impression 等
        ai_result = result.pop("result", {})
        result.update(ai_result)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    finally:
        done.set()
        _pending.pop(key, None)


@router.get("/diagnosis")
async def get_diagnosis(
    request: Request,
    diagnosis_id: str,
) -> JSONResponse:
    """获取已有诊断数据（按 ID）。JWT 认证 + 归属校验。

    用于首页历史记录跳转、刷新页面后恢复等场景。
    """
    openid = request.state.openid
    logger.info(f"GET_DIAGNOSIS diagnosis_id={diagnosis_id}")

    try:
        diag = await DiagnosisRepository.get_by_id(diagnosis_id)
        if not diag:
            raise ResourceNotFoundError(resource_type="诊断", resource_id=diagnosis_id)
        if diag["openid"] != openid:
            raise AuthorizationError(message="诊断不属于当前用户")

        # 仅返回诊断页需要的字段，不泄露付费内容
        ai_result = diag.get("diagnose_result", {})
        if isinstance(ai_result, str):
            import json
            ai_result = json.loads(ai_result)

        result = {
            "diagnosis_id": diag.get("id", diagnosis_id),
            "overall_impression": ai_result.get("overall_impression", ""),
            "dimension_scan": ai_result.get("dimension_scan", {}),
            "fatal_issues": ai_result.get("fatal_issues", []),
            "interview_targets": ai_result.get("interview_targets", []),
            "is_paid": bool(diag.get("is_paid")),
        }

        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )
