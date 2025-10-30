"""
仓储模式单元测试
测试各种仓储实现
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.repositories.hybrid_detection_repository import (
    HybridDetectionRepository,
)
from src.infrastructure.repositories.postgresql_detection_repository import (
    PostgreSQLDetectionRepository,
)
from src.infrastructure.repositories.redis_detection_repository import (
    RedisDetectionRepository,
)
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
)


class TestPostgreSQLDetectionRepository:
    """测试PostgreSQL仓储"""

    @pytest.fixture
    def repository(self):
        """创建PostgreSQL仓储实例"""
        return PostgreSQLDetectionRepository(
            "postgresql://test:test@localhost:5432/test"
        )

    @pytest.fixture
    def sample_record(self):
        """创建示例记录"""
        return DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[
                {
                    "class_id": 0,
                    "class_name": "person",
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 200],
                }
            ],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_save_record(self, repository, sample_record):
        """测试保存记录"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            result = await repository.save(sample_record)

            assert result == "test_001"
            # 检查execute被调用了（包括创建表和插入数据）
            assert mock_conn.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository):
        """测试根据ID查找记录"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            # 模拟数据库返回
            mock_row = Mock()
            mock_row.__getitem__ = Mock(
                side_effect=lambda key: {
                    "id": "test_001",
                    "camera_id": "cam1",
                    "objects": json.dumps([{"class_name": "person"}]),
                    "timestamp": datetime.now(),
                    "confidence": 0.95,
                    "processing_time": 0.15,
                    "frame_id": 1,
                    "region_id": "region1",
                    "metadata": json.dumps({"test": "data"}),
                }[key]
            )

            mock_conn.fetchrow.return_value = mock_row

            record = await repository.find_by_id("test_001")

            assert record is not None
            assert record.id == "test_001"
            assert record.camera_id == "cam1"

    @pytest.mark.asyncio
    async def test_find_by_camera_id(self, repository):
        """测试根据摄像头ID查找记录"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            # 模拟数据库返回
            mock_rows = [Mock() for _ in range(2)]
            for i, row in enumerate(mock_rows):
                row.__getitem__ = Mock(
                    side_effect=lambda key, idx=i: {
                        "id": f"test_{idx:03d}",
                        "camera_id": "cam1",
                        "objects": json.dumps([{"class_name": "person"}]),
                        "timestamp": datetime.now(),
                        "confidence": 0.95,
                        "processing_time": 0.15,
                        "frame_id": idx + 1,
                        "region_id": "region1",
                        "metadata": json.dumps({"test": "data"}),
                    }[key]
                )

            mock_conn.fetch.return_value = mock_rows

            records = await repository.find_by_camera_id("cam1", limit=10)

            assert len(records) == 2
            assert all(record.camera_id == "cam1" for record in records)

    @pytest.mark.asyncio
    async def test_count_by_camera_id(self, repository):
        """测试统计摄像头记录数量"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            mock_conn.fetchval.return_value = 5

            count = await repository.count_by_camera_id("cam1")

            assert count == 5

    @pytest.mark.asyncio
    async def test_delete_by_id(self, repository):
        """测试根据ID删除记录"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            mock_conn.execute.return_value = "DELETE 1"

            result = await repository.delete_by_id("test_001")

            assert result is True
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_statistics(self, repository):
        """测试获取统计信息"""
        with patch.object(repository, "_get_connection") as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value = mock_conn

            mock_result = Mock()
            mock_result.__getitem__ = Mock(
                side_effect=lambda key: {
                    "total_records": 10,
                    "avg_confidence": 0.85,
                    "avg_processing_time": 0.12,
                    "earliest_record": datetime.now() - timedelta(hours=1),
                    "latest_record": datetime.now(),
                }[key]
            )

            mock_conn.fetchrow.return_value = mock_result

            stats = await repository.get_statistics("cam1")

            assert stats["total_records"] == 10
            assert stats["avg_confidence"] == 0.85


