"""
值对象
包含不可变的值对象
"""

from .bounding_box import BoundingBox
from .confidence import Confidence
from .handwash_step import HandwashStepLabel, HandwashStepType
from .timestamp import Timestamp

__all__ = [
    "BoundingBox",
    "Confidence",
    "Timestamp",
    "HandwashStepType",
    "HandwashStepLabel",
]
