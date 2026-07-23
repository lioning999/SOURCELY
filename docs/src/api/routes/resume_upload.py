"""简历上传路由"""

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from services.resume_upload import ResumeService
from utils.exceptions import ValidationError
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/resume", tags=["简历"])

# ── 依赖注入 ──────────────────────────────────────
_resume_service = ResumeService()


# ── 文件上传 ─────────────────────────────────────
# 文件上传: code=0 无 message 字段，与旧前端兼容

@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
) -> JSONResponse:
    """上传简历文件，提取文本，返回 resume_id。JWT 认证。"""
    openid = request.state.openid

    # ── 文件名兜底 ──────────────────────────
    filename = file.filename or "unknown.resume"

    # ── 格式校验 ──────────────────────────
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in Config.ALLOWED_EXTENSIONS:
        raise ValidationError(
            message=f"不支持的文件格式: .{ext}，仅支持 {', '.join(Config.ALLOWED_EXTENSIONS).upper()}",
            details={"filename": filename, "allowed": Config.ALLOWED_EXTENSIONS},
        )

    # ── 读取文件内容 ───────────────────────
    content = await file.read()
    logger.info(
        f"RESUME_UPLOAD_REQUEST filename={filename} "
        f"size={len(content)}"
    )

    # ── 调 Service ────────────────────────
    result = await _resume_service.upload(
        openid=openid,
        filename=filename,
        content=content,
    )

    return JSONResponse(content={"code": 0, "data": result})
