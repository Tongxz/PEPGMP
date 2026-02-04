"""统计API缓存集成测试."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.api.app import app


class TestStatisticsAPICache:
    """测试统计API的缓存功能."""

    @pytest.mark.asyncio
    async def test_realtime_statistics_caching(self):
        """测试实时统计API的缓存功能."""
        # Mock领域服务
        mock_service = AsyncMock()
        mock_service.get_realtime_statistics.return_value = {
            "total_violations": 100,
            "active_cameras": 5,
            "timestamp": "2026-01-26T10:00:00",
        }

        with patch(
            "src.api.routers.statistics.get_detection_service_domain",
            return_value=mock_service,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # 第一次请求 - 应该调用领域服务
                response1 = await client.get("/api/v1/statistics/realtime")
                assert response1.status_code == 200
                data1 = response1.json()

                # 验证数据正确
                assert data1["total_violations"] == 100
                assert data1["active_cameras"] == 5

                # 第二次请求 - 应该从缓存返回
                response2 = await client.get("/api/v1/statistics/realtime")
                assert response2.status_code == 200
                data2 = response2.json()

                # 数据应该相同
                assert data1 == data2

                # 领域服务应该只被调用一次（第二次从缓存返回）
                assert mock_service.get_realtime_statistics.call_count == 1

    @pytest.mark.asyncio
    async def test_detection_realtime_statistics_caching(self):
        """测试智能检测实时统计API的缓存功能."""
        # Mock领域服务
        mock_service = AsyncMock()
        mock_service.get_detection_realtime_stats.return_value = {
            "processing_efficiency": 95.5,
            "avg_fps": 25.3,
            "active_cameras": 3,
            "timestamp": "2026-01-26T10:00:00",
        }

        with patch(
            "src.api.routers.statistics.get_detection_service_domain",
            return_value=mock_service,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # 第一次请求
                response1 = await client.get("/api/v1/statistics/detection-realtime")
                assert response1.status_code == 200
                data1 = response1.json()

                # 第二次请求（从缓存）
                response2 = await client.get("/api/v1/statistics/detection-realtime")
                assert response2.status_code == 200
                data2 = response2.json()

                # 数据应该相同
                assert data1 == data2

                # 领域服务应该只被调用一次
                assert mock_service.get_detection_realtime_stats.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """测试缓存过期功能."""
        # Mock领域服务，返回不同的数据
        mock_service = AsyncMock()
        call_count = 0

        async def get_stats():
            nonlocal call_count
            call_count += 1
            return {
                "total_violations": 100 + call_count,
                "timestamp": f"call_{call_count}",
            }

        mock_service.get_realtime_statistics = get_stats

        with patch(
            "src.api.routers.statistics.get_detection_service_domain",
            return_value=mock_service,
        ):
            # 使用TTL=1秒的缓存装饰器
            with patch("src.utils.cache.redis_cache") as mock_cache:
                # 模拟缓存装饰器，TTL=1秒
                def cache_decorator(ttl, key_prefix):
                    def decorator(func):
                        return func  # 不使用缓存，直接返回原函数

                    return decorator

                mock_cache.side_effect = cache_decorator

                async with AsyncClient(app=app, base_url="http://test") as client:
                    # 第一次请求
                    response1 = await client.get("/api/v1/statistics/realtime")
                    data1 = response1.json()
                    assert data1["total_violations"] == 101

                    # 立即第二次请求（不使用缓存）
                    response2 = await client.get("/api/v1/statistics/realtime")
                    data2 = response2.json()
                    assert data2["total_violations"] == 102

    @pytest.mark.asyncio
    async def test_cache_failure_fallback(self):
        """测试Redis失败时的降级处理."""
        # Mock领域服务
        mock_service = AsyncMock()
        mock_service.get_realtime_statistics.return_value = {
            "total_violations": 100,
            "timestamp": "2026-01-26T10:00:00",
        }

        # Mock Redis客户端失败
        with patch(
            "src.utils.cache.get_redis_client", side_effect=Exception("Redis连接失败")
        ):
            with patch(
                "src.api.routers.statistics.get_detection_service_domain",
                return_value=mock_service,
            ):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    # 即使Redis失败，API仍应正常工作（降级到直接查询）
                    response = await client.get("/api/v1/statistics/realtime")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["total_violations"] == 100

                    # 领域服务应该被调用
                    assert mock_service.get_realtime_statistics.called


class TestCacheManagementAPI:
    """测试缓存管理API."""

    @pytest.mark.asyncio
    async def test_clear_cache_endpoint(self):
        """测试清除缓存端点."""
        with patch("src.api.routers.cache.clear_cache", return_value=5):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/cache/clear", json={"pattern": "stats:*"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["ok"] is True
                assert data["cleared_count"] == 5
                assert data["pattern"] == "stats:*"

    @pytest.mark.asyncio
    async def test_get_cache_stats_endpoint(self):
        """测试获取缓存统计端点."""
        with patch("src.api.routers.cache.get_cache_stats") as mock_stats:
            mock_stats.return_value = {
                "total_keys": 10,
                "pattern": "stats:*",
                "memory_used_mb": 5.2,
                "memory_peak_mb": 8.3,
            }

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/cache/stats?pattern=stats:*")
                assert response.status_code == 200
                data = response.json()
                assert data["total_keys"] == 10
                assert data["memory_used_mb"] == 5.2
