"""告警规则领域服务."""

import logging
from typing import Any, Dict, List, Optional

from src.domain.entities.alert_rule import AlertRule
from src.domain.repositories.alert_rule_repository import IAlertRuleRepository

logger = logging.getLogger(__name__)


class AlertRuleService:
    """告警规则领域服务.

    提供告警规则相关的业务逻辑。
    """

    def __init__(self, alert_rule_repository: IAlertRuleRepository):
        """初始化告警规则服务.

        Args:
            alert_rule_repository: 告警规则仓储
        """
        self.alert_rule_repository = alert_rule_repository

    async def list_alert_rules(
        self,
        camera_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """列出告警规则.

        Args:
            camera_id: 摄像头ID过滤（可选）
            enabled: 是否启用过滤（可选）

        Returns:
            包含告警规则列表和总数的字典
        """
        try:
            rules = await self.alert_rule_repository.find_all(
                camera_id=camera_id, enabled=enabled
            )

            items = [rule.to_dict() for rule in rules]

            return {"count": len(items), "items": items}

        except Exception as e:
            logger.error(f"列出告警规则失败: {e}")
            raise

    async def create_alert_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建告警规则.

        Args:
            rule_data: 告警规则数据字典

        Returns:
            包含创建结果的字典

        Raises:
            ValueError: 如果必填字段缺失
        """
        try:
            # 验证必填字段
            required_fields = ["name", "rule_type", "conditions"]
            for field in required_fields:
                if field not in rule_data:
                    raise ValueError(f"缺少必填字段: {field}")

            # 创建AlertRule实体
            from datetime import datetime
            rule = AlertRule(
                id=0,  # 临时ID，保存后会返回真实ID
                name=rule_data["name"],
                rule_type=rule_data["rule_type"],
                conditions=rule_data["conditions"],
                camera_id=rule_data.get("camera_id"),
                notification_channels=rule_data.get("notification_channels"),
                recipients=rule_data.get("recipients"),
                enabled=rule_data.get("enabled", True),
                priority=rule_data.get("priority", "medium"),
                created_by=rule_data.get("created_by"),
            )

            # 保存到仓储
            rule_id = await self.alert_rule_repository.save(rule)

            logger.info(f"告警规则创建成功: {rule_id}")
            return {"ok": True, "id": rule_id}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"创建告警规则失败: {e}")
            raise

    async def update_alert_rule(
        self, rule_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新告警规则.

        Args:
            rule_id: 告警规则ID
            updates: 要更新的字段字典

        Returns:
            包含更新结果的字典

        Raises:
            ValueError: 如果告警规则不存在
        """
        try:
            # 查找告警规则
            rule = await self.alert_rule_repository.find_by_id(rule_id)
            if not rule:
                raise ValueError(f"告警规则不存在: {rule_id}")

            # 只允许更新特定字段
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

            # 过滤允许的字段
            filtered_updates = {
                k: v for k, v in updates.items() if k in allowed_fields
            }

            if not filtered_updates:
                return {"ok": True}

            # 更新到仓储
            updated = await self.alert_rule_repository.update(rule_id, filtered_updates)

            if updated:
                logger.info(f"告警规则更新成功: {rule_id}")
                return {"ok": True}
            else:
                raise ValueError(f"告警规则更新失败: {rule_id}")

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新告警规则失败: {e}")
            raise

