"""监控和健康检查端点."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# 尝试导入CameraService相关模块（可选）
try:
    from src.domain.services.camera_service import CameraService
    from src.services.detection_service_domain import DefaultCameraRepository

    async def get_camera_service() -> Optional[CameraService]:
        """获取摄像头服务实例."""
        try:
            if DefaultCameraRepository is None:
                return None
            camera_repo = DefaultCameraRepository()
            # 尝试从配置中获取YAML路径
            import os

            cameras_yaml_path = os.getenv("CAMERAS_YAML_PATH", "config/cameras.yaml")
            return CameraService(camera_repo, cameras_yaml_path)
        except Exception:
            return None

except Exception:
    get_camera_service = None  # type: ignore

# 简单的内存指标存储（生产环境应使用Redis或专业metrics系统）
_metrics = {
    "requests_total": 0,
    "requests_by_status": {},
    "domain_service_usage": {"count": 0, "old_count": 0},
    "response_times": [],
    "errors": [],
}


async def check_camera_data_consistency() -> Dict[str, Any]:
    """检查CameraService数据一致性.

    Returns:
        包含一致性检查结果的字典
    """
    if get_camera_service is None:
        return {"consistent": True, "issues": [], "message": "CameraService未可用"}

    issues = []

    try:
        camera_service = await get_camera_service()
        if not camera_service:
            return {"consistent": True, "issues": [], "message": "CameraService未初始化"}

        # 从数据库获取所有摄像头
        db_cameras = await camera_service.camera_repository.find_all()
        db_camera_ids = {cam.id for cam in db_cameras}

        # 从YAML获取所有摄像头
        yaml_config = camera_service._read_yaml_config()
        yaml_cameras = yaml_config.get("cameras", [])
        yaml_camera_ids = {cam.get("id") for cam in yaml_cameras if cam.get("id")}

        # 检查不一致
        only_in_db = db_camera_ids - yaml_camera_ids
        only_in_yaml = yaml_camera_ids - db_camera_ids

        if only_in_db:
            issues.append(f"数据库中存在但YAML中不存在: {sorted(only_in_db)}")

        if only_in_yaml:
            issues.append(f"YAML中存在但数据库中不存在: {sorted(only_in_yaml)}")

        # 检查字段一致性（对于同时存在的摄像头）
        common_ids = db_camera_ids & yaml_camera_ids
        for camera_id in common_ids:
            db_camera = next((c for c in db_cameras if c.id == camera_id), None)
            yaml_camera = next(
                (c for c in yaml_cameras if c.get("id") == camera_id), None
            )

            if db_camera and yaml_camera:
                # 检查关键字段是否一致
                if db_camera.name != yaml_camera.get("name"):
                    issues.append(
                        f"摄像头 {camera_id} name不一致: DB={db_camera.name}, YAML={yaml_camera.get('name')}"
                    )

                if db_camera.metadata.get("source") != yaml_camera.get("source"):
                    issues.append(f"摄像头 {camera_id} source不一致")

        return {
            "consistent": len(issues) == 0,
            "issues": issues,
            "db_count": len(db_camera_ids),
            "yaml_count": len(yaml_camera_ids),
        }
    except Exception as e:
        logger.error(f"数据一致性检查失败: {e}")
        return {
            "consistent": False,
            "issues": [f"检查失败: {str(e)}"],
            "error": str(e),
        }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查端点.

    Returns:
        包含健康状态的字典
    """
    try:
        # 基础健康检查
        checks = {
            "database": "ok",
            "redis": "ok",
            "domain_services": "ok",
        }

        # 注意: camera_data_consistency检查已移除
        # 相机配置现在只存储在数据库中（单一数据源）

        # 检查数据库连接
        try:
            import os

            database_url = os.getenv("DATABASE_URL")
            if database_url:
                try:
                    import asyncpg

                    # 尝试连接数据库
                    conn = await asyncpg.connect(database_url, timeout=2)
                    await conn.close()
                    checks["database"] = "ok"
                except Exception as e:
                    checks["database"] = "error"
                    checks["database_error"] = str(e)
        except Exception as e:
            logger.warning(f"数据库连接检查失败: {e}")
            checks["database"] = "error"
            checks["database_error"] = str(e)

        # 检查Redis连接
        try:
            import os

            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    import redis.asyncio as redis

                    # 尝试连接Redis
                    redis_client = redis.from_url(redis_url)
                    await redis_client.ping()
                    await redis_client.close()
                    checks["redis"] = "ok"
                except Exception as e:
                    checks["redis"] = "error"
                    checks["redis_error"] = str(e)
        except Exception as e:
            logger.warning(f"Redis连接检查失败: {e}")
            checks["redis"] = "error"
            checks["redis_error"] = str(e)

        # 判断整体状态
        all_ok = all(
            v == "ok"
            for k, v in checks.items()
            if k not in ["database_error", "redis_error"]
        )

        health_status = {
            "status": "healthy" if all_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }

        return health_status
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不健康")


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """获取监控指标（Prometheus格式）.

    Returns:
        包含监控指标的字典
    """
    try:
        # 计算成功率
        total_requests = _metrics["requests_total"]
        success_requests = sum(
            count
            for status, count in _metrics["requests_by_status"].items()
            if status.startswith("2")
        )
        error_requests = sum(
            count
            for status, count in _metrics["requests_by_status"].items()
            if status.startswith("4") or status.startswith("5")
        )

        success_rate = (
            (success_requests / total_requests * 100) if total_requests > 0 else 100.0
        )
        error_rate = (
            (error_requests / total_requests * 100) if total_requests > 0 else 0.0
        )

        # 计算领域服务使用率
        domain_usage = _metrics["domain_service_usage"]
        domain_total = domain_usage["count"] + domain_usage["old_count"]
        domain_service_usage_rate = (
            (domain_usage["count"] / domain_total * 100) if domain_total > 0 else 0.0
        )

        # 计算响应时间统计
        response_times = _metrics["response_times"]
        if response_times:
            sorted_times = sorted(response_times)
            p50_idx = int(len(sorted_times) * 0.5)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)

            p50 = sorted_times[p50_idx] if p50_idx < len(sorted_times) else 0
            p95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
            p99 = sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0
            max_time = max(response_times)
            avg_time = sum(response_times) / len(response_times)
        else:
            p50 = p95 = p99 = max_time = avg_time = 0

        # 添加数据一致性指标
        consistency_check = await check_camera_data_consistency()

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "requests": {
                "total": total_requests,
                "success": success_requests,
                "error": error_requests,
                "success_rate": round(success_rate, 2),
                "error_rate": round(error_rate, 2),
                "by_status": _metrics["requests_by_status"],
            },
            "domain_service": {
                "usage_count": domain_usage["count"],
                "old_count": domain_usage["old_count"],
                "usage_rate": round(domain_service_usage_rate, 2),
            },
            "response_time": {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "max_ms": round(max_time, 2),
                "avg_ms": round(avg_time, 2),
            },
            "errors": {
                "total": len(_metrics["errors"]),
                "recent": _metrics["errors"][-10:] if _metrics["errors"] else [],
            },
            "data_consistency": {
                "consistent": consistency_check.get("consistent", True),
                "issues_count": len(consistency_check.get("issues", [])),
                "db_count": consistency_check.get("db_count", 0),
                "yaml_count": consistency_check.get("yaml_count", 0),
                "last_check": datetime.now().isoformat(),
            },
        }

        return metrics
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取指标失败")


def record_request(
    status_code: int, domain_service_used: bool = False, response_time_ms: float = 0.0
):
    """记录请求指标.

    Args:
        status_code: HTTP状态码
        domain_service_used: 是否使用领域服务
        response_time_ms: 响应时间（毫秒）
    """
    _metrics["requests_total"] += 1

    status_str = str(status_code)
    _metrics["requests_by_status"][status_str] = (
        _metrics["requests_by_status"].get(status_str, 0) + 1
    )

    if domain_service_used:
        _metrics["domain_service_usage"]["count"] += 1
    else:
        _metrics["domain_service_usage"]["old_count"] += 1

    if response_time_ms > 0:
        _metrics["response_times"].append(response_time_ms)
        # 只保留最近1000个响应时间记录
        if len(_metrics["response_times"]) > 1000:
            _metrics["response_times"] = _metrics["response_times"][-1000:]

    if status_code >= 400:
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code,
        }
        _metrics["errors"].append(error_entry)
        # 只保留最近100个错误记录
        if len(_metrics["errors"]) > 100:
            _metrics["errors"] = _metrics["errors"][-100:]
