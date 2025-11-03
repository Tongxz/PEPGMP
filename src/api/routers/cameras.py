#!/usr/bin/env python3
"""API routes for camera configuration and control."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import cv2
import yaml
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import Response

from src.api.redis_listener import CAMERA_STATS_CACHE
from src.api.utils.rollout import should_use_domain
from src.services.scheduler import get_scheduler

try:
    from src.services.detection_service_domain import (
        DefaultCameraRepository,
        get_detection_service_domain,
    )
except Exception:
    get_detection_service_domain = None  # type: ignore
    DefaultCameraRepository = None  # type: ignore

try:
    from src.domain.services.camera_control_service import CameraControlService
    from src.domain.services.camera_service import CameraService

    async def get_camera_service() -> CameraService | None:
        """获取摄像头服务实例."""
        try:
            if DefaultCameraRepository is None:
                return None
            # 使用默认的摄像头仓储（内存存储）
            camera_repo = DefaultCameraRepository()
            cameras_yaml_path = _cameras_path()
            return CameraService(camera_repo, cameras_yaml_path)
        except Exception:
            return None

    async def get_camera_control_service() -> CameraControlService | None:
        """获取摄像头控制服务实例."""
        try:
            camera_service = await get_camera_service()
            if camera_service is None:
                return None
            scheduler = get_scheduler()
            return CameraControlService(camera_service, scheduler)
        except Exception:
            return None

except Exception:
    get_camera_service = None  # type: ignore
    get_camera_control_service = None  # type: ignore

router = APIRouter()
# 为本模块创建 logger，避免未定义引用导致 500
logger = logging.getLogger(__name__)


def _project_root() -> str:
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def _cameras_path() -> str:
    return os.path.join(_project_root(), "config", "cameras.yaml")


def _read_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"cameras": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        # 避免因配置格式错误导致 500，记录错误并返回空列表
        logger.error(f"读取摄像头配置失败: {e}")
        return {"cameras": []}
    if not isinstance(data.get("cameras"), list):
        data["cameras"] = []
    return data


def _write_yaml(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 原子写
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=os.path.dirname(path)
    ) as tf:
        yaml.safe_dump(data, tf, allow_unicode=True, sort_keys=False)
        tmp_name = tf.name
    os.replace(tmp_name, path)


@router.get("/cameras")
async def list_cameras(
    active_only: bool = Query(False, description="是否只返回活跃摄像头"),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取所有已配置的摄像头列表.

    Args:
        active_only: 是否只返回活跃摄像头
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个包含所有摄像头配置列表的字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            cameras = await domain_service.get_cameras(active_only=active_only)
            return {"cameras": cameras}
    except Exception as e:
        logger.warning(f"领域服务获取摄像头列表失败，回退到YAML配置: {e}")

    # 旧实现（回退）
    data = _read_yaml(_cameras_path())
    return {"cameras": data.get("cameras", [])}


@router.post("/cameras")
async def create_camera(
    payload: Dict[str, Any],
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """创建一个新的摄像头配置.

    Args:
        payload: 包含新摄像头信息的字典.
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个表示操作成功的字典，包含新创建的摄像头信息.
    """
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_camera_service is not None:
            camera_service = await get_camera_service()  # type: ignore
            if camera_service:
                result = await camera_service.create_camera(payload)
                return result
    except ValueError as e:
        # 业务逻辑错误（如ID已存在），直接抛出HTTP异常
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务创建摄像头失败，回退到旧实现: {e}")

    # 旧实现（回退）
    required = ["id", "name", "source"]
    for k in required:
        if k not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {k}")
    data = _read_yaml(_cameras_path())
    cams: List[Dict[str, Any]] = list(data.get("cameras", []))
    if any(c.get("id") == payload["id"] for c in cams):
        raise HTTPException(status_code=409, detail="Camera id already exists")
    cams.append(payload)
    data["cameras"] = cams
    _write_yaml(_cameras_path(), data)
    return {"ok": True, "camera": payload}


@router.put("/cameras/{camera_id}")
async def update_camera(
    camera_id: str = Path(...),
    payload: Dict[str, Any] = {},
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """更新指定摄像头的配置.

    Args:
        camera_id: 要更新的摄像头的ID.
        payload: 包含要更新的字段的字典.
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个表示操作成功的字典.
    """
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_camera_service is not None:
            camera_service = await get_camera_service()  # type: ignore
            if camera_service:
                result = await camera_service.update_camera(camera_id, payload)
                return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务更新摄像头失败，回退到旧实现: {e}")

    # 旧实现（回退）
    data = _read_yaml(_cameras_path())
    cameras = data.get("cameras", [])
    for i, cam in enumerate(cameras):
        if cam.get("id") == camera_id:
            cameras[i].update(payload)
            _write_yaml(_cameras_path(), data)
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Camera not found")


@router.delete("/cameras/{camera_id}")
async def delete_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """删除指定摄像头的配置.

    Args:
        camera_id: 要删除的摄像头的ID.
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个表示操作成功的字典.
    """
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_camera_service is not None:
            camera_service = await get_camera_service()  # type: ignore
            if camera_service:
                result = await camera_service.delete_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务删除摄像头失败，回退到旧实现: {e}")

    # 旧实现（回退）
    data = _read_yaml(_cameras_path())
    cameras = data.get("cameras", [])
    for i, cam in enumerate(cameras):
        if cam.get("id") == camera_id:
            del cameras[i]
            _write_yaml(_cameras_path(), data)
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Camera not found")


@router.get("/cameras/{camera_id}/preview")
def preview_camera(camera_id: str = Path(...)) -> Response:  # noqa: C901
    """返回指定摄像头的一帧 JPEG 预览.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含JPEG图像数据的 StreamingResponse.
    """
    data = _read_yaml(_cameras_path())
    cams: List[Dict[str, Any]] = list(data.get("cameras", []))
    cam = next((c for c in cams if str(c.get("id")) == camera_id), None)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    source = str(cam.get("source", "")).strip()
    if source == "":
        raise HTTPException(status_code=400, detail="Camera source is empty")
    # 打开视频源
    try:
        cap = None
        if source.isdigit():
            cap = cv2.VideoCapture(int(source), cv2.CAP_AVFOUNDATION)
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(int(source))
        else:
            cap = cv2.VideoCapture(source)
        if not cap or not cap.isOpened():
            raise HTTPException(status_code=502, detail="Failed to open camera source")
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise HTTPException(status_code=502, detail="Failed to read frame")
        # 可选：按配置分辨率缩放
        res = str(cam.get("resolution", "")).lower()
        if "x" in res:
            try:
                w_str, h_str = res.split("x", 1)
                w = int(w_str)
                h = int(h_str)
                if w > 0 and h > 0:
                    frame = cv2.resize(frame, (w, h))
            except Exception:
                # Ignore errors if resolution is invalid, proceed with original frame.
                pass  # nosec B110
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise HTTPException(status_code=500, detail="JPEG encode failed")
        return Response(content=buf.tobytes(), media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {e}")


@router.post("/cameras/{camera_id}/start")
async def start_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """启动指定摄像头的检测进程."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.start_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如启动失败），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务启动失败，回退到调度器: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()
    res = scheduler.start_detection(camera_id)
    if not res.get("ok"):
        logger.error(f"Failed to start camera {camera_id}: {res}")
        raise HTTPException(
            status_code=400, detail=res.get("error") or "Failed to start camera"
        )
    logger.info(
        f"Started camera {camera_id}: pid={res.get('pid')} log={res.get('log')}"
    )
    return res


