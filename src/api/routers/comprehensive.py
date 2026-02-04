import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from src.api.dependencies import get_detection_app_service, get_optimized_pipeline
from src.application.detection_application_service import DetectionApplicationService
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/comprehensive", summary="综合检测接口（图片）")
async def detect_comprehensive(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    save_to_db: bool = Query(True, description="是否保存到数据库"),
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> Dict[str, Any]:
    """
    执行综合检测，包括人体、发网、洗手、消毒等。

    完整流程：
    1. 图像解码
    2. 执行检测（基础设施层）
    3. 业务处理（领域层）：质量分析、违规检测
    4. 智能保存（根据保存策略）
    5. 返回完整结果

    Args:
        file: 上传的图片文件
        camera_id: 摄像头ID（默认: api_upload）
        save_to_db: 是否保存到数据库（默认: True）
        app_service: 检测应用服务（自动注入）

    Returns:
        检测结果，包括人数、违规情况、质量分析等
    """
    if not file.filename:
        raise raise_http_exception(
            status_code=400,
            message="未提供文件名",
            error_code=ErrorCode.VALIDATION_ERROR,
        )

    if app_service is None:
        raise raise_http_exception(
            status_code=500,
            message="检测服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    contents = await file.read()

    try:
        logger.info(
            f"开始综合检测: {file.filename}, 文件大小: {len(contents)} bytes, "
            f"camera_id={camera_id}, save_to_db={save_to_db}"
        )

        # 使用应用服务处理（完整流程）
        result = await app_service.process_image_detection(
            camera_id=camera_id, image_bytes=contents, save_to_db=save_to_db
        )

        logger.info(
            f"综合检测完成: detection_id={result['detection_id']}, "
            f"person_count={result['result']['person_count']}, "
            f"has_violations={result['result']['has_violations']}, "
            f"saved_to_db={result['saved_to_db']}"
        )

        return result

    except Exception as e:
        logger.exception(f"综合检测失败: {e}")
        raise raise_http_exception(
            status_code=500,
            message="处理失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/image", summary="单张图像检测")
async def detect_image(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    save_to_db: bool = Query(True, description="是否保存到数据库"),
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> Dict[str, Any]:
    """
    对单张图像进行人体行为检测。

    与 /comprehensive 端点功能相同，提供更直观的命名。

    Args:
        file: 上传的图片文件
        camera_id: 摄像头ID（默认: api_upload）
        save_to_db: 是否保存到数据库（默认: True）
        app_service: 检测应用服务（自动注入）

    Returns:
        检测结果，包括人数、违规情况、质量分析等
    """
    if not file.filename:
        raise raise_http_exception(
            status_code=400,
            message="未提供文件名",
            error_code=ErrorCode.VALIDATION_ERROR,
        )

    if app_service is None:
        raise raise_http_exception(
            status_code=500,
            message="检测服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    contents = await file.read()

    try:
        logger.info(
            f"开始图像检测: {file.filename}, 文件大小: {len(contents)} bytes, "
            f"camera_id={camera_id}, save_to_db={save_to_db}"
        )

        # 使用应用服务处理
        result = await app_service.process_image_detection(
            camera_id=camera_id, image_bytes=contents, save_to_db=save_to_db
        )

        logger.info(
            f"图像检测完成: detection_id={result['detection_id']}, "
            f"person_count={result['result']['person_count']}"
        )

        return result

    except Exception as e:
        logger.exception(f"图像检测失败: {e}")
        raise raise_http_exception(
            status_code=500,
            message="处理失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.post("/hairnet", summary="发网检测接口")
async def detect_hairnet(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    save_to_db: bool = Query(True, description="是否保存到数据库"),
    app_service: Optional[DetectionApplicationService] = Depends(
        get_detection_app_service
    ),
) -> Dict[str, Any]:
    """
    专门进行发网检测。

    实际上会执行完整的检测流程，但重点关注发网检测结果。

    Args:
        file: 上传的图片文件
        camera_id: 摄像头ID（默认: api_upload）
        save_to_db: 是否保存到数据库（默认: True）
        app_service: 检测应用服务（自动注入）

    Returns:
        检测结果，重点返回发网检测信息
    """
    if not file.filename:
        raise raise_http_exception(
            status_code=400,
            message="未提供文件名",
            error_code=ErrorCode.VALIDATION_ERROR,
        )

    if app_service is None:
        raise raise_http_exception(
            status_code=500,
            message="检测服务未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    contents = await file.read()

    try:
        logger.info(
            f"开始发网检测: {file.filename}, 文件大小: {len(contents)} bytes, "
            f"camera_id={camera_id}"
        )

        # 使用应用服务处理
        full_result = await app_service.process_image_detection(
            camera_id=camera_id, image_bytes=contents, save_to_db=save_to_db
        )

        # 提取发网检测结果
        hairnet_results = full_result["result"]["hairnet_results"]
        has_violations = full_result["result"]["has_violations"]

        # 构建发网专用响应
        result = {
            "ok": True,
            "filename": file.filename,
            "detection_type": "hairnet",
            "detection_id": full_result["detection_id"],
            "results": {
                "hairnet_detected": not has_violations,
                "hairnet_results": hairnet_results,
                "person_count": full_result["result"]["person_count"],
            },
            "saved_to_db": full_result["saved_to_db"],
        }

        logger.info(
            f"发网检测完成: detection_id={result['detection_id']}, "
            f"hairnet_detected={result['results']['hairnet_detected']}"
        )

        return result

    except Exception as e:
        logger.exception(f"发网检测失败: {e}")
        raise raise_http_exception(
            status_code=500,
            message="处理失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.get("/stats", summary="获取检测管道统计信息")
async def get_detection_stats(
    pipeline: Optional[OptimizedDetectionPipeline] = Depends(get_optimized_pipeline),
) -> Dict[str, Any]:
    """
    获取检测管道的统计信息，包括优化功能状态和性能指标。

    Returns:
        检测管道统计信息，包括：
        - 优化功能启用状态
        - 状态管理统计
        - 缓存统计
        - 性能指标
        - ROI优化统计
    """
    if pipeline is None:
        raise raise_http_exception(
            status_code=503,
            message="检测管道未初始化",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )

    try:
        stats = {
            "optimization_enabled": True,
            "state_management": {
                "enabled": getattr(pipeline, "enable_state_management", False),
                "stats": {},
            },
            "async_detection": {
                "enabled": getattr(pipeline, "enable_async", False),
                "max_workers": 0,
            },
            "cache": {
                "enabled": getattr(pipeline, "enable_cache", False),
                "stats": {},
            },
            "performance": {
                "total_detections": pipeline.stats.get("total_detections", 0),
                "avg_processing_time": pipeline.stats.get("avg_processing_time", 0.0),
                "cache_hits": pipeline.stats.get("cache_hits", 0),
                "cache_misses": pipeline.stats.get("cache_misses", 0),
            },
        }

        # 状态管理统计
        if stats["state_management"]["enabled"]:
            state_manager = getattr(pipeline, "state_manager", None)
            if state_manager:
                stats["state_management"]["stats"] = state_manager.get_stats()

        # 异步检测统计
        if stats["async_detection"]["enabled"]:
            async_pipeline = getattr(pipeline, "async_pipeline", None)
            if async_pipeline is not None and hasattr(async_pipeline, "executor"):
                stats["async_detection"][
                    "max_workers"
                ] = async_pipeline.executor._max_workers

        # 缓存统计
        if stats["cache"]["enabled"]:
            frame_cache = getattr(pipeline, "frame_cache", None)
            if frame_cache:
                stats["cache"]["stats"] = frame_cache.get_stats()

                # 计算缓存命中率
                cache_hits = pipeline.stats.get("cache_hits", 0)
                cache_misses = pipeline.stats.get("cache_misses", 0)
                total_requests = cache_hits + cache_misses
                if total_requests > 0:
                    stats["cache"]["hit_rate"] = cache_hits / total_requests
                else:
                    stats["cache"]["hit_rate"] = 0.0

        # ROI优化统计（通过检查方法是否存在）
        stats["roi_optimization"] = {
            "enabled": hasattr(pipeline, "_detect_hairnet_for_persons"),
        }

        # 帧跳过统计（如果可用）
        stats["frame_skip"] = {
            "enabled": False,  # 默认未启用，需要手动配置
        }

        return stats

    except Exception as e:
        logger.exception(f"获取统计信息失败: {e}")
        raise raise_http_exception(
            status_code=500,
            message="获取统计信息失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )
