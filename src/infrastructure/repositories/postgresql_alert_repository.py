"""PostgreSQL告警仓储实现."""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

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
                           notification_sent, notification_channels_used, timestamp
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
        camera_id: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Alert]:
        """查询告警历史."""
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, rule_id, camera_id, alert_type, message, details,
                           notification_sent, notification_channels_used, timestamp
                    FROM alert_history
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::VARCHAR IS NULL OR alert_type = $2)
                    ORDER BY timestamp DESC
                    LIMIT $3
                    """,
                    camera_id,
                    alert_type,
                    limit,
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

    async def save(self, alert: Alert) -> int:
        """保存告警."""
        try:
            conn = await self._get_connection()
            try:
                alert_id = await conn.fetchval(
                    """
                    INSERT INTO alert_history (
                        rule_id, camera_id, alert_type, message, details,
                        notification_sent, notification_channels_used, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
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
                    alert.timestamp,
                )
                return alert_id
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
            raise RepositoryError(f"保存告警失败: {e}")

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
        )

