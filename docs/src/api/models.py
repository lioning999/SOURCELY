"""Pydantic 请求/响应模型 — MVP"""

from pydantic import BaseModel, Field


# ── 认证 ──────────────────────────────────────

class TokenExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1, description="微信授权码")


# ── 简历 ──────────────────────────────────────

class DiagnoseRequest(BaseModel):
    resume_id: str = Field(..., min_length=36, max_length=36, description="简历 UUID")


class ResumeUploadResponse(BaseModel):
    resume_id: str = Field(..., description="简历 UUID")
    filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小(字节)")
    text_length: int = Field(..., description="提取文本长度")
