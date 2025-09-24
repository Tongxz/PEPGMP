"""
高级监控系统
Advanced Monitoring System

提供全面的系统监控、性能指标收集、实时告警和可视化功能
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import psutil

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""

    COUNTER = "counter"  # 计数器
    GAUGE = "gauge"  # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"  # 摘要


class AlertSeverity(Enum):
    """告警严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """指标数据"""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    metric_name: str
    condition: str  # 条件表达式，如 "value > 80"
    severity: AlertSeverity
    duration: int = 0  # 持续时间（秒）
    enabled: bool = True
    last_triggered: float = 0
    cooldown: int = 300  # 冷却时间（秒）


@dataclass
class Alert:
    """告警"""

    alert_id: str
    rule_name: str
    metric_name: str
    value: float
    threshold: float
    severity: AlertSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: Optional[float] = None


class MetricCollector:
    """指标收集器"""

    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.lock = threading.Lock()

    def record_metric(self, metric: MetricData):
        """记录指标"""
        with self.lock:
            self.metrics[metric.name].append(metric)

    def get_metric(self, name: str, duration: int = 3600) -> List[MetricData]:
        """获取指标数据"""
        cutoff_time = time.time() - duration

        with self.lock:
            return [
                metric
                for metric in self.metrics[name]
                if metric.timestamp >= cutoff_time
            ]

    def get_latest_metric(self, name: str) -> Optional[MetricData]:
        """获取最新指标"""
        with self.lock:
            if self.metrics[name]:
                return self.metrics[name][-1]
            return None

    def get_metric_stats(self, name: str, duration: int = 3600) -> Dict[str, float]:
        """获取指标统计"""
        metrics = self.get_metric(name, duration)
        if not metrics:
            return {}

        values = [m.value for m in metrics]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": np.mean(values),
            "median": np.median(values),
            "std": np.std(values),
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99),
        }


