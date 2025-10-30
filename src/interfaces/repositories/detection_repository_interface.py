"""
检测记录仓储接口定义
遵循接口隔离原则，提供细粒度的数据访问接口
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DetectionRecord:
    """检测记录实体"""

    id: str
    camera_id: str
    objects: List[Dict[str, Any]]
    timestamp: datetime
    confidence: float
    processing_time: float
    frame_id: Optional[int] = None
    region_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.metadata:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "objects": self.objects,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "frame_id": self.frame_id,
            "region_id": self.region_id,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionRecord":
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            camera_id=data["camera_id"],
            objects=data["objects"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            confidence=data["confidence"],
            processing_time=data["processing_time"],
            frame_id=data.get("frame_id"),
            region_id=data.get("region_id"),
            metadata=data.get("metadata", {}),
        )


class IDetectionRepository(ABC):
    """检测记录仓储接口"""

    @abstractmethod
    async def save(self, record: DetectionRecord) -> str:
        """
        保存检测记录

        Args:
            record: 检测记录

        Returns:
            str: 保存的记录ID

        Raises:
            RepositoryError: 保存失败时抛出
        """

    @abstractmethod
    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """
        根据ID查找记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[DetectionRecord]: 检测记录，如果不存在则返回None
        """

    @abstractmethod
    async def find_by_camera_id(
        self, camera_id: str, limit: int = 100, offset: int = 0
    ) -> List[DetectionRecord]:
        """
        根据摄像头ID查找记录

        Args:
            camera_id: 摄像头ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """

    @abstractmethod
    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DetectionRecord]:
        """
        根据时间范围查找记录

        Args:
            start_time: 开始时间
            end_time: 结束时间
            camera_id: 摄像头ID（可选）
            limit: 限制数量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """

    @abstractmethod
    async def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DetectionRecord]:
        """
        根据置信度范围查找记录

        Args:
            min_confidence: 最小置信度
            max_confidence: 最大置信度
            camera_id: 摄像头ID（可选）
            limit: 限制数量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """

    @abstractmethod
    async def count_by_camera_id(self, camera_id: str) -> int:
        """
        统计摄像头记录数量

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 记录数量
        """

    @abstractmethod
    async def delete_by_id(self, record_id: str) -> bool:
        """
        根据ID删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 删除是否成功
        """

    @abstractmethod
    async def delete_by_camera_id(self, camera_id: str) -> int:
        """
        删除摄像头的所有记录

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 删除的记录数量
        """

    @abstractmethod
    async def get_statistics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict[str, Any]: 统计信息
        """


class RepositoryError(Exception):
    """仓储异常"""

    def __init__(self, message: str, error_code: str = "REPOSITORY_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
