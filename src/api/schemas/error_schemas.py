"""
统一错误响应模型
Unified Error Response Schemas

定义所有API错误响应的统一格式
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ErrorType(str, Enum):
    """错误类型枚举"""

    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    CONFLICT_ERROR = "conflict_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"


class ErrorCode(str, Enum):
    """错误码枚举"""

    # 验证错误 (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # 认证错误 (401)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # 授权错误 (403)
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # 资源不存在 (404)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"

    # 资源冲突 (409)
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"

    # 速率限制 (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # 服务器错误 (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"

    # 服务不可用 (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"


class ErrorDetail(BaseModel):
    """错误详情模型"""

    code: str = Field(..., description="错误码")
    type: str = Field(..., description="错误类型")
    message: str = Field(..., description="用户友好的错误消息")
    details: Optional[str] = Field(None, description="详细错误信息（可选，仅开发环境）")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: float = Field(..., description="时间戳")


class ErrorResponse(BaseModel):
    """统一错误响应模型"""

    error: ErrorDetail = Field(..., description="错误详情")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "type": "not_found_error",
                    "message": "资源不存在",
                    "details": "详细错误信息（可选）",
                    "request_id": "req_1234567890",
                    "timestamp": 1234567890.123,
                }
            }
        }


def get_error_type_from_status_code(status_code: int) -> ErrorType:
    """根据HTTP状态码获取错误类型"""
    if status_code == 400:
        return ErrorType.VALIDATION_ERROR
    elif status_code == 401:
        return ErrorType.AUTHENTICATION_ERROR
    elif status_code == 403:
        return ErrorType.AUTHORIZATION_ERROR
    elif status_code == 404:
        return ErrorType.NOT_FOUND_ERROR
    elif status_code == 409:
        return ErrorType.CONFLICT_ERROR
    elif status_code == 429:
        return ErrorType.RATE_LIMIT_ERROR
    elif status_code == 500:
        return ErrorType.SERVER_ERROR
    elif status_code == 503:
        return ErrorType.SERVICE_UNAVAILABLE
    else:
        return ErrorType.SERVER_ERROR


def get_error_code_from_status_code(status_code: int) -> ErrorCode:
    """根据HTTP状态码获取默认错误码"""
    if status_code == 400:
        return ErrorCode.VALIDATION_ERROR
    elif status_code == 401:
        return ErrorCode.AUTHENTICATION_REQUIRED
    elif status_code == 403:
        return ErrorCode.AUTHORIZATION_FAILED
    elif status_code == 404:
        return ErrorCode.RESOURCE_NOT_FOUND
    elif status_code == 409:
        return ErrorCode.RESOURCE_CONFLICT
    elif status_code == 429:
        return ErrorCode.RATE_LIMIT_EXCEEDED
    elif status_code == 500:
        return ErrorCode.INTERNAL_SERVER_ERROR
    elif status_code == 503:
        return ErrorCode.SERVICE_UNAVAILABLE
    else:
        return ErrorCode.INTERNAL_SERVER_ERROR
