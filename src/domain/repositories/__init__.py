"""
领域仓储接口
包含领域仓储接口定义
"""

from .camera_repository import ICameraRepository
from .detection_repository import IDetectionRepository
from .violation_repository import IViolationRepository

__all__ = ["IDetectionRepository", "ICameraRepository", "IViolationRepository"]