class SystemMetricsCollector:
    """系统指标收集器"""

    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.running = False
        self.collection_thread: Optional[threading.Thread] = None

    def start(self, interval: float = 10.0):
        """启动系统指标收集"""
        if self.running:
            return

        self.running = True
        self.collection_thread = threading.Thread(
            target=self._collect_loop, args=(interval,), daemon=True
        )
        self.collection_thread.start()
        logger.info("系统指标收集已启动")

    def stop(self):
        """停止系统指标收集"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("系统指标收集已停止")

    def _collect_loop(self, interval: float):
        """收集循环"""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"系统指标收集错误: {e}")
                time.sleep(interval)

    def _collect_system_metrics(self):
        """收集系统指标"""
        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=1)
        self.collector.record_metric(
            MetricData(
                name="system.cpu.usage", value=cpu_percent, metric_type=MetricType.GAUGE
            )
        )

        # 内存指标
        memory = psutil.virtual_memory()
        self.collector.record_metric(
            MetricData(
                name="system.memory.usage",
                value=memory.percent,
                metric_type=MetricType.GAUGE,
            )
        )

        self.collector.record_metric(
            MetricData(
                name="system.memory.available",
                value=memory.available / (1024**3),  # GB
                metric_type=MetricType.GAUGE,
            )
        )

        # 磁盘指标
        disk = psutil.disk_usage("/")
        self.collector.record_metric(
            MetricData(
                name="system.disk.usage",
                value=disk.percent,
                metric_type=MetricType.GAUGE,
            )
        )

        # 网络指标
        network = psutil.net_io_counters()
        self.collector.record_metric(
            MetricData(
                name="system.network.bytes_sent",
                value=network.bytes_sent,
                metric_type=MetricType.COUNTER,
            )
        )

        self.collector.record_metric(
            MetricData(
                name="system.network.bytes_recv",
                value=network.bytes_recv,
                metric_type=MetricType.COUNTER,
            )
        )

        # 进程指标
        process = psutil.Process()
        self.collector.record_metric(
            MetricData(
                name="system.process.cpu_percent",
                value=process.cpu_percent(),
                metric_type=MetricType.GAUGE,
            )
        )

        self.collector.record_metric(
            MetricData(
                name="system.process.memory_percent",
                value=process.memory_percent(),
                metric_type=MetricType.GAUGE,
            )
        )


class ApplicationMetricsCollector:
    """应用指标收集器"""

    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.request_count = 0
        self.error_count = 0
        self.response_times: deque = deque(maxlen=1000)

    def record_request(self, response_time: float, status_code: int):
        """记录请求"""
        self.request_count += 1

        # 记录响应时间
        self.response_times.append(response_time)

        # 记录请求指标
        self.collector.record_metric(
            MetricData(
                name="app.requests.total",
                value=self.request_count,
                metric_type=MetricType.COUNTER,
            )
        )

        self.collector.record_metric(
            MetricData(
                name="app.requests.response_time",
                value=response_time,
                metric_type=MetricType.HISTOGRAM,
            )
        )

        # 记录状态码指标
        self.collector.record_metric(
            MetricData(
                name="app.requests.status_code",
                value=status_code,
                labels={"status": str(status_code)},
                metric_type=MetricType.COUNTER,
            )
        )

        if status_code >= 400:
            self.error_count += 1
            self.collector.record_metric(
                MetricData(
                    name="app.requests.errors",
                    value=self.error_count,
                    metric_type=MetricType.COUNTER,
                )
            )

    def record_detection(self, detection_time: float, detection_count: int):
        """记录检测指标"""
        self.collector.record_metric(
            MetricData(
                name="app.detection.time",
                value=detection_time,
                metric_type=MetricData.HISTOGRAM,
            )
        )

        self.collector.record_metric(
            MetricData(
                name="app.detection.count",
                value=detection_count,
                metric_type=MetricType.COUNTER,
            )
        )

    def record_model_inference(self, model_name: str, inference_time: float):
        """记录模型推理指标"""
        self.collector.record_metric(
            MetricData(
                name="app.model.inference_time",
                value=inference_time,
                labels={"model": model_name},
                metric_type=MetricType.HISTOGRAM,
            )
        )


class AlertManager:
    """告警管理器"""

    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.running = False
        self.check_thread: Optional[threading.Thread] = None

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules[rule.name] = rule
        logger.info(f"告警规则已添加: {rule.name}")

    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"告警规则已移除: {rule_name}")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)

    def start(self, check_interval: float = 30.0):
        """启动告警检查"""
        if self.running:
            return

        self.running = True
        self.check_thread = threading.Thread(
            target=self._check_loop, args=(check_interval,), daemon=True
        )
        self.check_thread.start()
        logger.info("告警管理器已启动")

    def stop(self):
        """停止告警检查"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("告警管理器已停止")

    def _check_loop(self, interval: float):
        """检查循环"""
        while self.running:
            try:
                self._check_rules()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"告警检查错误: {e}")
                time.sleep(interval)

    def _check_rules(self):
        """检查告警规则"""
        current_time = time.time()

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            # 检查冷却时间
            if current_time - rule.last_triggered < rule.cooldown:
                continue

            # 获取最新指标
            metric = self.collector.get_latest_metric(rule.metric_name)
            if not metric:
                continue

            # 检查条件
            if self._evaluate_condition(rule.condition, metric.value):
                self._trigger_alert(rule, metric.value)
                rule.last_triggered = current_time

    def _evaluate_condition(self, condition: str, value: float) -> bool:
        """评估条件"""
        try:
            # 简单的条件评估（实际项目中可以使用更复杂的表达式解析器）
            if ">" in condition:
                threshold = float(condition.split(">")[1].strip())
                return value > threshold
            elif "<" in condition:
                threshold = float(condition.split("<")[1].strip())
                return value < threshold
            elif ">=" in condition:
                threshold = float(condition.split(">=")[1].strip())
                return value >= threshold
            elif "<=" in condition:
                threshold = float(condition.split("<=")[1].strip())
                return value <= threshold
            elif "==" in condition:
                threshold = float(condition.split("==")[1].strip())
                return value == threshold
            else:
                return False
        except Exception as e:
            logger.error(f"条件评估失败: {condition}, 错误: {e}")
            return False

    def _trigger_alert(self, rule: AlertRule, value: float):
        """触发告警"""
        alert_id = f"alert_{int(time.time())}_{rule.name}"

        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            metric_name=rule.metric_name,
            value=value,
            threshold=self._extract_threshold(rule.condition),
            severity=rule.severity,
            message=f"指标 {rule.metric_name} 触发告警: {value} {rule.condition}",
        )

        self.active_alerts[alert_id] = alert

        # 触发告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")

        logger.warning(f"告警触发: {alert.message}")

    def _extract_threshold(self, condition: str) -> float:
        """提取阈值"""
        try:
            for op in [">=", "<=", ">", "<", "=="]:
                if op in condition:
                    return float(condition.split(op)[1].strip())
            return 0.0
        except:
            return 0.0

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()
            logger.info(f"告警已解决: {alert_id}")


