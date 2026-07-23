"""简历优化路由：预览 + 结果 + 追问预判"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.resume_optimize import ResumeOptimizeService, QuotaExhaustedError
from adapters.ai_client import AIClient
from config import Config
from utils.exceptions import AppError
from utils.logger import get_logger, mask_openid

logger = get_logger(__name__)
router = APIRouter(prefix="/resume", tags=["简历优化"])

# ── 依赖注入 ──────────────────────────────────────
_ai_client = AIClient(
    api_key=Config.DASHSCOPE_API_KEY,
    base_url=Config.DASHSCOPE_BASE_URL,
    model=Config.AI_MODEL_NAME,
    timeout=Config.AI_OPTIMIZE_TIMEOUT,
    connect_timeout=Config.AI_CONNECT_TIMEOUT,
    max_retries=Config.AI_MAX_RETRIES,
    temperature=0.0,
    max_tokens=Config.AI_MAX_TOKENS,
)
_optimize_service = ResumeOptimizeService(ai_client=_ai_client)

# ── 防重 ──────────────────────────────────────────
_pending: dict[str, asyncio.Event] = {}


class PreviewRequest(BaseModel):
    diagnosis_id: str = Field(..., min_length=36, max_length=36)


class InterviewQARequest(BaseModel):
    diagnosis_id: str = Field(..., min_length=36, max_length=36)


@router.post("/preview")
async def preview_resume(
    request: Request,
    body: PreviewRequest,
) -> JSONResponse:
    """优化预览 — 全文 AI 优化 + 入库 + 返回 Top 2 对比。

    需 JWT。防重：同 openid + diagnosis_id 并发请求返回 409。
    """
    openid = request.state.openid
    key = f"{openid}:preview:{body.diagnosis_id}"

    if key in _pending:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "data": None, "message": "优化进行中，请勿重复提交"},
        )

    done = asyncio.Event()
    _pending[key] = done

    try:
        logger.info(f"PREVIEW_REQUEST diagnosis_id={body.diagnosis_id}")
        result = await _optimize_service.preview(openid, body.diagnosis_id)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except QuotaExhaustedError as e:
        return JSONResponse(
            status_code=402,
            content={"code": 402, "data": {"quota_type": e.quota_type}, "message": e.message},
        )
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )
    finally:
        done.set()
        _pending.pop(key, None)


@router.get("/result")
async def get_optimize_result(
    request: Request,
    diagnosis_id: str,
) -> JSONResponse:
    """获取完整优化结果。需已打赏 ¥1，否则返回 402。"""
    openid = request.state.openid
    logger.info(f"RESULT_REQUEST diagnosis_id={diagnosis_id}")
    try:
        result = await _optimize_service.get_result(openid, diagnosis_id)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except QuotaExhaustedError as e:
        return JSONResponse(
            status_code=402,
            content={"code": 402, "data": {"quota_type": e.quota_type}, "message": e.message},
        )
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )


@router.post("/interview-qa")
async def get_interview_qa(
    request: Request,
    body: InterviewQARequest,
) -> JSONResponse:
    """追问预判 — 调 AI 生成 + resolved 标注 + 入库。

    需 JWT。防重：同 openid + diagnosis_id 并发请求返回 409。
    """
    openid = request.state.openid
    key = f"{openid}:qa:{body.diagnosis_id}"

    if key in _pending:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "data": None, "message": "追问预判进行中，请勿重复提交"},
        )

    done = asyncio.Event()
    _pending[key] = done

    try:
        logger.info(f"QA_REQUEST diagnosis_id={body.diagnosis_id}")
        result = await _optimize_service.get_interview_qa(openid, body.diagnosis_id)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except QuotaExhaustedError as e:
        return JSONResponse(
            status_code=402,
            content={"code": 402, "data": {"quota_type": e.quota_type}, "message": e.message},
        )
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )
    finally:
        done.set()
        _pending.pop(key, None)


class InterviewQuestionsRequest(BaseModel):
    diagnosis_id: str = Field(..., min_length=36, max_length=36)


@router.post("/interview-questions")
async def get_interview_questions(
    request: Request,
    body: InterviewQuestionsRequest,
) -> JSONResponse:
    """模拟面试 — 调 AI 生成 5 道面试题 + 入库。

    需 JWT。防重：同 openid + diagnosis_id 并发请求返回 409。
    """
    openid = request.state.openid
    key = f"{openid}:mock:{body.diagnosis_id}"

    if key in _pending:
        return JSONResponse(
            status_code=409,
            content={"code": 409, "data": None, "message": "面试题生成中，请勿重复提交"},
        )

    done = asyncio.Event()
    _pending[key] = done

    try:
        logger.info(f"MOCK_INTERVIEW_REQUEST diagnosis_id={body.diagnosis_id}")
        result = await _optimize_service.get_interview_questions(openid, body.diagnosis_id)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except QuotaExhaustedError as e:
        return JSONResponse(
            status_code=402,
            content={"code": 402, "data": {"quota_type": e.quota_type}, "message": e.message},
        )
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )
    finally:
        done.set()
        _pending.pop(key, None)


@router.get("/latest")
async def get_latest_status(request: Request) -> JSONResponse:
    """查询最近一次诊断摘要 + 各环节完成状态。

    需 JWT。纯读取，不防重。
    """
    openid = request.state.openid
    logger.info(f"LATEST_REQUEST openid={mask_openid(openid)}")
    try:
        result = await _optimize_service.get_latest(openid)
        return JSONResponse(content={"code": 200, "data": result, "message": "ok"})
    except AppError as e:
        return JSONResponse(
            status_code=e.http_status,
            content={"code": e.http_status, "data": None, "message": e.message},
        )
