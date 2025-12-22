"""
区域仓储接口（Domain）

领域层只定义抽象接口，不依赖基础设施实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.core.region import Region


class IRegionRepository(ABC):
    """区域仓储接口."""

    @abstractmethod
    async def save(self, region: Region, camera_id: Optional[str] = None) -> str:
        """保存区域并返回 region_id."""

    @abstractmethod
    async def find_by_id(self, region_id: str) -> Optional[Region]:
        """按 region_id 查询区域."""

    @abstractmethod
    async def find_by_camera_id(self, camera_id: str) -> List[Region]:
        """按 camera_id 查询区域列表."""

    @abstractmethod
    async def find_all(self, active_only: bool = False) -> List[Region]:
        """查询所有区域."""

    @abstractmethod
    async def delete_by_id(self, region_id: str) -> bool:
        """删除区域，成功返回 True."""

    @abstractmethod
    async def save_meta(self, meta: Dict[str, Any]) -> None:
        """保存区域 meta 配置."""

    @abstractmethod
    async def get_meta(self) -> Optional[Dict[str, Any]]:
        """获取区域 meta 配置."""
