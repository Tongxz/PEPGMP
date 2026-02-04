"""
API依赖注入

提供API路由所需的依赖项
"""

import logging
from typing import Optional

from fastapi import Request

from src.application.detection_application_service import (
    DetectionApplicationService,
    create_save_policy_from_env,
)
from src.container.service_container import get_service
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector
from src.interfaces.storage import SnapshotStorageProtocol
from src.services.detection_service_domain import get_detection_service_domain

logger = logging.getLogger(__name__)

async def get_optimized_pipeline(
    request: Request,
) -> Optional[OptimizedDetectionPipeline]:
    """获取优化检测管道实例"""
    pipeline = getattr(request.app.state, "optimized_pipeline", None)
    if pipeline is not None:
        return pipeline

    # 兼容：若 app.state 未初始化，则尝试惰性初始化并写入 state
    try:
        from src.services.detection_service import initialize_detection_services

        pipeline, hairnet_pipeline = initialize_detection_services()
        request.app.state.optimized_pipeline = pipeline
        request.app.state.hairnet_pipeline = hairnet_pipeline
        logger.info("OptimizedDetectionPipeline 已惰性初始化并写入 app.state")
        return pipeline
    except Exception as e:
        logger.error(f"初始化检测管道失败: {e}")
        return None


async def get_hairnet_pipeline(
    request: Request,
) -> Optional[YOLOHairnetDetector]:
    """获取发网检测管道实例"""
    hairnet_pipeline = getattr(request.app.state, "hairnet_pipeline", None)
    if hairnet_pipeline is not None:
        return hairnet_pipeline

    # 兼容：若 app.state 未初始化，则尝试惰性初始化并写入 state
    try:
        from src.services.detection_service import initialize_detection_services

        pipeline, hairnet_pipeline = initialize_detection_services()
        request.app.state.optimized_pipeline = pipeline
        request.app.state.hairnet_pipeline = hairnet_pipeline
        logger.info("YOLOHairnetDetector 已惰性初始化并写入 app.state")
        return hairnet_pipeline
    except Exception as e:
        logger.error(f"初始化发网检测管道失败: {e}")
        return None


async def get_detection_app_service(
    request: Request,
) -> Optional[DetectionApplicationService]:
    """获取检测应用服务实例"""
    detection_app_service = getattr(request.app.state, "detection_app_service", None)
    if detection_app_service is not None:
        return detection_app_service

    try:
        # 获取检测管道
        pipeline = await get_optimized_pipeline(request)
        if pipeline is None:
            logger.error("检测管道未初始化，无法创建应用服务")
            return None

        # 获取领域服务
        domain_service = get_detection_service_domain()

        # 从环境变量创建保存策略
        save_policy = create_save_policy_from_env()

        # 创建应用服务
        try:
            snapshot_storage = get_service(SnapshotStorageProtocol)
        except Exception as storage_error:
            logger.error(f"获取快照存储服务失败: {storage_error}")
            snapshot_storage = None

        detection_app_service = DetectionApplicationService(
            detection_pipeline=pipeline,
            detection_domain_service=domain_service,
            snapshot_storage=snapshot_storage,
            save_policy=save_policy,
            inference_lock=getattr(request.app.state, "detection_lock", None),
            inference_semaphore=getattr(request.app.state, "detection_semaphore", None),
        )
        request.app.state.detection_app_service = detection_app_service

        logger.info(
            f"DetectionApplicationService 已初始化，保存策略: {save_policy.strategy.value}"
        )
    except Exception as e:
        logger.error(f"初始化检测应用服务失败: {e}")
        return None

    return detection_app_service
