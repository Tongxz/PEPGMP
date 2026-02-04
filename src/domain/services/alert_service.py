"""告警领域服务."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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

    async def update_alert_status(
        self,
        alert_id: int,
        status: str,
        handled_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新告警状态.

        Args:
            alert_id: 告警ID
            status: 新状态 (confirmed, false_positive, resolved)
            handled_by: 处理人（可选）

        Returns:
            更新后的告警信息字典

        Raises:
            ValueError: 当告警不存在或状态值无效时
        """
        try:
            # 验证状态值
            valid_statuses = ["pending", "confirmed", "false_positive", "resolved"]
            if status not in valid_statuses:
                raise ValueError(f"无效的状态值: {status}，有效值为: {valid_statuses}")

            # 更新状态
            updated_alert = await self.alert_repository.update_status(
                alert_id=alert_id,
                status=status,
                handled_by=handled_by,
            )

            if updated_alert is None:
                raise ValueError(f"告警不存在: alert_id={alert_id}")

            return updated_alert.to_dict()

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新告警状态失败: {e}")
            raise

    async def get_alert_by_id(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取告警详情.

        Args:
            alert_id: 告警ID

        Returns:
            告警信息字典，如果不存在则返回None
        """
        try:
            alert = await self.alert_repository.find_by_id(alert_id)
            if alert is None:
                return None
            return alert.to_dict()
        except Exception as e:
            logger.error(f"获取告警详情失败: {e}")
            raise

    async def get_alert_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取告警统计数据.

        Args:
            start_time: 开始时间（可选，默认7天前）
            end_time: 结束时间（可选，默认当前时间）
            camera_id: 摄像头ID过滤（可选）

        Returns:
            包含告警统计数据的字典
        """
        try:
            # 默认时间范围：最近7天
            if end_time is None:
                end_time = datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(days=7)

            # 获取总告警数
            total_count = await self.alert_repository.count(camera_id=camera_id)

            # 获取各状态的告警数
            pending_alerts = await self.alert_repository.find_all(
                limit=10000, camera_id=camera_id, alert_type=None
            )

            # 统计各状态的数量
            status_counts = {
                "pending": 0,
                "confirmed": 0,
                "false_positive": 0,
                "resolved": 0,
            }
            type_counts: Dict[str, int] = {}
            camera_counts: Dict[str, int] = {}

            for alert in pending_alerts:
                # 状态统计
                status = alert.status if hasattr(alert, "status") else "pending"
                if status in status_counts:
                    status_counts[status] += 1

                # 类型统计
                alert_type = (
                    alert.alert_type if hasattr(alert, "alert_type") else "unknown"
                )
                type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

                # 摄像头统计
                cam_id = alert.camera_id if hasattr(alert, "camera_id") else "unknown"
                camera_counts[cam_id] = camera_counts.get(cam_id, 0) + 1

            return {
                "total": total_count,
                "by_status": status_counts,
                "by_type": type_counts,
                "by_camera": camera_counts,
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None,
                },
            }

        except Exception as e:
            logger.error(f"获取告警统计失败: {e}")
            raise

    async def batch_update_status(
        self,
        alert_ids: List[int],
        status: str,
        handled_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """批量更新告警状态.

        Args:
            alert_ids: 告警ID列表
            status: 新状态 (confirmed, false_positive, resolved)
            handled_by: 处理人（可选）

        Returns:
            包含更新结果的字典

        Raises:
            ValueError: 当状态值无效时
        """
        try:
            # 验证状态值
            valid_statuses = ["pending", "confirmed", "false_positive", "resolved"]
            if status not in valid_statuses:
                raise ValueError(f"无效的状态值: {status}，有效值为: {valid_statuses}")

            success_count = 0
            failed_ids: List[int] = []

            for alert_id in alert_ids:
                try:
                    updated_alert = await self.alert_repository.update_status(
                        alert_id=alert_id,
                        status=status,
                        handled_by=handled_by,
                    )
                    if updated_alert is not None:
                        success_count += 1
                    else:
                        failed_ids.append(alert_id)
                except Exception:
                    failed_ids.append(alert_id)

            return {
                "ok": True,
                "success_count": success_count,
                "failed_count": len(failed_ids),
                "failed_ids": failed_ids,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"批量更新告警状态失败: {e}")
            raise
