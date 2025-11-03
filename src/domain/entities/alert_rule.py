"""告警规则领域实体."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AlertRule:
    """告警规则领域实体.

    代表一条告警规则，定义告警条件和通知配置。
    """

    id: int
    name: str
    rule_type: str
    conditions: Dict[str, Any]

    # 可选字段
    camera_id: Optional[str] = None
    notification_channels: Optional[List[str]] = None
    recipients: Optional[List[str]] = None
    enabled: bool = True
    priority: str = "medium"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式.

        Returns:
            告警规则信息的字典表示
        """
        result = {
            "id": self.id,
            "name": self.name,
            "rule_type": self.rule_type,
            "conditions": self.conditions,
            "enabled": self.enabled,
            "priority": self.priority,
        }

        if self.camera_id is not None:
            result["camera_id"] = self.camera_id

        if self.notification_channels is not None:
            result["notification_channels"] = self.notification_channels

        if self.recipients is not None:
            result["recipients"] = self.recipients

        if self.created_at is not None:
            result["created_at"] = (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else str(self.created_at)
            )

        if self.updated_at is not None:
            result["updated_at"] = (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, datetime)
                else str(self.updated_at)
            )

        if self.created_by is not None:
            result["created_by"] = self.created_by

        return result

    def is_active(self) -> bool:
        """检查规则是否激活.

        Returns:
            规则是否激活
        """
        return self.enabled
