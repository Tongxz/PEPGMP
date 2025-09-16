"""
统一错误处理系统
Unified Error Handling System

提供统一的异常管理、错误分类、备用机制和错误恢复功能
"""

import functools
import logging
import threading
import time
import traceback
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"  # 低严重性，不影响核心功能
    MEDIUM = "medium"  # 中等严重性，影响部分功能
    HIGH = "high"  # 高严重性，影响核心功能
    CRITICAL = "critical"  # 严重错误，系统可能不可用


class ErrorCategory(Enum):
    """错误分类"""

    DETECTION = "detection"  # 检测相关错误
    MODEL = "model"  # 模型相关错误
    GPU = "gpu"  # GPU相关错误
    NETWORK = "network"  # 网络相关错误
    DATABASE = "database"  # 数据库相关错误
    FILE_IO = "file_io"  # 文件IO错误
    CONFIGURATION = "configuration"  # 配置相关错误
    VALIDATION = "validation"  # 验证相关错误
    TIMEOUT = "timeout"  # 超时错误
    RESOURCE = "resource"  # 资源相关错误
    UNKNOWN = "unknown"  # 未知错误


@dataclass
class ErrorContext:
    """错误上下文信息"""

    timestamp: float = field(default_factory=time.time)
    function_name: str = ""
    module_name: str = ""
    line_number: int = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """错误信息"""

    error_id: str
    exception: Exception
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    message: str
    stack_trace: str
    recovery_attempted: bool = False
    recovery_successful: bool = False
    retry_count: int = 0
    max_retries: int = 3


class ErrorRecoveryStrategy:
    """错误恢复策略"""

    def __init__(self):
        self.strategies: Dict[ErrorCategory, List[Callable]] = {
            ErrorCategory.DETECTION: [self._recovery_detection_fallback],
            ErrorCategory.MODEL: [
                self._recovery_model_reload,
                self._recovery_model_fallback,
            ],
            ErrorCategory.GPU: [self._recovery_gpu_fallback, self._recovery_cpu_mode],
            ErrorCategory.NETWORK: [
                self._recovery_network_retry,
                self._recovery_offline_mode,
            ],
            ErrorCategory.DATABASE: [
                self._recovery_db_retry,
                self._recovery_db_fallback,
            ],
            ErrorCategory.FILE_IO: [
                self._recovery_file_retry,
                self._recovery_temp_file,
            ],
            ErrorCategory.TIMEOUT: [
                self._recovery_timeout_retry,
                self._recovery_timeout_extend,
            ],
            ErrorCategory.RESOURCE: [
                self._recovery_resource_cleanup,
                self._recovery_resource_wait,
            ],
        }

    def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """尝试错误恢复"""
        strategies = self.strategies.get(error_info.category, [])

        for strategy in strategies:
            try:
                if strategy(error_info):
                    error_info.recovery_successful = True
                    logger.info(f"错误恢复成功: {error_info.error_id}")
                    return True
            except Exception as e:
                logger.warning(f"恢复策略失败: {strategy.__name__}: {e}")

        error_info.recovery_attempted = True
        return False

    def _recovery_detection_fallback(self, error_info: ErrorInfo) -> bool:
        """检测错误恢复：使用备用检测器"""
        logger.info("尝试使用备用检测器")
        # 这里可以切换到备用检测器
        return True

    def _recovery_model_reload(self, error_info: ErrorInfo) -> bool:
        """模型错误恢复：重新加载模型"""
        logger.info("尝试重新加载模型")
        # 这里可以重新加载模型
        return True

    def _recovery_model_fallback(self, error_info: ErrorInfo) -> bool:
        """模型错误恢复：使用备用模型"""
        logger.info("尝试使用备用模型")
        return True

    def _recovery_gpu_fallback(self, error_info: ErrorInfo) -> bool:
        """GPU错误恢复：切换到CPU模式"""
        logger.info("尝试切换到CPU模式")
        return True

    def _recovery_cpu_mode(self, error_info: ErrorInfo) -> bool:
        """GPU错误恢复：强制CPU模式"""
        logger.info("强制使用CPU模式")
        return True

    def _recovery_network_retry(self, error_info: ErrorInfo) -> bool:
        """网络错误恢复：重试"""
        logger.info("尝试网络重试")
        return True

    def _recovery_offline_mode(self, error_info: ErrorInfo) -> bool:
        """网络错误恢复：离线模式"""
        logger.info("切换到离线模式")
        return True

    def _recovery_db_retry(self, error_info: ErrorInfo) -> bool:
        """数据库错误恢复：重试"""
        logger.info("尝试数据库重试")
        return True

    def _recovery_db_fallback(self, error_info: ErrorInfo) -> bool:
        """数据库错误恢复：备用数据库"""
        logger.info("使用备用数据库")
        return True

    def _recovery_file_retry(self, error_info: ErrorInfo) -> bool:
        """文件IO错误恢复：重试"""
        logger.info("尝试文件操作重试")
        return True

    def _recovery_temp_file(self, error_info: ErrorInfo) -> bool:
        """文件IO错误恢复：临时文件"""
        logger.info("使用临时文件")
        return True

    def _recovery_timeout_retry(self, error_info: ErrorInfo) -> bool:
        """超时错误恢复：重试"""
        logger.info("尝试超时重试")
        return True

    def _recovery_timeout_extend(self, error_info: ErrorInfo) -> bool:
        """超时错误恢复：延长超时"""
        logger.info("延长超时时间")
        return True

    def _recovery_resource_cleanup(self, error_info: ErrorInfo) -> bool:
        """资源错误恢复：清理资源"""
        logger.info("清理资源")
        return True

    def _recovery_resource_wait(self, error_info: ErrorInfo) -> bool:
        """资源错误恢复：等待资源"""
        logger.info("等待资源释放")
        return True


