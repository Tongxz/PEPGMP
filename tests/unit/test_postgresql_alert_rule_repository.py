"""PostgreSQL告警规则仓储单元测试."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

from src.domain.entities.alert_rule import AlertRule
from src.infrastructure.repositories.postgresql_alert_rule_repository import (
    PostgreSQLAlertRuleRepository,
)
from src.interfaces.repositories.detection_repository_interface import RepositoryError


class MockRecord:
    """模拟asyncpg.Record."""
    
    def __init__(self, data):
        self._data = data
    
    def __getitem__(self, key):
        return self._data[key]
    
    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.fixture
def mock_pool():
    """创建模拟的连接池."""
    return MagicMock(spec=asyncpg.Pool)


@pytest.fixture
def alert_rule_repository(mock_pool):
    """创建PostgreSQL告警规则仓储实例."""
    return PostgreSQLAlertRuleRepository(mock_pool)


@pytest.fixture
def sample_alert_rule():
    """创建示例告警规则."""
    return AlertRule(
        id=1,
        name="测试规则",
        rule_type="violation",
        conditions={"threshold": 5},
        camera_id="cam1",
        notification_channels=["email", "sms"],
        recipients=["user@example.com"],
        enabled=True,
        priority="high",
        created_by="admin",
    )


@pytest.fixture
def mock_row():
    """创建模拟的数据库行."""
    return MockRecord({
        "id": 1,
        "name": "测试规则",
        "camera_id": "cam1",
        "rule_type": "violation",
        "conditions": json.dumps({"threshold": 5}),
        "notification_channels": json.dumps(["email", "sms"]),
        "recipients": json.dumps(["user@example.com"]),
        "enabled": True,
        "priority": "high",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "created_by": "admin",
    })


@pytest.mark.asyncio
class TestPostgreSQLAlertRuleRepository:
    """测试PostgreSQL告警规则仓储."""

    async def test_find_by_id_success(
        self, alert_rule_repository, mock_pool, mock_row
    ):
        """测试根据ID查找告警规则成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await alert_rule_repository.find_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "测试规则"
        assert result.rule_type == "violation"
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_by_id_not_found(self, alert_rule_repository, mock_pool):
        """测试根据ID查找告警规则不存在."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result = await alert_rule_repository.find_by_id(999)

        assert result is None
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_by_id_exception(self, alert_rule_repository, mock_pool):
        """测试根据ID查找告警规则时发生异常."""
        mock_pool.acquire = AsyncMock(side_effect=Exception("数据库连接失败"))

        with pytest.raises(RepositoryError, match="查询告警规则失败"):
            await alert_rule_repository.find_by_id(1)

    async def test_find_all_success(
        self, alert_rule_repository, mock_pool, mock_row
    ):
        """测试查询所有告警规则成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_rule_repository.find_all()

        assert len(result) == 1
        assert result[0].id == 1
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_all_with_camera_filter(
        self, alert_rule_repository, mock_pool, mock_row
    ):
        """测试按camera_id过滤查询告警规则."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_rule_repository.find_all(camera_id="cam1")

        assert len(result) == 1
        mock_conn.fetch.assert_called_once()

    async def test_find_all_with_enabled_filter(
        self, alert_rule_repository, mock_pool, mock_row
    ):
        """测试按enabled过滤查询告警规则."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_rule_repository.find_all(enabled=True)

        assert len(result) == 1
        mock_conn.fetch.assert_called_once()

    async def test_find_all_empty(self, alert_rule_repository, mock_pool):
        """测试查询所有告警规则为空."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        result = await alert_rule_repository.find_all()

        assert len(result) == 0

    async def test_find_all_exception(self, alert_rule_repository, mock_pool):
        """测试查询所有告警规则时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("查询失败"))

        with pytest.raises(RepositoryError, match="查询告警规则列表失败"):
            await alert_rule_repository.find_all()

    async def test_save_success(
        self, alert_rule_repository, mock_pool, sample_alert_rule
    ):
        """测试保存告警规则成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        result = await alert_rule_repository.save(sample_alert_rule)

        assert result == 1
        mock_conn.fetchval.assert_called_once()
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_save_without_optional_fields(
        self, alert_rule_repository, mock_pool
    ):
        """测试保存没有可选字段的告警规则."""
        rule = AlertRule(
            id=0,
            name="测试规则",
            rule_type="violation",
            conditions={"threshold": 5},
        )
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        result = await alert_rule_repository.save(rule)

        assert result == 1
        mock_conn.fetchval.assert_called_once()

    async def test_save_exception(
        self, alert_rule_repository, mock_pool, sample_alert_rule
    ):
        """测试保存告警规则时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("保存失败"))

        with pytest.raises(RepositoryError, match="保存告警规则失败"):
            await alert_rule_repository.save(sample_alert_rule)

    async def test_update_success(
        self, alert_rule_repository, mock_pool, sample_alert_rule
    ):
        """测试更新告警规则成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        updates = {"name": "更新后的规则", "enabled": False}
        result = await alert_rule_repository.update(1, updates)

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_update_not_found(self, alert_rule_repository, mock_pool):
        """测试更新不存在的告警规则."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")

        updates = {"name": "新名称"}
        result = await alert_rule_repository.update(999, updates)

        assert result is False

    async def test_update_empty_updates(self, alert_rule_repository, mock_pool):
        """测试空更新."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()

        result = await alert_rule_repository.update(1, {})

        assert result is True
        mock_conn.execute.assert_not_called()

    async def test_update_filter_disallowed_fields(
        self, alert_rule_repository, mock_pool
    ):
        """测试过滤不允许的字段."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        updates = {
            "name": "新名称",
            "disallowed_field": "不应该被更新",
            "id": 999,  # 不应该被更新
        }
        result = await alert_rule_repository.update(1, updates)

        assert result is True
        # 验证SQL中不包含disallowed_field（SET子句中）
        call_args = mock_conn.execute.call_args[0][0]
        assert "disallowed_field" not in call_args
        # WHERE子句中的id是正常的，SET子句中不应该有id
        set_clause = call_args.split("SET")[1].split("WHERE")[0]
        assert "id" not in set_clause or "id = $" not in set_clause

    async def test_update_with_json_fields(self, alert_rule_repository, mock_pool):
        """测试更新JSON字段."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        updates = {
            "conditions": {"new_condition": True},
            "notification_channels": ["email"],
            "recipients": ["user@example.com"],
        }
        result = await alert_rule_repository.update(1, updates)

        assert result is True
        mock_conn.execute.assert_called_once()

    async def test_update_exception(self, alert_rule_repository, mock_pool):
        """测试更新告警规则时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("更新失败"))

        with pytest.raises(RepositoryError, match="更新告警规则失败"):
            await alert_rule_repository.update(1, {"name": "新名称"})

    async def test_delete_success(self, alert_rule_repository, mock_pool):
        """测试删除告警规则成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")

        result = await alert_rule_repository.delete(1)

        assert result is True
        mock_conn.execute.assert_called_once()
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_delete_not_found(self, alert_rule_repository, mock_pool):
        """测试删除不存在的告警规则."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 0")

        result = await alert_rule_repository.delete(999)

        assert result is False

    async def test_delete_exception(self, alert_rule_repository, mock_pool):
        """测试删除告警规则时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("删除失败"))

        with pytest.raises(RepositoryError, match="删除告警规则失败"):
            await alert_rule_repository.delete(1)

    async def test_row_to_alert_rule_with_json_string(
        self, alert_rule_repository, mock_pool
    ):
        """测试_row_to_alert_rule解析JSON字符串."""
        row = MockRecord({
            "id": 1,
            "name": "测试规则",
            "camera_id": "cam1",
            "rule_type": "violation",
            "conditions": json.dumps({"threshold": 5}),
            "notification_channels": json.dumps(["email", "sms"]),
            "recipients": json.dumps(["user@example.com"]),
            "enabled": True,
            "priority": "high",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "admin",
        })

        rule = alert_rule_repository._row_to_alert_rule(row)

        assert rule.conditions == {"threshold": 5}
        assert rule.notification_channels == ["email", "sms"]
        assert rule.recipients == ["user@example.com"]

    async def test_row_to_alert_rule_with_json_object(
        self, alert_rule_repository, mock_pool
    ):
        """测试_row_to_alert_rule解析JSON对象."""
        row = MockRecord({
            "id": 1,
            "name": "测试规则",
            "camera_id": "cam1",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
            "notification_channels": ["email", "sms"],
            "recipients": ["user@example.com"],
            "enabled": True,
            "priority": "high",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "admin",
        })

        rule = alert_rule_repository._row_to_alert_rule(row)

        assert rule.conditions == {"threshold": 5}
        assert rule.notification_channels == ["email", "sms"]
        assert rule.recipients == ["user@example.com"]

    async def test_row_to_alert_rule_with_invalid_json(
        self, alert_rule_repository, mock_pool
    ):
        """测试_row_to_alert_rule处理无效JSON."""
        row = MockRecord({
            "id": 1,
            "name": "测试规则",
            "camera_id": "cam1",
            "rule_type": "violation",
            "conditions": "invalid json{",
            "notification_channels": None,
            "recipients": None,
            "enabled": True,
            "priority": "high",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "created_by": "admin",
        })

        rule = alert_rule_repository._row_to_alert_rule(row)

        assert rule.conditions == {}
        assert rule.notification_channels is None
        assert rule.recipients is None
