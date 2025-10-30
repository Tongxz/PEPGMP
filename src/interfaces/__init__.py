"""
接口层 - 定义系统核心接口
遵循接口隔离原则，提供细粒度的接口定义
"""

from .detection.detector_interface import DetectionResult, IDetector
from .repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
)
from .tracking.tracker_interface import ITracker, TrackingResult

__all__ = [
    "IDetector",
    "DetectionResult",
    "ITracker",
    "TrackingResult",
    "IDetectionRepository",
    "DetectionRecord",
]
