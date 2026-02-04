"""系统信息API路由."""

import logging
import os
import platform
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from src.api.utils.rollout import should_use_domain

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

logger = logging.getLogger(__name__)

# 尝试导入系统服务（可选）
try:
    from src.domain.services.system_service import get_system_service
except ImportError:
    get_system_service = None  # type: ignore

# 可选依赖
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

router = APIRouter()


def _project_root():
    """获取项目根目录."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def get_config_file_info(file_path: str) -> Dict[str, Any]:
    """获取配置文件信息."""
    try:
        if not os.path.exists(file_path):
            return {"exists": False, "path": file_path}

        stat = os.stat(file_path)
        return {
            "exists": True,
            "path": file_path,
            "size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "readable": os.access(file_path, os.R_OK),
            "writable": os.access(file_path, os.W_OK),
        }
    except Exception as e:
        return {"exists": False, "path": file_path, "error": str(e)}


def load_yaml_config(file_path: str) -> Optional[Dict[str, Any]]:
    """加载YAML配置文件."""
    if not HAS_YAML or not yaml:
        return None
    try:
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


@router.get("/system/info", summary="获取系统信息")
async def get_system_info(
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取系统基本信息.

    Args:
        force_domain: 测试用途，强制走领域分支

    Returns:
        包含系统信息的字典
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_system_service is not None:
            system_service = get_system_service()
            result = await system_service.get_system_info()
            return result
    except Exception as e:
        logger.warning(f"系统服务获取信息失败，回退到旧实现: {e}")

    # 旧实现（回退）
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
        if HAS_PSUTIL and psutil:
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
            "psutil_available": HAS_PSUTIL,
        }
    except Exception as e:
        raise raise_http_exception(
            status_code=500,
            message="获取系统信息失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.get("/system/config", summary="获取系统配置信息")
async def get_system_config() -> Dict[str, Any]:
    """获取系统配置文件信息."""
    try:
        project_root = _project_root()

        # 主要配置文件
        config_files = {
            "cameras": os.path.join(project_root, "config", "cameras.yaml"),
            "regions": os.path.join(project_root, "config", "regions.json"),
            "default": os.path.join(project_root, "config", "default.yaml"),
            "unified_params": os.path.join(
                project_root, "config", "unified_params.yaml"
            ),
            "enhanced_detection": os.path.join(
                project_root, "config", "enhanced_detection_config.yaml"
            ),
        }

        config_info = {}
        for name, path in config_files.items():
            config_info[name] = get_config_file_info(path)

        # 尝试加载部分配置内容
        default_config = load_yaml_config(config_files["default"])
        unified_config = load_yaml_config(config_files["unified_params"])

        # 环境变量
        env_vars = {
            "HBD_REGIONS_FILE": os.environ.get("HBD_REGIONS_FILE"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "PATH": os.environ.get("PATH", "")[:200] + "..."
            if len(os.environ.get("PATH", "")) > 200
            else os.environ.get("PATH"),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": project_root,
            "config_files": config_info,
            "default_config": default_config,
            "unified_config": unified_config,
            "environment": env_vars,
            "python_executable": os.sys.executable,
            "working_directory": os.getcwd(),
        }
    except Exception as e:
        raise raise_http_exception(
            status_code=500,
            message="获取配置信息失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.get("/system/health", summary="获取系统健康状态")
async def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态."""
    try:
        project_root = _project_root()

        # 检查关键目录
        critical_dirs = ["config", "src", "models", "data", "frontend"]

        dir_status = {}
        for dir_name in critical_dirs:
            dir_path = os.path.join(project_root, dir_name)
            dir_status[dir_name] = {
                "exists": os.path.exists(dir_path),
                "is_directory": os.path.isdir(dir_path),
                "readable": os.access(dir_path, os.R_OK)
                if os.path.exists(dir_path)
                else False,
                "writable": os.access(dir_path, os.W_OK)
                if os.path.exists(dir_path)
                else False,
            }

        # 检查关键文件
        critical_files = ["requirements.txt", "main.py", "config/default.yaml"]

        file_status = {}
        for file_name in critical_files:
            file_path = os.path.join(project_root, file_name)
            file_status[file_name] = {
                "exists": os.path.exists(file_path),
                "readable": os.access(file_path, os.R_OK)
                if os.path.exists(file_path)
                else False,
            }

        # 系统资源检查
        health_status = "healthy"
        issues = []

        if HAS_PSUTIL and psutil:
            try:
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(project_root)

                # 检查内存使用率
                if memory.percent > 90:
                    health_status = "warning"
                    issues.append("内存使用率过高")

                # 检查磁盘使用率
                if (disk.used / disk.total) > 0.9:
                    health_status = "warning"
                    issues.append("磁盘空间不足")
            except Exception as e:
                issues.append(f"资源检查失败: {str(e)}")
        else:
            issues.append("未安装psutil库，无法进行详细的资源检查")

        # 检查关键文件
        if not file_status.get("main.py", {}).get("exists"):
            health_status = "error"
            issues.append("主程序文件丢失")

        # 构建资源信息
        resources_info = {}
        if HAS_PSUTIL and psutil:
            try:
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(project_root)
                resources_info = {
                    "memory_usage": memory.percent,
                    "disk_usage": (disk.used / disk.total) * 100,
                    "cpu_usage": psutil.cpu_percent(interval=0.1),
                }
            except Exception:
                resources_info = {
                    "memory_usage": 0,
                    "disk_usage": 0,
                    "cpu_usage": 0,
                    "note": "资源信息获取失败",
                }
        else:
            resources_info = {
                "memory_usage": 0,
                "disk_usage": 0,
                "cpu_usage": 0,
                "note": "需要安装psutil库获取资源信息",
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "status": health_status,
            "issues": issues,
            "directories": dir_status,
            "files": file_status,
            "resources": resources_info,
            "psutil_available": HAS_PSUTIL,
        }
    except Exception as e:
        raise raise_http_exception(
            status_code=500,
            message="健康检查失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )
