"""
检测对象实体
表示检测到的目标对象
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence


@dataclass
class DetectedObject:
    """检测对象实体"""

    class_id: int
    class_name: str
    confidence: Confidence
    bbox: BoundingBox
    track_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_person(self) -> bool:
        """是否为人体"""
        return self.class_name.lower() in ["person", "人", "human"]

    @property
    def is_vehicle(self) -> bool:
        """是否为车辆"""
        return self.class_name.lower() in [
            "car",
            "truck",
            "bus",
            "motorcycle",
            "bicycle",
            "车",
            "汽车",
        ]

    @property
    def is_high_confidence(self) -> bool:
        """是否为高置信度"""
        return self.confidence.value >= 0.8

    @property
    def is_medium_confidence(self) -> bool:
        """是否为中等置信度"""
        return 0.5 <= self.confidence.value < 0.8

    @property
    def is_low_confidence(self) -> bool:
        """是否为低置信度"""
        return self.confidence.value < 0.5

    @property
    def area(self) -> float:
        """获取边界框面积"""
        return self.bbox.area

    @property
    def center(self) -> tuple[float, float]:
        """获取边界框中心点"""
        return self.bbox.center

    def is_same_object(
        self, other: "DetectedObject", iou_threshold: float = 0.5
    ) -> bool:
        """
        判断是否为同一个对象

        Args:
            other: 另一个检测对象
            iou_threshold: IoU阈值

        Returns:
            bool: 是否为同一个对象
        """
        if not isinstance(other, DetectedObject):
            return False

        # 类别必须相同
        if self.class_name != other.class_name:
            return False

        # 计算IoU
        iou = self.bbox.calculate_iou(other.bbox)
        return iou >= iou_threshold

    def update_tracking(
        self, new_bbox: BoundingBox, new_confidence: Confidence
    ) -> None:
        """
        更新跟踪信息

        Args:
            new_bbox: 新的边界框
            new_confidence: 新的置信度
        """
        self.bbox = new_bbox
        self.confidence = new_confidence
        self.timestamp = datetime.now()

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 键
            value: 值
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据

        Args:
            key: 键
            default: 默认值

        Returns:
            Any: 元数据值
        """
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence.value,
            "bbox": self.bbox.to_dict(),
            "track_id": self.track_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectedObject":
        """从字典创建实例"""
        return cls(
            class_id=data["class_id"],
            class_name=data["class_name"],
            confidence=Confidence(data["confidence"]),
            bbox=BoundingBox.from_dict(data["bbox"]),
            track_id=data.get("track_id"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else None,
            metadata=data.get("metadata"),
        )

    def __str__(self) -> str:
        return f"DetectedObject({self.class_name}, conf={self.confidence.value:.2f}, bbox={self.bbox})"

    def __repr__(self) -> str:
        return self.__str__()
