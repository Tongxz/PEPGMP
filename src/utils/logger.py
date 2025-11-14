# Logging utilities
# 日志工具模块

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


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


def get_logger(
    name: str = "HumanBehaviorDetection",
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_category: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    获取配置好的日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
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

    logger.setLevel(getattr(logging, level.upper()))

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
