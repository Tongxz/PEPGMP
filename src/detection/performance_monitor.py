"""
性能监控器 - 实时监控检测系统性能并生成优化建议

核心功能：
1. 实时性能监控 - CPU、内存、GPU、FPS等关键指标
2. 性能分析 - 识别性能瓶颈和优化机会
3. 自适应调整 - 根据性能数据自动调整系统参数
4. 性能报告 - 生成详细的性能分析报告
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
    """指标类型枚举"""

    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    GPU_USAGE = "gpu_usage"
    FPS = "fps"
    PROCESSING_TIME = "processing_time"
    FRAME_DROP_RATE = "frame_drop_rate"
    DETECTION_ACCURACY = "detection_accuracy"
    CACHE_HIT_RATE = "cache_hit_rate"


@dataclass
class PerformanceAlert:
    """性能告警数据类"""

    alert_type: str
    severity: str  # critical, warning, info
    message: str
    timestamp: float
    metric_value: float
    threshold: float
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceSnapshot:
    """性能快照数据类"""

    timestamp: float
    metrics: Dict[str, float]
    alerts: List[PerformanceAlert] = field(default_factory=list)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(
        self,
        monitoring_interval: float = 1.0,
        history_size: int = 300,  # 5分钟历史（1秒间隔）
        alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        enable_gpu_monitoring: bool = True,
    ):
        """
        初始化性能监控器

        Args:
            monitoring_interval: 监控间隔（秒）
            history_size: 历史数据大小
            alert_thresholds: 告警阈值配置
            enable_gpu_monitoring: 是否启用GPU监控
        """
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        self.enable_gpu_monitoring = enable_gpu_monitoring

        # 历史数据存储
        self.metric_history = {
            metric_type.value: deque(maxlen=history_size) for metric_type in MetricType
        }
        self.snapshot_history = deque(maxlen=history_size)
        self.alert_history = deque(maxlen=100)

        # 告警阈值
        self.alert_thresholds = alert_thresholds or self._get_default_thresholds()

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()

        # 性能统计
        self.stats = {
            "total_snapshots": 0,
            "total_alerts": 0,
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "avg_fps": 0.0,
            "max_cpu_usage": 0.0,
            "max_memory_usage": 0.0,
            "min_fps": float("inf"),
            "performance_score": 0.0,
        }

        # 回调函数
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []

        logger.info(f"性能监控器初始化: 监控间隔={monitoring_interval}s, 历史大小={history_size}")

    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """获取默认告警阈值"""
        return {
            MetricType.CPU_USAGE.value: {
                "critical": 90.0,
                "warning": 75.0,
                "info": 60.0,
            },
            MetricType.MEMORY_USAGE.value: {
                "critical": 90.0,
                "warning": 80.0,
                "info": 70.0,
            },
            MetricType.GPU_USAGE.value: {
                "critical": 95.0,
                "warning": 85.0,
                "info": 70.0,
            },
            MetricType.FPS.value: {"critical": 5.0, "warning": 10.0, "info": 15.0},
            MetricType.PROCESSING_TIME.value: {
                "critical": 1.0,
                "warning": 0.5,
                "info": 0.2,
            },
            MetricType.FRAME_DROP_RATE.value: {
                "critical": 0.5,
                "warning": 0.3,
                "info": 0.1,
            },
        }

    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            logger.warning("性能监控已在运行")
            return

        self.is_monitoring = True
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()
        logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        self.stop_event.set()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        logger.info("性能监控已停止")

    def _monitoring_loop(self):
        """监控循环"""
        while not self.stop_event.is_set():
            try:
                # 收集性能数据
                snapshot = self._collect_performance_snapshot()

                # 检查告警
                self._check_alerts(snapshot)

                # 更新统计
                self._update_stats(snapshot)

                # 存储快照
                self.snapshot_history.append(snapshot)

                # 等待下次监控
                self.stop_event.wait(self.monitoring_interval)

            except Exception as e:
                logger.error(f"性能监控循环异常: {e}")
                time.sleep(1.0)

    def _collect_performance_snapshot(self) -> PerformanceSnapshot:
        """收集性能快照"""
        timestamp = time.time()
        metrics = {}

        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            metrics[MetricType.CPU_USAGE.value] = cpu_usage
            self.metric_history[MetricType.CPU_USAGE.value].append(
                (timestamp, cpu_usage)
            )

            # 内存使用率
            memory_info = psutil.virtual_memory()
            memory_usage = memory_info.percent
            metrics[MetricType.MEMORY_USAGE.value] = memory_usage
            self.metric_history[MetricType.MEMORY_USAGE.value].append(
                (timestamp, memory_usage)
            )

            # GPU使用率
            if self.enable_gpu_monitoring:
                gpu_usage = self._get_gpu_usage()
                metrics[MetricType.GPU_USAGE.value] = gpu_usage
                self.metric_history[MetricType.GPU_USAGE.value].append(
                    (timestamp, gpu_usage)
                )

            # 其他指标（由外部设置）
            for metric_type in [
                MetricType.FPS,
                MetricType.PROCESSING_TIME,
                MetricType.FRAME_DROP_RATE,
            ]:
                if metric_type.value in metrics:
                    self.metric_history[metric_type.value].append(
                        (timestamp, metrics[metric_type.value])
                    )

        except Exception as e:
            logger.error(f"性能数据收集失败: {e}")

        return PerformanceSnapshot(timestamp=timestamp, metrics=metrics)

    def _get_gpu_usage(self) -> float:
        """获取GPU使用率"""
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return float(utilization.gpu)
        except ImportError:
            return 0.0
        except Exception as e:
            logger.debug(f"GPU使用率获取失败: {e}")
            return 0.0

    def update_metric(self, metric_type: MetricType, value: float):
        """更新指标值"""
        timestamp = time.time()
        self.metric_history[metric_type.value].append((timestamp, value))

    def _check_alerts(self, snapshot: PerformanceSnapshot):
        """检查告警"""
        alerts = []

        for metric_name, value in snapshot.metrics.items():
            if metric_name not in self.alert_thresholds:
                continue

            thresholds = self.alert_thresholds[metric_name]

            # 检查各级别阈值
            for severity, threshold in thresholds.items():
                if self._should_trigger_alert(metric_name, value, threshold, severity):
                    alert = PerformanceAlert(
                        alert_type=metric_name,
                        severity=severity,
                        message=f"{metric_name} {severity}: {value:.2f} > {threshold}",
                        timestamp=snapshot.timestamp,
                        metric_value=value,
                        threshold=threshold,
                        recommendations=self._get_recommendations(
                            metric_name, severity
                        ),
                    )
                    alerts.append(alert)
                    self.alert_history.append(alert)

                    # 触发回调
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"告警回调执行失败: {e}")

        snapshot.alerts = alerts

    def _should_trigger_alert(
        self, metric_name: str, value: float, threshold: float, severity: str
    ) -> bool:
        """判断是否应该触发告警"""
        # 对于FPS，值越低越严重
        if metric_name == MetricType.FPS.value:
            return value < threshold

        # 对于其他指标，值越高越严重
        return value > threshold

    def _get_recommendations(self, metric_name: str, severity: str) -> List[str]:
        """获取优化建议"""
        recommendations = {
            MetricType.CPU_USAGE.value: {
                "critical": [
                    "CPU使用率过高，建议立即增加跳帧率",
                    "考虑降低检测精度或减少检测模块",
                    "检查是否有其他进程占用CPU资源",
                ],
                "warning": ["CPU使用率较高，建议适当增加跳帧率", "考虑优化检测算法"],
                "info": ["CPU使用率正常，但可以进一步优化"],
            },
            MetricType.MEMORY_USAGE.value: {
                "critical": ["内存使用率过高，建议立即清理缓存", "减少批处理大小或模型缓存", "检查内存泄漏"],
                "warning": ["内存使用率较高，建议清理不必要的缓存", "考虑减少历史数据存储"],
                "info": ["内存使用率正常"],
            },
            MetricType.FPS.value: {
                "critical": ["FPS过低，严重影响实时性", "建议大幅增加跳帧率", "检查系统性能瓶颈"],
                "warning": ["FPS较低，建议增加跳帧率", "优化检测流程"],
                "info": ["FPS正常"],
            },
        }

        return recommendations.get(metric_name, {}).get(severity, ["请检查系统配置"])

    def _update_stats(self, snapshot: PerformanceSnapshot):
        """更新统计信息"""
        self.stats["total_snapshots"] += 1
        self.stats["total_alerts"] += len(snapshot.alerts)

        # 更新平均值
        if len(self.metric_history[MetricType.CPU_USAGE.value]) > 0:
            recent_cpu = [
                v
                for _, v in list(self.metric_history[MetricType.CPU_USAGE.value])[-10:]
            ]
            self.stats["avg_cpu_usage"] = np.mean(recent_cpu)
            self.stats["max_cpu_usage"] = max(
                self.stats["max_cpu_usage"], max(recent_cpu)
            )

        if len(self.metric_history[MetricType.MEMORY_USAGE.value]) > 0:
            recent_memory = [
                v
                for _, v in list(self.metric_history[MetricType.MEMORY_USAGE.value])[
                    -10:
                ]
            ]
            self.stats["avg_memory_usage"] = np.mean(recent_memory)
            self.stats["max_memory_usage"] = max(
                self.stats["max_memory_usage"], max(recent_memory)
            )

        if len(self.metric_history[MetricType.FPS.value]) > 0:
            recent_fps = [
                v for _, v in list(self.metric_history[MetricType.FPS.value])[-10:]
            ]
            self.stats["avg_fps"] = np.mean(recent_fps)
            self.stats["min_fps"] = min(self.stats["min_fps"], min(recent_fps))

        # 计算性能评分
        self.stats["performance_score"] = self._calculate_performance_score()

    def _calculate_performance_score(self) -> float:
        """计算性能评分（0-100）"""
        score = 100.0

        # CPU使用率评分
        if self.stats["avg_cpu_usage"] > 80:
            score -= 30
        elif self.stats["avg_cpu_usage"] > 60:
            score -= 15

        # 内存使用率评分
        if self.stats["avg_memory_usage"] > 85:
            score -= 25
        elif self.stats["avg_memory_usage"] > 70:
            score -= 10

        # FPS评分
        if self.stats["avg_fps"] < 10:
            score -= 40
        elif self.stats["avg_fps"] < 15:
            score -= 20

        return max(0.0, min(100.0, score))

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def get_performance_report(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """获取性能报告"""
        current_time = time.time()
        start_time = current_time - (duration_minutes * 60)

        # 过滤时间范围内的数据
        recent_snapshots = [
            s for s in self.snapshot_history if s.timestamp >= start_time
        ]

        if not recent_snapshots:
            return {"error": "没有足够的历史数据"}

        # 计算统计信息
        report = {
            "duration_minutes": duration_minutes,
            "total_snapshots": len(recent_snapshots),
            "performance_score": self.stats["performance_score"],
            "metrics": {},
            "alerts": [],
            "recommendations": [],
        }

        # 各指标统计
        for metric_type in MetricType:
            metric_name = metric_type.value
            if metric_name in self.metric_history:
                recent_values = [
                    v for t, v in self.metric_history[metric_name] if t >= start_time
                ]

                if recent_values:
                    report["metrics"][metric_name] = {
                        "avg": np.mean(recent_values),
                        "min": np.min(recent_values),
                        "max": np.max(recent_values),
                        "std": np.std(recent_values),
                        "count": len(recent_values),
                    }

        # 告警统计
        recent_alerts = [
            alert for alert in self.alert_history if alert.timestamp >= start_time
        ]

        alert_summary = defaultdict(int)
        for alert in recent_alerts:
            alert_summary[f"{alert.alert_type}_{alert.severity}"] += 1

        report["alerts"] = dict(alert_summary)

        # 生成建议
        report["recommendations"] = self._generate_recommendations(recent_snapshots)

        return report

    def _generate_recommendations(
        self, snapshots: List[PerformanceSnapshot]
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        if not snapshots:
            return recommendations

        # 分析告警模式
        alert_types = defaultdict(int)
        for snapshot in snapshots:
            for alert in snapshot.alerts:
                alert_types[alert.alert_type] += 1

        # 根据告警频率生成建议
        for alert_type, count in alert_types.items():
            if count > len(snapshots) * 0.3:  # 30%以上的时间都有告警
                if alert_type == MetricType.CPU_USAGE.value:
                    recommendations.append("CPU使用率持续过高，建议增加跳帧率或优化算法")
                elif alert_type == MetricType.MEMORY_USAGE.value:
                    recommendations.append("内存使用率持续过高，建议清理缓存或减少批处理大小")
                elif alert_type == MetricType.FPS.value:
                    recommendations.append("FPS持续过低，建议检查系统性能瓶颈")

        # 性能评分建议
        if self.stats["performance_score"] < 60:
            recommendations.append("整体性能评分较低，建议进行系统优化")
        elif self.stats["performance_score"] < 80:
            recommendations.append("性能评分中等，可以进一步优化")
        else:
            recommendations.append("性能评分良好，系统运行正常")

        return recommendations

    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标值"""
        current_metrics = {}

        for metric_type in MetricType:
            metric_name = metric_type.value
            if metric_name in self.metric_history and self.metric_history[metric_name]:
                _, latest_value = self.metric_history[metric_name][-1]
                current_metrics[metric_name] = latest_value

        return current_metrics

    def export_data(self, filepath: str):
        """导出性能数据"""
        data = {
            "stats": self.stats,
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "metrics": s.metrics,
                    "alerts": [
                        {
                            "type": a.alert_type,
                            "severity": a.severity,
                            "message": a.message,
                            "value": a.metric_value,
                            "threshold": a.threshold,
                        }
                        for a in s.alerts
                    ],
                }
                for s in self.snapshot_history
            ],
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "value": a.metric_value,
                    "threshold": a.threshold,
                    "recommendations": a.recommendations,
                }
                for a in self.alert_history
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"性能数据已导出到: {filepath}")

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_snapshots": 0,
            "total_alerts": 0,
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "avg_fps": 0.0,
            "max_cpu_usage": 0.0,
            "max_memory_usage": 0.0,
            "min_fps": float("inf"),
            "performance_score": 0.0,
        }

        for metric_history in self.metric_history.values():
            metric_history.clear()

        self.snapshot_history.clear()
        self.alert_history.clear()

        logger.info("性能统计已重置")