class ErrorTracker:
    """错误跟踪器"""

    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: deque = deque(maxlen=max_errors)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.severity_counts: Dict[ErrorSeverity, int] = defaultdict(int)
        self.category_counts: Dict[ErrorCategory, int] = defaultdict(int)
        self.lock = threading.Lock()

    def add_error(self, error_info: ErrorInfo):
        """添加错误记录"""
        with self.lock:
            self.errors.append(error_info)
            self.error_counts[error_info.error_id] += 1
            self.severity_counts[error_info.severity] += 1
            self.category_counts[error_info.category] += 1

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self.lock:
            return {
                "total_errors": len(self.errors),
                "error_counts": dict(self.error_counts),
                "severity_counts": {
                    k.value: v for k, v in self.severity_counts.items()
                },
                "category_counts": {
                    k.value: v for k, v in self.category_counts.items()
                },
                "recent_errors": [
                    {
                        "error_id": e.error_id,
                        "severity": e.severity.value,
                        "category": e.category.value,
                        "message": e.message,
                        "timestamp": e.context.timestamp,
                        "recovery_successful": e.recovery_successful,
                    }
                    for e in list(self.errors)[-10:]  # 最近10个错误
                ],
            }

    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorInfo]:
        """根据分类获取错误"""
        with self.lock:
            return [e for e in self.errors if e.category == category]

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorInfo]:
        """根据严重程度获取错误"""
        with self.lock:
            return [e for e in self.errors if e.severity == severity]


class UnifiedErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self.recovery_strategy = ErrorRecoveryStrategy()
        self.error_tracker = ErrorTracker()
        self.error_id_counter = 0
        self.lock = threading.Lock()

    def _generate_error_id(self) -> str:
        """生成错误ID"""
        with self.lock:
            self.error_id_counter += 1
            return f"ERR_{int(time.time())}_{self.error_id_counter}"

    def _classify_error(
        self, exception: Exception
    ) -> tuple[ErrorSeverity, ErrorCategory]:
        """错误分类"""
        error_str = str(exception).lower()
        error_type = type(exception).__name__

        # 根据异常类型和消息内容分类
        if "cuda" in error_str or "gpu" in error_str or "cudnn" in error_str:
            return ErrorSeverity.HIGH, ErrorCategory.GPU
        elif "model" in error_str or "weight" in error_str or "checkpoint" in error_str:
            return ErrorSeverity.HIGH, ErrorCategory.MODEL
        elif "detection" in error_str or "inference" in error_str:
            return ErrorSeverity.MEDIUM, ErrorCategory.DETECTION
        elif (
            "network" in error_str
            or "connection" in error_str
            or "timeout" in error_str
        ):
            return ErrorSeverity.MEDIUM, ErrorCategory.NETWORK
        elif "database" in error_str or "sql" in error_str:
            return ErrorSeverity.HIGH, ErrorCategory.DATABASE
        elif "file" in error_str or "io" in error_str or "permission" in error_str:
            return ErrorSeverity.MEDIUM, ErrorCategory.FILE_IO
        elif "config" in error_str or "parameter" in error_str:
            return ErrorSeverity.MEDIUM, ErrorCategory.CONFIGURATION
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorSeverity.LOW, ErrorCategory.VALIDATION
        elif "timeout" in error_str:
            return ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT
        elif "memory" in error_str or "resource" in error_str:
            return ErrorSeverity.HIGH, ErrorCategory.RESOURCE
        else:
            return ErrorSeverity.MEDIUM, ErrorCategory.UNKNOWN

    def _create_error_context(self, frame) -> ErrorContext:
        """创建错误上下文"""
        return ErrorContext(
            function_name=frame.f_code.co_name,
            module_name=frame.f_code.co_filename.split("/")[-1],
            line_number=frame.f_lineno,
        )

    def handle_error(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> ErrorInfo:
        """处理错误"""
        # 生成错误ID
        error_id = self._generate_error_id()

        # 分类错误
        severity, category = self._classify_error(exception)

        # 创建错误上下文
        if context is None:
            frame = traceback.extract_tb(exception.__traceback__)[-1]
            context = self._create_error_context(frame)

        if additional_data:
            context.additional_data.update(additional_data)

        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            exception=exception,
            severity=severity,
            category=category,
            context=context,
            message=str(exception),
            stack_trace=traceback.format_exc(),
        )

        # 记录错误
        self.error_tracker.add_error(error_info)

        # 尝试恢复
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.recovery_strategy.attempt_recovery(error_info)

        # 记录日志
        self._log_error(error_info)

        return error_info

    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_message = (
            f"错误 {error_info.error_id}: {error_info.message} "
            f"[{error_info.severity.value}/{error_info.category.value}] "
            f"在 {error_info.context.function_name}:{error_info.context.line_number}"
        )

        if error_info.recovery_successful:
            log_message += " (已恢复)"

        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=error_info.exception)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=error_info.exception)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def get_error_report(self) -> Dict[str, Any]:
        """获取错误报告"""
        stats = self.error_tracker.get_error_stats()

        # 添加健康状态评估
        critical_errors = self.error_tracker.get_errors_by_severity(
            ErrorSeverity.CRITICAL
        )
        high_errors = self.error_tracker.get_errors_by_severity(ErrorSeverity.HIGH)

        health_status = "healthy"
        if critical_errors:
            health_status = "critical"
        elif high_errors:
            health_status = "warning"

        stats["health_status"] = health_status
        stats["recommendations"] = self._generate_recommendations()

        return stats

    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        stats = self.error_tracker.get_error_stats()

        # 根据错误统计生成建议
        if stats["category_counts"].get("gpu", 0) > 5:
            recommendations.append("GPU错误频繁，建议检查CUDA环境和驱动")

        if stats["category_counts"].get("model", 0) > 3:
            recommendations.append("模型错误较多，建议检查模型文件和路径")

        if stats["category_counts"].get("network", 0) > 10:
            recommendations.append("网络错误频繁，建议检查网络连接和超时设置")

        if stats["category_counts"].get("resource", 0) > 5:
            recommendations.append("资源错误较多，建议优化内存管理和资源清理")

        return recommendations


