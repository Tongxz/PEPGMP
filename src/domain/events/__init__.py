"""
领域事件
包含领域事件定义
"""

from .detection_events import DetectionCreatedEvent, ViolationDetectedEvent

__all__ = ["DetectionCreatedEvent", "ViolationDetectedEvent"]
