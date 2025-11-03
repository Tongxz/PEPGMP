"""告警领域服务."""

import logging
from typing import Any, Dict, Optional

from src.domain.repositories.alert_repository import IAlertRepository

logger = logging.getLogger(__name__)


class AlertService:
    """告警领域服务.

    提供告警相关的业务逻辑。
    """

    def __init__(self, alert_repository: IAlertRepository):
        """初始化告警服务.

        Args:
            alert_repository: 告警仓储
        """
        self.alert_repository = alert_repository

    async def get_alert_history(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取告警历史.

        Args:
            limit: 返回数量限制
            camera_id: 摄像头ID过滤（可选）
            alert_type: 告警类型过滤（可选）

        Returns:
            包含告警列表和总数的字典
        """
        try:
            alerts = await self.alert_repository.find_all(
                limit=limit, camera_id=camera_id, alert_type=alert_type
            )

            items = [alert.to_dict() for alert in alerts]

            return {"count": len(items), "items": items}

        except Exception as e:
            logger.error(f"获取告警历史失败: {e}")
            raise