@router.post("/cameras/{camera_id}/stop")
async def stop_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """停止指定摄像头的检测进程."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.stop_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如停止失败），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务停止失败，回退到调度器: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()
    res = scheduler.stop_detection(camera_id)
    if not res.get("ok"):
        logger.error(f"Failed to stop camera {camera_id}: {res}")
        raise HTTPException(
            status_code=400, detail=res.get("error") or "Failed to stop camera"
        )
    logger.info(f"Stopped camera {camera_id}")
    return res


@router.post("/cameras/{camera_id}/restart")
async def restart_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """重启指定摄像头的检测进程."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.restart_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如重启失败），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务重启失败，回退到调度器: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()
    res = scheduler.restart_detection(camera_id)
    if not res.get("ok"):
        logger.error(f"Failed to restart camera {camera_id}: {res}")
        raise HTTPException(
            status_code=400, detail=res.get("error") or "Failed to restart camera"
        )
    logger.info(
        f"Restarted camera {camera_id}: pid={res.get('pid')} log={res.get('log')}"
    )
    return res


@router.get("/cameras/{camera_id}/status")
async def status_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取指定摄像头检测进程的状态."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.get_camera_status(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误，直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务状态查询失败，回退到调度器: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()
    res = scheduler.get_status(camera_id)
    logger.info(
        f"Status camera {camera_id}: running={res.get('running')} pid={res.get('pid')}"
    )
    return res


