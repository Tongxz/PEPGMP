"""违规仓储接口."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.domain.services.violation_service import Violation


class IViolationRepository(ABC):
    """违规仓储接口.

    定义违规数据的访问接口，支持不同的存储实现（PostgreSQL、Redis等）。
    """

    @abstractmethod
    async def save(
        self, violation: Violation, detection_id: Optional[str] = None
    ) -> int:
        """保存违规事件.

        Args:
            violation: 违规实体
            detection_id: 关联的检测记录ID（可选）

        Returns:
            保存后的违规事件ID
        """

    @abstractmethod
    async def find_by_id(self, violation_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查找违规事件.

        Args:
            violation_id: 违规事件ID

        Returns:
            违规事件字典，如果不存在则返回None
        """

    @abstractmethod
    async def find_all(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, any]:
        """查询违规事件列表.

        Args:
            camera_id: 摄像头ID过滤（可选）
            status: 状态过滤（可选）
            violation_type: 违规类型过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            包含违规列表和总数的字典: {"violations": List[Dict], "total": int, "limit": int, "offset": int}
        """

    @abstractmethod
    async def update_status(
        self,
        violation_id: int,
        status: str,
        notes: Optional[str] = None,
        handled_by: Optional[str] = None,
    ) -> bool:
        """更新违规事件状态.

        Args:
            violation_id: 违规事件ID
            status: 新状态（pending, confirmed, false_positive, resolved）
            notes: 备注信息（可选）
            handled_by: 处理人（可选）

        Returns:
            bool: 更新是否成功
        """
