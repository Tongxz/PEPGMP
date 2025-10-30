"""
摄像头领域仓储接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.camera import Camera


class ICameraRepository(ABC):
    """摄像头领域仓储接口"""

    @abstractmethod
    async def save(self, camera: Camera) -> str:
        """
        保存摄像头

        Args:
            camera: 摄像头实体

        Returns:
            str: 保存的摄像头ID
        """

    @abstractmethod
    async def find_by_id(self, camera_id: str) -> Optional[Camera]:
        """
        根据ID查找摄像头

        Args:
            camera_id: 摄像头ID

        Returns:
            Optional[Camera]: 摄像头实体，如果不存在则返回None
        """

    @abstractmethod
    async def find_by_region_id(self, region_id: str) -> List[Camera]:
        """
        根据区域ID查找摄像头

        Args:
            region_id: 区域ID

        Returns:
            List[Camera]: 摄像头列表
        """

    @abstractmethod
    async def find_all(self) -> List[Camera]:
        """
        查找所有摄像头

        Returns:
            List[Camera]: 摄像头列表
        """

    @abstractmethod
    async def find_active(self) -> List[Camera]:
        """
        查找活跃的摄像头

        Returns:
            List[Camera]: 活跃摄像头列表
        """

    @abstractmethod
    async def count(self) -> int:
        """
        统计摄像头数量

        Returns:
            int: 摄像头数量
        """

    @abstractmethod
    async def delete_by_id(self, camera_id: str) -> bool:
        """
        根据ID删除摄像头

        Args:
            camera_id: 摄像头ID

        Returns:
            bool: 删除是否成功
        """

    @abstractmethod
    async def exists(self, camera_id: str) -> bool:
        """
        检查摄像头是否存在

        Args:
            camera_id: 摄像头ID

        Returns:
            bool: 是否存在
        """
