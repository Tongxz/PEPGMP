"""系统信息服务 - 提供系统信息收集功能."""

import logging
import os
import platform
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 可选依赖
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None


class SystemService:
    """系统信息服务 - 提供系统信息收集功能."""

    def __init__(self):
        """初始化系统服务."""
        self.has_psutil = HAS_PSUTIL

    async def get_system_info(self) -> Dict[str, Any]:
        """获取系统基本信息.

        Returns:
            包含系统信息的字典，包括平台、内存、CPU、磁盘等信息
        """
        try:
            # 系统基本信息
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "version": platform.version(),
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
            }

            # 如果psutil可用，获取详细的系统信息
            if self.has_psutil and psutil:
                # 内存信息
                memory = psutil.virtual_memory()
                memory_info = {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percentage": memory.percent,
                }

                # CPU信息
                cpu_info = {
                    "count": psutil.cpu_count(),
                    "physical_count": psutil.cpu_count(logical=False),
                    "current_frequency": psutil.cpu_freq().current
                    if psutil.cpu_freq()
                    else None,
                    "usage_percent": psutil.cpu_percent(interval=1),
                }

                # 磁盘信息
                disk = psutil.disk_usage("/")
                disk_info = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percentage": (disk.used / disk.total) * 100,
                }
            else:
                # 备用信息（无psutil时）
                memory_info = {
                    "total": 0,
                    "available": 0,
                    "used": 0,
                    "percentage": 0,
                    "note": "需要安装psutil库获取详细内存信息",
                }

                cpu_info = {
                    "count": os.cpu_count() or 1,
                    "physical_count": None,
                    "current_frequency": None,
                    "usage_percent": 0,
                    "note": "需要安装psutil库获取详细CPU信息",
                }

                disk_info = {
                    "total": 0,
                    "used": 0,
                    "free": 0,
                    "percentage": 0,
                    "note": "需要安装psutil库获取详细磁盘信息",
                }

            return {
                "timestamp": datetime.now().isoformat(),
                "system": system_info,
                "memory": memory_info,
                "cpu": cpu_info,
                "disk": disk_info,
                "psutil_available": self.has_psutil,
            }

        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            raise


# 单例实例
_system_service_instance: Optional[SystemService] = None


def get_system_service() -> SystemService:
    """获取系统服务单例.

    Returns:
        SystemService实例
    """
    global _system_service_instance
    if _system_service_instance is None:
        _system_service_instance = SystemService()
    return _system_service_instance