@router.post("/cameras/batch-status")
async def batch_camera_status(
    request_body: Dict[str, Any] = None,
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """批量查询摄像头运行状态."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                camera_ids_to_query = None
                if request_body and "camera_ids" in request_body:
                    camera_ids_to_query = request_body["camera_ids"]
                result = control_service.get_batch_status(camera_ids_to_query)
                return result
    except ValueError as e:
        # 业务逻辑错误，直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务批量状态查询失败，回退到调度器: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()

    camera_ids_to_query = []
    if request_body and "camera_ids" in request_body:
        camera_ids_to_query = request_body["camera_ids"]

    # The scheduler's get_batch_status can handle the None case to query all
    result = scheduler.get_batch_status(camera_ids_to_query or None)

    logger.debug(f"Batch status query for {len(result)} cameras")
    return result


@router.post("/cameras/{camera_id}/activate")
async def activate_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """激活摄像头（允许启动检测）.

    Args:
        camera_id: 目标摄像头的ID.
        force_domain: 测试用途，强制走领域分支

    Returns:
        操作结果字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = await control_service.activate_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务激活失败，回退到YAML配置: {e}")

    # 旧实现（回退）
    path = _cameras_path()
    data = _read_yaml(path)
    cameras: List[Dict[str, Any]] = data.get("cameras", [])

    cam = next((c for c in cameras if str(c.get("id")) == str(camera_id)), None)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # 更新激活状态
    cam["active"] = True

    # 写回配置
    _write_yaml(path, data)

    logger.info(f"Activated camera {camera_id}")
    return {"ok": True, "camera_id": camera_id, "active": True}


@router.post("/cameras/{camera_id}/deactivate")
async def deactivate_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """停用摄像头（禁止启动检测，如正在运行则先停止）."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = await control_service.deactivate_camera(camera_id)
                return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务停用失败，回退到YAML配置: {e}")

    # 旧实现（回退）
    # 1. 先检查并停止运行中的进程
    scheduler = get_scheduler()
    status = scheduler.status(camera_id)

    if status.get("running"):
        logger.info(f"Camera {camera_id} is running, stopping before deactivation")
        stop_res = scheduler.stop_detection(camera_id)
        if not stop_res.get("ok"):
            logger.warning(f"Failed to stop camera {camera_id}: {stop_res}")

    # 2. 更新配置
    path = _cameras_path()
    data = _read_yaml(path)
    cameras: List[Dict[str, Any]] = data.get("cameras", [])

    cam = next((c for c in cameras if str(c.get("id")) == str(camera_id)), None)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # 更新停用状态
    cam["active"] = False
    cam["auto_start"] = False  # 停用时同时关闭自动启动

    # 写回配置
    _write_yaml(path, data)

    logger.info(f"Deactivated camera {camera_id}")
    return {
        "ok": True,
        "camera_id": camera_id,
        "active": False,
        "stopped": status.get("running", False),
    }


@router.put("/cameras/{camera_id}/auto-start")
async def toggle_auto_start(
    camera_id: str = Path(...),
    auto_start: bool = False,
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """切换摄像头的自动启动设置.

    Args:
        camera_id: 目标摄像头的ID.
        auto_start: 是否自动启动.
        force_domain: 测试用途，强制走领域分支

    Returns:
        操作结果字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = await control_service.toggle_auto_start(camera_id, auto_start)
                return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在或未激活），直接抛出HTTP异常
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务切换自动启动失败，回退到YAML配置: {e}")

    # 旧实现（回退）
    path = _cameras_path()
    data = _read_yaml(path)
    cameras: List[Dict[str, Any]] = data.get("cameras", [])

    cam = next((c for c in cameras if str(c.get("id")) == str(camera_id)), None)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    # 检查摄像头是否激活
    is_active = cam.get("active", cam.get("enabled", True))
    if not is_active:
        raise HTTPException(status_code=400, detail="摄像头未激活，无法设置自动启动")

    # 更新自动启动状态
    cam["auto_start"] = bool(auto_start)

    # 写回配置
    _write_yaml(path, data)

    logger.info(f"Toggled auto_start for camera {camera_id}: {auto_start}")
    return {"ok": True, "camera_id": camera_id, "auto_start": bool(auto_start)}


@router.get("/cameras/{camera_id}/stats")
async def get_camera_stats(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取指定摄像头的详细检测统计信息.

    数据源已切换为由Redis Pub/Sub实时更新的内存缓存.

    Args:
        camera_id: 目标摄像头的ID.
        force_domain: 测试用途，强制走领域分支

    Returns:
        包含检测统计数据的字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_camera_stats_detailed(camera_id)
            return result
    except Exception as e:
        logger.warning(f"领域服务获取摄像头统计失败，回退到缓存统计: {e}")

    # 旧实现（回退）
    scheduler = get_scheduler()
    status = scheduler.status(camera_id)

    # 1. 从ProcessManager获取基础运行状态
    stats_response = {
        "camera_id": camera_id,
        "running": status.get("running", False),
        "pid": status.get("pid", 0),
        "log_file": status.get("log", ""),
        "stats": {  # 提供默认值，以防缓存中无数据
            "total_frames": 0,
            "processed_frames": 0,
            "detected_persons": 0,
            "detected_hairnets": 0,
            "detected_handwash": 0,
            "avg_fps": 0.0,
            "avg_detection_time": 0.0,
            "last_detection_time": None,
        },
    }

    # 2. 从内存缓存中获取实时的详细统计数据
    latest_stats_msg = CAMERA_STATS_CACHE.get(camera_id)

    if latest_stats_msg and isinstance(latest_stats_msg, dict):
        # 提取 "data" 字段中的核心统计信息
        realtime_data = latest_stats_msg.get("data", {})

        # 提取时间戳
        timestamp = latest_stats_msg.get("timestamp")
        if timestamp:
            stats_response["stats"]["last_detection_time"] = datetime.fromtimestamp(
                timestamp
            ).strftime("%Y-%m-%d %H:%M:%S")

        # 更新统计信息 (使用.get确保键不存在时不会出错)
        stats_response["stats"].update(
            {
                "detected_persons": realtime_data.get("persons", 0),
                "detected_hairnets": realtime_data.get("hairnets", 0),
                "detected_handwash": realtime_data.get("handwash", 0),
                "avg_fps": realtime_data.get("fps", 0.0),
                # 注意：其他字段如 total_frames, processed_frames, avg_detection_time
                # 需要检测进程在发布的消息中一并提供，此处仅为示例
                "processed_frames": realtime_data.get("processed_frames", 0),
                "total_frames": realtime_data.get("total_frames", 0),
                "avg_detection_time": realtime_data.get("avg_detection_time", 0.0),
            }
        )

    return stats_response


@router.get("/cameras/{camera_id}/logs")
async def get_camera_logs(
    camera_id: str = Path(...),
    lines: int = 100,
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取指定摄像头的最新日志.

    Args:
        camera_id: 目标摄像头的ID.
        lines: 返回的日志行数（默认100）.
        force_domain: 测试用途，强制走领域分支

    Returns:
        包含日志内容的字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.get_camera_logs(camera_id, lines)
                return result
    except ValueError as e:
        # 业务逻辑错误（如日志文件未配置），直接抛出HTTP异常
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"摄像头控制服务读取日志失败，回退到直接读取: {e}")

    # 旧实现（回退）
    from pathlib import Path as FilePath

    scheduler = get_scheduler()
    status = scheduler.status(camera_id)

    if not status.get("log"):
        raise HTTPException(status_code=404, detail="Log file not configured")

    log_path = FilePath(status["log"])
    if not log_path.exists():
        return {
            "camera_id": camera_id,
            "log_file": str(log_path),
            "lines": [],
            "message": "Log file not found (process may not have started yet)",
        }

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "camera_id": camera_id,
            "log_file": str(log_path),
            "total_lines": len(all_lines),
            "lines": [line.rstrip("\n") for line in recent_lines],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")


@router.post("/cameras/refresh")
async def refresh_all_cameras(
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """刷新所有摄像头状态（占位实现）.

    前端仅用来触发状态刷新流程，随后会重新获取摄像头列表.
    这里返回简单的确认信息即可，未来可在此集成真实状态探测/进程同步.

    Args:
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个表示操作成功的确认信息字典.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_camera_control_service is not None:
            control_service = await get_camera_control_service()  # type: ignore
            if control_service:
                result = control_service.refresh_all_cameras()
                return result
    except Exception as e:
        logger.warning(f"摄像头控制服务刷新失败，回退到旧实现: {e}")

    # 旧实现（回退）
    return {
        "status": "success",
        "message": "All camera statuses refreshed",
        "timestamp": datetime.now().isoformat(),
    }
