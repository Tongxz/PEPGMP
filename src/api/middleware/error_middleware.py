"""
错误处理中间件
Error Handling Middleware

为FastAPI应用提供统一的错误处理和监控中间件
"""

import logging
import time
import traceback
from typing import Any, Callable, Dict

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...utils.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorInfo,
    ErrorSeverity,
    get_error_handler,
)
from ...utils.error_monitor import get_error_monitor

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""

    def __init__(self, app, enable_monitoring: bool = True):
        super().__init__(app)
        self.error_handler = get_error_handler()
        self.error_monitor = get_error_monitor() if enable_monitoring else None
        self.request_stats: Dict[str, Any] = {
            "total_requests": 0,
            "error_requests": 0,
            "avg_response_time": 0,
            "response_times": [],
        }

        if self.error_monitor:
            self.error_monitor.start_monitoring()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000)}"

        # 创建请求上下文
        context = ErrorContext(
            request_id=request_id,
            additional_data={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        try:
            # 处理请求
            response = await call_next(request)

            # 记录成功请求
            self._record_successful_request(start_time, context)

            return response

        except HTTPException as e:
            # FastAPI HTTP异常
            self._handle_http_exception(e, context, start_time)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "HTTP Error",
                    "message": e.detail,
                    "request_id": request_id,
                    "timestamp": time.time(),
                },
            )

        except Exception as e:
            # 其他异常
            self._handle_general_exception(e, context, start_time)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "服务器内部错误",
                    "request_id": request_id,
                    "timestamp": time.time(),
                },
            )

    def _record_successful_request(self, start_time: float, context: ErrorContext):
        """记录成功请求"""
        response_time = time.time() - start_time

        self.request_stats["total_requests"] += 1
        self.request_stats["response_times"].append(response_time)

        # 保持最近1000个请求的响应时间
        if len(self.request_stats["response_times"]) > 1000:
            self.request_stats["response_times"] = self.request_stats["response_times"][
                -1000:
            ]

        # 计算平均响应时间
        self.request_stats["avg_response_time"] = sum(
            self.request_stats["response_times"]
        ) / len(self.request_stats["response_times"])

        logger.debug(f"请求成功: {context.request_id}, 响应时间: {response_time:.3f}s")

    def _handle_http_exception(
        self, exception: HTTPException, context: ErrorContext, start_time: float
    ):
        """处理HTTP异常"""
        response_time = time.time() - start_time

        # 根据状态码确定错误严重程度
        if exception.status_code >= 500:
            severity = ErrorSeverity.HIGH
            category = ErrorCategory.NETWORK
        elif exception.status_code >= 400:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.VALIDATION
        else:
            severity = ErrorSeverity.LOW
            category = ErrorCategory.UNKNOWN

        # 创建错误信息
        error_info = ErrorInfo(
            error_id=f"HTTP_{exception.status_code}_{int(time.time())}",
            exception=exception,
            severity=severity,
            category=category,
            context=context,
            message=f"HTTP {exception.status_code}: {exception.detail}",
            stack_trace=traceback.format_exc(),
        )

        # 记录错误
        self.error_handler.error_tracker.add_error(error_info)

        # 更新统计
        self.request_stats["error_requests"] += 1

        logger.warning(
            f"HTTP异常: {context.request_id}, 状态码: {exception.status_code}, 响应时间: {response_time:.3f}s"
        )

    def _handle_general_exception(
        self, exception: Exception, context: ErrorContext, start_time: float
    ):
        """处理一般异常"""
        response_time = time.time() - start_time

        # 处理错误
        self.error_handler.handle_error(exception, context)

        # 更新统计
        self.request_stats["error_requests"] += 1

        logger.error(
            f"请求异常: {context.request_id}, 错误: {str(exception)}, 响应时间: {response_time:.3f}s"
        )

    def get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计"""
        total_requests = self.request_stats["total_requests"]
        error_requests = self.request_stats["error_requests"]

        error_rate = (
            (error_requests / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.request_stats,
            "error_rate_percent": error_rate,
            "success_rate_percent": 100 - error_rate,
        }


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.performance_data: Dict[str, Any] = {
            "endpoints": {},
            "slow_requests": [],
            "total_requests": 0,
            "avg_response_time": 0,
        }
        self.slow_request_threshold = 2.0  # 2秒

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        start_time = time.time()

        try:
            response = await call_next(request)

            # 计算响应时间
            response_time = time.time() - start_time

            # 记录端点性能
            endpoint = f"{request.method} {request.url.path}"
            if endpoint not in self.performance_data["endpoints"]:
                self.performance_data["endpoints"][endpoint] = {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "min_time": float("inf"),
                    "max_time": 0,
                }

            endpoint_data = self.performance_data["endpoints"][endpoint]
            endpoint_data["count"] += 1
            endpoint_data["total_time"] += response_time
            endpoint_data["avg_time"] = (
                endpoint_data["total_time"] / endpoint_data["count"]
            )
            endpoint_data["min_time"] = min(endpoint_data["min_time"], response_time)
            endpoint_data["max_time"] = max(endpoint_data["max_time"], response_time)

            # 记录慢请求
            if response_time > self.slow_request_threshold:
                slow_request = {
                    "endpoint": endpoint,
                    "response_time": response_time,
                    "timestamp": start_time,
                    "status_code": response.status_code,
                }
                self.performance_data["slow_requests"].append(slow_request)

                # 保持最近100个慢请求
                if len(self.performance_data["slow_requests"]) > 100:
                    self.performance_data["slow_requests"] = self.performance_data[
                        "slow_requests"
                    ][-100:]

            # 更新总体统计
            self.performance_data["total_requests"] += 1
            self.performance_data["avg_response_time"] = (
                self.performance_data["avg_response_time"]
                * (self.performance_data["total_requests"] - 1)
                + response_time
            ) / self.performance_data["total_requests"]

            return response

        except Exception as e:
            # 记录异常请求的性能
            response_time = time.time() - start_time
            logger.error(f"请求处理异常: {response_time:.3f}s, 错误: {str(e)}")
            raise

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            **self.performance_data,
            "slow_request_threshold": self.slow_request_threshold,
            "timestamp": time.time(),
        }


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips: set = set()
        self.request_counts: Dict[str, int] = {}
        self.rate_limit_threshold = 100  # 每分钟100个请求
        self.rate_limit_window = 60  # 1分钟

        # 检查是否为开发环境
        import os

        self.is_development = os.getenv("ENVIRONMENT", "development") == "development"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        client_ip = request.client.host if request.client else "unknown"

        # 检查IP是否被阻止
        if client_ip in self.blocked_ips:
            return JSONResponse(
                status_code=403, content={"error": "IP被阻止", "message": "您的IP地址已被阻止访问"}
            )

        # 检查速率限制
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429, content={"error": "请求过于频繁", "message": "请稍后再试"}
            )

        try:
            response = await call_next(request)

            # 检查可疑活动
            self._check_suspicious_activity(request, response)

            return response

        except Exception as e:
            # 记录安全相关异常
            self._log_security_event("exception", client_ip, str(e))
            raise

    def _check_rate_limit(self, client_ip: str) -> bool:
        """检查速率限制"""
        # 开发环境跳过速率限制
        if self.is_development:
            return True

        current_time = time.time()
        current_time - self.rate_limit_window

        # 清理过期的请求记录
        if client_ip in self.request_counts:
            # 这里应该实现更复杂的速率限制逻辑
            # 简化版本：检查最近1分钟的请求数
            pass

        # 更新请求计数
        self.request_counts[client_ip] = self.request_counts.get(client_ip, 0) + 1

        # 检查是否超过限制
        if self.request_counts[client_ip] > self.rate_limit_threshold:
            self._log_security_event(
                "rate_limit_exceeded",
                client_ip,
                f"请求数: {self.request_counts[client_ip]}",
            )
            return False

        return True

    def _check_suspicious_activity(self, request: Request, response: Response):
        """检查可疑活动"""
        client_ip = request.client.host if request.client else "unknown"

        # 检查异常状态码
        if response.status_code >= 500:
            self._log_security_event(
                "server_error", client_ip, f"状态码: {response.status_code}"
            )

        # 检查异常请求路径
        if ".." in str(request.url.path) or "admin" in str(request.url.path).lower():
            self._log_security_event(
                "suspicious_path", client_ip, f"路径: {request.url.path}"
            )

    def _log_security_event(self, event_type: str, client_ip: str, details: str):
        """记录安全事件"""
        logger.warning(f"安全事件: {event_type}, IP: {client_ip}, 详情: {details}")

    def block_ip(self, ip: str):
        """阻止IP"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP被阻止: {ip}")

    def unblock_ip(self, ip: str):
        """解除IP阻止"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP解除阻止: {ip}")


def setup_error_middleware(app):
    """设置错误处理中间件"""
    # 添加错误处理中间件
    app.add_middleware(ErrorHandlingMiddleware, enable_monitoring=True)

    # 添加性能监控中间件
    app.add_middleware(PerformanceMonitoringMiddleware)

    # 添加安全中间件
    app.add_middleware(SecurityMiddleware)

    logger.info("错误处理中间件已设置")


def get_middleware_stats(app) -> Dict[str, Any]:
    """获取中间件统计信息"""
    stats = {}

    # 获取错误处理中间件统计
    for middleware in app.user_middleware:
        if isinstance(middleware.cls, ErrorHandlingMiddleware):
            error_middleware = middleware.kwargs.get("app")
            if hasattr(error_middleware, "get_request_stats"):
                stats["error_handling"] = error_middleware.get_request_stats()

        elif isinstance(middleware.cls, PerformanceMonitoringMiddleware):
            perf_middleware = middleware.kwargs.get("app")
            if hasattr(perf_middleware, "get_performance_report"):
                stats["performance"] = perf_middleware.get_performance_report()

    return stats
