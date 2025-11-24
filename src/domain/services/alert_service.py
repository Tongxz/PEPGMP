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
        offset: int = 0,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """获取告警历史.

        Args:
            limit: 返回数量限制
            offset: 偏移量（用于分页）
            camera_id: 摄像头ID过滤（可选）
            alert_type: 告警类型过滤（可选）
            sort_by: 排序字段（可选，默认: timestamp）
            sort_order: 排序方向，asc 或 desc（默认: desc）

        Returns:
            包含告警列表、总数和分页信息的字典
        """
        try:
            # 获取总数
            total = await self.alert_repository.count(
                camera_id=camera_id, alert_type=alert_type
            )

            # 获取告警列表
            alerts = await self.alert_repository.find_all(
                limit=limit,
                offset=offset,
                camera_id=camera_id,
                alert_type=alert_type,
                sort_by=sort_by,
                sort_order=sort_order,
            )

            items = [alert.to_dict() for alert in alerts]

            return {
                "count": len(items),
                "total": total,
                "items": items,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"获取告警历史失败: {e}")
            raise
