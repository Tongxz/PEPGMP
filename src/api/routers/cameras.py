#!/usr/bin/env python3
"""API routes for camera configuration and control."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict

import cv2
import yaml
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import Response

from src.api.redis_listener import CAMERA_STATS_CACHE
from src.api.utils.rollout import should_use_domain
from src.services.scheduler import get_scheduler

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

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
    from src.infrastructure.repositories.postgresql_camera_repository import (
        PostgreSQLCameraRepository,
    )
    from src.services.database_service import get_db_service

    async def get_camera_service() -> CameraService | None:
        """获取摄像头服务实例."""
        try:
            # 使用PostgreSQL仓储
            db_service = await get_db_service()
            if not db_service.pool:
                logger.warning("数据库连接池未初始化，使用内存仓储作为回退")
                if DefaultCameraRepository is None:
                    return None
                camera_repo = DefaultCameraRepository()
            else:
                camera_repo = PostgreSQLCameraRepository(db_service.pool)
            # YAML路径仅用于初始化时导入（可选）
            cameras_yaml_path = (
                _cameras_path()
                if os.getenv("ENABLE_YAML_FALLBACK", "false").lower() == "true"
                else None
            )
            return CameraService(camera_repo, cameras_yaml_path)
        except Exception as e:
            logger.warning(f"创建CameraService失败: {e}，使用内存仓储作为回退")
            if DefaultCameraRepository is None:
                return None
            camera_repo = DefaultCameraRepository()
            cameras_yaml_path = _cameras_path()
            return CameraService(camera_repo, cameras_yaml_path)

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


def _sync_video_stream_config_to_redis(
    camera_id: str, camera_config: Dict[str, Any]
) -> None:
    """将相机配置中的视频流配置同步到Redis（旧实现回退）

    注意：此函数用于API层的旧实现回退路径。新实现应该使用领域服务的统一函数。
    """
    try:
        from src.infrastructure.notifications.redis_config_sync import (
            sync_camera_config_to_redis,
        )

        # 提取需要同步的配置项
        changed_keys = [
            key for key in ["log_interval", "stream_interval"] if key in camera_config
        ]

        if changed_keys:
            sync_camera_config_to_redis(
                camera_id=camera_id,
                camera_config=camera_config,
                changed_keys=changed_keys,
            )
    except Exception as e:
        logger.warning(f"同步视频流配置到Redis失败: camera_id={camera_id}, error={e}")


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
    # 统一使用数据库（无回退）
    if get_camera_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        camera_service = await get_camera_service()  # type: ignore
        if not camera_service:
            raise raise_http_exception(
                status_code=503,
                message="相机服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        cameras = await camera_service.camera_repository.find_all()
        if active_only:
            cameras = [c for c in cameras if c.is_active]
        # 转换为字典格式（同时提取metadata字段和active字段）
        cameras_dict = []
        for camera in cameras:
            cam_dict = camera.to_dict()
            metadata = cam_dict.get("metadata", {})
            # 提取source字段
            if "source" in metadata:
                cam_dict["source"] = metadata["source"]
            # 提取视频流配置字段
            if "log_interval" in metadata:
                cam_dict["log_interval"] = metadata["log_interval"]
            if "stream_interval" in metadata:
                cam_dict["stream_interval"] = metadata["stream_interval"]
            if "frame_by_frame" in metadata:
                cam_dict["frame_by_frame"] = metadata["frame_by_frame"]
            # 提取其他配置字段
            for key in [
                "regions_file",
                "profile",
                "device",
                "imgsz",
                "auto_start",
            ]:
                if key in metadata:
                    cam_dict[key] = metadata[key]
            # 兼容旧格式：active字段（从Camera实体的is_active属性获取）
            cam_dict["active"] = camera.is_active
            # 同时返回enabled字段（作为active的别名，兼容前端）
            cam_dict["enabled"] = camera.is_active
            cameras_dict.append(cam_dict)
        return {"cameras": cameras_dict}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取摄像头列表失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取摄像头列表失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


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
    # 统一使用数据库（无回退）
    if get_camera_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        camera_service = await get_camera_service()  # type: ignore
        if not camera_service:
            raise raise_http_exception(
                status_code=503,
                message="相机服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await camera_service.create_camera(payload)
        return result
    except ValueError as e:
        # 业务逻辑错误（如ID已存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=409,
            message=str(e),
            error_code=ErrorCode.RESOURCE_CONFLICT,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="创建摄像头失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


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
    # 统一使用数据库（无回退）
    if get_camera_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        camera_service = await get_camera_service()  # type: ignore
        if not camera_service:
            raise raise_http_exception(
                status_code=503,
                message="相机服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await camera_service.update_camera(camera_id, payload)
        return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="更新摄像头失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


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
    # 统一使用数据库（无回退）
    if get_camera_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        camera_service = await get_camera_service()  # type: ignore
        if not camera_service:
            raise raise_http_exception(
                status_code=503,
                message="相机服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await camera_service.delete_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="删除摄像头失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/cameras/{camera_id}/preview")
async def preview_camera(camera_id: str = Path(...)) -> Response:  # noqa: C901
    """返回指定摄像头的一帧 JPEG 预览.

    Args:
        camera_id: 目标摄像头的ID.

    Returns:
        一个包含JPEG图像数据的 StreamingResponse.
    """
    # 统一使用数据库（无回退）
    if get_camera_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        camera_service = await get_camera_service()  # type: ignore
        if not camera_service:
            raise raise_http_exception(
                status_code=503,
                message="相机服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        camera = await camera_service.camera_repository.find_by_id(camera_id)
        if not camera:
            raise raise_http_exception(
                status_code=404,
                message="Camera not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 转换为字典格式
        cam = camera.to_dict()
        metadata = cam.get("metadata", {})
        if "source" in metadata:
            cam["source"] = metadata["source"]
        if "resolution" in cam:
            # resolution是数组格式 [width, height]，转换为字符串
            if isinstance(cam["resolution"], list) and len(cam["resolution"]) == 2:
                cam["resolution"] = f"{cam['resolution'][0]}x{cam['resolution'][1]}"

        source = str(cam.get("source", "")).strip()
        if source == "":
            raise raise_http_exception(
                status_code=400,
                message="Camera source is empty",
                error_code=ErrorCode.VALIDATION_ERROR,
            )

        # 打开视频源
        cap = None
        if source.isdigit():
            cap = cv2.VideoCapture(int(source), cv2.CAP_AVFOUNDATION)
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(int(source))
        else:
            cap = cv2.VideoCapture(source)
        if not cap or not cap.isOpened():
            raise raise_http_exception(
                status_code=502,
                message="Failed to open camera source",
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise raise_http_exception(
                status_code=502,
                message="Failed to read frame",
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            )
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
            raise raise_http_exception(
                status_code=500,
                message="JPEG encode failed",
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            )
        return Response(content=buf.tobytes(), media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise raise_http_exception(
            status_code=500,
            message="Preview error",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/cameras/{camera_id}/start")
async def start_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """启动指定摄像头的检测进程."""
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await control_service.start_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如启动失败），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="启动摄像头失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/cameras/{camera_id}/stop")
async def stop_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """停止指定摄像头的检测进程."""
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = control_service.stop_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如停止失败），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="停止摄像头失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/cameras/{camera_id}/restart")
async def restart_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """重启指定摄像头的检测进程."""
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await control_service.restart_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如重启失败），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重启摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="重启摄像头失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


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
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
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
async def batch_camera_status(  # noqa: C901
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
                    camera_ids = request_body["camera_ids"]
                    # 如果 camera_ids 是空数组，视为查询所有摄像头（None）
                    # 如果 camera_ids 是有效数组，使用它
                    if camera_ids and len(camera_ids) > 0:
                        camera_ids_to_query = camera_ids
                    # 如果 camera_ids 是空数组或 None，保持为 None（查询所有）

                # 如果camera_ids为None，从数据库获取所有相机ID，避免调用executor.list_cameras()
                if camera_ids_to_query is None:
                    try:
                        if get_camera_service is not None:
                            camera_service = await get_camera_service()  # type: ignore
                            if camera_service:
                                cameras = (
                                    await camera_service.camera_repository.find_all()
                                )
                                camera_ids_to_query = [c.id for c in cameras]
                                logger.debug(
                                    f"从数据库获取到 {len(camera_ids_to_query)} 个相机ID（领域服务）"
                                )
                    except Exception as e:
                        logger.warning(f"从数据库获取相机列表失败: {e}，返回空结果")
                        return {}

                result = control_service.get_batch_status(camera_ids_to_query)
                return result
    except ValueError as e:
        # 业务逻辑错误，直接抛出HTTP异常
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except Exception as e:
        logger.warning(f"摄像头控制服务批量状态查询失败，回退到调度器: {e}")

    # 旧实现（回退）：从数据库获取相机列表，而不是调用executor.list_cameras()
    scheduler = get_scheduler()

    camera_ids_to_query = None
    if request_body and "camera_ids" in request_body:
        camera_ids = request_body["camera_ids"]
        # 如果 camera_ids 是空数组，视为查询所有摄像头（None）
        # 如果 camera_ids 是有效数组，使用它
        if camera_ids and len(camera_ids) > 0:
            camera_ids_to_query = camera_ids
        # 如果 camera_ids 是空数组或 None，保持为 None（查询所有）

    # 如果camera_ids为None，从数据库获取所有相机ID，避免调用executor.list_cameras()
    if camera_ids_to_query is None:
        try:
            if get_camera_service is not None:
                camera_service = await get_camera_service()  # type: ignore
                if camera_service:
                    cameras = await camera_service.camera_repository.find_all()
                    camera_ids_to_query = [c.id for c in cameras]
                    logger.debug(f"从数据库获取到 {len(camera_ids_to_query)} 个相机ID")
        except Exception as e:
            logger.warning(f"从数据库获取相机列表失败: {e}，将查询已启动的相机状态")
            # 如果数据库查询失败，保持为None，让scheduler查询已启动的相机
            # 但这样不会触发list_cameras()调用，因为scheduler会直接查询状态

    # 如果camera_ids_to_query仍然为None或空列表，则不查询任何相机
    if not camera_ids_to_query:
        logger.debug("没有相机ID需要查询，返回空结果")
        return {}

    # 查询指定相机的状态
    result = scheduler.get_batch_status(camera_ids_to_query)

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
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await control_service.activate_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="激活摄像头失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/cameras/{camera_id}/deactivate")
async def deactivate_camera(
    camera_id: str = Path(...),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """停用摄像头（禁止启动检测，如正在运行则先停止）."""
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await control_service.deactivate_camera(camera_id)
        return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在），直接抛出HTTP异常
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用摄像头失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="停用摄像头失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


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
    # 统一使用数据库（无回退）
    if get_camera_control_service is None:
        raise raise_http_exception(
            status_code=503,
            message="相机控制服务不可用：数据库连接未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        control_service = await get_camera_control_service()  # type: ignore
        if not control_service:
            raise raise_http_exception(
                status_code=503,
                message="相机控制服务不可用：无法创建服务实例",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        result = await control_service.toggle_auto_start(camera_id, auto_start)
        return result
    except ValueError as e:
        # 业务逻辑错误（如摄像头不存在或未激活），直接抛出HTTP异常
        if "不存在" in str(e):
            raise raise_http_exception(
                status_code=404,
                message=str(e),
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )
        raise raise_http_exception(
            status_code=400,
            message=str(e),
            error_code=ErrorCode.VALIDATION_ERROR,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换自动启动失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="切换自动启动失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


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

    logger.info(f"获取摄像头统计: camera_id={camera_id}, status={status}")

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

    logger.info(
        f"摄像头统计响应: running={stats_response['running']}, pid={stats_response['pid']}, log_file={stats_response['log_file']}"
    )

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
        raise raise_http_exception(
            status_code=404,
            message=str(e),
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )
    except Exception as e:
        logger.warning(f"摄像头控制服务读取日志失败，回退到直接读取: {e}")

    # 旧实现（回退）
    from pathlib import Path as FilePath

    scheduler = get_scheduler()
    status = scheduler.status(camera_id)

    if not status.get("log"):
        raise raise_http_exception(
            status_code=404,
            message="Log file not configured",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
        )

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
        raise raise_http_exception(
            status_code=500,
            message="Failed to read log file",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


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


@router.post("/cameras/{camera_id}/test", summary="测试摄像头连接")
async def test_camera(camera_id: str = Path(..., description="摄像头ID")):
    """测试摄像头连接状态

    尝试连接摄像头并读取一帧，验证RTSP流是否可用。

    Returns:
        - success: 连接成功
        - message: 测试结果消息
        - details: 详细信息（分辨率、FPS等）
    """
    try:
        # 获取摄像头服务
        camera_service = await get_camera_service()
        if camera_service is None:
            raise raise_http_exception(
                status_code=503,
                message="摄像头服务不可用",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
            )

        # 直接从仓储获取摄像头信息
        camera = await camera_service.camera_repository.find_by_id(camera_id)
        if camera is None:
            raise raise_http_exception(
                status_code=404,
                message=f"摄像头不存在: {camera_id}",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 测试RTSP连接
        rtsp_url = camera.rtsp_url
        if not rtsp_url:
            return {"success": False, "message": "摄像头未配置RTSP地址", "details": None}

        logger.info(f"测试摄像头连接: {camera_id}, RTSP: {rtsp_url}")

        # 尝试打开视频流
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            return {
                "success": False,
                "message": "无法连接到摄像头RTSP流",
                "details": {"rtsp_url": rtsp_url, "error": "连接失败，请检查RTSP地址和网络连接"},
            }

        # 尝试读取一帧
        ret, frame = cap.read()

        if not ret or frame is None:
            cap.release()
            return {
                "success": False,
                "message": "连接成功但无法读取视频帧",
                "details": {"rtsp_url": rtsp_url, "error": "可能是摄像头未启动或视频流异常"},
            }

        # 获取视频流信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        cap.release()

        return {
            "success": True,
            "message": "摄像头连接正常",
            "details": {
                "rtsp_url": rtsp_url,
                "resolution": f"{width}x{height}",
                "fps": fps if fps > 0 else "未知",
                "frame_size": frame.shape if frame is not None else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试摄像头失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
            "details": {"error": str(e)},
        }
