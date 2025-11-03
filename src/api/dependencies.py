"""
API依赖注入

提供API路由所需的依赖项
"""

import logging
from typing import Optional

from src.application.detection_application_service import (
    DetectionApplicationService,
    create_save_policy_from_env,
)
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector
from src.services.detection_service_domain import get_detection_service_domain

logger = logging.getLogger(__name__)

# 全局实例（单例）
_optimized_pipeline: Optional[OptimizedDetectionPipeline] = None
_hairnet_pipeline: Optional[YOLOHairnetDetector] = None
_detection_app_service: Optional[DetectionApplicationService] = None


async def get_optimized_pipeline() -> Optional[OptimizedDetectionPipeline]:
    """获取优化检测管道实例"""
    global _optimized_pipeline

    if _optimized_pipeline is None:
        try:
            from src.services.detection_service import initialize_detection_services

            initialize_detection_services()
            # 假设 initialize_detection_services 设置了全局变量
            from src.services.detection_service import optimized_pipeline

            _optimized_pipeline = optimized_pipeline
            logger.info("OptimizedDetectionPipeline 已初始化")
        except Exception as e:
            logger.error(f"初始化检测管道失败: {e}")
            return None

    return _optimized_pipeline


async def get_hairnet_pipeline() -> Optional[YOLOHairnetDetector]:
    """获取发网检测管道实例"""
    global _hairnet_pipeline

    if _hairnet_pipeline is None:
        try:
            from src.services.detection_service import initialize_detection_services

            initialize_detection_services()
            from src.services.detection_service import hairnet_pipeline

            _hairnet_pipeline = hairnet_pipeline
            logger.info("YOLOHairnetDetector 已初始化")
        except Exception as e:
            logger.error(f"初始化发网检测管道失败: {e}")
            return None

    return _hairnet_pipeline


async def get_detection_app_service() -> Optional[DetectionApplicationService]:
    """获取检测应用服务实例"""
    global _detection_app_service

    if _detection_app_service is None:
        try:
            # 获取检测管道
            pipeline = await get_optimized_pipeline()
            if pipeline is None:
                logger.error("检测管道未初始化，无法创建应用服务")
                return None

            # 获取领域服务
            domain_service = get_detection_service_domain()

            # 从环境变量创建保存策略
            save_policy = create_save_policy_from_env()

            # 创建应用服务
            _detection_app_service = DetectionApplicationService(
                detection_pipeline=pipeline,
                detection_domain_service=domain_service,
                save_policy=save_policy,
            )

            logger.info(
                f"DetectionApplicationService 已初始化，保存策略: {save_policy.strategy.value}"
            )
        except Exception as e:
            logger.error(f"初始化检测应用服务失败: {e}")
            return None

    return _detection_app_service
