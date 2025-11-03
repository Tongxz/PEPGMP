"""AlertRuleService单元测试."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.alert_rule import AlertRule
from src.domain.repositories.alert_rule_repository import IAlertRuleRepository
from src.domain.services.alert_rule_service import AlertRuleService


class MockAlertRuleRepository(IAlertRuleRepository):
    """模拟告警规则仓储."""

    def __init__(self):
        self._rules: list[AlertRule] = []

    async def find_by_id(self, rule_id: int) -> AlertRule | None:
        return next((r for r in self._rules if r.id == rule_id), None)

    async def find_all(
        self, camera_id: str | None = None, enabled: bool | None = None
    ) -> list[AlertRule]:
        result = self._rules.copy()
        if camera_id:
            result = [r for r in result if r.camera_id == camera_id]
        if enabled is not None:
            result = [r for r in result if r.enabled == enabled]
        return result

    async def save(self, rule: AlertRule) -> int:
        rule.id = len(self._rules) + 1
        self._rules.append(rule)
        return rule.id

    async def update(self, rule_id: int, updates: dict) -> bool:
        rule = await self.find_by_id(rule_id)
        if not rule:
            return False
        for key, value in updates.items():
            setattr(rule, key, value)
        return True

    async def delete(self, rule_id: int) -> bool:
        rule = await self.find_by_id(rule_id)
        if not rule:
            return False
        self._rules.remove(rule)
        return True


@pytest.fixture
def mock_repository():
    """创建模拟仓储."""
    return MockAlertRuleRepository()


@pytest.fixture
def alert_rule_service(mock_repository):
    """创建AlertRuleService实例."""
    return AlertRuleService(mock_repository)


@pytest.mark.asyncio
class TestAlertRuleService:
    """测试AlertRuleService."""

    async def test_list_alert_rules_success(self, alert_rule_service):
        """测试成功列出告警规则."""
        from datetime import datetime

        rule1 = AlertRule(
            id=1,
            name="规则1",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
        )
        rule2 = AlertRule(
            id=2,
            name="规则2",
            rule_type="error",
            conditions={"threshold": 10},
            enabled=False,
        )
        await alert_rule_service.alert_rule_repository.save(rule1)
        await alert_rule_service.alert_rule_repository.save(rule2)

        result = await alert_rule_service.list_alert_rules()

        assert "count" in result
        assert "items" in result
        assert result["count"] == 2
        assert len(result["items"]) == 2

    async def test_list_alert_rules_with_camera_filter(self, alert_rule_service):
        """测试按camera_id过滤告警规则."""
        rule1 = AlertRule(
            id=1,
            name="规则1",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
            camera_id="cam1",
        )
        rule2 = AlertRule(
            id=2,
            name="规则2",
            rule_type="violation",
            conditions={"threshold": 10},
            enabled=True,
            camera_id="cam2",
        )
        await alert_rule_service.alert_rule_repository.save(rule1)
        await alert_rule_service.alert_rule_repository.save(rule2)

        result = await alert_rule_service.list_alert_rules(camera_id="cam1")

        assert result["count"] == 1
        assert result["items"][0]["camera_id"] == "cam1"

    async def test_list_alert_rules_with_enabled_filter(self, alert_rule_service):
        """测试按enabled过滤告警规则."""
        rule1 = AlertRule(
            id=1,
            name="规则1",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
        )
        rule2 = AlertRule(
            id=2,
            name="规则2",
            rule_type="violation",
            conditions={"threshold": 10},
            enabled=False,
        )
        await alert_rule_service.alert_rule_repository.save(rule1)
        await alert_rule_service.alert_rule_repository.save(rule2)

        result = await alert_rule_service.list_alert_rules(enabled=True)

        assert result["count"] == 1
        assert result["items"][0]["enabled"] is True

    async def test_create_alert_rule_success(self, alert_rule_service):
        """测试成功创建告警规则."""
        rule = AlertRule(
            id=0,
            name="新规则",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
        )

        rule_id = await alert_rule_service.alert_rule_repository.save(rule)

        assert rule_id > 0

        saved_rule = await alert_rule_service.alert_rule_repository.find_by_id(rule_id)
        assert saved_rule is not None
        assert saved_rule.name == "新规则"

    async def test_update_alert_rule_success(self, alert_rule_service):
        """测试成功更新告警规则."""
        rule = AlertRule(
            id=1,
            name="原始规则",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
        )
        rule_id = await alert_rule_service.alert_rule_repository.save(rule)

        updates = {"name": "更新后的规则", "enabled": False}

        success = await alert_rule_service.alert_rule_repository.update(rule_id, updates)

        assert success is True

        updated_rule = await alert_rule_service.alert_rule_repository.find_by_id(rule_id)
        assert updated_rule.name == "更新后的规则"
        assert updated_rule.enabled is False

    async def test_update_alert_rule_not_found(self, alert_rule_service):
        """测试更新不存在的告警规则."""
        updates = {"name": "新名称"}

        # 更新不存在的规则会返回False，不会抛出异常
        success = await alert_rule_service.alert_rule_repository.update(999, updates)
        assert success is False

    async def test_delete_alert_rule_success(self, alert_rule_service):
        """测试成功删除告警规则."""
        rule = AlertRule(
            id=1,
            name="待删除规则",
            rule_type="violation",
            conditions={"threshold": 5},
            enabled=True,
        )
        rule_id = await alert_rule_service.alert_rule_repository.save(rule)

        success = await alert_rule_service.alert_rule_repository.delete(rule_id)

        assert success is True

        deleted_rule = await alert_rule_service.alert_rule_repository.find_by_id(rule_id)
        assert deleted_rule is None

    async def test_delete_alert_rule_not_found(self, alert_rule_service):
        """测试删除不存在的告警规则."""
        # 删除不存在的规则会返回False，不会抛出异常
        success = await alert_rule_service.alert_rule_repository.delete(999)
        assert success is False

    async def test_list_alert_rules_exception_handling(self, alert_rule_service):
        """测试列出告警规则时的异常处理."""
        # 模拟仓储异常
        original_find_all = alert_rule_service.alert_rule_repository.find_all
        
        async def mock_find_all_error(*args, **kwargs):
            raise RuntimeError("查询失败")
        
        alert_rule_service.alert_rule_repository.find_all = mock_find_all_error

        try:
            with pytest.raises(RuntimeError, match="查询失败"):
                await alert_rule_service.list_alert_rules()
        finally:
            alert_rule_service.alert_rule_repository.find_all = original_find_all

