# Logging utilities
# 日志工具模块

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class LogThrottler:
    """日志节流器，控制高频日志的输出频率.

    用于减少高频操作的日志输出，避免日志洪水。

    Example:
        >>> throttler = LogThrottler(interval=30)
        >>> for i in range(100):
        ...     should_log, count = throttler.should_log("operation")
        ...     if should_log:
        ...         logger.info(f"已处理 {count} 次操作")
    """

    def __init__(self, interval: int = 30, max_keys: int = 100):
        """
        初始化日志节流器.

        Args:
            interval: 每N次操作记录一次日志
            max_keys: 最大key数量，防止内存无限增长
        """
        self.interval = interval
        self.max_keys = max_keys
        self.counters: Dict[str, int] = {}

    def should_log(self, key: str) -> Tuple[bool, int]:
        """
        检查是否应该记录日志.

        Args:
            key: 操作的唯一标识（如 "push_frame_camera_001"）

        Returns:
            (是否记录日志, 当前计数)
        """
        # 防止内存无限增长
        if len(self.counters) >= self.max_keys and key not in self.counters:
            # 清理计数最小的key（最不活跃）
            oldest_key = min(self.counters, key=self.counters.get)  # type: ignore
            del self.counters[oldest_key]

        if key not in self.counters:
            self.counters[key] = 0

        self.counters[key] += 1
        count = self.counters[key]

        if count % self.interval == 0:
            return True, count
        return False, count

    def reset(self, key: str):
        """重置指定key的计数器."""
        if key in self.counters:
            self.counters[key] = 0

    def reset_all(self):
        """重置所有计数器."""
        self.counters.clear()


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_log_level_from_env() -> int:
    """根据环境获取日志级别.

    优先级:
    1. LOG_LEVEL环境变量（如 LOG_LEVEL=DEBUG）
    2. ENV环境变量（development/production/testing）
    3. 默认 INFO

    Returns:
        日志级别常量（logging.DEBUG, logging.INFO等）

    Example:
        >>> import os
        >>> os.environ["ENV"] = "production"
        >>> level = get_log_level_from_env()
        >>> level == logging.INFO
        True
    """
    # 优先使用LOG_LEVEL环境变量
    log_level_str = os.getenv("LOG_LEVEL", "").upper()
    if log_level_str and hasattr(logging, log_level_str):
        return getattr(logging, log_level_str)

    # 根据ENV环境变量自动选择
    env = os.getenv("ENV", "development").lower()
    level_map = {
        "production": logging.INFO,
        "prod": logging.INFO,
        "testing": logging.WARNING,
        "test": logging.WARNING,
        "development": logging.DEBUG,
        "dev": logging.DEBUG,
    }
    return level_map.get(env, logging.INFO)


