"""
自适应帧处理器 - 基于运动分析的智能帧跳过系统

核心功能：
1. 运动强度分析 - 检测帧间运动变化
2. 智能跳帧决策 - 根据运动强度动态调整处理频率
3. 场景感知处理 - 区分静态、动态、关键场景
4. 性能自适应 - 根据系统负载调整处理策略
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SceneType(Enum):
    """场景类型枚举"""

    STATIC = "static"  # 静态场景（无人或静止）
    LOW_MOTION = "low_motion"  # 低运动场景（缓慢移动）
    HIGH_MOTION = "high_motion"  # 高运动场景（快速移动）
    CRITICAL = "critical"  # 关键场景（检测到违规行为）


@dataclass
class MotionMetrics:
    """运动指标数据类"""

    frame_diff: float  # 帧间差异
    optical_flow_magnitude: float  # 光流幅度
    motion_density: float  # 运动密度
    scene_complexity: float  # 场景复杂度
    timestamp: float  # 时间戳


@dataclass
class ProcessingDecision:
    """处理决策数据类"""

    should_process: bool  # 是否应该处理
    skip_frames: int  # 跳过帧数
    processing_mode: str  # 处理模式
    confidence: float  # 决策置信度
    reason: str  # 决策原因


class AdaptiveFrameProcessor:
    """自适应帧处理器"""

    def __init__(
        self,
        base_skip_rate: int = 3,
        motion_threshold: float = 0.1,
        complexity_threshold: float = 0.5,
        history_size: int = 30,
        min_processing_interval: float = 0.1,  # 最小处理间隔（秒）
        max_skip_frames: int = 15,  # 最大跳过帧数
    ):
        """
        初始化自适应帧处理器

        Args:
            base_skip_rate: 基础跳帧率
            motion_threshold: 运动阈值
            complexity_threshold: 复杂度阈值
            history_size: 历史记录大小
            min_processing_interval: 最小处理间隔
            max_skip_frames: 最大跳过帧数
        """
        self.base_skip_rate = base_skip_rate
        self.motion_threshold = motion_threshold
        self.complexity_threshold = complexity_threshold
        self.history_size = history_size
        self.min_processing_interval = min_processing_interval
        self.max_skip_frames = max_skip_frames

        # 历史数据存储
        self.motion_history = deque(maxlen=history_size)
        self.processing_history = deque(maxlen=history_size)
        self.last_processed_time = 0
        self.frame_count = 0
        self.consecutive_skips = 0

        # 处理统计
        self.processed_frames = 0
        self.skipped_frames = 0

        # 光流检测器
        self.optical_flow = cv2.calcOpticalFlowPyrLK

        # 性能统计
        self.stats = {
            "total_frames": 0,
            "processed_frames": 0,
            "skipped_frames": 0,
            "avg_motion": 0.0,
            "avg_skip_rate": 0.0,
            "scene_distribution": {scene.value: 0 for scene in SceneType},
        }

        # 场景检测参数
        self.scene_params = {
            "static_threshold": 0.05,
            "low_motion_threshold": 0.15,
            "high_motion_threshold": 0.4,
        }

        logger.info(f"自适应帧处理器初始化完成: 基础跳帧率={base_skip_rate}, 运动阈值={motion_threshold}")

    def analyze_motion(
        self, current_frame: np.ndarray, previous_frame: Optional[np.ndarray] = None
    ) -> MotionMetrics:
        """
        分析帧间运动

        Args:
            current_frame: 当前帧
            previous_frame: 前一帧

        Returns:
            MotionMetrics: 运动指标
        """
        timestamp = time.time()

        if previous_frame is None:
            return MotionMetrics(
                frame_diff=0.0,
                optical_flow_magnitude=0.0,
                motion_density=0.0,
                scene_complexity=0.0,
                timestamp=timestamp,
            )

        # 1. 计算帧间差异
        frame_diff = self._calculate_frame_difference(current_frame, previous_frame)

        # 2. 计算光流幅度
        optical_flow_magnitude = self._calculate_optical_flow(
            current_frame, previous_frame
        )

        # 3. 计算运动密度
        motion_density = self._calculate_motion_density(current_frame, previous_frame)

        # 4. 计算场景复杂度
        scene_complexity = self._calculate_scene_complexity(current_frame)

        return MotionMetrics(
            frame_diff=frame_diff,
            optical_flow_magnitude=optical_flow_magnitude,
            motion_density=motion_density,
            scene_complexity=scene_complexity,
            timestamp=timestamp,
        )

    def _calculate_frame_difference(
        self, frame1: np.ndarray, frame2: np.ndarray
    ) -> float:
        """计算帧间差异"""
        try:
            # 转换为灰度图
            gray1 = (
                cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                if len(frame1.shape) == 3
                else frame1
            )
            gray2 = (
                cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                if len(frame2.shape) == 3
                else frame2
            )

            # 计算绝对差异
            diff = cv2.absdiff(gray1, gray2)

            # 计算平均差异
            mean_diff = np.mean(diff) / 255.0

            return float(mean_diff)
        except Exception as e:
            logger.debug(f"帧差异计算失败: {e}")
            return 0.0

    def _calculate_optical_flow(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算光流幅度"""
        try:
            # 转换为灰度图
            gray1 = (
                cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                if len(frame1.shape) == 3
                else frame1
            )
            gray2 = (
                cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                if len(frame2.shape) == 3
                else frame2
            )

            # 使用Lucas-Kanade光流
            # 创建角点检测器
            corners = cv2.goodFeaturesToTrack(
                gray1, maxCorners=100, qualityLevel=0.01, minDistance=10
            )

            if corners is None or len(corners) < 5:
                return 0.0

            # 计算光流
            next_corners, status, error = cv2.calcOpticalFlowPyrLK(
                gray1, gray2, corners, None
            )

            # 过滤有效点
            valid_corners = corners[status == 1]
            valid_next = next_corners[status == 1]

            if len(valid_corners) < 3:
                return 0.0

            # 计算位移幅度
            displacement = valid_next - valid_corners
            magnitudes = np.sqrt(np.sum(displacement**2, axis=1))

            return float(np.mean(magnitudes))
        except Exception as e:
            logger.debug(f"光流计算失败: {e}")
            return 0.0

    def _calculate_motion_density(
        self, frame1: np.ndarray, frame2: np.ndarray
    ) -> float:
        """计算运动密度"""
        try:
            # 计算帧差
            gray1 = (
                cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                if len(frame1.shape) == 3
                else frame1
            )
            gray2 = (
                cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                if len(frame2.shape) == 3
                else frame2
            )

            diff = cv2.absdiff(gray1, gray2)

            # 二值化
            _, binary = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

            # 计算运动像素比例
            motion_pixels = np.sum(binary > 0)
            total_pixels = binary.size

            return float(motion_pixels) / float(total_pixels)
        except Exception as e:
            logger.debug(f"运动密度计算失败: {e}")
            return 0.0

    def _calculate_scene_complexity(self, frame: np.ndarray) -> float:
        """计算场景复杂度"""
        try:
            # 转换为灰度图
            gray = (
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if len(frame.shape) == 3
                else frame
            )

            # 计算边缘密度
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size

            # 计算纹理复杂度
            texture = cv2.Laplacian(gray, cv2.CV_64F)
            texture_complexity = np.var(texture) / 10000.0  # 归一化

            # 综合复杂度
            complexity = (edge_density + texture_complexity) / 2.0

            return float(complexity)
        except Exception as e:
            logger.debug(f"场景复杂度计算失败: {e}")
            return 0.0

    def classify_scene(self, motion_metrics: MotionMetrics) -> SceneType:
        """分类场景类型"""
        motion_score = motion_metrics.frame_diff
        complexity_score = motion_metrics.scene_complexity

        # 综合运动评分
        combined_score = (motion_score + complexity_score) / 2.0

        if combined_score < self.scene_params["static_threshold"]:
            return SceneType.STATIC
        elif combined_score < self.scene_params["low_motion_threshold"]:
            return SceneType.LOW_MOTION
        elif combined_score < self.scene_params["high_motion_threshold"]:
            return SceneType.HIGH_MOTION
        else:
            return SceneType.CRITICAL

    def make_processing_decision(
        self,
        current_frame: np.ndarray,
        previous_frame: Optional[np.ndarray] = None,
        force_process: bool = False,
    ) -> ProcessingDecision:
        """
        做出处理决策

        Args:
            current_frame: 当前帧
            previous_frame: 前一帧
            force_process: 是否强制处理

        Returns:
            ProcessingDecision: 处理决策
        """
        self.frame_count += 1
        current_time = time.time()

        # 强制处理
        if force_process:
            return ProcessingDecision(
                should_process=True,
                skip_frames=0,
                processing_mode="forced",
                confidence=1.0,
                reason="强制处理",
            )

        # 分析运动
        motion_metrics = self.analyze_motion(current_frame, previous_frame)
        self.motion_history.append(motion_metrics)

        # 分类场景
        scene_type = self.classify_scene(motion_metrics)
        self.stats["scene_distribution"][scene_type.value] += 1

        # 检查最小处理间隔
        time_since_last = current_time - self.last_processed_time
        if time_since_last < self.min_processing_interval:
            return ProcessingDecision(
                should_process=False,
                skip_frames=1,
                processing_mode="interval_limit",
                confidence=0.8,
                reason=f"处理间隔限制 ({time_since_last:.3f}s < {self.min_processing_interval}s)",
            )

        # 根据场景类型和运动强度做决策
        decision = self._make_scene_based_decision(motion_metrics, scene_type)

        # 更新统计
        if decision.should_process:
            self.processed_frames += 1
            self.last_processed_time = current_time
            self.consecutive_skips = 0
        else:
            self.skipped_frames += 1
            self.consecutive_skips += 1

        # 更新平均统计
        self._update_stats()

        return decision

    def _make_scene_based_decision(
        self, motion_metrics: MotionMetrics, scene_type: SceneType
    ) -> ProcessingDecision:
        """基于场景类型做决策"""
        motion_score = motion_metrics.frame_diff
        complexity_score = motion_metrics.scene_complexity

        # 静态场景 - 大幅跳帧
        if scene_type == SceneType.STATIC:
            skip_frames = min(self.max_skip_frames, self.base_skip_rate * 3)
            return ProcessingDecision(
                should_process=False,
                skip_frames=skip_frames,
                processing_mode="static_skip",
                confidence=0.9,
                reason=f"静态场景 (运动={motion_score:.3f}, 复杂度={complexity_score:.3f})",
            )

        # 低运动场景 - 适度跳帧
        elif scene_type == SceneType.LOW_MOTION:
            skip_frames = min(self.max_skip_frames, self.base_skip_rate * 2)
            return ProcessingDecision(
                should_process=False,
                skip_frames=skip_frames,
                processing_mode="low_motion_skip",
                confidence=0.8,
                reason=f"低运动场景 (运动={motion_score:.3f}, 复杂度={complexity_score:.3f})",
            )

        # 高运动场景 - 减少跳帧
        elif scene_type == SceneType.HIGH_MOTION:
            skip_frames = max(1, self.base_skip_rate // 2)
            return ProcessingDecision(
                should_process=True,
                skip_frames=0,
                processing_mode="high_motion_process",
                confidence=0.85,
                reason=f"高运动场景 (运动={motion_score:.3f}, 复杂度={complexity_score:.3f})",
            )

        # 关键场景 - 必须处理
        else:  # CRITICAL
            return ProcessingDecision(
                should_process=True,
                skip_frames=0,
                processing_mode="critical_process",
                confidence=0.95,
                reason=f"关键场景 (运动={motion_score:.3f}, 复杂度={complexity_score:.3f})",
            )

    def _update_stats(self):
        """更新统计信息"""
        if len(self.motion_history) > 0:
            recent_motions = [m.frame_diff for m in list(self.motion_history)[-10:]]
            self.stats["avg_motion"] = np.mean(recent_motions)

        if self.frame_count > 0:
            self.stats["avg_skip_rate"] = self.skipped_frames / self.frame_count

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.stats,
            "total_frames": self.frame_count,
            "processed_frames": self.processed_frames,
            "skipped_frames": self.skipped_frames,
            "consecutive_skips": self.consecutive_skips,
            "processing_efficiency": self.processed_frames / max(self.frame_count, 1),
            "current_skip_rate": self.consecutive_skips,
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_frames": 0,
            "processed_frames": 0,
            "skipped_frames": 0,
            "avg_motion": 0.0,
            "avg_skip_rate": 0.0,
            "scene_distribution": {scene.value: 0 for scene in SceneType},
        }
        self.frame_count = 0
        self.processed_frames = 0
        self.skipped_frames = 0
        self.consecutive_skips = 0
        self.motion_history.clear()
        self.processing_history.clear()

    def adjust_parameters(self, target_fps: float, current_fps: float):
        """
        根据性能调整参数

        Args:
            target_fps: 目标FPS
            current_fps: 当前FPS
        """
        if current_fps < target_fps * 0.8:  # 性能不足
            # 增加跳帧率
            self.base_skip_rate = min(self.max_skip_frames, self.base_skip_rate + 1)
            self.motion_threshold = min(0.5, self.motion_threshold + 0.05)
            logger.info(
                f"性能不足，调整参数: 跳帧率={self.base_skip_rate}, 运动阈值={self.motion_threshold:.3f}"
            )

        elif current_fps > target_fps * 1.2:  # 性能过剩
            # 减少跳帧率
            self.base_skip_rate = max(1, self.base_skip_rate - 1)
            self.motion_threshold = max(0.05, self.motion_threshold - 0.02)
            logger.info(
                f"性能过剩，调整参数: 跳帧率={self.base_skip_rate}, 运动阈值={self.motion_threshold:.3f}"
            )
