"""告警规则写操作单元测试."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.entities.alert_rule import AlertRule
from src.domain.services.alert_rule_service import AlertRuleService
from src.domain.repositories.alert_rule_repository import IAlertRuleRepository


class MockAlertRuleRepository(IAlertRuleRepository):
    """Mock告警规则仓储."""

    def __init__(self):
        self.rules = {}
        self.next_id = 1

    async def find_by_id(self, rule_id: int) -> AlertRule | None:
        """根据ID查找告警规则."""
        return self.rules.get(rule_id)

    async def find_all(self, camera_id=None, enabled=None):
        """查询告警规则列表."""
        rules = list(self.rules.values())
        if camera_id is not None:
            rules = [r for r in rules if r.camera_id == camera_id]
        if enabled is not None:
            rules = [r for r in rules if r.enabled == enabled]
        return rules

    async def save(self, rule: AlertRule) -> int:
        """保存告警规则."""
        rule_id = self.next_id
        rule.id = rule_id
        self.next_id += 1
        self.rules[rule_id] = rule
        return rule_id

    async def update(self, rule_id: int, updates: dict) -> bool:
        """更新告警规则."""
        if rule_id not in self.rules:
            return False
        rule = self.rules[rule_id]
        for key, value in updates.items():
            setattr(rule, key, value)
        return True

    async def delete(self, rule_id: int) -> bool:
        """删除告警规则."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False


@pytest.fixture
def mock_repository():
    """创建Mock仓储."""
    return MockAlertRuleRepository()


@pytest.fixture
def alert_rule_service(mock_repository):
    """创建告警规则服务."""
    return AlertRuleService(mock_repository)


class TestCreateAlertRule:
    """测试创建告警规则."""

    @pytest.mark.asyncio
    async def test_create_alert_rule_success(self, alert_rule_service):
        """测试成功创建告警规则."""
        rule_data = {
            "name": "测试规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
            "camera_id": "camera_001",
            "enabled": True,
        }

        result = await alert_rule_service.create_alert_rule(rule_data)

        assert result["ok"] is True
        assert "id" in result
        assert result["id"] > 0

    @pytest.mark.asyncio
    async def test_create_alert_rule_missing_required_fields(self, alert_rule_service):
        """测试缺少必填字段."""
        rule_data = {
            "name": "测试规则",
            # 缺少 rule_type 和 conditions
        }

        with pytest.raises(ValueError, match="缺少必填字段"):
            await alert_rule_service.create_alert_rule(rule_data)

    @pytest.mark.asyncio
    async def test_create_alert_rule_with_optional_fields(self, alert_rule_service):
        """测试创建告警规则（包含可选字段）."""
        rule_data = {
            "name": "测试规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
            "notification_channels": ["email", "sms"],
            "recipients": ["user1@example.com"],
            "priority": "high",
            "created_by": "admin",
        }

        result = await alert_rule_service.create_alert_rule(rule_data)

        assert result["ok"] is True
        assert result["id"] > 0

    @pytest.mark.asyncio
    async def test_create_alert_rule_default_values(self, alert_rule_service):
        """测试创建告警规则（默认值）."""
        rule_data = {
            "name": "测试规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
        }

        result = await alert_rule_service.create_alert_rule(rule_data)

        assert result["ok"] is True

        # 验证默认值已设置
        rule = await alert_rule_service.alert_rule_repository.find_by_id(result["id"])
        assert rule.enabled is True
        assert rule.priority == "medium"


class TestUpdateAlertRule:
    """测试更新告警规则."""

    @pytest.mark.asyncio
    async def test_update_alert_rule_success(self, alert_rule_service, mock_repository):
        """测试成功更新告警规则."""
        # 先创建一个规则
        rule_data = {
            "name": "原始规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
        }
        create_result = await alert_rule_service.create_alert_rule(rule_data)
        rule_id = create_result["id"]

        # 更新规则
        updates = {
            "name": "更新后的规则",
            "enabled": False,
        }

        result = await alert_rule_service.update_alert_rule(rule_id, updates)

        assert result["ok"] is True

        # 验证更新
        rule = await mock_repository.find_by_id(rule_id)
        assert rule.name == "更新后的规则"
        assert rule.enabled is False

    @pytest.mark.asyncio
    async def test_update_alert_rule_not_found(self, alert_rule_service):
        """测试更新不存在的告警规则."""
        updates = {"name": "新名称"}

        with pytest.raises(ValueError, match="告警规则不存在"):
            await alert_rule_service.update_alert_rule(999, updates)

    @pytest.mark.asyncio
    async def test_update_alert_rule_empty_updates(self, alert_rule_service, mock_repository):
        """测试空更新（应该成功但不做任何更改）."""
        # 先创建一个规则
        rule_data = {
            "name": "原始规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
        }
        create_result = await alert_rule_service.create_alert_rule(rule_data)
        rule_id = create_result["id"]

        # 空更新
        result = await alert_rule_service.update_alert_rule(rule_id, {})

        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_update_alert_rule_filter_disallowed_fields(self, alert_rule_service, mock_repository):
        """测试过滤不允许的字段."""
        # 先创建一个规则
        rule_data = {
            "name": "原始规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
        }
        create_result = await alert_rule_service.create_alert_rule(rule_data)
        rule_id = create_result["id"]

        # 更新包含不允许的字段
        updates = {
            "name": "更新后的规则",
            "disallowed_field": "不应该被更新",
        }

        result = await alert_rule_service.update_alert_rule(rule_id, updates)

        assert result["ok"] is True

        # 验证只允许的字段被更新
        rule = await mock_repository.find_by_id(rule_id)
        assert rule.name == "更新后的规则"
        # disallowed_field 不应该被设置

    @pytest.mark.asyncio
    async def test_update_alert_rule_all_allowed_fields(self, alert_rule_service, mock_repository):
        """测试更新所有允许的字段."""
        # 先创建一个规则
        rule_data = {
            "name": "原始规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
        }
        create_result = await alert_rule_service.create_alert_rule(rule_data)
        rule_id = create_result["id"]

        # 更新所有允许的字段
        updates = {
            "name": "新名称",
            "camera_id": "camera_002",
            "rule_type": "threshold",
            "conditions": {"new_condition": True},
            "notification_channels": ["email"],
            "recipients": ["user@example.com"],
            "enabled": False,
            "priority": "high",
        }

        result = await alert_rule_service.update_alert_rule(rule_id, updates)

        assert result["ok"] is True

        # 验证所有字段都已更新
        rule = await mock_repository.find_by_id(rule_id)
        assert rule.name == "新名称"
        assert rule.camera_id == "camera_002"
        assert rule.rule_type == "threshold"
        assert rule.conditions == {"new_condition": True}
        assert rule.notification_channels == ["email"]
        assert rule.recipients == ["user@example.com"]
        assert rule.enabled is False
        assert rule.priority == "high"

