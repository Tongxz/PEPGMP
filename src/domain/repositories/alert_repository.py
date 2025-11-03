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
        pass

    @abstractmethod
    async def find_all(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Alert]:
        """查询告警历史.

        Args:
            limit: 返回数量限制
            camera_id: 摄像头ID过滤（可选）
            alert_type: 告警类型过滤（可选）

        Returns:
            告警列表，按时间倒序
        """
        pass

    @abstractmethod
    async def save(self, alert: Alert) -> int:
        """保存告警.

        Args:
            alert: 告警实体

        Returns:
            保存后的告警ID
        """
        pass

