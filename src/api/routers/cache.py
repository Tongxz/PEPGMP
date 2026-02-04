"""缓存管理路由模块.

提供Redis缓存的管理接口，包括清除缓存和查看缓存统计.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.utils.cache import clear_cache, get_cache_stats

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

router = APIRouter()
logger = logging.getLogger(__name__)


class ClearCacheRequest(BaseModel):
    """清除缓存请求模型."""

    pattern: str = Field(
        default="stats:*",
        description="缓存键模式（支持通配符），例如: stats:*, cache:*, *",
    )


class ClearCacheResponse(BaseModel):
    """清除缓存响应模型."""

    ok: bool = Field(description="操作是否成功")
    cleared_count: int = Field(description="清除的缓存数量")
    pattern: str = Field(description="使用的缓存键模式")


@router.post("/cache/clear", summary="清除缓存")
async def clear_cache_endpoint(request: ClearCacheRequest) -> ClearCacheResponse:
    """清除匹配的缓存键.

    Args:
        request: 清除缓存请求，包含缓存键模式

    Returns:
        清除结果，包含清除数量

    Raises:
        HTTPException: 如果清除缓存失败

    Example:
        POST /api/v1/cache/clear
        {"pattern": "stats:*"}

        → {"ok": true, "cleared_count": 5, "pattern": "stats:*"}
    """
    try:
        cleared_count = await clear_cache(request.pattern)
        logger.info(f"缓存清除成功: pattern={request.pattern}, count={cleared_count}")
        return ClearCacheResponse(
            ok=True, cleared_count=cleared_count, pattern=request.pattern
        )
    except Exception as e:
        logger.error(f"清除缓存失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="清除缓存失败",
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=str(e),
        )


@router.get("/cache/stats", summary="获取缓存统计")
async def get_cache_stats_endpoint(pattern: str = "stats:*") -> Dict[str, Any]:
    """获取缓存统计信息.

    Args:
        pattern: 缓存键模式（支持通配符）

    Returns:
        缓存统计信息，包括：
        - total_keys: 匹配的缓存键数量
        - pattern: 使用的模式
        - memory_used_mb: Redis使用的内存（MB）
        - memory_peak_mb: Redis内存峰值（MB）

    Raises:
        HTTPException: 如果获取统计失败

    Example:
        GET /api/v1/cache/stats?pattern=stats:*

        → {
            "total_keys": 10,
            "pattern": "stats:*",
            "memory_used_mb": 5.2,
            "memory_peak_mb": 8.3
          }
    """
    try:
        stats = await get_cache_stats(pattern)

        # 检查是否有错误
        if "error" in stats:
            raise raise_http_exception(
                status_code=500,
                message=stats["error"],
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )

        logger.debug(f"获取缓存统计成功: {stats}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取缓存统计失败",
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=str(e),
        )
