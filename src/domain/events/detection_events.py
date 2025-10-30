"""
检测相关领域事件
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.detection_record import DetectionRecord
from src.domain.services.violation_service import Violation


@dataclass
class DetectionCreatedEvent:
    """检测创建事件"""

    detection_id: str
    camera_id: str
    timestamp: datetime
    object_count: int
    confidence: float
    processing_time: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_detection_record(cls, record: DetectionRecord) -> "DetectionCreatedEvent":
        """从检测记录创建事件"""
        return cls(
            detection_id=record.id,
            camera_id=record.camera_id,
            timestamp=record.timestamp.value,
            object_count=record.object_count,
            confidence=record.average_confidence,
            processing_time=record.processing_time,
            metadata=record.metadata.copy(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": "detection_created",
            "detection_id": self.detection_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "object_count": self.object_count,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }


@dataclass
class ViolationDetectedEvent:
    """违规检测事件"""

    violation_id: str
    violation_type: str
    severity: str
    camera_id: str
    timestamp: datetime
    confidence: float
    description: str
    detected_object_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_violation(cls, violation: Violation) -> "ViolationDetectedEvent":
        """从违规记录创建事件"""
        return cls(
            violation_id=violation.id,
            violation_type=violation.violation_type.value,
            severity=violation.severity.value,
            camera_id=violation.camera_id,
            timestamp=violation.timestamp,
            confidence=violation.confidence.value,
            description=violation.description,
            detected_object_id=str(violation.detected_object.track_id)
            if violation.detected_object.track_id
            else None,
            metadata=violation.metadata.copy(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": "violation_detected",
            "violation_id": self.violation_id,
            "violation_type": self.violation_type,
            "severity": self.severity,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "description": self.description,
            "detected_object_id": self.detected_object_id,
            "metadata": self.metadata,
        }
