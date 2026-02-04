"""PostgreSQLDetectionRepository单元测试"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.repositories.postgresql_detection_repository import (
    PostgreSQLDetectionRepository,
)
from tests.unit.helpers import AsyncMockContext


@pytest.fixture
def detection_repository():
    """创建检测记录仓储实例"""
    # 创建mock pool
    pool = MagicMock()
    conn = AsyncMock()

    # Mock connection methods
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)

    # Mock pool methods
    pool.acquire = MagicMock(return_value=AsyncMockContext(conn))
    pool.release = AsyncMock()
    pool._test_connection = conn

    # 创建仓储实例（使用connection_string）
    repo = PostgreSQLDetectionRepository(
        connection_string="postgresql://test:test@localhost:5432/test"
    )
    # 直接设置_pool避免异步初始化
    repo._pool = pool

    return repo


class TestFindByCameraId:
    """测试find_by_camera_id方法"""

    @pytest.mark.asyncio
    async def test_find_by_camera_id_success(self, detection_repository):
        """测试成功按camera_id查询"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection

        mock_records = [
            {
                "id": 1,
                "camera_id": "camera_001",
                "frame_id": "100",  # 注意：数据库中是VARCHAR
                "timestamp": datetime.now(timezone.utc),
                "detected_objects": 2,
                "has_violation": False,
                "confidence": 0.9,
                "processing_time": 0.1,
                "image_url": None,
                "objects": [],
                "violations": [],
            }
        ]
        conn.fetch = AsyncMock(return_value=mock_records)

        # Act
        results = await detection_repository.find_by_camera_id(
            camera_id="camera_001", limit=100, offset=0
        )

        # Assert
        assert isinstance(results, list)
        conn.fetch.assert_called_once()

        # 验证SQL包含camera_id条件
        call_args = conn.fetch.call_args
        if call_args:
            sql = call_args[0][0]
            assert "camera_id" in sql.lower()

    @pytest.mark.asyncio
    async def test_find_by_camera_id_with_pagination(self, detection_repository):
        """测试带分页的查询"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetch = AsyncMock(return_value=[])

        # Act
        results = await detection_repository.find_by_camera_id(
            camera_id="camera_001", limit=20, offset=40
        )

        # Assert
        assert results == []
        conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_camera_id_empty_result(self, detection_repository):
        """测试空结果"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetch = AsyncMock(return_value=[])

        # Act
        results = await detection_repository.find_by_camera_id(camera_id="nonexistent")

        # Assert
        assert results == []


class TestCountByCameraId:
    """测试count_by_camera_id方法"""

    @pytest.mark.asyncio
    async def test_count_by_camera_id_success(self, detection_repository):
        """测试成功统计"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetchval = AsyncMock(return_value=42)

        # Act
        count = await detection_repository.count_by_camera_id(camera_id="camera_001")

        # Assert
        assert count == 42
        conn.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_camera_id_zero(self, detection_repository):
        """测试零记录"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetchval = AsyncMock(return_value=0)

        # Act
        count = await detection_repository.count_by_camera_id(camera_id="camera_999")

        # Assert
        assert count == 0


class TestRepositoryBasic:
    """测试基本仓储功能"""

    @pytest.mark.asyncio
    async def test_repository_initialization_default(self):
        """测试默认初始化"""
        repo = PostgreSQLDetectionRepository()

        assert repo.connection_string is not None

    @pytest.mark.asyncio
    async def test_repository_initialization_with_connection_string(self):
        """测试使用connection_string初始化"""
        conn_string = "postgresql://test:test@localhost:5432/test"
        repo = PostgreSQLDetectionRepository(connection_string=conn_string)

        assert repo.connection_string == conn_string


class TestSaveBasic:
    """测试save方法（基本功能）"""

    @pytest.mark.asyncio
    async def test_save_method_exists(self, detection_repository):
        """测试save方法存在且可调用"""
        # Note: save方法需要完整的DomainDetectionRecord对象
        # 由于对象构造复杂，这里只验证仓储对象有save方法
        assert hasattr(detection_repository, "save")
        assert callable(detection_repository.save)


class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_find_by_camera_id_database_error(self, detection_repository):
        """测试数据库错误场景（仓储会捕获异常并返回空列表）"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetch = AsyncMock(side_effect=Exception("Database connection failed"))

        # Act
        result = await detection_repository.find_by_camera_id(camera_id="camera_001")

        # Assert - 仓储捕获异常并返回空列表
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_camera_id_database_error(self, detection_repository):
        """测试统计时的数据库错误"""
        # Arrange
        pool = detection_repository._pool
        conn = pool._test_connection
        conn.fetchval = AsyncMock(side_effect=Exception("Query execution failed"))

        # Act & Assert
        with pytest.raises(Exception, match="Query execution failed"):
            await detection_repository.count_by_camera_id(camera_id="camera_001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