def get_logger(  # noqa: C901
    name: str = "HumanBehaviorDetection",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_category: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    获取配置好的日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)，
               如果为None则根据环境自动选择
        log_file: 日志文件路径，如果为None则不写入文件
        log_category: 日志分类（detection, api, application, error, event），用于自动构建日志路径
        console_output: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 如果未指定level，使用环境感知的级别
    if level is None:
        log_level = get_log_level_from_env()
    else:
        log_level = getattr(logging, level.upper())

    logger.setLevel(log_level)

    # 如果指定了分类且未指定日志文件，自动构建日志路径
    if log_category and log_file is None:
        log_dir = Path("logs") / log_category
        log_dir.mkdir(parents=True, exist_ok=True)

        # 根据分类构建日志文件名
        if log_category == "detection":
            # 检测日志：从name中提取camera_id（格式：...:camera_id）
            camera_id = name.split(":")[-1] if ":" in name else "default"
            log_file = str(log_dir / f"detect_{camera_id}.log")
        elif log_category == "api":
            log_file = str(log_dir / "api.log")
        elif log_category == "application":
            log_file = str(log_dir / "application.log")
        elif log_category == "error":
            log_file = str(log_dir / "error.log")
        elif log_category == "event":
            log_file = str(log_dir / "events_record.jsonl")
        else:
            log_file = str(log_dir / f"{log_category}.log")

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    colored_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

    # 文件处理器（使用轮转功能）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 根据分类设置不同的轮转参数
        if log_category == "api":
            # API日志：50MB，5个备份
            max_bytes = 50 * 1024 * 1024  # 50MB
            backup_count = 5
        elif log_category == "error":
            # 错误日志：50MB，20个备份（需要保留更长时间）
            max_bytes = 50 * 1024 * 1024  # 50MB
            backup_count = 20
        elif log_category == "detection":
            # 检测日志：100MB，10个备份
            max_bytes = 100 * 1024 * 1024  # 100MB
            backup_count = 10
        else:
            # 默认：100MB，10个备份
            max_bytes = 100 * 1024 * 1024  # 100MB
            backup_count = 10

        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 如果是ERROR级别或以上，同时写入统一错误日志
        if logger.level <= logging.ERROR:
            try:
                setup_error_logger()
                # 创建一个共享的错误处理器，避免重复添加
                root_logger = logging.getLogger()
                error_handler_exists = any(
                    isinstance(h, logging.handlers.RotatingFileHandler)
                    and str(h.baseFilename).endswith("logs/errors/error.log")
                    for h in root_logger.handlers
                )
                if not error_handler_exists:
                    error_handler = logging.handlers.RotatingFileHandler(
                        str(Path("logs/errors/error.log")),
                        maxBytes=50 * 1024 * 1024,
                        backupCount=20,
                        encoding="utf-8",
                    )
                    error_handler.setLevel(logging.ERROR)

                    class ErrorFilter(logging.Filter):
                        def filter(self, record):
                            return record.levelno >= logging.ERROR

                    error_handler.addFilter(ErrorFilter())
                    error_handler.setFormatter(formatter)
                    root_logger.addHandler(error_handler)
            except Exception:
                # 如果错误日志设置失败，不影响主日志功能
                pass

    return logger


def setup_project_logger(log_dir: str = "logs") -> logging.Logger:
    """
    设置项目默认日志记录器

    Args:
        log_dir: 日志目录

    Returns:
        项目日志记录器
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/human_behavior_detection_{timestamp}.log"

    return get_logger(
        name="HumanBehaviorDetection",
        level="INFO",
        log_file=log_file,
        console_output=True,
    )


# 默认日志记录器
default_logger = get_logger()

# 全局日志节流器（用于高频操作）
_global_throttler = LogThrottler(interval=30)


def get_throttler() -> LogThrottler:
    """获取全局日志节流器.

    Returns:
        全局日志节流器实例

    Example:
        >>> from src.utils.logger import get_throttler
        >>> throttler = get_throttler()
        >>> should_log, count = throttler.should_log("operation")
        >>> if should_log:
        ...     logger.info(f"已处理 {count} 次操作")
    """
    return _global_throttler


def setup_error_logger() -> logging.Logger:
    """
    设置统一错误日志记录器

    所有ERROR级别的日志都会写入 logs/errors/error.log

    Returns:
        错误日志记录器
    """
    error_log_dir = Path("logs/errors")
    error_log_dir.mkdir(parents=True, exist_ok=True)

    error_logger = logging.getLogger("error")

    # 避免重复添加处理器
    if error_logger.handlers:
        return error_logger

    error_logger.setLevel(logging.ERROR)

    error_handler = logging.handlers.RotatingFileHandler(
        str(error_log_dir / "error.log"),
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=20,  # 保留20个备份（错误日志需要保留更长时间）
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    error_handler.setFormatter(formatter)
    error_logger.addHandler(error_handler)

    return error_logger


def log_error(
    message: str, exc_info: bool = False, extra_context: Optional[Dict[str, Any]] = None
):
    """
    记录错误到统一错误日志

    Args:
        message: 错误消息
        exc_info: 是否包含异常信息
        extra_context: 额外的上下文信息
    """
    error_logger = setup_error_logger()

    if extra_context:
        context_str = ", ".join(f"{k}={v}" for k, v in extra_context.items())
        message = f"{message} | Context: {context_str}"

    error_logger.error(message, exc_info=exc_info)
