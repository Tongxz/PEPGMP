"""PostgreSQL告警仓储实现."""

import json
import logging
from typing import List, Optional

import asyncpg
from asyncpg import Pool

from src.domain.entities.alert import Alert
from src.domain.repositories.alert_repository import IAlertRepository
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLAlertRepository(IAlertRepository):
    """PostgreSQL告警仓储实现."""

    def __init__(self, pool: Pool):
        """初始化PostgreSQL告警仓储.

        Args:
            pool: PostgreSQL连接池
        """
        self.pool = pool

    async def _get_connection(self):
        """获取数据库连接."""
        return await self.pool.acquire()

    async def find_by_id(self, alert_id: int) -> Optional[Alert]:
        """根据ID查找告警."""
        try:
            conn = await self._get_connection()
            try:
                row = await conn.fetchrow(
                    """
                    SELECT id, rule_id, camera_id, alert_type, message, details,
                           notification_sent, notification_channels_used, timestamp,
                           status, handled_at, handled_by
                    FROM alert_history
                    WHERE id = $1
                    """,
                    alert_id,
                )

                if not row:
                    return None

                return self._row_to_alert(row)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询告警失败: {e}")
            raise RepositoryError(f"查询告警失败: {e}")

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[Alert]:
        """查询告警历史."""
        try:
            conn = await self._get_connection()
            try:
                # 验证排序字段
                valid_sort_fields = ["timestamp", "camera_id", "alert_type", "id"]
                sort_field = sort_by if sort_by in valid_sort_fields else "timestamp"
                sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

                rows = await conn.fetch(
                    f"""
                    SELECT id, rule_id, camera_id, alert_type, message, details,
                           notification_sent, notification_channels_used, timestamp,
                           status, handled_at, handled_by
                    FROM alert_history
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::VARCHAR IS NULL OR alert_type = $2)
                    ORDER BY {sort_field} {sort_direction}
                    LIMIT $3 OFFSET $4
                    """,  # nosec B608 - sort_field/sort_direction from allowlist
                    camera_id,
                    alert_type,
                    limit,
                    offset,
                )

                alerts = []
                for row in rows:
                    alerts.append(self._row_to_alert(row))

                return alerts
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询告警历史失败: {e}")
            raise RepositoryError(f"查询告警历史失败: {e}")

    async def count(
        self,
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> int:
        """统计告警总数（用于分页）."""
        try:
            conn = await self._get_connection()
            try:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM alert_history
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::VARCHAR IS NULL OR alert_type = $2)
                    """,
                    camera_id,
                    alert_type,
                )
                return count or 0
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"统计告警总数失败: {e}")
            raise RepositoryError(f"统计告警总数失败: {e}")

    async def save(self, alert: Alert) -> int:
        """保存告警."""
        try:
            conn = await self._get_connection()
            try:
                # 数据库列是 TIMESTAMP WITHOUT TIME ZONE，需要naive datetime
                # 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
                from datetime import timezone as tz

                timestamp_value = alert.timestamp
                if timestamp_value.tzinfo is not None:
                    # 转换为UTC并去掉时区信息
                    timestamp_value = timestamp_value.astimezone(tz.utc).replace(
                        tzinfo=None
                    )

                alert_id = await conn.fetchval(
                    """
                    INSERT INTO alert_history (
                        rule_id, camera_id, alert_type, message, details,
                        notification_sent, notification_channels_used, timestamp,
                        status, handled_at, handled_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id
                    """,
                    alert.rule_id,
                    alert.camera_id,
                    alert.alert_type,
                    alert.message,
                    json.dumps(alert.details) if alert.details else None,
                    alert.notification_sent,
                    json.dumps(alert.notification_channels_used)
                    if alert.notification_channels_used
                    else None,
                    timestamp_value,
                    alert.status or "pending",
                    alert.handled_at.astimezone(tz.utc).replace(tzinfo=None)
                    if alert.handled_at and alert.handled_at.tzinfo
                    else alert.handled_at,
                    alert.handled_by,
                )
                return alert_id
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
            raise RepositoryError(f"保存告警失败: {e}")

    async def update_status(
        self,
        alert_id: int,
        status: str,
        handled_by: Optional[str] = None,
    ) -> Optional[Alert]:
        """更新告警状态."""
        try:
            conn = await self._get_connection()
            try:
                from datetime import datetime

                # 验证状态值
                valid_statuses = ["pending", "confirmed", "false_positive", "resolved"]
                if status not in valid_statuses:
                    raise ValueError(f"无效的状态值: {status}，有效值为: {valid_statuses}")

                # 更新状态
                handled_at = datetime.utcnow()
                row = await conn.fetchrow(
                    """
                    UPDATE alert_history
                    SET status = $1, handled_at = $2, handled_by = $3
                    WHERE id = $4
                    RETURNING id, rule_id, camera_id, alert_type, message, details,
                              notification_sent, notification_channels_used, timestamp,
                              status, handled_at, handled_by
                    """,
                    status,
                    handled_at,
                    handled_by,
                    alert_id,
                )

                if not row:
                    return None

                return self._row_to_alert(row)
            finally:
                await self.pool.release(conn)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新告警状态失败: {e}")
            raise RepositoryError(f"更新告警状态失败: {e}")

    def _row_to_alert(self, row: asyncpg.Record) -> Alert:
        """将数据库行转换为Alert实体."""
        # 解析JSON字段
        details = None
        if row.get("details"):
            try:
                if isinstance(row["details"], str):
                    details = json.loads(row["details"])
                else:
                    details = row["details"]
            except Exception:
                pass

        notification_channels_used = None
        if row.get("notification_channels_used"):
            try:
                if isinstance(row["notification_channels_used"], str):
                    notification_channels_used = json.loads(
                        row["notification_channels_used"]
                    )
                else:
                    notification_channels_used = row["notification_channels_used"]
            except Exception:
                pass

        return Alert(
            id=row["id"],
            rule_id=row.get("rule_id"),
            camera_id=row["camera_id"],
            alert_type=row["alert_type"],
            message=row.get("message", ""),
            timestamp=row["timestamp"],
            details=details,
            notification_sent=row.get("notification_sent", False),
            notification_channels_used=notification_channels_used,
            status=row.get("status", "pending"),
            handled_at=row.get("handled_at"),
            handled_by=row.get("handled_by"),
        )
