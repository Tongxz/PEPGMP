"""告警规则仓储接口."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.alert_rule import AlertRule


class IAlertRuleRepository(ABC):
    """告警规则仓储接口.

    定义告警规则数据的访问接口，支持不同的存储实现（PostgreSQL、Redis等）。
    """

    @abstractmethod
    async def find_by_id(self, rule_id: int) -> Optional[AlertRule]:
        """根据ID查找告警规则.

        Args:
            rule_id: 告警规则ID

        Returns:
            告警规则实体，如果不存在则返回None
        """

    @abstractmethod
    async def find_all(
        self,
        camera_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[AlertRule]:
        """查询告警规则列表.

        Args:
            camera_id: 摄像头ID过滤（可选）
            enabled: 是否启用过滤（可选）

        Returns:
            告警规则列表
        """

    @abstractmethod
    async def save(self, rule: AlertRule) -> int:
        """保存告警规则.

        Args:
            rule: 告警规则实体

        Returns:
            保存后的规则ID
        """

    @abstractmethod
    async def update(self, rule_id: int, updates: dict) -> bool:
        """更新告警规则.

        Args:
            rule_id: 告警规则ID
            updates: 要更新的字段字典

        Returns:
            更新是否成功
        """

    @abstractmethod
    async def delete(self, rule_id: int) -> bool:
        """删除告警规则.

        Args:
            rule_id: 告警规则ID

        Returns:
            删除是否成功
        """
