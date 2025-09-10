from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import Response
import cv2
import numpy as np
import yaml


router = APIRouter()


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


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
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=os.path.dirname(path)) as tf:
        yaml.safe_dump(data, tf, allow_unicode=True, sort_keys=False)
        tmp_name = tf.name
    os.replace(tmp_name, path)


@router.get("/api/v1/cameras")
def list_cameras() -> Dict[str, Any]:
    data = _read_yaml(_cameras_path())
    return {"cameras": data.get("cameras", [])}


@router.post("/api/v1/cameras")
def create_camera(payload: Dict[str, Any]) -> Dict[str, Any]:
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


@router.put("/api/v1/cameras/{camera_id}")
def update_camera(camera_id: str = Path(...), payload: Dict[str, Any] = {}) -> Dict[str, Any]:
    data = _read_yaml(_cameras_path())
    cams: List[Dict[str, Any]] = list(data.get("cameras", []))
    for i, cam in enumerate(cams):
        if str(cam.get("id")) == camera_id:
            updated = {**cam, **payload, "id": camera_id}
            cams[i] = updated
            data["cameras"] = cams
            _write_yaml(_cameras_path(), data)
            return {"ok": True, "camera": updated}
    raise HTTPException(status_code=404, detail="Camera not found")


@router.delete("/api/v1/cameras/{camera_id}")
def delete_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    data = _read_yaml(_cameras_path())
    cams: List[Dict[str, Any]] = list(data.get("cameras", []))
    new_cams = [c for c in cams if str(c.get("id")) != camera_id]
    if len(new_cams) == len(cams):
        raise HTTPException(status_code=404, detail="Camera not found")
    data["cameras"] = new_cams
    _write_yaml(_cameras_path(), data)
    return {"ok": True}


@router.get("/api/v1/cameras/{camera_id}/preview")
def preview_camera(camera_id: str = Path(...)) -> Response:
    """返回指定摄像头的一帧 JPEG 预览。"""
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
                w = int(w); h = int(h)
                if w > 0 and h > 0:
                    frame = cv2.resize(frame, (w, h))
            except Exception:
                pass
        ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise HTTPException(status_code=500, detail="JPEG encode failed")
        return Response(content=buf.tobytes(), media_type='image/jpeg')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview error: {e}")


# --- 新增：进程控制路由 ---
from src.services.process_manager import get_process_manager


@router.post("/api/v1/cameras/{camera_id}/start")
def start_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    pm = get_process_manager()
    return pm.start(camera_id)


@router.post("/api/v1/cameras/{camera_id}/stop")
def stop_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    pm = get_process_manager()
    return pm.stop(camera_id)


@router.post("/api/v1/cameras/{camera_id}/restart")
def restart_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    pm = get_process_manager()
    return pm.restart(camera_id)


@router.get("/api/v1/cameras/{camera_id}/status")
def status_camera(camera_id: str = Path(...)) -> Dict[str, Any]:
    pm = get_process_manager()
    return pm.status(camera_id)


