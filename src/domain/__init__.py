"""
领域层
包含业务逻辑、实体、值对象、领域服务等
"""

from .entities.camera import Camera
from .entities.detected_object import DetectedObject
from .entities.detection_record import DetectionRecord
from .events.detection_events import DetectionCreatedEvent, ViolationDetectedEvent
from .services.detection_service import DetectionService
from .services.violation_service import ViolationService
from .value_objects.bounding_box import BoundingBox
from .value_objects.confidence import Confidence
from .value_objects.timestamp import Timestamp

__all__ = [
    "DetectionRecord",
    "Camera",
    "DetectedObject",
    "BoundingBox",
    "Confidence",
    "Timestamp",
    "DetectionService",
    "ViolationService",
    "DetectionCreatedEvent",
    "ViolationDetectedEvent",
]
