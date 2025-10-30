"""
跟踪器接口定义
遵循接口隔离原则，提供细粒度的跟踪器接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class Track:
    """跟踪轨迹"""

    track_id: int
    class_id: int
    class_name: str
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    age: int  # 轨迹年龄（帧数）
    hits: int  # 匹配次数
    time_since_update: int  # 自上次更新以来的帧数
    state: str  # 轨迹状态：'tentative', 'confirmed', 'deleted'

    @property
    def is_confirmed(self) -> bool:
        """轨迹是否已确认"""
        return self.state == "confirmed"

    @property
    def is_deleted(self) -> bool:
        """轨迹是否已删除"""
        return self.state == "deleted"


@dataclass
class TrackingResult:
    """跟踪结果"""

    tracks: List[Track]
    frame_id: int
    processing_time: float
    timestamp: Optional[datetime] = None

    @property
    def confirmed_tracks(self) -> List[Track]:
        """已确认的轨迹"""
        return [track for track in self.tracks if track.is_confirmed]

    @property
    def active_tracks(self) -> List[Track]:
        """活跃的轨迹（未删除）"""
        return [track for track in self.tracks if not track.is_deleted]

    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        """根据ID获取轨迹"""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None


class ITracker(ABC):
    """跟踪器接口"""

    @abstractmethod
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

    @abstractmethod
    def reset(self) -> None:
        """重置跟踪器状态"""

    @abstractmethod
    def get_track_count(self) -> int:
        """
        获取当前跟踪的轨迹数量

        Returns:
            int: 轨迹数量
        """

    @abstractmethod
    def get_track_statistics(self) -> Dict[str, Any]:
        """
        获取跟踪统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """

    @abstractmethod
    def set_max_age(self, max_age: int) -> None:
        """
        设置轨迹最大年龄

        Args:
            max_age: 最大年龄（帧数）
        """

    @abstractmethod
    def set_min_hits(self, min_hits: int) -> None:
        """
        设置轨迹确认所需的最小匹配次数

        Args:
            min_hits: 最小匹配次数
        """


class TrackingError(Exception):
    """跟踪异常"""

    def __init__(self, message: str, error_code: str = "TRACKING_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
