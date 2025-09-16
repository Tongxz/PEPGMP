"""
结构化日志系统
Structured Logging System

提供结构化日志记录、日志分析、日志聚合和可视化功能
"""

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类"""

    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    AUDIT = "audit"


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    thread_id: int = 0
    process_id: int = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    exception_info: Optional[str] = None


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_stack_trace: bool = True):
        super().__init__()
        self.include_stack_trace = include_stack_trace

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 创建日志条目
        log_entry = LogEntry(
            timestamp=record.created,
            level=LogLevel(record.levelname),
            category=getattr(record, "category", LogCategory.APPLICATION),
            message=record.getMessage(),
            module=record.module or "",
            function=record.funcName or "",
            line_number=record.lineno or 0,
            thread_id=record.thread or 0,
            process_id=record.process or 0,
            user_id=getattr(record, "user_id", None),
            session_id=getattr(record, "session_id", None),
            request_id=getattr(record, "request_id", None),
            correlation_id=getattr(record, "correlation_id", None),
            extra_data=getattr(record, "extra_data", {}),
            exception_info=self._format_exception(record) if record.exc_info else None,
        )

        return self._serialize_log_entry(log_entry)

    def _format_exception(self, record: logging.LogRecord) -> str:
        """格式化异常信息"""
        if not record.exc_info:
            return None

        import traceback

        return traceback.format_exception(*record.exc_info)

    def _serialize_log_entry(self, log_entry: LogEntry) -> str:
        """序列化日志条目"""
        # 转换为字典
        log_dict = {
            "timestamp": datetime.fromtimestamp(log_entry.timestamp).isoformat(),
            "level": log_entry.level.value,
            "category": log_entry.category.value,
            "message": log_entry.message,
            "module": log_entry.module,
            "function": log_entry.function,
            "line_number": log_entry.line_number,
            "thread_id": log_entry.thread_id,
            "process_id": log_entry.process_id,
        }

        # 添加可选字段
        if log_entry.user_id:
            log_dict["user_id"] = log_entry.user_id
        if log_entry.session_id:
            log_dict["session_id"] = log_entry.session_id
        if log_entry.request_id:
            log_dict["request_id"] = log_entry.request_id
        if log_entry.correlation_id:
            log_dict["correlation_id"] = log_entry.correlation_id
        if log_entry.extra_data:
            log_dict["extra_data"] = log_entry.extra_data
        if log_entry.exception_info:
            log_dict["exception_info"] = log_entry.exception_info

        return json.dumps(log_dict, ensure_ascii=False)


class LogAnalyzer:
    """日志分析器"""

    def __init__(self, max_entries: int = 100000):
        self.max_entries = max_entries
        self.log_entries: deque = deque(maxlen=max_entries)
        self.lock = threading.Lock()

    def add_log_entry(self, log_entry: LogEntry):
        """添加日志条目"""
        with self.lock:
            self.log_entries.append(log_entry)

    def analyze_logs(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        module: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分析日志"""
        with self.lock:
            filtered_entries = list(self.log_entries)

        # 时间过滤
        if start_time:
            filtered_entries = [
                e for e in filtered_entries if e.timestamp >= start_time
            ]
        if end_time:
            filtered_entries = [e for e in filtered_entries if e.timestamp <= end_time]

        # 级别过滤
        if level:
            filtered_entries = [e for e in filtered_entries if e.level == level]

        # 分类过滤
        if category:
            filtered_entries = [e for e in filtered_entries if e.category == category]

        # 模块过滤
        if module:
            filtered_entries = [e for e in filtered_entries if module in e.module]

        # 统计分析
        total_count = len(filtered_entries)
        if total_count == 0:
            return {"total_count": 0}

        # 按级别统计
        level_counts = defaultdict(int)
        for entry in filtered_entries:
            level_counts[entry.level.value] += 1

        # 按分类统计
        category_counts = defaultdict(int)
        for entry in filtered_entries:
            category_counts[entry.category.value] += 1

        # 按模块统计
        module_counts = defaultdict(int)
        for entry in filtered_entries:
            module_counts[entry.module] += 1

        # 错误分析
        error_entries = [
            e
            for e in filtered_entries
            if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]
        error_patterns = self._analyze_error_patterns(error_entries)

        # 性能分析
        performance_entries = [
            e for e in filtered_entries if e.category == LogCategory.PERFORMANCE
        ]
        performance_stats = self._analyze_performance(performance_entries)

        return {
            "total_count": total_count,
            "time_range": {
                "start": min(e.timestamp for e in filtered_entries)
                if filtered_entries
                else None,
                "end": max(e.timestamp for e in filtered_entries)
                if filtered_entries
                else None,
            },
            "level_distribution": dict(level_counts),
            "category_distribution": dict(category_counts),
            "module_distribution": dict(module_counts),
            "error_analysis": error_patterns,
            "performance_stats": performance_stats,
        }

    def _analyze_error_patterns(self, error_entries: List[LogEntry]) -> Dict[str, Any]:
        """分析错误模式"""
        if not error_entries:
            return {}

        # 错误消息频率
        error_messages = defaultdict(int)
        for entry in error_entries:
            error_messages[entry.message] += 1

        # 错误模块频率
        error_modules = defaultdict(int)
        for entry in error_entries:
            error_modules[entry.module] += 1

        # 异常类型分析
        exception_types = defaultdict(int)
        for entry in error_entries:
            if entry.exception_info:
                # 提取异常类型
                exception_line = entry.exception_info[0] if entry.exception_info else ""
                if ":" in exception_line:
                    exception_type = exception_line.split(":")[0].strip()
                    exception_types[exception_type] += 1

        return {
            "total_errors": len(error_entries),
            "unique_error_messages": len(error_messages),
            "most_common_errors": sorted(
                error_messages.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "error_by_module": dict(error_modules),
            "exception_types": dict(exception_types),
        }

    def _analyze_performance(
        self, performance_entries: List[LogEntry]
    ) -> Dict[str, Any]:
        """分析性能日志"""
        if not performance_entries:
            return {}

        # 提取性能数据
        performance_data = []
        for entry in performance_entries:
            if "duration" in entry.extra_data:
                performance_data.append(entry.extra_data["duration"])
            elif "response_time" in entry.extra_data:
                performance_data.append(entry.extra_data["response_time"])

        if not performance_data:
            return {}

        import numpy as np

        return {
            "count": len(performance_data),
            "min": min(performance_data),
            "max": max(performance_data),
            "mean": np.mean(performance_data),
            "median": np.median(performance_data),
            "p95": np.percentile(performance_data, 95),
            "p99": np.percentile(performance_data, 99),
        }


class LogAggregator:
    """日志聚合器"""

    def __init__(self, analyzer: LogAnalyzer):
        self.analyzer = analyzer
        self.aggregation_rules: List[Dict[str, Any]] = []

    def add_aggregation_rule(self, rule: Dict[str, Any]):
        """添加聚合规则"""
        self.aggregation_rules.append(rule)

    def aggregate_logs(
        self, time_window: int = 3600, group_by: List[str] = None  # 1小时
    ) -> Dict[str, Any]:
        """聚合日志"""
        current_time = time.time()
        start_time = current_time - time_window

        # 获取时间窗口内的日志
        logs = self.analyzer.analyze_logs(start_time=start_time, end_time=current_time)

        # 按指定字段分组
        if group_by:
            grouped_data = self._group_logs(logs, group_by)
            logs["grouped_data"] = grouped_data

        return logs

    def _group_logs(self, logs: Dict[str, Any], group_by: List[str]) -> Dict[str, Any]:
        """按字段分组日志"""
        # 这里可以实现更复杂的分组逻辑
        return {"group_by": group_by, "data": logs}


class LogVisualizer:
    """日志可视化器"""

    def __init__(self, analyzer: LogAnalyzer):
        self.analyzer = analyzer

    def generate_log_report(
        self, start_time: Optional[float] = None, end_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """生成日志报告"""
        analysis = self.analyzer.analyze_logs(start_time=start_time, end_time=end_time)

        # 生成趋势数据
        trends = self._generate_trends(start_time, end_time)

        # 生成热点分析
        hotspots = self._generate_hotspots(analysis)

        # 生成异常检测
        anomalies = self._detect_anomalies(analysis)

        return {
            "summary": analysis,
            "trends": trends,
            "hotspots": hotspots,
            "anomalies": anomalies,
            "recommendations": self._generate_recommendations(analysis),
        }

    def _generate_trends(
        self, start_time: Optional[float], end_time: Optional[float]
    ) -> Dict[str, Any]:
        """生成趋势数据"""
        # 按小时分组统计
        hourly_data = {}

        with self.analyzer.lock:
            entries = list(self.analyzer.log_entries)

        if start_time and end_time:
            entries = [e for e in entries if start_time <= e.timestamp <= end_time]

        for entry in entries:
            hour = int(entry.timestamp // 3600) * 3600
            if hour not in hourly_data:
                hourly_data[hour] = {"total": 0, "errors": 0, "warnings": 0}

            hourly_data[hour]["total"] += 1
            if entry.level == LogLevel.ERROR:
                hourly_data[hour]["errors"] += 1
            elif entry.level == LogLevel.WARNING:
                hourly_data[hour]["warnings"] += 1

        return {"hourly": hourly_data}

    def _generate_hotspots(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成热点分析"""
        hotspots = {
            "error_hotspots": analysis.get("error_analysis", {}).get(
                "most_common_errors", []
            )[:5],
            "module_hotspots": sorted(
                analysis.get("module_distribution", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
            "category_hotspots": sorted(
                analysis.get("category_distribution", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }

        return hotspots

    def _detect_anomalies(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """检测异常"""
        anomalies = []

        # 检测错误率异常
        error_count = analysis.get("level_distribution", {}).get("ERROR", 0)
        total_count = analysis.get("total_count", 1)
        error_rate = error_count / total_count

        if error_rate > 0.1:  # 错误率超过10%
            anomalies.append(
                {
                    "type": "high_error_rate",
                    "severity": "warning",
                    "description": f"错误率过高: {error_rate:.2%}",
                    "recommendation": "检查系统状态和错误日志",
                }
            )

        # 检测性能异常
        performance_stats = analysis.get("performance_stats", {})
        if performance_stats.get("p95", 0) > 5.0:  # 95%分位数超过5秒
            anomalies.append(
                {
                    "type": "performance_degradation",
                    "severity": "warning",
                    "description": f"性能下降: P95响应时间 {performance_stats['p95']:.2f}秒",
                    "recommendation": "优化性能瓶颈",
                }
            )

        return {"anomalies": anomalies}

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于错误分析的建议
        error_analysis = analysis.get("error_analysis", {})
        if error_analysis.get("total_errors", 0) > 100:
            recommendations.append("错误数量较多，建议增加错误处理和监控")

        # 基于性能分析的建议
        performance_stats = analysis.get("performance_stats", {})
        if performance_stats.get("mean", 0) > 2.0:
            recommendations.append("平均响应时间较长，建议优化性能")

        # 基于模块分布的建议
        module_distribution = analysis.get("module_distribution", {})
        if len(module_distribution) > 20:
            recommendations.append("模块数量较多，建议重构和模块化")

        return recommendations


class StructuredLoggingSystem:
    """结构化日志系统"""

    def __init__(
        self,
        log_dir: str = "logs",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 5,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.analyzer = LogAnalyzer()
        self.aggregator = LogAggregator(self.analyzer)
        self.visualizer = LogVisualizer(self.analyzer)

        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: List[logging.Handler] = []

        self._setup_logging()

    def _setup_logging(self):
        """设置日志系统"""
        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 创建文件处理器
        log_file = self.log_dir / "application.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        self.handlers.append(file_handler)

        # 创建错误日志文件处理器
        error_log_file = self.log_dir / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
        self.handlers.append(error_handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
        self.handlers.append(console_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]

    def log_with_context(
        self,
        logger: logging.Logger,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.APPLICATION,
        **kwargs,
    ):
        """带上下文的日志记录"""
        extra = {"category": category, **kwargs}

        getattr(logger, level.value.lower())(message, extra=extra)

    def get_log_analysis(self, **kwargs) -> Dict[str, Any]:
        """获取日志分析"""
        return self.analyzer.analyze_logs(**kwargs)

    def get_log_report(self, **kwargs) -> Dict[str, Any]:
        """获取日志报告"""
        return self.visualizer.generate_log_report(**kwargs)

    def aggregate_logs(self, **kwargs) -> Dict[str, Any]:
        """聚合日志"""
        return self.aggregator.aggregate_logs(**kwargs)


# 全局日志系统实例
_logging_system: Optional[StructuredLoggingSystem] = None


def get_logging_system() -> StructuredLoggingSystem:
    """获取全局日志系统"""
    global _logging_system
    if _logging_system is None:
        _logging_system = StructuredLoggingSystem()
    return _logging_system


def get_structured_logger(name: str) -> logging.Logger:
    """获取结构化日志记录器（便捷函数）"""
    system = get_logging_system()
    return system.get_logger(name)


def log_with_context(
    logger: logging.Logger,
    level: LogLevel,
    message: str,
    category: LogCategory = LogCategory.APPLICATION,
    **kwargs,
):
    """带上下文的日志记录（便捷函数）"""
    system = get_logging_system()
    system.log_with_context(logger, level, message, category, **kwargs)


# 使用示例
if __name__ == "__main__":
    # 获取日志系统
    logging_system = get_logging_system()

    # 获取日志记录器
    logger = logging_system.get_logger("test_module")

    # 记录日志
    logging_system.log_with_context(
        logger,
        LogLevel.INFO,
        "测试消息",
        LogCategory.APPLICATION,
        user_id="user123",
        request_id="req456",
    )

    # 获取日志分析
    analysis = logging_system.get_log_analysis()
    print(f"日志分析: {analysis}")

    # 获取日志报告
    report = logging_system.get_log_report()
    print(f"日志报告: {report}")
