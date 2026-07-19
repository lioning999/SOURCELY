"""Pydantic 数据模型 — 请求/响应定义。"""

from pydantic import BaseModel, Field
from typing import Optional, Any


# ===== 通用响应模型 =====

class ApiResponse(BaseModel):
    """标准 API 响应格式。"""
    code: int = 200
    data: Optional[Any] = None
    message: str = "ok"


# ===== 示例：认证相关 =====
# TODO: 替换为项目实际的请求/响应模型

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    user_id: str
    nickname: str
    avatar: Optional[str] = None


# ===== 示例：通用分页 =====

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
