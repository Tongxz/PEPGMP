"""
检测器接口定义
遵循接口隔离原则，提供细粒度的检测器接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class DetectedObject:
    """检测到的对象"""

    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]
    track_id: Optional[int] = None  # 跟踪ID，如果可用


@dataclass
class DetectionResult:
    """检测结果"""

    objects: List[DetectedObject]
    processing_time: float
    frame_id: Optional[int] = None
    timestamp: Optional[datetime] = None

    @property
    def object_count(self) -> int:
        """检测到的对象数量"""
        return len(self.objects)

    @property
    def confidence_score(self) -> float:
        """平均置信度"""
        if not self.objects:
            return 0.0
        return sum(obj.confidence for obj in self.objects) / len(self.objects)

    def get_objects_by_class(self, class_name: str) -> List[DetectedObject]:
        """根据类别获取对象"""
        return [obj for obj in self.objects if obj.class_name == class_name]

    def get_high_confidence_objects(
        self, threshold: float = 0.5
    ) -> List[DetectedObject]:
        """获取高置信度对象"""
        return [obj for obj in self.objects if obj.confidence >= threshold]


class IDetector(ABC):
    """检测器接口"""

    @abstractmethod
    async def detect(self, image: np.ndarray) -> DetectionResult:
        """
        检测图像中的对象

        Args:
            image: 输入图像 (numpy array)

        Returns:
            DetectionResult: 检测结果

        Raises:
            DetectionError: 检测失败时抛出
        """

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict[str, Any]: 模型信息字典
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查检测器是否可用

        Returns:
            bool: 检测器是否可用
        """

    @abstractmethod
    def get_supported_classes(self) -> List[str]:
        """
        获取支持的类别列表

        Returns:
            List[str]: 支持的类别名称列表
        """

    @abstractmethod
    def set_confidence_threshold(self, threshold: float) -> None:
        """
        设置置信度阈值

        Args:
            threshold: 置信度阈值 (0.0-1.0)
        """

    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """
        获取当前置信度阈值

        Returns:
            float: 当前置信度阈值
        """


class DetectionError(Exception):
    """检测异常"""

    def __init__(self, message: str, error_code: str = "DETECTION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
