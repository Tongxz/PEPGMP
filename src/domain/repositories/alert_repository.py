"""告警仓储接口."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.alert import Alert


class IAlertRepository(ABC):
    """告警仓储接口.

    定义告警数据的访问接口，支持不同的存储实现（PostgreSQL、Redis等）。
    """

    @abstractmethod
    async def find_by_id(self, alert_id: int) -> Optional[Alert]:
        """根据ID查找告警.

        Args:
            alert_id: 告警ID

        Returns:
            告警实体，如果不存在则返回None
        """

    @abstractmethod
    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[Alert]:
        """查询告警历史.

        Args:
            limit: 返回数量限制
            offset: 偏移量（用于分页）
            camera_id: 摄像头ID过滤（可选）
            alert_type: 告警类型过滤（可选）
            sort_by: 排序字段（可选，默认: timestamp）
            sort_order: 排序方向，asc 或 desc（默认: desc）

        Returns:
            告警列表，按指定字段和方向排序
        """

    @abstractmethod
    async def count(
        self,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> int:
        """统计告警总数（用于分页）.

        Args:
            camera_id: 摄像头ID过滤（可选）
            alert_type: 告警类型过滤（可选）

        Returns:
            符合条件的告警总数
        """

    @abstractmethod
    async def save(self, alert: Alert) -> int:
        """保存告警.

        Args:
            alert: 告警实体

        Returns:
            保存后的告警ID
        """

    @abstractmethod
    async def update_status(
        self,
        alert_id: int,
        status: str,
        handled_by: Optional[str] = None,
    ) -> Optional[Alert]:
        """更新告警状态.

        Args:
            alert_id: 告警ID
            status: 新状态 (confirmed, false_positive, resolved)
            handled_by: 处理人（可选）

        Returns:
            更新后的告警实体，如果不存在则返回None
        """
