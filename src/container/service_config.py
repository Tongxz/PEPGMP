"""
服务配置
配置所有服务的依赖注入
"""

import logging
import os

from src.application.dataset_generation_service import DatasetGenerationService
from src.application.handwash_dataset_generation_service import (
    HandwashDatasetGenerationService,
)
from src.application.handwash_training_service import HandwashTrainingService
from src.application.model_registry_service import ModelRegistryService
from src.application.model_training_service import ModelTrainingService
from src.application.multi_behavior_dataset_service import (
    MultiBehaviorDatasetGenerationService,
)
from src.application.multi_behavior_training_service import MultiBehaviorTrainingService
from src.config.dataset_config import get_dataset_generation_config
from src.config.handwash_dataset_config import get_handwash_dataset_config
from src.config.handwash_training_config import get_handwash_training_config
from src.config.model_training_config import get_model_training_config
from src.config.multi_behavior_dataset_config import get_multi_behavior_dataset_config
from src.config.multi_behavior_training_config import get_multi_behavior_training_config
from src.container.service_container import container
from src.domain.repositories.handwash_session_repository import (
    IHandwashSessionRepository,
)
from src.infrastructure.pose.mediapipe_pose_extractor import (
    MediapipePoseExtractor,
    MediapipePoseExtractorConfig,
)
from src.infrastructure.repositories.file_handwash_session_repository import (
    FileHandwashSessionRepository,
)
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.interfaces.detection.detector_interface import IDetector
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)
from src.interfaces.services.pose_extractor import PoseExtractorProtocol
from src.interfaces.storage import SnapshotStorageProtocol
from src.interfaces.tracking.tracker_interface import ITracker

logger = logging.getLogger(__name__)

_STRICT_DI = False
_REQUIRED_SERVICES = set()
_SERVICE_METADATA = {}


def _normalize_service_name(service_name: str) -> str:
    return service_name.strip().lower()


def _parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_required_services_env() -> set:
    raw = os.getenv("REQUIRED_SERVICES", "")
    if not raw:
        return set()
    return {
        _normalize_service_name(item)
        for item in raw.replace(";", ",").split(",")
        if item.strip()
    }


def _load_di_config() -> None:
    global _STRICT_DI, _REQUIRED_SERVICES
    _STRICT_DI = _parse_bool_env("STRICT_DI", False)
    _REQUIRED_SERVICES = _parse_required_services_env()
    logger.info("STRICT_DI=%s", _STRICT_DI)
    if _REQUIRED_SERVICES:
        logger.info("REQUIRED_SERVICES=%s", ", ".join(sorted(_REQUIRED_SERVICES)))
    else:
        logger.info("REQUIRED_SERVICES=[]")


def _is_required_service(interface) -> bool:
    return _normalize_service_name(interface.__name__) in _REQUIRED_SERVICES


def _mark_service(interface, *, degraded: bool) -> None:
    _SERVICE_METADATA[interface.__name__] = {"degraded": degraded}


def _register_singleton(interface, implementation, *, degraded: bool = False) -> None:
    container.register_singleton(interface, implementation)
    _mark_service(interface, degraded=degraded)


def _register_instance(interface, instance, *, degraded: bool = False) -> None:
    container.register_instance(interface, instance)
    _mark_service(interface, degraded=degraded)


def _register_factory(interface, factory, *, degraded: bool = False) -> None:
    container.register_factory(interface, factory)
    _mark_service(interface, degraded=degraded)


def _register_transient(interface, implementation, *, degraded: bool = False) -> None:
    container.register_transient(interface, implementation)
    _mark_service(interface, degraded=degraded)


def _handle_fallback_or_raise(interface, error: Exception, fallback_register_fn) -> None:
    if _STRICT_DI and _is_required_service(interface):
        raise RuntimeError(
            f"服务 {interface.__name__} 为 REQUIRED_SERVICES，且 STRICT_DI=true，"
            "禁止降级注册。"
        ) from error
    fallback_register_fn()


def configure_services():
    """配置所有服务"""
    logger.info("开始配置服务...")
    _load_di_config()
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
        _register_singleton(IDetector, HumanDetector)
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

        _handle_fallback_or_raise(
            IDetector,
            e,
            lambda: _register_singleton(IDetector, DefaultDetector, degraded=True),
        )
        logger.warning("使用默认检测器实现")


def _configure_tracker_services():
    """配置跟踪器服务"""
    try:
        from src.core.tracker import MultiObjectTracker

        # 注册多目标跟踪器
        _register_singleton(ITracker, MultiObjectTracker)
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

        _handle_fallback_or_raise(
            ITracker,
            e,
            lambda: _register_singleton(ITracker, DefaultTracker, degraded=True),
        )
        logger.warning("使用默认跟踪器实现")


def _configure_repository_services():  # noqa: C901
    """配置仓储服务"""
    try:
        # 通过工厂按配置创建仓储实现（postgresql|redis|hybrid）
        repo = RepositoryFactory.create_repository_from_env()
        _register_instance(IDetectionRepository, repo)
        logger.info(f"检测记录仓储服务已注册: {repo.__class__.__name__}")

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

        _handle_fallback_or_raise(
            IDetectionRepository,
            e,
            lambda: _register_singleton(
                IDetectionRepository, DefaultRepository, degraded=True
            ),
        )
        logger.warning("使用默认仓储实现")


def _configure_other_services():
    """配置其他服务"""
    _configure_storage_services()
    _configure_dataset_services()
    _configure_model_registry_services()
    _configure_training_services()
    _configure_handwash_services()
    _configure_multi_behavior_services()
    _configure_deployment_services()

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
            _register_instance(DetectionServiceDomain, domain_service)
            logger.info("领域检测服务已启用并注册")
        except Exception as e:
            logger.error(f"注册领域检测服务失败: {e}")
    else:
        logger.info("领域检测服务未启用（USE_DOMAIN_SERVICE=false）")