class MonitoringDashboard:
    """监控仪表板"""

    def __init__(self, collector: MetricCollector, alert_manager: AlertManager):
        self.collector = collector
        self.alert_manager = alert_manager

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        current_time = time.time()

        # 系统指标
        system_metrics = {
            "cpu": self._get_metric_summary("system.cpu.usage"),
            "memory": self._get_metric_summary("system.memory.usage"),
            "disk": self._get_metric_summary("system.disk.usage"),
            "network": {
                "bytes_sent": self._get_metric_summary("system.network.bytes_sent"),
                "bytes_recv": self._get_metric_summary("system.network.bytes_recv"),
            },
        }

        # 应用指标
        app_metrics = {
            "requests": {
                "total": self._get_metric_summary("app.requests.total"),
                "response_time": self._get_metric_summary("app.requests.response_time"),
                "errors": self._get_metric_summary("app.requests.errors"),
            },
            "detection": {
                "time": self._get_metric_summary("app.detection.time"),
                "count": self._get_metric_summary("app.detection.count"),
            },
        }

        # 告警状态
        alert_status = {
            "active_alerts": len(self.alert_manager.active_alerts),
            "critical_alerts": len(
                [
                    alert
                    for alert in self.alert_manager.active_alerts.values()
                    if alert.severity == AlertSeverity.CRITICAL
                ]
            ),
            "warning_alerts": len(
                [
                    alert
                    for alert in self.alert_manager.active_alerts.values()
                    if alert.severity == AlertSeverity.WARNING
                ]
            ),
        }

        return {
            "timestamp": current_time,
            "system_metrics": system_metrics,
            "app_metrics": app_metrics,
            "alert_status": alert_status,
            "health_score": self._calculate_health_score(
                system_metrics, app_metrics, alert_status
            ),
        }

    def _get_metric_summary(self, metric_name: str) -> Dict[str, Any]:
        """获取指标摘要"""
        stats = self.collector.get_metric_stats(metric_name, 3600)  # 最近1小时
        latest = self.collector.get_latest_metric(metric_name)

        return {"current": latest.value if latest else 0, "stats": stats}

    def _calculate_health_score(
        self, system_metrics: Dict, app_metrics: Dict, alert_status: Dict
    ) -> int:
        """计算健康分数"""
        score = 100

        # 系统指标影响
        cpu_usage = system_metrics["cpu"]["current"]
        memory_usage = system_metrics["memory"]["current"]
        disk_usage = system_metrics["disk"]["current"]

        if cpu_usage > 90:
            score -= 20
        elif cpu_usage > 80:
            score -= 10

        if memory_usage > 90:
            score -= 20
        elif memory_usage > 80:
            score -= 10

        if disk_usage > 90:
            score -= 15
        elif disk_usage > 80:
            score -= 5

        # 告警影响
        score -= alert_status["critical_alerts"] * 30
        score -= alert_status["warning_alerts"] * 10

        return max(0, min(100, score))


