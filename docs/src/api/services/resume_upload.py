"""简历服务 — 上传解析 + 内容校验 + 存储编排"""

from repositories.resumes import ResumeRepository
from utils.file_utils import extract_resume_text
from utils.exceptions import ValidationError
from utils.logger import get_logger, mask_openid
from config import Config

logger = get_logger(__name__)

# 简历特征词：文本命中 ≥2 个才算简历，拦截非简历文件
_RESUME_KEYWORDS = [
    "教育", "学历", "学校", "毕业", "专业", "学位", "成绩",
    "工作", "公司", "经验", "项目", "负责", "任职", "岗位",
    "技能", "掌握", "熟悉", "了解", "精通",
    "电话", "邮箱", "年龄", "性别", "姓名",
]


def _validate_resume_content(text: str) -> None:
    """检查文本内容是否像简历。不通过抛 ValidationError。

    规则：≥50 字符 + 简历特征词命中 ≥2。
    """
    if len(text) < 50:
        raise ValidationError(
            message="文件内容过短，不像简历，请上传正确的简历文件",
            details={"text_length": len(text), "min_length": 50},
        )

    hits = sum(1 for kw in _RESUME_KEYWORDS if kw in text)
    if hits < 2:
        raise ValidationError(
            message="文件内容不像简历，请上传正确的简历文件",
            details={"keyword_hits": hits, "min_hits": 2},
        )


class ResumeService:
    """简历上传 + 文本提取编排。"""

    async def upload(self, openid: str, filename: str, content: bytes) -> dict:
        """提取文本 → 写入数据库 → 返回 resume 信息。

        Raises:
            ValidationError: 文件格式不支持
        """
        file_size = len(content)

        # ── 格式二次校验（Route 已做，Service 做防御性兜底）──
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in Config.ALLOWED_EXTENSIONS:
            raise ValidationError(
                message=f"不支持的文件格式: .{ext}",
                details={"allowed": Config.ALLOWED_EXTENSIONS},
            )

        # ── 大小校验 ──────────────────────────
        if file_size > Config.MAX_FILE_SIZE:
            raise ValidationError(
                message=f"文件过大，最大 {Config.MAX_FILE_SIZE // 1024 // 1024}MB",
                details={"file_size": file_size, "max": Config.MAX_FILE_SIZE},
            )

        # ── 提取文本 ──────────────────────────
        raw_text = await extract_resume_text(content, filename)
        if not raw_text or not raw_text.strip():
            raise ValidationError(
                message="无法识别简历内容，OCR 解析失败，请确认 PDF 清晰可读"
            )

        # ── 简历内容校验（防垃圾文件）────────
        _validate_resume_content(raw_text)

        # ── 写入数据库 ────────────────────────
        resume_id = await ResumeRepository.create(
            openid=openid,
            filename=filename,
            raw_text=raw_text,
            file_size=file_size,
        )

        logger.info(
            f"RESUME_UPLOADED resume_id={resume_id} "
            f"openid={mask_openid(openid)} "
            f"text_len={len(raw_text)}"
        )

        return {
            "resume_id": resume_id,
            "filename": filename,
            "file_size": file_size,
            "text_length": len(raw_text),
        }
