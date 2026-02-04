"""告警领域实体."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Alert:
    """告警领域实体.

    代表一条告警历史记录，包含告警的所有相关信息。
    """

    id: int
    camera_id: str
    alert_type: str
    message: str
    timestamp: datetime

    # 可选字段
    rule_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    notification_sent: bool = False
    notification_channels_used: Optional[List[str]] = None
    status: Optional[str] = "pending"  # pending, confirmed, false_positive, resolved
    handled_at: Optional[datetime] = None
    handled_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式.

        Returns:
            告警信息的字典表示
        """
        result = {
            "id": self.id,
            "camera_id": self.camera_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
            if isinstance(self.timestamp, datetime)
            else str(self.timestamp),
            "notification_sent": self.notification_sent,
        }

        if self.rule_id is not None:
            result["rule_id"] = self.rule_id

        if self.details is not None:
            result["details"] = self.details

        if self.notification_channels_used is not None:
            result["notification_channels_used"] = self.notification_channels_used

        if self.status is not None:
            result["status"] = self.status

        if self.handled_at is not None:
            result["handled_at"] = (
                self.handled_at.isoformat()
                if isinstance(self.handled_at, datetime)
                else str(self.handled_at)
            )

        if self.handled_by is not None:
            result["handled_by"] = self.handled_by

        return result