class AdvancedMonitoringSystem:
    """高级监控系统"""

    def __init__(self):
        self.collector = MetricCollector()
        self.system_collector = SystemMetricsCollector(self.collector)
        self.app_collector = ApplicationMetricsCollector(self.collector)
        self.alert_manager = AlertManager(self.collector)
        self.dashboard = MonitoringDashboard(self.collector, self.alert_manager)

        # 设置默认告警规则
        self._setup_default_rules()

        # 设置默认告警处理器
        self._setup_default_handlers()

    def _setup_default_rules(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="system.cpu.usage",
                condition="value > 80",
                severity=AlertSeverity.WARNING,
                cooldown=300,
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="system.memory.usage",
                condition="value > 85",
                severity=AlertSeverity.WARNING,
                cooldown=300,
            ),
            AlertRule(
                name="high_disk_usage",
                metric_name="system.disk.usage",
                condition="value > 90",
                severity=AlertSeverity.ERROR,
                cooldown=600,
            ),
            AlertRule(
                name="high_response_time",
                metric_name="app.requests.response_time",
                condition="value > 5.0",
                severity=AlertSeverity.WARNING,
                cooldown=300,
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="app.requests.errors",
                condition="value > 10",
                severity=AlertSeverity.ERROR,
                cooldown=300,
            ),
        ]

        for rule in default_rules:
            self.alert_manager.add_rule(rule)

    def _setup_default_handlers(self):
        """设置默认告警处理器"""

        def log_alert_handler(alert: Alert):
            logger.warning(f"告警: {alert.message}")

        self.alert_manager.add_alert_handler(log_alert_handler)

    def start(self):
        """启动监控系统"""
        self.system_collector.start()
        self.alert_manager.start()
        logger.info("高级监控系统已启动")

    def stop(self):
        """停止监控系统"""
        self.system_collector.stop()
        self.alert_manager.stop()
        logger.info("高级监控系统已停止")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        return self.dashboard.get_dashboard_data()

    def record_request(self, response_time: float, status_code: int):
        """记录请求"""
        self.app_collector.record_request(response_time, status_code)

    def record_detection(self, detection_time: float, detection_count: int):
        """记录检测"""
        self.app_collector.record_detection(detection_time, detection_count)

    def record_model_inference(self, model_name: str, inference_time: float):
        """记录模型推理"""
        self.app_collector.record_model_inference(model_name, inference_time)


# 全局监控系统实例
_monitoring_system: Optional[AdvancedMonitoringSystem] = None


def get_monitoring_system() -> AdvancedMonitoringSystem:
    """获取全局监控系统"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = AdvancedMonitoringSystem()
    return _monitoring_system


def start_monitoring():
    """启动监控（便捷函数）"""
    system = get_monitoring_system()
    system.start()


def stop_monitoring():
    """停止监控（便捷函数）"""
    system = get_monitoring_system()
    system.stop()


def record_request(response_time: float, status_code: int):
    """记录请求（便捷函数）"""
    system = get_monitoring_system()
    system.record_request(response_time, status_code)


def record_detection(detection_time: float, detection_count: int):
    """记录检测（便捷函数）"""
    system = get_monitoring_system()
    system.record_detection(detection_time, detection_count)


# 使用示例
if __name__ == "__main__":
    # 启动监控系统
    monitoring = get_monitoring_system()
    monitoring.start()

    # 模拟一些指标
    monitoring.record_request(0.5, 200)
    monitoring.record_request(1.2, 404)
    monitoring.record_detection(0.8, 3)

    # 获取仪表板数据
    dashboard_data = monitoring.get_dashboard_data()
    print(f"仪表板数据: {json.dumps(dashboard_data, indent=2)}")

    # 停止监控
    monitoring.stop()
