"""监控API路由.

提供系统监控、连接池状态查询等功能。
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# 请求指标（用于metrics_middleware）
_request_metrics = {
    "total_requests": 0,
    "status_codes": {},
    "domain_service_requests": 0,
    "response_times": [],
}


def record_request(
    status_code: int,
    domain_service_used: bool = False,
    response_time_ms: float = 0.0,
):
    """记录请求指标（用于metrics_middleware）.

    Args:
        status_code: HTTP状态码
        domain_service_used: 是否使用了领域服务
        response_time_ms: 响应时间（毫秒）
    """
    _request_metrics["total_requests"] += 1

    # 记录状态码
    status_key = str(status_code)
    _request_metrics["status_codes"][status_key] = (
        _request_metrics["status_codes"].get(status_key, 0) + 1
    )

    # 记录领域服务使用
    if domain_service_used:
        _request_metrics["domain_service_requests"] += 1

    # 记录响应时间（保留最近1000个）
    _request_metrics["response_times"].append(response_time_ms)
    if len(_request_metrics["response_times"]) > 1000:
        _request_metrics["response_times"].pop(0)


@router.get("/db-pool/status", summary="获取数据库连接池状态")
async def get_db_pool_status() -> Dict[str, Any]:
    """获取数据库连接池状态.

    Returns:
        连接池状态信息，包括：
        - status: 状态（healthy/not_initialized）
        - size: 连接池大小
        - free_size: 空闲连接数
        - min_size: 最小连接数
        - max_size: 最大连接数
        - usage_percent: 使用率（百分比）
    """
    try:
        # 导入DatabaseService（延迟导入避免循环依赖）
        from src.services.detection_service_domain import _db_service

        if _db_service is None or _db_service.pool is None:
            return {"status": "not_initialized", "message": "数据库连接池未初始化"}

        pool = _db_service.pool
        size = pool.get_size()
        idle_size = pool.get_idle_size()
        min_size = pool.get_min_size()
        max_size = pool.get_max_size()

        # 计算使用率
        usage_percent = round((1 - idle_size / size) * 100, 2) if size > 0 else 0

        return {
            "status": "healthy",
            "size": size,
            "free_size": idle_size,
            "min_size": min_size,
            "max_size": max_size,
            "usage_percent": usage_percent,
        }
    except Exception as e:
        logger.error(f"获取连接池状态失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取连接池状态失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/db-pool/config", summary="获取数据库连接池配置")
async def get_db_pool_config() -> Dict[str, Any]:
    """获取数据库连接池配置.

    Returns:
        连接池配置信息，包括：
        - min_size: 最小连接数
        - max_size: 最大连接数
        - command_timeout: 命令超时时间（秒）
        - max_queries: 每个连接最多执行查询数
        - max_inactive_connection_lifetime: 非活跃连接最大生存时间（秒）
        - env: 当前环境
    """
    try:
        from src.database.pool_config import PoolConfig

        config = PoolConfig.from_env()

        return {
            "min_size": config.min_size,
            "max_size": config.max_size,
            "command_timeout": config.command_timeout,
            "max_queries": config.max_queries,
            "max_inactive_connection_lifetime": config.max_inactive_connection_lifetime,
            "env": os.getenv("ENV", "development"),
        }
    except Exception as e:
        logger.error(f"获取连接池配置失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取连接池配置失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/db-pool/health", summary="数据库连接池健康检查")
async def db_pool_health_check() -> Dict[str, Any]:
    """执行数据库连接池健康检查.

    Returns:
        健康检查结果，包括：
        - healthy: 是否健康
        - message: 状态消息
        - size: 连接池大小（如果可用）
        - idle_size: 空闲连接数（如果可用）
        - usage_percent: 使用率（如果可用）
    """
    try:
        from src.services.detection_service_domain import _db_service

        if _db_service is None:
            return {"healthy": False, "message": "数据库服务未初始化"}

        # 执行健康检查
        result = await _db_service.health_check()
        return result
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {"healthy": False, "message": f"健康检查异常: {str(e)}"}


@router.get("/metrics", summary="获取请求指标")
async def get_metrics() -> Dict[str, Any]:
    """获取请求指标（用于监控面板）.

    Returns:
        请求指标信息，包括：
        - total_requests: 总请求数
        - status_codes: 状态码分布
        - domain_service_requests: 领域服务请求数
        - avg_response_time: 平均响应时间（毫秒）
    """
    try:
        # 计算平均响应时间
        response_times = _request_metrics["response_times"]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0.0
        )

        return {
            "total_requests": _request_metrics["total_requests"],
            "status_codes": _request_metrics["status_codes"],
            "domain_service_requests": _request_metrics["domain_service_requests"],
            "avg_response_time_ms": round(avg_response_time, 2),
        }
    except Exception as e:
        logger.error(f"获取指标失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取指标失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )
