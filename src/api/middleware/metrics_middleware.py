"""监控指标中间件."""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routers.monitoring import record_request

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """监控指标中间件.
    
    记录请求指标，包括：
    - 请求计数
    - 状态码分布
    - 响应时间
    - 领域服务使用情况
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录指标.
        
        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理函数
            
        Returns:
            FastAPI响应对象
        """
        start_time = time.time()
        
        # 记录是否使用领域服务（从查询参数中获取）
        domain_service_used = request.query_params.get("force_domain") == "true"
        
        try:
            response = await call_next(request)
            
            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000
            
            # 记录指标
            record_request(
                status_code=response.status_code,
                domain_service_used=domain_service_used,
                response_time_ms=response_time_ms,
            )
            
            return response
            
        except Exception as e:
            # 记录异常
            response_time_ms = (time.time() - start_time) * 1000
            
            record_request(
                status_code=500,
                domain_service_used=domain_service_used,
                response_time_ms=response_time_ms,
            )
            
            logger.error(f"请求处理异常: {e}")
            raise

