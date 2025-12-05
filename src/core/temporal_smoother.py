"""
时间平滑器

负责：
1. 关键点时间平滑（指数移动平均）
2. 置信度时间平滑
3. 动作一致性检查
"""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class TemporalSmoother:
    """时间平滑器

    功能：
    1. 关键点时间平滑：使用指数移动平均（EMA）平滑关键点坐标
    2. 置信度时间平滑：平滑关键点置信度
    3. 动作一致性检查：检查动作在时间窗口内的一致性
    """

    def __init__(
        self,
        window_size: int = 5,  # 时间窗口大小
        alpha: float = 0.7,  # 指数移动平均系数（0-1，越大越依赖当前值）
        consistency_threshold: float = 0.8,  # 一致性阈值
    ):
        """
        初始化时间平滑器

        Args:
            window_size: 时间窗口大小（保留最近N帧）
            alpha: 指数移动平均系数（0-1）
                - 接近1：更依赖当前值（响应快，但可能不稳定）
                - 接近0：更依赖历史值（稳定，但响应慢）
            consistency_threshold: 一致性阈值（0-1）
        """
        self.window_size = window_size
        self.alpha = alpha
        self.consistency_threshold = consistency_threshold

        # 关键点历史：track_id -> deque of keypoints
        self.keypoint_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

        # 置信度历史：track_id -> deque of confidences
        self.confidence_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

        # 平滑后的关键点缓存：track_id -> smoothed_keypoints
        self.smoothed_keypoints_cache: Dict[str, np.ndarray] = {}

        # 平滑后的置信度缓存：track_id -> smoothed_confidences
        self.smoothed_confidences_cache: Dict[str, np.ndarray] = {}

        logger.info(
            f"TemporalSmoother initialized: window_size={window_size}, "
            f"alpha={alpha}, consistency_threshold={consistency_threshold}"
        )

    def smooth_keypoints(
        self,
        track_id: str,
        keypoints: np.ndarray,
        confidences: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        平滑关键点坐标和置信度

        Args:
            track_id: 跟踪ID
            keypoints: 关键点坐标 (N, 2) 或 (N, 3) - (x, y) 或 (x, y, z)
            confidences: 关键点置信度 (N,) - 可选

        Returns:
            (smoothed_keypoints, smoothed_confidences)
        """
        if keypoints is None or len(keypoints) == 0:
            return keypoints, confidences if confidences is not None else np.array([])

        # 确保是numpy数组
        keypoints = np.array(keypoints)
        if confidences is None:
            # 如果没有提供置信度，使用默认值1.0
            confidences = np.ones(len(keypoints))
        else:
            confidences = np.array(confidences)

        # 添加到历史
        self.keypoint_history[track_id].append(keypoints.copy())
        self.confidence_history[track_id].append(confidences.copy())

        # 获取历史数据
        keypoint_history = list(self.keypoint_history[track_id])
        confidence_history = list(self.confidence_history[track_id])

        if len(keypoint_history) == 0:
            return keypoints, confidences

        # 指数移动平均平滑
        smoothed_keypoints = self._exponential_moving_average(
            keypoint_history, self.alpha
        )
        smoothed_confidences = self._exponential_moving_average(
            confidence_history, self.alpha
        )

        # 更新缓存
        self.smoothed_keypoints_cache[track_id] = smoothed_keypoints
        self.smoothed_confidences_cache[track_id] = smoothed_confidences

        return smoothed_keypoints, smoothed_confidences

    def _exponential_moving_average(
        self,
        history: List[np.ndarray],
        alpha: float,
    ) -> np.ndarray:
        """
        计算指数移动平均

        Args:
            history: 历史数据列表
            alpha: 平滑系数

        Returns:
            平滑后的数据
        """
        if len(history) == 0:
            return np.array([])

        if len(history) == 1:
            return history[0].copy()

        # 从最旧到最新
        result = history[0].copy()

        for i in range(1, len(history)):
            result = alpha * history[i] + (1 - alpha) * result

        return result

    def check_consistency(
        self,
        track_id: str,
        current_keypoints: np.ndarray,
        threshold: Optional[float] = None,
    ) -> float:
        """
        检查动作一致性（0.0-1.0）

        Args:
            track_id: 跟踪ID
            current_keypoints: 当前关键点坐标
            threshold: 一致性阈值（可选，使用默认值如果为None）

        Returns:
            一致性分数（0.0-1.0，1.0表示完全一致）
        """
        if threshold is None:
            threshold = self.consistency_threshold

        if track_id not in self.keypoint_history:
            return 1.0  # 没有历史，认为一致

        history = list(self.keypoint_history[track_id])
        if len(history) < 2:
            return 1.0  # 历史不足，认为一致

        # 计算关键点位置的变化
        changes = []
        for i in range(1, len(history)):
            prev_keypoints = history[i - 1]
            curr_keypoints = history[i]

            # 计算欧氏距离
            if len(prev_keypoints) == len(curr_keypoints):
                diff = np.linalg.norm(curr_keypoints - prev_keypoints, axis=-1)
                changes.append(np.mean(diff))

        if len(changes) == 0:
            return 1.0

        # 计算平均变化
        avg_change = np.mean(changes)

        # 计算当前帧与历史平均的变化
        if len(history) > 0:
            avg_keypoints = np.mean(history, axis=0)
            current_change = np.mean(
                np.linalg.norm(current_keypoints - avg_keypoints, axis=-1)
            )
        else:
            current_change = 0.0

        # 一致性分数：变化越小，一致性越高
        # 使用阈值归一化
        consistency_score = 1.0 / (1.0 + avg_change + current_change)

        return float(np.clip(consistency_score, 0.0, 1.0))

    def get_smoothed_keypoints(self, track_id: str) -> Optional[np.ndarray]:
        """获取平滑后的关键点"""
        return self.smoothed_keypoints_cache.get(track_id)

    def get_smoothed_confidences(self, track_id: str) -> Optional[np.ndarray]:
        """获取平滑后的置信度"""
        return self.smoothed_confidences_cache.get(track_id)

    def reset_track(self, track_id: str):
        """重置指定track的历史"""
        if track_id in self.keypoint_history:
            del self.keypoint_history[track_id]
        if track_id in self.confidence_history:
            del self.confidence_history[track_id]
        if track_id in self.smoothed_keypoints_cache:
            del self.smoothed_keypoints_cache[track_id]
        if track_id in self.smoothed_confidences_cache:
            del self.smoothed_confidences_cache[track_id]
        logger.debug(f"Reset history for track_id={track_id}")

    def reset_all(self):
        """重置所有历史"""
        self.keypoint_history.clear()
        self.confidence_history.clear()
        self.smoothed_keypoints_cache.clear()
        self.smoothed_confidences_cache.clear()
        logger.info("Reset all temporal smoothing history")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_tracks": len(self.keypoint_history),
            "window_size": self.window_size,
            "alpha": self.alpha,
            "consistency_threshold": self.consistency_threshold,
            "tracks": {
                track_id: {
                    "history_size": len(self.keypoint_history[track_id]),
                    "has_smoothed": track_id in self.smoothed_keypoints_cache,
                }
                for track_id in self.keypoint_history.keys()
            },
        }