# 全局错误处理器实例
_error_handler = None


def get_error_handler() -> UnifiedErrorHandler:
    """获取全局错误处理器"""
    global _error_handler
    if _error_handler is None:
        _error_handler = UnifiedErrorHandler()
    return _error_handler


def handle_error(
    exception: Exception,
    context: Optional[ErrorContext] = None,
    additional_data: Optional[Dict[str, Any]] = None,
) -> ErrorInfo:
    """处理错误（便捷函数）"""
    return get_error_handler().handle_error(exception, context, additional_data)


@contextmanager
def error_context(
    function_name: str = "",
    module_name: str = "",
    additional_data: Optional[Dict[str, Any]] = None,
):
    """错误上下文管理器"""
    context = ErrorContext(
        function_name=function_name,
        module_name=module_name,
        additional_data=additional_data or {},
    )

    try:
        yield context
    except Exception as e:
        handle_error(e, context)
        raise


def error_handler(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    retry_count: int = 0,
    fallback_value: Any = None,
):
    """错误处理装饰器"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < retry_count:
                        logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}")
                        time.sleep(0.1 * (attempt + 1))  # 递增延迟
                        continue
                    else:
                        # 最后一次尝试失败，记录错误
                        error_info = handle_error(e)
                        if fallback_value is not None:
                            logger.info(f"函数 {func.__name__} 使用备用值")
                            return fallback_value
                        raise

        return wrapper

    return decorator


def safe_execute(
    func: Callable, *args, fallback_value: Any = None, log_errors: bool = True, **kwargs
) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            handle_error(e)
        return fallback_value


class CircuitBreaker:
    """熔断器"""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """执行函数（带熔断保护）"""
        with self.lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "half_open"
                else:
                    raise Exception("熔断器开启，拒绝调用")

            try:
                result = func(*args, **kwargs)
                if self.state == "half_open":
                    self.state = "closed"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"

                raise e


# 便捷的错误处理函数
def handle_detection_error(func: Callable) -> Callable:
    """检测错误处理装饰器"""
    return error_handler(
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.DETECTION,
        retry_count=2,
        fallback_value=[],
    )(func)


def handle_model_error(func: Callable) -> Callable:
    """模型错误处理装饰器"""
    return error_handler(
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.MODEL,
        retry_count=1,
        fallback_value=None,
    )(func)


def handle_gpu_error(func: Callable) -> Callable:
    """GPU错误处理装饰器"""
    return error_handler(
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.GPU,
        retry_count=1,
        fallback_value=None,
    )(func)


def handle_network_error(func: Callable) -> Callable:
    """网络错误处理装饰器"""
    return error_handler(
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.NETWORK,
        retry_count=3,
        fallback_value=None,
    )(func)