def _configure_storage_services():
    """配置存储服务"""
    try:
        from src.config.storage_config import build_snapshot_storage

        snapshot_storage = build_snapshot_storage()
        _register_instance(SnapshotStorageProtocol, snapshot_storage)
        logger.info(
            "快照存储服务已注册: %s",
            snapshot_storage.__class__.__name__,
        )
    except Exception as exc:
        logger.error(f"注册快照存储服务失败: {exc}")


def _configure_dataset_services():
    """配置数据集服务"""
    try:
        detection_repository = container.get(IDetectionRepository)
        dataset_config = get_dataset_generation_config()
        dataset_service = DatasetGenerationService(
            detection_repository=detection_repository,
            config=dataset_config,
        )
        _register_instance(DatasetGenerationService, dataset_service)
        logger.info("数据集生成服务已注册")
    except Exception as exc:
        logger.error(f"注册数据集生成服务失败: {exc}")


def _configure_training_services():
    """配置模型训练服务"""
    try:
        training_config = get_model_training_config()
        model_registry_service = None
        if container.is_registered(ModelRegistryService):
            model_registry_service = container.get(ModelRegistryService)
        training_service = ModelTrainingService(
            training_config, model_registry_service=model_registry_service
        )
        _register_instance(ModelTrainingService, training_service)
        logger.info("模型训练服务已注册")
    except Exception as exc:
        logger.error(f"注册模型训练服务失败: {exc}")


def _configure_handwash_services():
    """配置洗手工作流相关服务"""
    try:
        dataset_config = get_handwash_dataset_config()
        session_repo = FileHandwashSessionRepository(dataset_config.session_base_dir)
        _register_instance(IHandwashSessionRepository, session_repo)

        pose_extractor = MediapipePoseExtractor(
            MediapipePoseExtractorConfig(
                frame_interval=dataset_config.default_frame_interval
            )
        )
        _register_instance(PoseExtractorProtocol, pose_extractor)

        handwash_dataset_service = HandwashDatasetGenerationService(
            session_repository=session_repo,
            pose_extractor=pose_extractor,
            config=dataset_config,
        )
        _register_instance(
            HandwashDatasetGenerationService, handwash_dataset_service
        )

        handwash_training_config = get_handwash_training_config()
        model_registry_service = None
        if container.is_registered(ModelRegistryService):
            model_registry_service = container.get(ModelRegistryService)
        handwash_training_service = HandwashTrainingService(
            handwash_training_config, model_registry_service=model_registry_service
        )
        _register_instance(HandwashTrainingService, handwash_training_service)
        logger.info("洗手工作流服务已注册")
    except Exception as exc:
        # 生产要求：mediapipe 必须可用，洗手服务必须成功注册；禁止“失败但继续运行”的隐性降级
        logger.error(f"注册洗手服务失败(生产必需): {exc}")
        raise RuntimeError(f"洗手服务注册失败(生产必需): {exc}") from exc


def _configure_multi_behavior_services():
    """配置多行为工作流相关服务"""
    try:
        dataset_config = get_multi_behavior_dataset_config()
        detection_repository = container.get(IDetectionRepository)
        multi_dataset_service = MultiBehaviorDatasetGenerationService(
            detection_repository=detection_repository,
            config=dataset_config,
        )
        _register_instance(
            MultiBehaviorDatasetGenerationService, multi_dataset_service
        )

        multi_training_config = get_multi_behavior_training_config()
        model_registry_service = None
        if container.is_registered(ModelRegistryService):
            model_registry_service = container.get(ModelRegistryService)
        multi_training_service = MultiBehaviorTrainingService(
            multi_training_config, model_registry_service=model_registry_service
        )
        _register_instance(
            MultiBehaviorTrainingService, multi_training_service
        )
        logger.info("多行为工作流服务已注册")
    except Exception as exc:
        logger.error(f"注册多行为服务失败: {exc}")


def _configure_model_registry_services():
    """配置模型注册服务"""
    try:
        model_registry_service = ModelRegistryService()
        _register_instance(ModelRegistryService, model_registry_service)
        logger.info("模型注册服务已注册")
    except Exception as exc:
        logger.error(f"注册模型注册服务失败: {exc}")


def _configure_deployment_services():
    """配置部署服务"""
    try:
        from src.domain.interfaces.deployment_interface import IDeploymentService
        from src.infrastructure.deployment.docker_service import DockerDeploymentService

        _register_singleton(IDeploymentService, DockerDeploymentService)
        logger.info("部署服务已注册: DockerDeploymentService")
    except ImportError as exc:
        # 生产要求：aiodocker 必须可用；禁止“导入失败但继续运行”的隐性降级
        logger.error(f"部署服务导入失败(生产必需，可能缺少 aiodocker 依赖): {exc}")
        raise RuntimeError(f"部署服务导入失败(生产必需，可能缺少 aiodocker 依赖): {exc}") from exc
    except Exception as exc:
        logger.error(f"注册部署服务失败(生产必需): {exc}")
        raise RuntimeError(f"部署服务注册失败(生产必需): {exc}") from exc


def _log_registered_services():
    """记录已注册的服务"""
    services = container.get_registered_services()
    logger.info("已注册的服务:")
    for service_name, service_type in services.items():
        degraded = _SERVICE_METADATA.get(service_name, {}).get("degraded", False)
        status = "degraded" if degraded else "available"
        logger.info(f"  - {service_name}: {service_type} ({status})")


def get_configured_container():
    """获取已配置的容器"""
    return container


# 在模块导入时自动配置服务
configure_services()
