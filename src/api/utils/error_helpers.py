"""
错误处理工具函数
Error Handling Helper Functions

提供统一的错误响应生成函数
"""

import os
from typing import Any, Dict, Optional

from fastapi import HTTPException

from ..schemas.error_schemas import (
    ErrorCode,
    ErrorDetail,
    ErrorType,
    get_error_code_from_status_code,
    get_error_type_from_status_code,
)


def is_development() -> bool:
    """检查是否为开发环境"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env in ("dev", "development")


def create_error_response(
    status_code: int,
    message: str,
    error_code: Optional[ErrorCode] = None,
    error_type: Optional[ErrorType] = None,
    details: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    创建统一格式的错误响应

    Args:
        status_code: HTTP状态码
        message: 用户友好的错误消息
        error_code: 错误码（可选，默认根据状态码推断）
        error_type: 错误类型（可选，默认根据状态码推断）
        details: 详细错误信息（可选，仅开发环境返回）
        request_id: 请求ID（可选）

    Returns:
        统一格式的错误响应字典
    """
    # 如果没有指定错误类型，根据状态码推断
    if error_type is None:
        error_type = get_error_type_from_status_code(status_code)

    # 如果没有指定错误码，根据状态码推断
    if error_code is None:
        error_code = get_error_code_from_status_code(status_code)

    # 构建错误详情
    error_detail = ErrorDetail(
        code=error_code.value,
        type=error_type.value,
        message=message,
        details=details if is_development() else None,
        request_id=request_id,
        timestamp=__import__("time").time(),
    )

    return {"error": error_detail.model_dump(exclude_none=True)}


def raise_http_exception(
    status_code: int,
    message: str,
    error_code: Optional[ErrorCode] = None,
    error_type: Optional[ErrorType] = None,
    details: Optional[str] = None,
) -> HTTPException:
    """
    抛出统一格式的HTTPException

    Args:
        status_code: HTTP状态码
        message: 用户友好的错误消息
        error_code: 错误码（可选，默认根据状态码推断）
        error_type: 错误类型（可选，默认根据状态码推断）
        details: 详细错误信息（可选，仅开发环境返回）

    Returns:
        HTTPException对象（包含统一格式的detail）

    Example:
        ```python
        raise raise_http_exception(
            status_code=404,
            message="资源不存在",
            error_code=ErrorCode.RESOURCE_NOT_FOUND
        )
        ```
    """
    error_response = create_error_response(
        status_code=status_code,
        message=message,
        error_code=error_code,
        error_type=error_type,
        details=details,
    )

    return HTTPException(status_code=status_code, detail=error_response)
