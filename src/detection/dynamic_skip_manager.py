"""
动态跳帧管理器 - 根据系统性能和场景复杂度动态调整跳帧策略

核心功能：
1. 性能监控 - 实时监控系统性能指标
2. 动态调整 - 根据性能自动调整跳帧参数
3. 场景适应 - 根据场景类型优化处理策略
4. 负载均衡 - 在性能和准确性之间找到平衡点
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

import numpy as np
import psutil

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """性能等级枚举"""

    EXCELLENT = "excellent"  # 优秀 (>80% 目标FPS)
    GOOD = "good"  # 良好 (60-80% 目标FPS)
    FAIR = "fair"  # 一般 (40-60% 目标FPS)
    POOR = "poor"  # 较差 (<40% 目标FPS)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    cpu_usage: float  # CPU使用率
    memory_usage: float  # 内存使用率
    gpu_usage: float  # GPU使用率（如果可用）
    processing_time: float  # 处理时间
    fps: float  # 实际FPS
    frame_drop_rate: float  # 丢帧率
    timestamp: float  # 时间戳


@dataclass
class SkipStrategy:
    """跳帧策略数据类"""

    base_skip_rate: int  # 基础跳帧率
    motion_threshold: float  # 运动阈值
    complexity_threshold: float  # 复杂度阈值
    max_skip_frames: int  # 最大跳帧数
    min_processing_interval: float  # 最小处理间隔
    processing_mode: str  # 处理模式


class DynamicSkipManager:
    """动态跳帧管理器"""

    def __init__(
        self,
        target_fps: float = 15.0,
        performance_window: int = 30,
        adjustment_sensitivity: float = 0.1,
        min_skip_rate: int = 1,
        max_skip_rate: int = 20,
    ):
        """
        初始化动态跳帧管理器

        Args:
            target_fps: 目标FPS
            performance_window: 性能监控窗口大小
            adjustment_sensitivity: 调整敏感度
            min_skip_rate: 最小跳帧率
            max_skip_rate: 最大跳帧率
        """
        self.target_fps = target_fps
        self.performance_window = performance_window
        self.adjustment_sensitivity = adjustment_sensitivity
        self.min_skip_rate = min_skip_rate
        self.max_skip_rate = max_skip_rate

        # 性能历史
        self.performance_history = deque(maxlen=performance_window)
        self.fps_history = deque(maxlen=performance_window)

        # 当前策略
        self.current_strategy = SkipStrategy(
            base_skip_rate=3,
            motion_threshold=0.1,
            complexity_threshold=0.5,
            max_skip_frames=15,
            min_processing_interval=0.1,
            processing_mode="adaptive",
        )

        # 性能等级阈值
        self.performance_thresholds = {
            PerformanceLevel.EXCELLENT: 0.8,
            PerformanceLevel.GOOD: 0.6,
            PerformanceLevel.FAIR: 0.4,
            PerformanceLevel.POOR: 0.0,
        }

        # 统计信息
        self.stats = {
            "total_adjustments": 0,
            "performance_level_changes": 0,
            "avg_fps": 0.0,
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "current_performance_level": PerformanceLevel.GOOD.value,
        }

        # 调整历史
        self.adjustment_history = deque(maxlen=50)

        logger.info(f"动态跳帧管理器初始化: 目标FPS={target_fps}, 调整敏感度={adjustment_sensitivity}")

    def collect_performance_metrics(self, processing_time: float) -> PerformanceMetrics:
        """
        收集性能指标

        Args:
            processing_time: 处理时间

        Returns:
            PerformanceMetrics: 性能指标
        """
        try:
            # 系统资源使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent

            # GPU使用率（如果可用）
            gpu_usage = self._get_gpu_usage()

            # 计算FPS
            fps = 1.0 / processing_time if processing_time > 0 else 0.0

            # 计算丢帧率
            frame_drop_rate = max(0.0, 1.0 - (fps / self.target_fps))

            metrics = PerformanceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                gpu_usage=gpu_usage,
                processing_time=processing_time,
                fps=fps,
                frame_drop_rate=frame_drop_rate,
                timestamp=time.time(),
            )

            # 添加到历史
            self.performance_history.append(metrics)
            self.fps_history.append(fps)

            return metrics

        except Exception as e:
            logger.error(f"性能指标收集失败: {e}")
            return PerformanceMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                gpu_usage=0.0,
                processing_time=processing_time,
                fps=0.0,
                frame_drop_rate=1.0,
                timestamp=time.time(),
            )

    def _get_gpu_usage(self) -> float:
        """获取GPU使用率"""
        try:
            # 尝试使用nvidia-ml-py获取GPU使用率
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return float(utilization.gpu)
        except ImportError:
            logger.debug("nvidia-ml-py未安装，无法获取GPU使用率")
            return 0.0
        except Exception as e:
            logger.debug(f"GPU使用率获取失败: {e}")
            return 0.0

    def evaluate_performance_level(self) -> PerformanceLevel:
        """评估当前性能等级"""
        if len(self.fps_history) < 5:
            return PerformanceLevel.GOOD

        # 计算平均FPS
        avg_fps = np.mean(list(self.fps_history)[-10:])
        fps_ratio = avg_fps / self.target_fps

        # 根据FPS比例确定性能等级
        if fps_ratio >= self.performance_thresholds[PerformanceLevel.EXCELLENT]:
            return PerformanceLevel.EXCELLENT
        elif fps_ratio >= self.performance_thresholds[PerformanceLevel.GOOD]:
            return PerformanceLevel.GOOD
        elif fps_ratio >= self.performance_thresholds[PerformanceLevel.FAIR]:
            return PerformanceLevel.FAIR
        else:
            return PerformanceLevel.POOR

    def adjust_skip_strategy(
        self, scene_type: str, motion_intensity: float
    ) -> SkipStrategy:
        """
        调整跳帧策略

        Args:
            scene_type: 场景类型
            motion_intensity: 运动强度

        Returns:
            SkipStrategy: 调整后的策略
        """
        # 评估当前性能
        performance_level = self.evaluate_performance_level()
        old_level = self.stats["current_performance_level"]

        if performance_level.value != old_level:
            self.stats["performance_level_changes"] += 1
            self.stats["current_performance_level"] = performance_level.value
            logger.info(f"性能等级变化: {old_level} -> {performance_level.value}")

        # 根据性能等级调整策略
        new_strategy = self._create_adaptive_strategy(
            performance_level, scene_type, motion_intensity
        )

        # 记录调整
        adjustment = {
            "timestamp": time.time(),
            "old_strategy": self.current_strategy.__dict__,
            "new_strategy": new_strategy.__dict__,
            "performance_level": performance_level.value,
            "reason": f"性能等级: {performance_level.value}, 场景: {scene_type}, 运动强度: {motion_intensity:.3f}",
        }
        self.adjustment_history.append(adjustment)
        self.stats["total_adjustments"] += 1

        # 更新当前策略
        self.current_strategy = new_strategy

        logger.debug(f"跳帧策略调整: {adjustment['reason']}")

        return new_strategy

    def _create_adaptive_strategy(
        self,
        performance_level: PerformanceLevel,
        scene_type: str,
        motion_intensity: float,
    ) -> SkipStrategy:
        """创建自适应策略"""

        # 基础参数
        base_skip_rate = self.current_strategy.base_skip_rate
        motion_threshold = self.current_strategy.motion_threshold
        complexity_threshold = self.current_strategy.complexity_threshold
        max_skip_frames = self.current_strategy.max_skip_frames
        min_processing_interval = self.current_strategy.min_processing_interval

        # 根据性能等级调整
        if performance_level == PerformanceLevel.EXCELLENT:
            # 性能优秀，可以降低跳帧率
            base_skip_rate = max(self.min_skip_rate, base_skip_rate - 1)
            motion_threshold = max(0.05, motion_threshold - 0.02)
            max_skip_frames = min(20, max_skip_frames + 2)
            min_processing_interval = max(0.05, min_processing_interval - 0.02)

        elif performance_level == PerformanceLevel.GOOD:
            # 性能良好，保持当前策略或微调
            if motion_intensity > 0.3:  # 高运动场景
                base_skip_rate = max(self.min_skip_rate, base_skip_rate - 1)
            elif motion_intensity < 0.1:  # 低运动场景
                base_skip_rate = min(self.max_skip_rate, base_skip_rate + 1)

        elif performance_level == PerformanceLevel.FAIR:
            # 性能一般，增加跳帧率
            base_skip_rate = min(self.max_skip_rate, base_skip_rate + 2)
            motion_threshold = min(0.3, motion_threshold + 0.05)
            max_skip_frames = min(25, max_skip_frames + 3)
            min_processing_interval = min(0.2, min_processing_interval + 0.05)

        else:  # POOR
            # 性能较差，大幅增加跳帧率
            base_skip_rate = min(self.max_skip_rate, base_skip_rate + 3)
            motion_threshold = min(0.5, motion_threshold + 0.1)
            max_skip_frames = min(30, max_skip_frames + 5)
            min_processing_interval = min(0.3, min_processing_interval + 0.1)

        # 根据场景类型进一步调整
        if scene_type == "static":
            base_skip_rate = min(self.max_skip_rate, base_skip_rate + 2)
            motion_threshold = min(0.4, motion_threshold + 0.05)
        elif scene_type == "critical":
            base_skip_rate = max(self.min_skip_rate, base_skip_rate - 1)
            motion_threshold = max(0.05, motion_threshold - 0.02)

        # 确保参数在合理范围内
        base_skip_rate = max(
            self.min_skip_rate, min(self.max_skip_rate, base_skip_rate)
        )
        motion_threshold = max(0.01, min(0.8, motion_threshold))
        complexity_threshold = max(0.1, min(0.9, complexity_threshold))
        max_skip_frames = max(5, min(50, max_skip_frames))
        min_processing_interval = max(0.01, min(1.0, min_processing_interval))

        return SkipStrategy(
            base_skip_rate=base_skip_rate,
            motion_threshold=motion_threshold,
            complexity_threshold=complexity_threshold,
            max_skip_frames=max_skip_frames,
            min_processing_interval=min_processing_interval,
            processing_mode="adaptive",
        )

    def get_current_strategy(self) -> SkipStrategy:
        """获取当前策略"""
        return self.current_strategy

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if len(self.performance_history) > 0:
            recent_metrics = list(self.performance_history)[-10:]
            self.stats["avg_fps"] = np.mean([m.fps for m in recent_metrics])
            self.stats["avg_cpu_usage"] = np.mean([m.cpu_usage for m in recent_metrics])
            self.stats["avg_memory_usage"] = np.mean(
                [m.memory_usage for m in recent_metrics]
            )

        return {
            **self.stats,
            "target_fps": self.target_fps,
            "current_strategy": self.current_strategy.__dict__,
            "recent_adjustments": list(self.adjustment_history)[-5:],
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_adjustments": 0,
            "performance_level_changes": 0,
            "avg_fps": 0.0,
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "current_performance_level": PerformanceLevel.GOOD.value,
        }
        self.performance_history.clear()
        self.fps_history.clear()
        self.adjustment_history.clear()

    def set_target_fps(self, target_fps: float):
        """设置目标FPS"""
        self.target_fps = target_fps
        logger.info(f"目标FPS已更新: {target_fps}")

    def get_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        if len(self.performance_history) < 5:
            return ["需要更多性能数据来生成建议"]

        recent_metrics = list(self.performance_history)[-10:]
        avg_cpu = np.mean([m.cpu_usage for m in recent_metrics])
        avg_memory = np.mean([m.memory_usage for m in recent_metrics])
        avg_fps = np.mean([m.fps for m in recent_metrics])

        if avg_cpu > 80:
            recommendations.append("CPU使用率过高，建议增加跳帧率或降低检测精度")

        if avg_memory > 85:
            recommendations.append("内存使用率过高，建议清理缓存或减少批处理大小")

        if avg_fps < self.target_fps * 0.6:
            recommendations.append("FPS低于目标，建议优化检测算法或增加跳帧率")

        if self.current_strategy.base_skip_rate > 15:
            recommendations.append("跳帧率过高，可能影响检测准确性，建议检查系统性能")

        if not recommendations:
            recommendations.append("系统性能良好，当前配置合理")

        return recommendations
