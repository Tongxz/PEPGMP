"""
服务配置
配置所有服务的依赖注入
"""

import logging
import os

from src.container.service_container import container
from src.interfaces.detection.detector_interface import IDetector
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)
from src.interfaces.tracking.tracker_interface import ITracker
from src.infrastructure.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


def configure_services():
    """配置所有服务"""
    logger.info("开始配置服务...")
    use_domain_service = os.getenv("USE_DOMAIN_SERVICE", "false").lower() == "true"
    logger.info(f"USE_DOMAIN_SERVICE={use_domain_service}")

    try:
        # 注册检测器服务
        _configure_detector_services()

        # 注册跟踪器服务
        _configure_tracker_services()

        # 注册仓储服务
        _configure_repository_services()

        # 注册其他服务
        _configure_other_services()

        logger.info("服务配置完成")
        _log_registered_services()

    except Exception as e:
        logger.error(f"服务配置失败: {e}")
        raise


def _configure_detector_services():
    """配置检测器服务"""
    try:
        # 尝试导入检测器实现
        from src.detection.detector import HumanDetector

        # 注册人体检测器
        container.register_singleton(IDetector, HumanDetector)
        logger.info("人体检测器服务已注册")

    except ImportError as e:
        logger.warning(f"检测器服务导入失败: {e}")
        # 注册一个默认的检测器实现
        from src.interfaces.detection.detector_interface import DetectionError

        class DefaultDetector(IDetector):
            def __init__(self):
                self._confidence_threshold = 0.5
                self._supported_classes = ["person", "object"]

            async def detect(self, image):
                raise DetectionError("检测器未正确配置")

            def get_model_info(self):
                return {"type": "default", "status": "not_configured"}

            def is_available(self):
                return False

            def get_supported_classes(self):
                return self._supported_classes

            def set_confidence_threshold(self, threshold: float):
                self._confidence_threshold = threshold

            def get_confidence_threshold(self):
                return self._confidence_threshold

        container.register_singleton(IDetector, DefaultDetector)
        logger.warning("使用默认检测器实现")


def _configure_tracker_services():
    """配置跟踪器服务"""
    try:
        from src.core.tracker import MultiObjectTracker

        # 注册多目标跟踪器
        container.register_singleton(ITracker, MultiObjectTracker)
        logger.info("多目标跟踪器服务已注册")

    except ImportError as e:
        logger.warning(f"跟踪器服务导入失败: {e}")
        # 注册一个默认的跟踪器实现

        class DefaultTracker(ITracker):
            def __init__(self):
                self._track_count = 0

            async def track(self, detections, frame):
                from src.interfaces.tracking.tracker_interface import TrackingResult

                return TrackingResult(tracks=[], frame_id=0, processing_time=0.0)

            def reset(self):
                self._track_count = 0

            def get_track_count(self):
                return self._track_count

            def get_track_statistics(self):
                return {"total_tracks": self._track_count}

            def set_max_age(self, max_age: int):
                pass

            def set_min_hits(self, min_hits: int):
                pass

        container.register_singleton(ITracker, DefaultTracker)
        logger.warning("使用默认跟踪器实现")


def _configure_repository_services():
    """配置仓储服务"""
    try:
        # 通过工厂按配置创建仓储实现（postgresql|redis|hybrid）
        repo = RepositoryFactory.create_repository_from_env()
        container.register_instance(IDetectionRepository, repo)
        logger.info(
            f"检测记录仓储服务已注册: {repo.__class__.__name__}"
        )

    except ImportError as e:
        logger.warning(f"仓储服务导入失败: {e}")
        # 注册一个默认的仓储实现

        class DefaultRepository(IDetectionRepository):
            def __init__(self):
                self._records = {}

            async def save(self, record):
                self._records[record.id] = record
                return record.id

            async def find_by_id(self, record_id):
                return self._records.get(record_id)

            async def find_by_camera_id(self, camera_id, limit=100, offset=0):
                records = [
                    r for r in self._records.values() if r.camera_id == camera_id
                ]
                return records[offset : offset + limit]

            async def find_by_time_range(
                self, start_time, end_time, camera_id=None, limit=100
            ):
                records = [
                    r
                    for r in self._records.values()
                    if start_time <= r.timestamp <= end_time
                ]
                if camera_id:
                    records = [r for r in records if r.camera_id == camera_id]
                return records[:limit]

            async def find_by_confidence_range(
                self, min_confidence, max_confidence, camera_id=None, limit=100
            ):
                records = [
                    r
                    for r in self._records.values()
                    if min_confidence <= r.confidence <= max_confidence
                ]
                if camera_id:
                    records = [r for r in records if r.camera_id == camera_id]
                return records[:limit]

            async def count_by_camera_id(self, camera_id):
                return len(
                    [r for r in self._records.values() if r.camera_id == camera_id]
                )

            async def delete_by_id(self, record_id):
                if record_id in self._records:
                    del self._records[record_id]
                    return True
                return False

            async def delete_by_camera_id(self, camera_id):
                to_delete = [
                    id for id, r in self._records.items() if r.camera_id == camera_id
                ]
                for id in to_delete:
                    del self._records[id]
                return len(to_delete)

            async def get_statistics(
                self, camera_id=None, start_time=None, end_time=None
            ):
                records = list(self._records.values())
                if camera_id:
                    records = [r for r in records if r.camera_id == camera_id]
                if start_time:
                    records = [r for r in records if r.timestamp >= start_time]
                if end_time:
                    records = [r for r in records if r.timestamp <= end_time]

                return {
                    "total_records": len(records),
                    "avg_confidence": sum(r.confidence for r in records) / len(records)
                    if records
                    else 0,
                    "avg_processing_time": sum(r.processing_time for r in records)
                    / len(records)
                    if records
                    else 0,
                }

        container.register_singleton(IDetectionRepository, DefaultRepository)
        logger.warning("使用默认仓储实现")


def _configure_other_services():
    """配置其他服务"""
    # 领域服务开关
    use_domain_service = os.getenv("USE_DOMAIN_SERVICE", "false").lower() == "true"
    if use_domain_service:
        try:
            from src.services.detection_service_domain import (
                DetectionServiceDomain,
                get_detection_service_domain,
            )

            domain_service = get_detection_service_domain()
            # 以类型为key注册实例，供API注入获取
            container.register_instance(DetectionServiceDomain, domain_service)
            logger.info("领域检测服务已启用并注册")
        except Exception as e:
            logger.error(f"注册领域检测服务失败: {e}")
    else:
        logger.info("领域检测服务未启用（USE_DOMAIN_SERVICE=false）")


def _log_registered_services():
    """记录已注册的服务"""
    services = container.get_registered_services()
    logger.info("已注册的服务:")
    for service_name, service_type in services.items():
        logger.info(f"  - {service_name}: {service_type}")


def get_configured_container():
    """获取已配置的容器"""
    return container


# 在模块导入时自动配置服务
configure_services()
