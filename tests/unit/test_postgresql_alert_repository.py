"""PostgreSQL告警仓储单元测试."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

from src.domain.entities.alert import Alert
from src.infrastructure.repositories.postgresql_alert_repository import (
    PostgreSQLAlertRepository,
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
def alert_repository(mock_pool):
    """创建PostgreSQL告警仓储实例."""
    return PostgreSQLAlertRepository(mock_pool)


@pytest.fixture
def sample_alert():
    """创建示例告警."""
    return Alert(
        id=1,
        rule_id=10,
        camera_id="cam1",
        alert_type="violation",
        message="测试告警",
        timestamp=datetime.now(),
        details={"key": "value"},
        notification_sent=True,
        notification_channels_used=["email"],
    )


@pytest.fixture
def mock_row():
    """创建模拟的数据库行."""
    return MockRecord({
        "id": 1,
        "rule_id": 10,
        "camera_id": "cam1",
        "alert_type": "violation",
        "message": "测试告警",
        "details": json.dumps({"key": "value"}),
        "notification_sent": True,
        "notification_channels_used": json.dumps(["email"]),
        "timestamp": datetime.now(),
    })


@pytest.mark.asyncio
class TestPostgreSQLAlertRepository:
    """测试PostgreSQL告警仓储."""

    async def test_find_by_id_success(self, alert_repository, mock_pool, mock_row):
        """测试根据ID查找告警成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await alert_repository.find_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.camera_id == "cam1"
        assert result.alert_type == "violation"
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_by_id_not_found(self, alert_repository, mock_pool):
        """测试根据ID查找告警不存在."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result = await alert_repository.find_by_id(999)

        assert result is None
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_by_id_exception(self, alert_repository, mock_pool):
        """测试根据ID查找告警时发生异常."""
        mock_pool.acquire = AsyncMock(side_effect=Exception("数据库连接失败"))

        with pytest.raises(RepositoryError, match="查询告警失败"):
            await alert_repository.find_by_id(1)

    async def test_find_all_success(self, alert_repository, mock_pool, mock_row):
        """测试查询所有告警成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_repository.find_all(limit=10)

        assert len(result) == 1
        assert result[0].id == 1
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_find_all_with_camera_filter(
        self, alert_repository, mock_pool, mock_row
    ):
        """测试按camera_id过滤查询告警."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_repository.find_all(limit=10, camera_id="cam1")

        assert len(result) == 1
        mock_conn.fetch.assert_called_once()
        # 验证SQL参数包含camera_id
        call_args = mock_conn.fetch.call_args
        assert call_args[0][1] == "cam1"  # 第一个参数是SQL，第二个是camera_id

    async def test_find_all_with_type_filter(
        self, alert_repository, mock_pool, mock_row
    ):
        """测试按alert_type过滤查询告警."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        result = await alert_repository.find_all(limit=10, alert_type="violation")

        assert len(result) == 1
        mock_conn.fetch.assert_called_once()

    async def test_find_all_empty(self, alert_repository, mock_pool):
        """测试查询所有告警为空."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        result = await alert_repository.find_all(limit=10)

        assert len(result) == 0

    async def test_find_all_exception(self, alert_repository, mock_pool):
        """测试查询所有告警时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("查询失败"))

        with pytest.raises(RepositoryError, match="查询告警历史失败"):
            await alert_repository.find_all(limit=10)

    async def test_save_success(self, alert_repository, mock_pool, sample_alert):
        """测试保存告警成功."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        result = await alert_repository.save(sample_alert)

        assert result == 1
        mock_conn.fetchval.assert_called_once()
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once_with(mock_conn)

    async def test_save_without_details(self, alert_repository, mock_pool):
        """测试保存没有details的告警."""
        alert = Alert(
            id=0,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警",
            timestamp=datetime.now(),
        )
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        result = await alert_repository.save(alert)

        assert result == 1
        mock_conn.fetchval.assert_called_once()

    async def test_save_exception(self, alert_repository, mock_pool, sample_alert):
        """测试保存告警时发生异常."""
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("保存失败"))

        with pytest.raises(RepositoryError, match="保存告警失败"):
            await alert_repository.save(sample_alert)

    async def test_row_to_alert_with_json_string(self, alert_repository, mock_pool):
        """测试_row_to_alert解析JSON字符串."""
        row = MockRecord({
            "id": 1,
            "rule_id": 10,
            "camera_id": "cam1",
            "alert_type": "violation",
            "message": "测试告警",
            "details": json.dumps({"key": "value"}),
            "notification_sent": True,
            "notification_channels_used": json.dumps(["email"]),
            "timestamp": datetime.now(),
        })

        alert = alert_repository._row_to_alert(row)

        assert alert.details == {"key": "value"}
        assert alert.notification_channels_used == ["email"]

    async def test_row_to_alert_with_json_object(self, alert_repository, mock_pool):
        """测试_row_to_alert解析JSON对象."""
        row = MockRecord({
            "id": 1,
            "rule_id": 10,
            "camera_id": "cam1",
            "alert_type": "violation",
            "message": "测试告警",
            "details": {"key": "value"},
            "notification_sent": True,
            "notification_channels_used": ["email"],
            "timestamp": datetime.now(),
        })

        alert = alert_repository._row_to_alert(row)

        assert alert.details == {"key": "value"}
        assert alert.notification_channels_used == ["email"]

    async def test_row_to_alert_with_invalid_json(self, alert_repository, mock_pool):
        """测试_row_to_alert处理无效JSON."""
        row = MockRecord({
            "id": 1,
            "rule_id": 10,
            "camera_id": "cam1",
            "alert_type": "violation",
            "message": "测试告警",
            "details": "invalid json{",
            "notification_sent": True,
            "notification_channels_used": None,
            "timestamp": datetime.now(),
        })

        alert = alert_repository._row_to_alert(row)

        assert alert.details is None
        assert alert.notification_channels_used is None
