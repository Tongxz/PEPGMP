#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import yaml
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response

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
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
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
    """获取所有已配置的摄像头列表。

    Returns:
        一个包含所有摄像头配置列表的字典。
    """
    data = _read_yaml(_cameras_path())
    return {"cameras": data.get("cameras", [])}


@router.post("/cameras")
def create_camera(payload: Dict[str, Any]) -> Dict[str, Any]:
    """创建一个新的摄像头配置。

    Args:
        payload: 包含新摄像头信息的字典。

    Returns:
        一个表示操作成功的字典，包含新创建的摄像头信息。
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
    """更新指定摄像头的配置。

    Args:
        camera_id: 要更新的摄像头的ID。
        payload: 包含要更新的字段的字典。

    Returns:
        一个表示操作成功的字典。
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
    """删除指定摄像头的配置。

    Args:
        camera_id: 要删除的摄像头的ID。

    Returns:
        一个表示操作成功的字典。
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
def preview_camera(camera_id: str = Path(...)) -> Response:
    """返回指定摄像头的一帧 JPEG 预览。

    Args:
        camera_id: 目标摄像头的ID。

    Returns:
        一个包含JPEG图像数据的 StreamingResponse。
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
                w, h = res.split("x", 1)
                w = int(w)
                h = int(h)
                if w > 0 and h > 0:
                    frame = cv2.resize(frame, (w, h))
            except Exception:
                pass
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise HTTPException(status_code=500, detail="JPEG encode failed")
        return Response(content=buf.tobytes(), media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {e}")


# --- 新增：进程控制路由 ---
from src.services.process_manager import get_process_manager


@router.post("/cameras/{camera_id}/start")
def start_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """启动指定摄像头的检测进程。

    Args:
        camera_id: 目标摄像头的ID。

    Returns:
        一个包含操作结果和进程信息的字典。
    """
    pm = get_process_manager()
    res = pm.start(camera_id)
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
    """停止指定摄像头的检测进程。

    Args:
        camera_id: 目标摄像头的ID。

    Returns:
        一个包含操作结果的字典。
    """
    pm = get_process_manager()
    res = pm.stop(camera_id)
    if not res.get("ok"):
        logger.error(f"Failed to stop camera {camera_id}: {res}")
        raise HTTPException(
            status_code=400, detail=res.get("error") or "Failed to stop camera"
        )
    logger.info(f"Stopped camera {camera_id}")
    return res


@router.post("/cameras/{camera_id}/restart")
def restart_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    """重启指定摄像头的检测进程。

    Args:
        camera_id: 目标摄像头的ID。

    Returns:
        一个包含操作结果和新进程信息的字典。
    """
    pm = get_process_manager()
    res = pm.restart(camera_id)
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
    """获取指定摄像头检测进程的状态。

    Args:
        camera_id: 目标摄像头的ID。

    Returns:
        一个包含进程运行状态和PID的字典。
    """
    pm = get_process_manager()
    res = pm.status(camera_id)
    logger.info(
        f"Status camera {camera_id}: running={res.get('running')} pid={res.get('pid')}"
    )
    return res


@router.post("/cameras/refresh")
def refresh_all_cameras() -> Dict[str, Any]:
    """
    刷新所有摄像头状态（占位实现）。

    前端仅用来触发状态刷新流程，随后会重新获取摄像头列表。
    这里返回简单的确认信息即可，未来可在此集成真实状态探测/进程同步。

    Returns:
        一个表示操作成功的确认信息字典。
    """
    return {
        "status": "success",
        "message": "All camera statuses refreshed",
        "timestamp": datetime.now().isoformat(),
    }
