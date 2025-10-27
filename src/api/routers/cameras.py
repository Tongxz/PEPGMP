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
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

from src.api.redis_listener import CAMERA_STATS_CACHE
from src.services.scheduler import get_scheduler

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
def list_cameras() -> Dict[str, Any]:
    """获取所有已配置的摄像头列表.

    Returns:
        一个包含所有摄像头配置列表的字典.
    """
    data = _read_yaml(_cameras_path())
    return {"cameras": data.get("cameras", [])}


@router.post("/cameras")
def create_camera(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建一个新的摄像头配置.

    Args:
        payload: 包含新摄像头信息的字典.

    Returns:
        一个表示操作成功的字典，包含新创建的摄像头信息.
    """
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
def update_camera(
    camera_id: str = Path(...), payload: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """更新指定摄像头的配置.

    Args:
        camera_id: 要更新的摄像头的ID.
        payload: 包含要更新的字段的字典.

    Returns:
        一个表示操作成功的字典.
    """
    data = _read_yaml(_cameras_path())
    cameras = data.get("cameras", [])
    for i, cam in enumerate(cameras):
        if cam.get("id") == camera_id:
            cameras[i].update(payload)
            _write_yaml(_cameras_path(), data)
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Camera not found")


@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """删除指定摄像头的配置.

    Args:
        camera_id: 要删除的摄像头的ID.

    Returns:
        一个表示操作成功的字典.
    """
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
def start_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """启动指定摄像头的检测进程."""
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
def stop_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """停止指定摄像头的检测进程."""
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
def restart_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """重启指定摄像头的检测进程."""
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
def status_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """获取指定摄像头检测进程的状态."""
    scheduler = get_scheduler()
    res = scheduler.get_status(camera_id)
    logger.info(
        f"Status camera {camera_id}: running={res.get('running')} pid={res.get('pid')}"
    )
    return res


@router.post("/cameras/batch-status")
def batch_camera_status(request_body: Dict[str, Any] = None) -> Dict[str, Any]:
    """批量查询摄像头运行状态."""
    scheduler = get_scheduler()

    camera_ids_to_query = []
    if request_body and "camera_ids" in request_body:
        camera_ids_to_query = request_body["camera_ids"]

    # The scheduler's get_batch_status can handle the None case to query all
    result = scheduler.get_batch_status(camera_ids_to_query or None)

    logger.debug(f"Batch status query for {len(result)} cameras")
    return result


@router.post("/cameras/{camera_id}/activate")
def activate_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """激活摄像头（允许启动检测）.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        操作结果字典.
    """
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
def deactivate_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """停用摄像头（禁止启动检测，如正在运行则先停止）."""
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
def toggle_auto_start(
    camera_id: str = Path(...), auto_start: bool = False
) -> Dict[str, Any]:
    """切换摄像头的自动启动设置.

    Args:
        camera_id: 目标摄像头的ID.
        auto_start: 是否自动启动.

    Returns:
        操作结果字典.
    """
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
def get_camera_stats(camera_id: str = Path(...)) -> Dict[str, Any]:
    """获取指定摄像头的详细检测统计信息.

    数据源已切换为由Redis Pub/Sub实时更新的内存缓存.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        包含检测统计数据的字典.
    """
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
def get_camera_logs(camera_id: str = Path(...), lines: int = 100) -> Dict[str, Any]:
    """获取指定摄像头的最新日志.

    Args:
        camera_id: 目标摄像头的ID.
        lines: 返回的日志行数（默认100）.

    Returns:
        包含日志内容的字典.
    """
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
def refresh_all_cameras() -> Dict[str, Any]:
    """刷新所有摄像头状态（占位实现）.

    前端仅用来触发状态刷新流程，随后会重新获取摄像头列表.
    这里返回简单的确认信息即可，未来可在此集成真实状态探测/进程同步.

    Returns:
        一个表示操作成功的确认信息字典.
    """
    return {
        "status": "success",
        "message": "All camera statuses refreshed",
        "timestamp": datetime.now().isoformat(),
    }
