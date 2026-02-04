"""Redis缓存装饰器单元测试."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.utils.cache import (
    clear_cache,
    generate_cache_key,
    get_cache_stats,
    redis_cache,
)


class TestCacheKeyGeneration:
    """测试缓存键生成."""

    def test_generate_key_no_params(self):
        """测试无参数的缓存键生成."""
        key = generate_cache_key("stats", "get_data", (), {})
        assert key == "stats:get_data:v1"

    def test_generate_key_with_args(self):
        """测试带位置参数的缓存键生成."""
        key1 = generate_cache_key("stats", "get_data", (1, 2), {})
        key2 = generate_cache_key("stats", "get_data", (1, 2), {})
        key3 = generate_cache_key("stats", "get_data", (2, 1), {})

        # 相同参数生成相同的键
        assert key1 == key2
        # 不同参数生成不同的键
        assert key1 != key3

    def test_generate_key_with_kwargs(self):
        """测试带关键字参数的缓存键生成."""
        key1 = generate_cache_key("stats", "get_data", (), {"a": 1, "b": 2})
        key2 = generate_cache_key("stats", "get_data", (), {"b": 2, "a": 1})  # 顺序不同

        # 顺序不同但内容相同，生成相同的键（JSON sort_keys）
        assert key1 == key2


class TestRedisCacheDecorator:
    """测试Redis缓存装饰器."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """测试缓存命中场景."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"result": "cached"})

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test")
            async def test_func():
                return {"result": "fresh"}

            result = await test_func()

            # 应该返回缓存数据
            assert result == {"result": "cached"}
            # Redis.get 应该被调用
            mock_redis.get.assert_called_once()
            # Redis.setex 不应该被调用（因为命中缓存）
            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """测试缓存未命中场景."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # 缓存未命中

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test")
            async def test_func():
                return {"result": "fresh"}

            result = await test_func()

            # 应该返回函数执行结果
            assert result == {"result": "fresh"}
            # Redis.get 应该被调用
            mock_redis.get.assert_called_once()
            # Redis.setex 应该被调用（写入缓存）
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_failure_with_fallback(self):
        """测试Redis失败时的降级（启用fallback）."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis连接失败")

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test", enable_fallback=True)
            async def test_func():
                return {"result": "fresh"}

            # 不应该抛出异常，应该降级到执行原函数
            result = await test_func()
            assert result == {"result": "fresh"}

    @pytest.mark.asyncio
    async def test_redis_failure_without_fallback(self):
        """测试Redis失败时不降级."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis连接失败")

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test", enable_fallback=False)
            async def test_func():
                return {"result": "fresh"}

            # 应该抛出异常
            with pytest.raises(Exception, match="Redis连接失败"):
                await test_func()

    @pytest.mark.asyncio
    async def test_cache_disabled_with_zero_ttl(self):
        """测试TTL=0时禁用缓存."""
        mock_redis = AsyncMock()

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=0, key_prefix="test")
            async def test_func():
                return {"result": "fresh"}

            result = await test_func()

            # 应该直接返回函数结果
            assert result == {"result": "fresh"}
            # Redis不应该被调用
            mock_redis.get.assert_not_called()
            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_corrupted_cache_data(self):
        """测试缓存数据损坏的处理."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid json data"  # 无效的JSON

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test")
            async def test_func():
                return {"result": "fresh"}

            result = await test_func()

            # 应该删除损坏的缓存并返回新结果
            assert result == {"result": "fresh"}
            # 应该调用delete删除损坏的缓存
            mock_redis.delete.assert_called_once()
            # 应该写入新的缓存
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_ttl_jitter(self):
        """测试TTL抖动（防止缓存雪崩）."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):

            @redis_cache(ttl=10, key_prefix="test")
            async def test_func():
                return {"result": "fresh"}

            await test_func()

            # 检查setex的第二个参数（TTL）
            call_args = mock_redis.setex.call_args
            actual_ttl = call_args[0][1]  # 第二个位置参数

            # TTL应该在 8-12 秒之间（10 ± 2）
            assert 8 <= actual_ttl <= 12


class TestCacheManagement:
    """测试缓存管理功能."""

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """测试清除缓存."""
        mock_redis = AsyncMock()

        # 模拟scan_iter返回3个键
        async def mock_scan_iter(match):
            for key in ["test:1", "test:2", "test:3"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete.return_value = 3

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):
            cleared_count = await clear_cache("test:*")

            assert cleared_count == 3
            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_cache_no_match(self):
        """测试清除不存在的缓存."""
        mock_redis = AsyncMock()

        # 模拟scan_iter返回空
        async def mock_scan_iter(match):
            return
            yield  # 生成器

        mock_redis.scan_iter = mock_scan_iter

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):
            cleared_count = await clear_cache("nonexistent:*")

            assert cleared_count == 0
            mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """测试获取缓存统计."""
        mock_redis = AsyncMock()

        # 模拟scan_iter返回5个键
        async def mock_scan_iter(match):
            for key in ["test:1", "test:2", "test:3", "test:4", "test:5"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.info.return_value = {
            "used_memory": 10485760,  # 10MB
            "used_memory_peak": 20971520,  # 20MB
        }

        with patch("src.utils.cache.get_redis_client", return_value=mock_redis):
            stats = await get_cache_stats("test:*")

            assert stats["total_keys"] == 5
            assert stats["pattern"] == "test:*"
            assert stats["memory_used_mb"] == 10.0
            assert stats["memory_peak_mb"] == 20.0
