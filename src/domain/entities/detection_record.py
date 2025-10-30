"""
检测记录实体
表示一次检测的完整记录
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp

from .detected_object import DetectedObject


@dataclass
class DetectionRecord:
    """检测记录实体"""

    id: str
    camera_id: str
    objects: List[DetectedObject] = field(default_factory=list)
    timestamp: Timestamp = field(default_factory=Timestamp.now)
    confidence: Confidence = field(default_factory=lambda: Confidence(0.0))
    processing_time: float = 0.0
    frame_id: Optional[int] = None
    region_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.timestamp, datetime):
            self.timestamp = Timestamp(self.timestamp)
        if isinstance(self.confidence, (int, float)):
            self.confidence = Confidence(self.confidence)

    @property
    def object_count(self) -> int:
        """获取检测对象数量"""
        return len(self.objects)

    @property
    def person_count(self) -> int:
        """获取人体数量"""
        return sum(1 for obj in self.objects if obj.is_person)

    @property
    def vehicle_count(self) -> int:
        """获取车辆数量"""
        return sum(1 for obj in self.objects if obj.is_vehicle)

    @property
    def high_confidence_objects(self) -> List[DetectedObject]:
        """获取高置信度对象"""
        return [obj for obj in self.objects if obj.is_high_confidence]

    @property
    def medium_confidence_objects(self) -> List[DetectedObject]:
        """获取中等置信度对象"""
        return [obj for obj in self.objects if obj.is_medium_confidence]

    @property
    def low_confidence_objects(self) -> List[DetectedObject]:
        """获取低置信度对象"""
        return [obj for obj in self.objects if obj.is_low_confidence]

    @property
    def average_confidence(self) -> float:
        """获取平均置信度"""
        if not self.objects:
            return 0.0
        return sum(obj.confidence.value for obj in self.objects) / len(self.objects)

    @property
    def has_violations(self) -> bool:
        """是否有违规行为"""
        # 这里可以根据业务规则判断是否有违规
        # 例如：检测到未戴安全帽的人
        return any(
            obj.is_person
            and obj.confidence.is_high
            and obj.get_metadata("violation_type") is not None
            for obj in self.objects
        )

    @property
    def violation_types(self) -> List[str]:
        """获取违规类型列表"""
        violation_types = []
        for obj in self.objects:
            if obj.is_person and obj.confidence.is_high:
                violation_type = obj.get_metadata("violation_type")
                if violation_type and violation_type not in violation_types:
                    violation_types.append(violation_type)
        return violation_types

    def add_object(self, obj: DetectedObject) -> None:
        """
        添加检测对象

        Args:
            obj: 检测对象
        """
        if not isinstance(obj, DetectedObject):
            raise ValueError("Object must be a DetectedObject instance")

        self.objects.append(obj)
        self._update_confidence()

    def remove_object(self, obj: DetectedObject) -> bool:
        """
        移除检测对象

        Args:
            obj: 要移除的检测对象

        Returns:
            bool: 是否成功移除
        """
        try:
            self.objects.remove(obj)
            self._update_confidence()
            return True
        except ValueError:
            return False

    def get_objects_by_class(self, class_name: str) -> List[DetectedObject]:
        """
        根据类别获取对象

        Args:
            class_name: 类别名称

        Returns:
            List[DetectedObject]: 对象列表
        """
        return [obj for obj in self.objects if obj.class_name == class_name]

    def get_objects_by_confidence_range(
        self, min_confidence: float, max_confidence: float
    ) -> List[DetectedObject]:
        """
        根据置信度范围获取对象

        Args:
            min_confidence: 最小置信度
            max_confidence: 最大置信度

        Returns:
            List[DetectedObject]: 对象列表
        """
        return [
            obj
            for obj in self.objects
            if min_confidence <= obj.confidence.value <= max_confidence
        ]

    def get_tracked_objects(self) -> List[DetectedObject]:
        """获取有跟踪ID的对象"""
        return [obj for obj in self.objects if obj.track_id is not None]

    def get_untracked_objects(self) -> List[DetectedObject]:
        """获取没有跟踪ID的对象"""
        return [obj for obj in self.objects if obj.track_id is None]

    def find_object_by_track_id(self, track_id: int) -> Optional[DetectedObject]:
        """
        根据跟踪ID查找对象

        Args:
            track_id: 跟踪ID

        Returns:
            Optional[DetectedObject]: 找到的对象，如果不存在则返回None
        """
        for obj in self.objects:
            if obj.track_id == track_id:
                return obj
        return None

    def update_object_tracking(
        self, track_id: int, new_bbox, new_confidence: Confidence
    ) -> bool:
        """
        更新对象的跟踪信息

        Args:
            track_id: 跟踪ID
            new_bbox: 新的边界框
            new_confidence: 新的置信度

        Returns:
            bool: 是否成功更新
        """
        obj = self.find_object_by_track_id(track_id)
        if obj:
            obj.update_tracking(new_bbox, new_confidence)
            self._update_confidence()
            return True
        return False

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 键
            value: 值
        """
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
        return self.metadata.get(key, default)

    def _update_confidence(self) -> None:
        """更新整体置信度"""
        if self.objects:
            avg_conf = self.average_confidence
            self.confidence = Confidence(avg_conf)
        else:
            self.confidence = Confidence(0.0)

    def is_similar_to(
        self, other: "DetectionRecord", similarity_threshold: float = 0.8
    ) -> bool:
        """
        判断是否与另一个检测记录相似

        Args:
            other: 另一个检测记录
            similarity_threshold: 相似度阈值

        Returns:
            bool: 是否相似
        """
        if not isinstance(other, DetectionRecord):
            return False

        # 检查对象数量是否相近
        count_diff = abs(self.object_count - other.object_count)
        if count_diff > max(self.object_count, other.object_count) * 0.5:
            return False

        # 检查是否有相同的跟踪对象
        if self.get_tracked_objects() and other.get_tracked_objects():
            common_track_ids = set(
                obj.track_id for obj in self.get_tracked_objects()
            ) & set(obj.track_id for obj in other.get_tracked_objects())
            if len(common_track_ids) > 0:
                return True

        # 检查时间是否相近（5秒内）
        time_diff = abs(self.timestamp.time_difference(other.timestamp))
        if time_diff > 5.0:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "objects": [obj.to_dict() for obj in self.objects],
            "timestamp": self.timestamp.iso_string,
            "confidence": self.confidence.value,
            "processing_time": self.processing_time,
            "frame_id": self.frame_id,
            "region_id": self.region_id,
            "metadata": self.metadata,
            "object_count": self.object_count,
            "person_count": self.person_count,
            "vehicle_count": self.vehicle_count,
            "average_confidence": self.average_confidence,
            "has_violations": self.has_violations,
            "violation_types": self.violation_types,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionRecord":
        """从字典创建实例"""
        objects = [
            DetectedObject.from_dict(obj_data) for obj_data in data.get("objects", [])
        ]

        return cls(
            id=data["id"],
            camera_id=data["camera_id"],
            objects=objects,
            timestamp=Timestamp.from_iso(data["timestamp"]),
            confidence=Confidence(data["confidence"]),
            processing_time=data["processing_time"],
            frame_id=data.get("frame_id"),
            region_id=data.get("region_id"),
            metadata=data.get("metadata", {}),
        )

    def __str__(self) -> str:
        return f"DetectionRecord(id={self.id}, camera={self.camera_id}, objects={self.object_count})"

    def __repr__(self) -> str:
        return self.__str__()
