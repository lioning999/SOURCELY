"""统一异常体系 — 1基类+9子类，全局异常处理器自动转 {code, data, message}。"""

from typing import Optional, Dict, Any
from fastapi import status


class AppError(Exception):
    """应用异常基类。子类只需传 message + code + http_status。"""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """标准错误响应格式。"""
        return {"code": self.http_status, "data": None, "message": self.message}


class ValidationError(AppError):
    """400 — 输入参数验证失败。"""
    def __init__(self, message: str = "输入验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR",
                         http_status=status.HTTP_400_BAD_REQUEST, details=details)


class AuthenticationError(AppError):
    """401 — 认证失败（未登录/token无效）。"""
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="AUTHENTICATION_ERROR",
                         http_status=status.HTTP_401_UNAUTHORIZED, details=details)


class AuthorizationError(AppError):
    """403 — 权限不足。"""
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="AUTHORIZATION_ERROR",
                         http_status=status.HTTP_403_FORBIDDEN, details=details)


class ResourceNotFoundError(AppError):
    """404 — 资源不存在。"""
    def __init__(self, resource_type: str = "资源", resource_id: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type}不存在"
        if resource_id:
            message = f"{resource_type}[{resource_id}]不存在"
        super().__init__(message=message, code="RESOURCE_NOT_FOUND",
                         http_status=status.HTTP_404_NOT_FOUND, details=details)


class ServiceUnavailableError(AppError):
    """503 — 服务暂时不可用。"""
    def __init__(self, service_name: str = "服务", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=f"{service_name}暂时不可用，请稍后重试",
                         code="SERVICE_UNAVAILABLE",
                         http_status=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


class ExternalServiceError(AppError):
    """502 — 外部服务调用失败。"""
    def __init__(self, service_name: str = "外部服务", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=f"{service_name}调用失败", code="EXTERNAL_SERVICE_ERROR",
                         http_status=status.HTTP_502_BAD_GATEWAY, details=details)


class DatabaseError(AppError):
    """500 — 数据库操作失败。"""
    def __init__(self, operation: str = "数据库操作", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=f"{operation}失败", code="DATABASE_ERROR",
                         http_status=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


class OptimisticLockError(AppError):
    """409 — 乐观锁冲突。"""
    def __init__(self, message: str = "操作冲突，请稍后重试", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="OPTIMISTIC_LOCK_CONFLICT",
                         http_status=status.HTTP_409_CONFLICT, details=details)


class InsufficientQuotaError(AppError):
    """403 — 使用次数不足。"""
    def __init__(self, resource_type: str = "次数", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=f"{resource_type}不足", code="INSUFFICIENT_QUOTA",
                         http_status=status.HTTP_403_FORBIDDEN, details=details)