class TestRedisDetectionRepository:
    """测试Redis仓储"""

    @pytest.fixture
    def repository(self):
        """创建Redis仓储实例"""
        return RedisDetectionRepository("redis://localhost:6379/0")

    @pytest.fixture
    def sample_record(self):
        """创建示例记录"""
        return DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[
                {
                    "class_id": 0,
                    "class_name": "person",
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 200],
                }
            ],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_save_record(self, repository, sample_record):
        """测试保存记录"""
        with patch.object(repository, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await repository.save(sample_record)

            assert result == "test_001"
            # 验证调用了setex和zadd
            assert mock_redis.setex.call_count >= 1
            assert mock_redis.zadd.call_count >= 1

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository):
        """测试根据ID查找记录"""
        with patch.object(repository, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # 模拟Redis返回
            mock_redis.get.return_value = json.dumps(
                {
                    "id": "test_001",
                    "camera_id": "cam1",
                    "objects": [{"class_name": "person"}],
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 0.95,
                    "processing_time": 0.15,
                    "frame_id": 1,
                    "region_id": "region1",
                    "metadata": {"test": "data"},
                }
            )

            record = await repository.find_by_id("test_001")

            assert record is not None
            assert record.id == "test_001"
            assert record.camera_id == "cam1"

    @pytest.mark.asyncio
    async def test_find_by_camera_id(self, repository):
        """测试根据摄像头ID查找记录"""
        with patch.object(repository, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            # 模拟Redis返回
            mock_redis.zrevrange.return_value = ["test_001", "test_002"]
            mock_redis.get.side_effect = [
                json.dumps(
                    {
                        "id": "test_001",
                        "camera_id": "cam1",
                        "objects": [{"class_name": "person"}],
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.95,
                        "processing_time": 0.15,
                        "frame_id": 1,
                        "region_id": "region1",
                        "metadata": {"test": "data"},
                    }
                ),
                json.dumps(
                    {
                        "id": "test_002",
                        "camera_id": "cam1",
                        "objects": [{"class_name": "person"}],
                        "timestamp": datetime.now().isoformat(),
                        "confidence": 0.90,
                        "processing_time": 0.12,
                        "frame_id": 2,
                        "region_id": "region1",
                        "metadata": {"test": "data"},
                    }
                ),
            ]

            records = await repository.find_by_camera_id("cam1", limit=10)

            assert len(records) == 2
            assert all(record.camera_id == "cam1" for record in records)

    @pytest.mark.asyncio
    async def test_count_by_camera_id(self, repository):
        """测试统计摄像头记录数量"""
        with patch.object(repository, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            mock_redis.zcard.return_value = 5

            count = await repository.count_by_camera_id("cam1")

            assert count == 5


class TestHybridDetectionRepository:
    """测试混合仓储"""

    @pytest.fixture
    def primary_repo(self):
        """创建主存储仓储"""
        return Mock(spec=IDetectionRepository)

    @pytest.fixture
    def cache_repo(self):
        """创建缓存仓储"""
        return Mock(spec=IDetectionRepository)

    @pytest.fixture
    def hybrid_repo(self, primary_repo, cache_repo):
        """创建混合仓储"""
        return HybridDetectionRepository(primary_repo, cache_repo)

    @pytest.fixture
    def sample_record(self):
        """创建示例记录"""
        return DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[{"class_name": "person"}],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

    @pytest.mark.asyncio
    async def test_save_record(self, hybrid_repo, sample_record):
        """测试保存记录"""
        hybrid_repo.primary.save = AsyncMock(return_value="test_001")
        hybrid_repo.cache.save = AsyncMock(return_value="test_001")

        result = await hybrid_repo.save(sample_record)

        assert result == "test_001"
        hybrid_repo.primary.save.assert_called_once_with(sample_record)
        hybrid_repo.cache.save.assert_called_once_with(sample_record)

    @pytest.mark.asyncio
    async def test_find_by_id_cache_hit(self, hybrid_repo):
        """测试根据ID查找记录（缓存命中）"""
        sample_record = DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[{"class_name": "person"}],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

        hybrid_repo.cache.find_by_id = AsyncMock(return_value=sample_record)
        hybrid_repo.primary.find_by_id = AsyncMock()

        result = await hybrid_repo.find_by_id("test_001")

        assert result == sample_record
        hybrid_repo.cache.find_by_id.assert_called_once_with("test_001")
        hybrid_repo.primary.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_by_id_cache_miss(self, hybrid_repo):
        """测试根据ID查找记录（缓存未命中）"""
        sample_record = DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[{"class_name": "person"}],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

        hybrid_repo.cache.find_by_id = AsyncMock(return_value=None)
        hybrid_repo.primary.find_by_id = AsyncMock(return_value=sample_record)
        hybrid_repo.cache.save = AsyncMock()

        result = await hybrid_repo.find_by_id("test_001")

        assert result == sample_record
        hybrid_repo.cache.find_by_id.assert_called_once_with("test_001")
        hybrid_repo.primary.find_by_id.assert_called_once_with("test_001")
        hybrid_repo.cache.save.assert_called_once_with(sample_record)

    @pytest.mark.asyncio
    async def test_find_by_camera_id(self, hybrid_repo):
        """测试根据摄像头ID查找记录"""
        sample_records = [
            DetectionRecord(
                id=f"test_{i:03d}",
                camera_id="cam1",
                objects=[{"class_name": "person"}],
                timestamp=datetime.now(),
                confidence=0.95,
                processing_time=0.15,
                frame_id=i,
                region_id="region1",
                metadata={"test": "data"},
            )
            for i in range(1, 4)
        ]

        hybrid_repo.primary.find_by_camera_id = AsyncMock(return_value=sample_records)
        hybrid_repo.cache.save = AsyncMock()

        result = await hybrid_repo.find_by_camera_id("cam1", limit=10)

        assert len(result) == 3
        assert all(record.camera_id == "cam1" for record in result)
        hybrid_repo.primary.find_by_camera_id.assert_called_once_with("cam1", 10, 0)
        assert hybrid_repo.cache.save.call_count == 3


class TestRepositoryFactory:
    """测试仓储工厂"""

    def test_create_postgresql_repository(self):
        """测试创建PostgreSQL仓储"""
        with patch("asyncpg.connect"):
            repository = RepositoryFactory.create_repository(
                "postgresql",
                connection_string="postgresql://test:test@localhost:5432/test",
            )

            assert isinstance(repository, PostgreSQLDetectionRepository)

    def test_create_redis_repository(self):
        """测试创建Redis仓储"""
        with patch("redis.asyncio.from_url"):
            repository = RepositoryFactory.create_repository(
                "redis", connection_string="redis://localhost:6379/0"
            )

            assert isinstance(repository, RedisDetectionRepository)

    def test_create_unsupported_repository(self):
        """测试创建不支持的仓储"""
        with pytest.raises(ValueError, match="不支持的仓储类型"):
            RepositoryFactory.create_repository("unsupported")

    def test_get_available_repositories(self):
        """测试获取可用仓储列表"""
        available = RepositoryFactory.get_available_repositories()

        assert isinstance(available, list)
        # 具体内容取决于环境依赖

    def test_get_repository_info(self):
        """测试获取仓储信息"""
        info = RepositoryFactory.get_repository_info("postgresql")

        assert info["type"] == "postgresql"
        assert info["class"] == "PostgreSQLDetectionRepository"
        assert "PostgreSQL" in info["description"]

    def test_register_repository(self):
        """测试注册新仓储"""

        class MockRepository:
            pass

        # 这应该失败，因为MockRepository没有实现IDetectionRepository接口
        with pytest.raises(ValueError):
            RepositoryFactory.register_repository("mock", MockRepository)

    def test_create_repository_from_config(self):
        """测试从配置创建仓储"""
        config = {
            "type": "postgresql",
            "connection_string": "postgresql://test:test@localhost:5432/test",
        }

        with patch("asyncpg.connect"):
            repository = RepositoryFactory.create_repository_from_config(config)
            assert isinstance(repository, PostgreSQLDetectionRepository)

    def test_validate_repository_config(self):
        """测试验证仓储配置"""
        config = {"connection_string": "postgresql://test:test@localhost:5432/test"}

        with patch("asyncpg.connect"):
            result = RepositoryFactory.validate_repository_config("postgresql", config)
            assert result is True


class TestDetectionRecord:
    """测试DetectionRecord数据模型"""

    def test_detection_record_creation(self):
        """测试DetectionRecord创建"""
        record = DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[{"class_name": "person", "confidence": 0.95}],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

        assert record.id == "test_001"
        assert record.camera_id == "cam1"
        assert len(record.objects) == 1
        assert record.confidence == 0.95
        assert record.processing_time == 0.15
        assert record.frame_id == 1
        assert record.region_id == "region1"
        assert record.metadata == {"test": "data"}

    def test_detection_record_to_dict(self):
        """测试DetectionRecord转换为字典"""
        timestamp = datetime.now()
        record = DetectionRecord(
            id="test_001",
            camera_id="cam1",
            objects=[{"class_name": "person", "confidence": 0.95}],
            timestamp=timestamp,
            confidence=0.95,
            processing_time=0.15,
            frame_id=1,
            region_id="region1",
            metadata={"test": "data"},
        )

        data = record.to_dict()

        assert data["id"] == "test_001"
        assert data["camera_id"] == "cam1"
        assert data["objects"] == [{"class_name": "person", "confidence": 0.95}]
        assert data["timestamp"] == timestamp.isoformat()
        assert data["confidence"] == 0.95
        assert data["processing_time"] == 0.15
        assert data["frame_id"] == 1
        assert data["region_id"] == "region1"
        assert data["metadata"] == {"test": "data"}

    def test_detection_record_from_dict(self):
        """测试从字典创建DetectionRecord"""
        timestamp = datetime.now()
        data = {
            "id": "test_001",
            "camera_id": "cam1",
            "objects": [{"class_name": "person", "confidence": 0.95}],
            "timestamp": timestamp.isoformat(),
            "confidence": 0.95,
            "processing_time": 0.15,
            "frame_id": 1,
            "region_id": "region1",
            "metadata": {"test": "data"},
        }

        record = DetectionRecord.from_dict(data)

        assert record.id == "test_001"
        assert record.camera_id == "cam1"
        assert len(record.objects) == 1
        assert record.confidence == 0.95
        assert record.processing_time == 0.15
        assert record.frame_id == 1
        assert record.region_id == "region1"
        assert record.metadata == {"test": "data"}


if __name__ == "__main__":
    pytest.main([__file__])
