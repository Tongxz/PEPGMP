"""PostgreSQL告警规则仓储实现."""

import json
import logging
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg import Pool

from src.domain.entities.alert_rule import AlertRule
from src.domain.repositories.alert_rule_repository import IAlertRuleRepository
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLAlertRuleRepository(IAlertRuleRepository):
    """PostgreSQL告警规则仓储实现."""

    def __init__(self, pool: Pool):
        """初始化PostgreSQL告警规则仓储.

        Args:
            pool: PostgreSQL连接池
        """
        self.pool = pool

    async def _get_connection(self):
        """获取数据库连接."""
        return await self.pool.acquire()

    async def find_by_id(self, rule_id: int) -> Optional[AlertRule]:
        """根据ID查找告警规则."""
        try:
            conn = await self._get_connection()
            try:
                row = await conn.fetchrow(
                    """
                    SELECT id, name, camera_id, rule_type, conditions,
                           notification_channels, recipients, enabled, priority,
                           created_at, updated_at, created_by
                    FROM alert_rules
                    WHERE id = $1
                    """,
                    rule_id,
                )

                if not row:
                    return None

                return self._row_to_alert_rule(row)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询告警规则失败: {e}")
            raise RepositoryError(f"查询告警规则失败: {e}")

    async def find_all(
        self,
        camera_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> List[AlertRule]:
        """查询告警规则列表."""
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, camera_id, rule_type, conditions,
                           notification_channels, recipients, enabled, priority,
                           created_at, updated_at, created_by
                    FROM alert_rules
                    WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
                      AND ($2::BOOLEAN IS NULL OR enabled = $2)
                    ORDER BY created_at DESC
                    """,
                    camera_id,
                    enabled,
                )

                rules = []
                for row in rows:
                    rules.append(self._row_to_alert_rule(row))

                return rules
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查询告警规则列表失败: {e}")
            raise RepositoryError(f"查询告警规则列表失败: {e}")

    async def save(self, rule: AlertRule) -> int:
        """保存告警规则."""
        try:
            conn = await self._get_connection()
            try:
                rule_id = await conn.fetchval(
                    """
                    INSERT INTO alert_rules (
                        name, camera_id, rule_type, conditions,
                        notification_channels, recipients, enabled, priority,
                        created_at, updated_at, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), $9)
                    RETURNING id
                    """,
                    rule.name,
                    rule.camera_id,
                    rule.rule_type,
                    json.dumps(rule.conditions),
                    json.dumps(rule.notification_channels)
                    if rule.notification_channels
                    else None,
                    json.dumps(rule.recipients) if rule.recipients else None,
                    rule.enabled,
                    rule.priority,
                    rule.created_by,
                )
                return rule_id
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存告警规则失败: {e}")
            raise RepositoryError(f"保存告警规则失败: {e}")

    async def update(self, rule_id: int, updates: Dict[str, Any]) -> bool:
        """更新告警规则."""
        try:
            conn = await self._get_connection()
            try:
                # 构建更新字段
                update_fields = []
                params: List[Any] = []
                param_idx = 1

                allowed_fields = [
                    "name",
                    "camera_id",
                    "rule_type",
                    "conditions",
                    "notification_channels",
                    "recipients",
                    "enabled",
                    "priority",
                ]

                for field, value in updates.items():
                    if field in allowed_fields:
                        if field in ["conditions", "notification_channels", "recipients"]:
                            value = json.dumps(value) if value else None
                        update_fields.append(f"{field} = ${param_idx}")
                        params.append(value)
                        param_idx += 1

                if not update_fields:
                    return True  # 没有需要更新的字段

                # 添加更新时间
                update_fields.append("updated_at = NOW()")

                params.append(rule_id)
                update_sql = f"""
                    UPDATE alert_rules
                    SET {', '.join(update_fields)}
                    WHERE id = ${param_idx}
                """

                result = await conn.execute(update_sql, *params)

                # PostgreSQL返回格式: "UPDATE N"
                updated_count = int(result.split()[-1])
                return updated_count > 0
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"更新告警规则失败: {e}")
            raise RepositoryError(f"更新告警规则失败: {e}")

    async def delete(self, rule_id: int) -> bool:
        """删除告警规则."""
        try:
            conn = await self._get_connection()
            try:
                result = await conn.execute(
                    """
                    DELETE FROM alert_rules
                    WHERE id = $1
                    """,
                    rule_id,
                )

                # PostgreSQL返回格式: "DELETE N"
                deleted_count = int(result.split()[-1])
                return deleted_count > 0
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"删除告警规则失败: {e}")
            raise RepositoryError(f"删除告警规则失败: {e}")

    def _row_to_alert_rule(self, row: asyncpg.Record) -> AlertRule:
        """将数据库行转换为AlertRule实体."""
        # 解析JSON字段
        conditions = {}
        if row.get("conditions"):
            try:
                if isinstance(row["conditions"], str):
                    conditions = json.loads(row["conditions"])
                else:
                    conditions = row["conditions"]
            except Exception:
                pass

        notification_channels = None
        if row.get("notification_channels"):
            try:
                if isinstance(row["notification_channels"], str):
                    notification_channels = json.loads(row["notification_channels"])
                else:
                    notification_channels = row["notification_channels"]
            except Exception:
                pass

        recipients = None
        if row.get("recipients"):
            try:
                if isinstance(row["recipients"], str):
                    recipients = json.loads(row["recipients"])
                else:
                    recipients = row["recipients"]
            except Exception:
                pass

        return AlertRule(
            id=row["id"],
            name=row["name"],
            rule_type=row["rule_type"],
            conditions=conditions,
            camera_id=row.get("camera_id"),
            notification_channels=notification_channels,
            recipients=recipients,
            enabled=row.get("enabled", True),
            priority=row.get("priority", "medium"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            created_by=row.get("created_by"),
        )

