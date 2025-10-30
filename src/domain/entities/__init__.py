"""
领域实体
包含业务核心实体
"""

from .camera import Camera
from .detected_object import DetectedObject
from .detection_record import DetectionRecord

__all__ = ["DetectionRecord", "Camera", "DetectedObject"]
