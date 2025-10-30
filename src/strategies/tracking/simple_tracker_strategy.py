"""
简单跟踪策略实现
使用简单的IoU匹配进行多目标跟踪
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from src.interfaces.tracking.tracker_interface import (
    ITracker,
    Track,
    TrackingError,
    TrackingResult,
)

logger = logging.getLogger(__name__)


class SimpleTrackerStrategy(ITracker):
    """简单跟踪策略"""

    def __init__(
        self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3
    ):
        """
        初始化简单跟踪策略

        Args:
            max_age: 轨迹最大年龄
            min_hits: 轨迹确认所需的最小匹配次数
            iou_threshold: IoU阈值
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: List[Track] = []
        self.next_id = 1
        self.frame_id = 0

        logger.info(f"简单跟踪策略初始化: max_age={max_age}, min_hits={min_hits}")

    async def track(
        self, detections: List[Dict[str, Any]], frame: np.ndarray
    ) -> TrackingResult:
        """
        跟踪检测到的对象

        Args:
            detections: 检测结果列表
            frame: 当前帧图像

        Returns:
            TrackingResult: 跟踪结果
        """
        start_time = time.time()

        try:
            # 更新现有轨迹
            self._update_tracks(detections)

            # 创建新轨迹
            self._create_new_tracks(detections)

            # 清理过期轨迹
            self._cleanup_tracks()

            self.frame_id += 1
            processing_time = time.time() - start_time

            result = TrackingResult(
                tracks=self.tracks.copy(),
                frame_id=self.frame_id,
                processing_time=processing_time,
                timestamp=datetime.now(),
            )

            logger.debug(f"简单跟踪完成: {len(self.tracks)}个轨迹, 耗时: {processing_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"简单跟踪失败: {e}")
            raise TrackingError(f"简单跟踪失败: {e}")

    def _update_tracks(self, detections: List[Dict[str, Any]]) -> None:
        """更新现有轨迹"""
        if not detections or not self.tracks:
            return

        # 计算IoU矩阵
        iou_matrix = self._compute_iou_matrix(self.tracks, detections)

        # 匹配轨迹和检测
        matched_tracks, matched_detections = self._match_tracks(iou_matrix)

        # 更新匹配的轨迹
        for track_idx, det_idx in zip(matched_tracks, matched_detections):
            if track_idx < len(self.tracks) and det_idx < len(detections):
                track = self.tracks[track_idx]
                detection = detections[det_idx]

                # 更新轨迹信息
                track.bbox = detection.get("bbox", track.bbox)
                track.confidence = detection.get("confidence", track.confidence)
                track.hits += 1
                track.time_since_update = 0

                # 如果达到最小匹配次数，确认轨迹
                if track.hits >= self.min_hits:
                    track.state = "confirmed"

        # 标记未匹配的轨迹
        for i, track in enumerate(self.tracks):
            if i not in matched_tracks:
                track.time_since_update += 1

    def _create_new_tracks(self, detections: List[Dict[str, Any]]) -> None:
        """创建新轨迹"""
        if not detections:
            return

        # 计算IoU矩阵
        iou_matrix = self._compute_iou_matrix(self.tracks, detections)

        # 找到未匹配的检测
        matched_tracks, matched_detections = self._match_tracks(iou_matrix)
        unmatched_detections = [
            i for i in range(len(detections)) if i not in matched_detections
        ]

        # 为未匹配的检测创建新轨迹
        for det_idx in unmatched_detections:
            detection = detections[det_idx]

            track = Track(
                track_id=self.next_id,
                class_id=detection.get("class_id", 0),
                class_name=detection.get("class_name", "object"),
                bbox=detection.get("bbox", [0, 0, 0, 0]),
                confidence=detection.get("confidence", 0.0),
                age=1,
                hits=1,
                time_since_update=0,
                state="tentative",
            )

            self.tracks.append(track)
            self.next_id += 1

    def _cleanup_tracks(self) -> None:
        """清理过期轨迹"""
        self.tracks = [
            track for track in self.tracks if track.time_since_update < self.max_age
        ]

    def _compute_iou_matrix(
        self, tracks: List[Track], detections: List[Dict[str, Any]]
    ) -> np.ndarray:
        """计算IoU矩阵"""
        if not tracks or not detections:
            return np.zeros((len(tracks), len(detections)))

        iou_matrix = np.zeros((len(tracks), len(detections)))

        for i, track in enumerate(tracks):
            for j, detection in enumerate(detections):
                track_bbox = track.bbox
                det_bbox = detection.get("bbox", [0, 0, 0, 0])

                iou = self._compute_iou(track_bbox, det_bbox)
                iou_matrix[i, j] = iou

        return iou_matrix

    def _compute_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的IoU"""
        # 转换格式: [x, y, w, h] -> [x1, y1, x2, y2]
        x1_1, y1_1, w1, h1 = bbox1
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1

        x1_2, y1_2, w2, h2 = bbox2
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2

        # 计算交集
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # 计算并集
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _match_tracks(self, iou_matrix: np.ndarray) -> tuple:
        """匹配轨迹和检测"""
        matched_tracks = []
        matched_detections = []

        # 简单的贪心匹配
        for i in range(iou_matrix.shape[0]):
            for j in range(iou_matrix.shape[1]):
                if iou_matrix[i, j] >= self.iou_threshold:
                    if i not in matched_tracks and j not in matched_detections:
                        matched_tracks.append(i)
                        matched_detections.append(j)

        return matched_tracks, matched_detections

    def reset(self) -> None:
        """重置跟踪器状态"""
        self.tracks.clear()
        self.next_id = 1
        self.frame_id = 0
        logger.info("简单跟踪器已重置")

    def get_track_count(self) -> int:
        """获取当前跟踪的轨迹数量"""
        return len(self.tracks)

    def get_track_statistics(self) -> Dict[str, Any]:
        """获取跟踪统计信息"""
        confirmed_count = sum(1 for track in self.tracks if track.state == "confirmed")
        tentative_count = sum(1 for track in self.tracks if track.state == "tentative")

        return {
            "tracker_type": "SimpleTracker",
            "max_age": self.max_age,
            "min_hits": self.min_hits,
            "iou_threshold": self.iou_threshold,
            "frame_id": self.frame_id,
            "total_tracks": len(self.tracks),
            "confirmed_tracks": confirmed_count,
            "tentative_tracks": tentative_count,
            "next_id": self.next_id,
        }

    def set_max_age(self, max_age: int) -> None:
        """设置轨迹最大年龄"""
        self.max_age = max_age
        logger.info(f"简单跟踪器最大年龄已更新: {max_age}")

    def set_min_hits(self, min_hits: int) -> None:
        """设置轨迹确认所需的最小匹配次数"""
        self.min_hits = min_hits
        logger.info(f"简单跟踪器最小匹配次数已更新: {min_hits}")
