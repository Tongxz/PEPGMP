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

from src.services.process_manager import get_process_manager

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
    """启动指定摄像头的检测进程.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含操作结果和进程信息的字典.
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
    """停止指定摄像头的检测进程.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含操作结果的字典.
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
    """重启指定摄像头的检测进程.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含操作结果和新进程信息的字典.
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
    """获取指定摄像头检测进程的状态.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含进程运行状态和PID的字典.
    """
    pm = get_process_manager()
    res = pm.status(camera_id)
    logger.info(
        f"Status camera {camera_id}: running={res.get('running')} pid={res.get('pid')}"
    )
    return res


@router.post("/cameras/batch-status")
def batch_camera_status(request_body: Dict[str, Any] = None) -> Dict[str, Any]:
    """批量查询摄像头运行状态.

    Args:
        request_body: 请求体，包含 camera_ids 列表，为空则查询所有.

    Returns:
        摄像头ID到状态的映射字典.
        {
            "cam0": {"running": true, "pid": 3931, "log": "/path"},
            "vid1": {"running": false, "pid": 0, "log": "/path"}
        }
    """

    pm = get_process_manager()

    # 获取摄像头ID列表
    camera_ids = []
    if request_body and "camera_ids" in request_body:
        camera_ids = request_body["camera_ids"]

    # 如果未指定ID，则查询所有摄像头
    if not camera_ids:
        path = _cameras_path()
        data = _read_yaml(path)
        cameras = data.get("cameras", [])
        camera_ids = [str(c.get("id")) for c in cameras]

    # 批量查询状态
    result = {}
    for cam_id in camera_ids:
        try:
            status = pm.status(cam_id)
            result[cam_id] = {
                "running": status.get("running", False),
                "pid": status.get("pid", 0),
                "log": status.get("log", ""),
            }
        except Exception as e:
            logger.warning(f"Failed to get status for {cam_id}: {e}")
            result[cam_id] = {"running": False, "pid": 0, "log": ""}

    logger.debug(f"Batch status query for {len(camera_ids)} cameras")
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
    """停用摄像头（禁止启动检测，如正在运行则先停止）.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        操作结果字典.
    """
    # 1. 先检查并停止运行中的进程
    pm = get_process_manager()
    status = pm.status(camera_id)

    if status.get("running"):
        logger.info(f"Camera {camera_id} is running, stopping before deactivation")
        stop_res = pm.stop(camera_id)
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

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        包含检测统计数据的字典.
    """
    import re
    from pathlib import Path as FilePath

    pm = get_process_manager()
    status = pm.status(camera_id)

    stats = {
        "camera_id": camera_id,
        "running": status.get("running", False),
        "pid": status.get("pid", 0),
        "log_file": status.get("log", ""),
        "stats": {
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

    # 如果进程正在运行，尝试从日志文件中提取统计信息
    if status.get("running") and status.get("log"):
        log_path = FilePath(status["log"])
        if log_path.exists():
            try:
                # 读取最后100行日志
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:] if len(lines) > 100 else lines

                    for line in reversed(recent_lines):
                        # 提取检测结果: "检测: 人=2, 发网=1, 洗手=0"
                        match = re.search(r"检测: 人=(\d+), 发网=(\d+), 洗手=(\d+)", line)
                        if match:
                            stats["stats"]["detected_persons"] = int(match.group(1))
                            stats["stats"]["detected_hairnets"] = int(match.group(2))
                            stats["stats"]["detected_handwash"] = int(match.group(3))

                        # 提取FPS: "处理FPS: 2.01"
                        match_fps = re.search(r"处理FPS: ([\d.]+)", line)
                        if match_fps:
                            stats["stats"]["avg_fps"] = float(match_fps.group(1))

                        # 提取处理帧数: "处理帧数: 6"
                        match_processed = re.search(r"处理帧数: (\d+)", line)
                        if match_processed:
                            stats["stats"]["processed_frames"] = int(
                                match_processed.group(1)
                            )

                        # 提取总帧数: "总帧数: 805"
                        match_total = re.search(r"总帧数: (\d+)", line)
                        if match_total:
                            stats["stats"]["total_frames"] = int(match_total.group(1))

                        # 提取检测时间: "耗时: 0.270s"
                        match_time = re.search(r"耗时: ([\d.]+)s", line)
                        if match_time:
                            stats["stats"]["avg_detection_time"] = float(
                                match_time.group(1)
                            )

                        # 提取最后检测时间（日志时间戳）
                        match_timestamp = re.search(
                            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line
                        )
                        if (
                            match_timestamp
                            and not stats["stats"]["last_detection_time"]
                        ):
                            stats["stats"][
                                "last_detection_time"
                            ] = match_timestamp.group(1)

            except Exception as e:
                logger.warning(f"Failed to parse log file for {camera_id}: {e}")

    return stats


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

    pm = get_process_manager()
    status = pm.status(camera_id)

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
