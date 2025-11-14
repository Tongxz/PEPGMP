"""
检测参数配置仓储接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IDetectionConfigRepository(ABC):
    """检测参数配置仓储接口"""

    @abstractmethod
    async def save(
        self,
        camera_id: Optional[str],
        config_type: str,
        config_key: str,
        config_value: Any,
        description: Optional[str] = None,
    ) -> int:
        """
        保存检测参数配置

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型（human_detection, hairnet_detection等）
            config_key: 配置项名称
            config_value: 配置值
            description: 配置项描述

        Returns:
            int: 保存的配置项ID
        """

    @abstractmethod
    async def find_by_camera_and_type(
        self, camera_id: Optional[str], config_type: str
    ) -> Dict[str, Any]:
        """
        根据摄像头ID和配置类型查找配置

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型

        Returns:
            Dict[str, Any]: 配置字典（键值对）
        """

    @abstractmethod
    async def find_all_by_type(self, config_type: str) -> List[Dict[str, Any]]:
        """
        查找指定类型的所有配置（包括全局和按相机的）

        Args:
            config_type: 配置类型

        Returns:
            List[Dict[str, Any]]: 配置列表
        """

    @abstractmethod
    async def find_all(self) -> Dict[str, Dict[str, Any]]:
        """
        查找所有配置

        Returns:
            Dict[str, Dict[str, Any]]: 配置字典，键为config_type，值为配置字典
        """

    @abstractmethod
    async def delete(
        self, camera_id: Optional[str], config_type: str, config_key: str
    ) -> bool:
        """
        删除配置项

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型
            config_key: 配置项名称

        Returns:
            bool: 删除是否成功
        """

    @abstractmethod
    async def exists(
        self, camera_id: Optional[str], config_type: str, config_key: str
    ) -> bool:
        """
        检查配置项是否存在

        Args:
            camera_id: 摄像头ID，None表示全局默认值
            config_type: 配置类型
            config_key: 配置项名称

        Returns:
            bool: 是否存在
        """
