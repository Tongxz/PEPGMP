"""
智能检测系统 - 集成自适应帧处理、动态跳帧管理和性能监控

核心功能：
1. 统一接口 - 提供简化的检测接口
2. 智能优化 - 自动调整检测策略
3. 性能监控 - 实时监控和优化建议
4. 场景感知 - 根据场景类型优化处理
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .adaptive_frame_processor import AdaptiveFrameProcessor, ProcessingDecision
from .dynamic_skip_manager import DynamicSkipManager
from .performance_monitor import MetricType, PerformanceAlert, PerformanceMonitor

logger = logging.getLogger(__name__)


@dataclass
class DetectionConfig:
    """检测配置数据类"""

    target_fps: float = 15.0
    enable_adaptive_processing: bool = True
    enable_performance_monitoring: bool = True
    enable_gpu_monitoring: bool = True
    base_skip_rate: int = 3
    motion_threshold: float = 0.1
    complexity_threshold: float = 0.5
    max_skip_frames: int = 15
    min_processing_interval: float = 0.1


class IntelligentDetectionSystem:
    """智能检测系统"""

    def __init__(
        self,
        detection_pipeline,
        config: Optional[DetectionConfig] = None,
        alert_callback: Optional[Callable[[PerformanceAlert], None]] = None,
    ):
        """
        初始化智能检测系统

        Args:
            detection_pipeline: 检测管道实例
            config: 检测配置
            alert_callback: 告警回调函数
        """
        self.detection_pipeline = detection_pipeline
        self.config = config or DetectionConfig()

        # 初始化组件
        self.frame_processor = AdaptiveFrameProcessor(
            base_skip_rate=self.config.base_skip_rate,
            motion_threshold=self.config.motion_threshold,
            complexity_threshold=self.config.complexity_threshold,
            max_skip_frames=self.config.max_skip_frames,
            min_processing_interval=self.config.min_processing_interval,
        )

        self.skip_manager = DynamicSkipManager(
            target_fps=self.config.target_fps, max_skip_rate=self.config.max_skip_frames
        )

        self.performance_monitor = PerformanceMonitor(
            enable_gpu_monitoring=self.config.enable_gpu_monitoring
        )

        # 设置告警回调
        if alert_callback:
            self.performance_monitor.add_alert_callback(alert_callback)

        # 状态变量
        self.last_frame = None
        self.frame_count = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.last_processing_time = 0

        # 性能统计
        self.stats = {
            "total_frames": 0,
            "processed_frames": 0,
            "skipped_frames": 0,
            "avg_processing_time": 0.0,
            "avg_fps": 0.0,
            "current_skip_rate": 0,
            "performance_score": 0.0,
            "scene_distribution": {},
        }

        # 启动性能监控
        if self.config.enable_performance_monitoring:
            self.performance_monitor.start_monitoring()

        logger.info("智能检测系统初始化完成")

    def process_frame(
        self, frame: np.ndarray, force_process: bool = False, **detection_kwargs
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        """
        处理单帧图像

        Args:
            frame: 输入图像帧
            force_process: 是否强制处理
            **detection_kwargs: 检测参数

        Returns:
            Tuple[检测结果, 处理信息]
        """
        start_time = time.time()
        self.frame_count += 1

        # 更新性能监控
        if self.last_processing_time > 0:
            self.performance_monitor.update_metric(
                MetricType.PROCESSING_TIME, self.last_processing_time
            )

        # 做出处理决策
        decision = self.frame_processor.make_processing_decision(
            current_frame=frame,
            previous_frame=self.last_frame,
            force_process=force_process,
        )

        # 更新动态跳帧策略
        if self.config.enable_adaptive_processing:
            scene_type = self._classify_scene_from_decision(decision)
            motion_intensity = self._get_motion_intensity()
            self.skip_manager.adjust_skip_strategy(scene_type, motion_intensity)

        # 执行检测或跳过
        detection_result = None
        processing_info = {
            "should_process": decision.should_process,
            "skip_frames": decision.skip_frames,
            "processing_mode": decision.processing_mode,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "frame_count": self.frame_count,
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
        }

        if decision.should_process:
            try:
                # 执行检测
                detection_result = self.detection_pipeline.detect_comprehensive(
                    frame, **detection_kwargs
                )

                self.processed_count += 1
                processing_info["detection_success"] = True

                # 更新FPS
                processing_time = time.time() - start_time
                self.last_processing_time = processing_time
                fps = 1.0 / processing_time if processing_time > 0 else 0.0
                self.performance_monitor.update_metric(MetricType.FPS, fps)

                # 更新统计
                self._update_stats(processing_time, fps)

            except Exception as e:
                logger.error(f"检测执行失败: {e}")
                processing_info["detection_success"] = False
                processing_info["error"] = str(e)
        else:
            self.skipped_count += 1
            processing_info["detection_success"] = False
            processing_info["skipped"] = True

        # 更新帧历史
        self.last_frame = frame.copy()

        # 添加性能信息
        processing_info.update(self._get_performance_info())

        return detection_result, processing_info

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats

    def _classify_scene_from_decision(self, decision: ProcessingDecision) -> str:
        """从处理决策中推断场景类型"""
        if "static" in decision.reason.lower():
            return "static"
        elif "low_motion" in decision.reason.lower():
            return "low_motion"
        elif "high_motion" in decision.reason.lower():
            return "high_motion"
        elif "critical" in decision.reason.lower():
            return "critical"
        else:
            return "unknown"

    def _get_motion_intensity(self) -> float:
        """获取当前运动强度"""
        if len(self.frame_processor.motion_history) > 0:
            latest_motion = self.frame_processor.motion_history[-1]
            return latest_motion.frame_diff
        return 0.0

    def _update_stats(self, processing_time: float, fps: float):
        """更新统计信息"""
        # 更新平均处理时间
        if self.processed_count > 0:
            self.stats["avg_processing_time"] = (
                self.stats["avg_processing_time"] * (self.processed_count - 1)
                + processing_time
            ) / self.processed_count

        # 更新平均FPS
        if self.processed_count > 0:
            self.stats["avg_fps"] = (
                self.stats["avg_fps"] * (self.processed_count - 1) + fps
            ) / self.processed_count

        # 更新其他统计
        self.stats["total_frames"] = self.frame_count
        self.stats["processed_frames"] = self.processed_count
        self.stats["skipped_frames"] = self.skipped_count
        self.stats["current_skip_rate"] = self.frame_processor.consecutive_skips

        # 更新场景分布
        self.stats["scene_distribution"] = self.frame_processor.stats[
            "scene_distribution"
        ]

        # 更新性能评分
        self.stats["performance_score"] = self.performance_monitor.stats[
            "performance_score"
        ]

    def _get_performance_info(self) -> Dict[str, Any]:
        """获取性能信息"""
        return {
            "performance_stats": self.performance_monitor.get_current_metrics(),
            "skip_strategy": self.skip_manager.get_current_strategy().__dict__,
            "frame_processor_stats": self.frame_processor.get_performance_stats(),
            "system_stats": self.stats,
        }

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        return {
            "detection_stats": self.stats,
            "performance_monitor": self.performance_monitor.get_performance_stats(),
            "skip_manager": self.skip_manager.get_performance_stats(),
            "frame_processor": self.frame_processor.get_performance_stats(),
            "recommendations": self.skip_manager.get_recommendations(),
        }

    def get_performance_report(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """获取性能报告"""
        return self.performance_monitor.get_performance_report(duration_minutes)

    def adjust_target_fps(self, target_fps: float):
        """调整目标FPS"""
        self.config.target_fps = target_fps
        self.skip_manager.set_target_fps(target_fps)
        logger.info(f"目标FPS已调整为: {target_fps}")

    def force_optimization(self):
        """强制优化"""
        # 重置所有统计
        self.frame_processor.reset_stats()
        self.skip_manager.reset_stats()
        self.performance_monitor.reset_stats()

        # 重置状态
        self.frame_count = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.last_processing_time = 0

        logger.info("系统已强制优化重置")

    def export_performance_data(self, filepath: str):
        """导出性能数据"""
        self.performance_monitor.export_data(filepath)

    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        # 性能监控建议
        perf_recommendations = self.skip_manager.get_recommendations()
        recommendations.extend(perf_recommendations)

        # 帧处理器建议
        frame_stats = self.frame_processor.get_performance_stats()
        if frame_stats["processing_efficiency"] < 0.3:
            recommendations.append("处理效率较低，建议检查跳帧策略")

        if frame_stats["consecutive_skips"] > 10:
            recommendations.append("连续跳帧过多，可能影响检测准确性")

        # 系统性能建议
        if self.stats["performance_score"] < 60:
            recommendations.append("系统性能评分较低，建议进行整体优化")

        return recommendations

    def set_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """设置告警回调"""
        self.performance_monitor.add_alert_callback(callback)

    def shutdown(self):
        """关闭系统"""
        if self.config.enable_performance_monitoring:
            self.performance_monitor.stop_monitoring()

        logger.info("智能检测系统已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
