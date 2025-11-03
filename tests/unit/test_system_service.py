"""SystemService单元测试."""

from unittest.mock import MagicMock, patch

import pytest

from src.domain.services.system_service import SystemService


@pytest.fixture
def system_service():
    """创建SystemService实例."""
    return SystemService()


@pytest.mark.asyncio
class TestSystemService:
    """测试SystemService."""

    async def test_get_system_info_with_psutil(self, system_service):
        """测试有psutil时获取系统信息."""
        with patch.object(system_service, "has_psutil", True):
            with patch("psutil.virtual_memory") as mock_mem:
                with patch("psutil.cpu_count") as mock_cpu_count:
                    with patch("psutil.cpu_freq") as mock_cpu_freq:
                        with patch("psutil.cpu_percent") as mock_cpu_percent:
                            with patch("psutil.disk_usage") as mock_disk:
                                # 设置mock返回值
                                mock_mem.return_value.total = 8589934592  # 8GB
                                mock_mem.return_value.available = 4294967296  # 4GB
                                mock_mem.return_value.used = 4294967296  # 4GB
                                mock_mem.return_value.percent = 50.0

                                def cpu_count_side_effect(logical=True):
                                    return 8 if logical else 4

                                mock_cpu_count.side_effect = cpu_count_side_effect

                                mock_cpu_freq_result = MagicMock()
                                mock_cpu_freq_result.current = 2400.0
                                mock_cpu_freq.return_value = mock_cpu_freq_result

                                mock_cpu_percent.return_value = 25.5

                                mock_disk.return_value.total = 107374182400  # 100GB
                                mock_disk.return_value.used = 53687091200  # 50GB
                                mock_disk.return_value.free = 53687091200  # 50GB
                                mock_disk.return_value.percent = 50.0

                                result = await system_service.get_system_info()

                                assert "timestamp" in result
                                assert "system" in result
                                assert "memory" in result
                                assert "cpu" in result
                                assert "disk" in result
                                assert result["psutil_available"] is True
                                assert result["memory"]["total"] == 8589934592
                                assert result["cpu"]["count"] == 8

    async def test_get_system_info_without_psutil(self, system_service):
        """测试无psutil时获取系统信息."""
        with patch.object(system_service, "has_psutil", False):
            with patch("os.cpu_count", return_value=4):
                result = await system_service.get_system_info()

                assert "timestamp" in result
                assert "system" in result
                assert "memory" in result
                assert "cpu" in result
                assert "disk" in result
                assert result["psutil_available"] is False
                assert result["memory"]["note"] == "需要安装psutil库获取详细内存信息"
                assert result["cpu"]["count"] == 4
                assert result["cpu"]["note"] == "需要安装psutil库获取详细CPU信息"

    async def test_get_system_info_exception_handling(self, system_service):
        """测试异常处理."""
        with patch("platform.platform", side_effect=Exception("Platform error")):
            with pytest.raises(Exception):
                await system_service.get_system_info()

    @pytest.mark.asyncio
    async def test_get_system_service_singleton(self):
        """测试SystemService单例模式."""
        # 重置单例
        import src.domain.services.system_service
        from src.domain.services.system_service import get_system_service

        src.domain.services.system_service._system_service_instance = None

        # 第一次获取
        service1 = get_system_service()
        assert service1 is not None

        # 第二次获取应该是同一个实例
        service2 = get_system_service()
        assert service2 is service1
