"""
使用仓储模式的检测服务
演示如何使用仓储模式重构现有服务
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
)
from src.strategies.detection.detector_factory import DetectorFactory
from src.strategies.tracking.tracker_factory import TrackerFactory

logger = logging.getLogger(__name__)


class DetectionServiceRepository:
    """使用仓储模式的检测服务"""

    def __init__(
        self,
        repository_type: str = "postgresql",
        detector_type: str = "yolo",
        tracker_type: str = "simple_tracker",
        repository_config: Optional[Dict[str, Any]] = None,
        detector_config: Optional[Dict[str, Any]] = None,
        tracker_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化检测服务

        Args:
            repository_type: 仓储类型
            detector_type: 检测器类型
            tracker_type: 跟踪器类型
            repository_config: 仓储配置
            detector_config: 检测器配置
            tracker_config: 跟踪器配置
        """
        self.repository_type = repository_type
        self.detector_type = detector_type
        self.tracker_type = tracker_type

        # 默认配置
        default_repository_config = repository_config or {}
        default_detector_config = detector_config or {}
        default_tracker_config = tracker_config or {}

        # 创建仓储
        self.repository: IDetectionRepository = RepositoryFactory.create_repository(
            repository_type, **default_repository_config
        )

        # 创建检测器策略
        self.detector = DetectorFactory.create_detector(
            detector_type, **default_detector_config
        )

        # 创建跟踪器策略
        self.tracker = TrackerFactory.create_tracker(
            tracker_type, **default_tracker_config
        )

        logger.info(
            f"检测服务仓储模式初始化完成: {repository_type} + {detector_type} + {tracker_type}"
        )
        self._log_service_info()

    def _log_service_info(self):
        """记录服务信息"""
        detector_info = self.detector.get_model_info()
        tracker_stats = self.tracker.get_track_statistics()

        logger.info(f"仓储: {self.repository_type}")
        logger.info(f"检测器: {detector_info['type']}, 可用: {self.detector.is_available()}")
        logger.info(
            f"跟踪器: {tracker_stats['tracker_type']}, 轨迹数: {self.tracker.get_track_count()}"
        )

    async def process_image(
        self, image: np.ndarray, camera_id: str, frame_id: Optional[int] = None
    ) -> DetectionRecord:
        """
        处理图像 - 使用仓储模式

        Args:
            image: 输入图像
            camera_id: 摄像头ID
            frame_id: 帧ID（可选）

        Returns:
            DetectionRecord: 检测记录
        """
        start_time = time.time()

        try:
            # 1. 检测
            logger.debug(f"开始检测图像，摄像头: {camera_id}, 检测器: {self.detector_type}")
            detection_result = await self.detector.detect(image)

            # 2. 跟踪
            if detection_result.objects:
                logger.debug(
                    f"开始跟踪 {len(detection_result.objects)} 个对象，跟踪器: {self.tracker_type}"
                )
                tracking_result = await self.tracker.track(
                    [obj.__dict__ for obj in detection_result.objects], image
                )

                # 将跟踪ID添加到检测对象
                for i, track in enumerate(tracking_result.tracks):
                    if i < len(detection_result.objects):
                        detection_result.objects[i].track_id = track.track_id

            # 3. 创建检测记录
            record = DetectionRecord(
                id=f"{camera_id}_{int(time.time() * 1000)}",
                camera_id=camera_id,
                objects=[obj.__dict__ for obj in detection_result.objects],
                timestamp=detection_result.timestamp or time.time(),
                confidence=detection_result.confidence_score,
                processing_time=detection_result.processing_time,
                frame_id=frame_id,
            )

            # 4. 保存记录
            await self.repository.save(record)
            logger.debug(f"检测记录已保存: {record.id}")

            # 5. 记录处理时间
            total_time = time.time() - start_time
            logger.info(
                f"图像处理完成，摄像头: {camera_id}, 对象数: {len(detection_result.objects)}, 总时间: {total_time:.3f}s"
            )

            return record

        except Exception as e:
            logger.error(f"图像处理失败，摄像头: {camera_id}, 错误: {e}")
            raise

    async def get_detection_records(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DetectionRecord]:
        """
        获取检测记录

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 限制数量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """
        try:
            if start_time and end_time:
                records = await self.repository.find_by_time_range(
                    start_time, end_time, camera_id, limit
                )
            elif camera_id:
                records = await self.repository.find_by_camera_id(camera_id, limit)
            else:
                # 获取最近的记录
                records = await self.repository.find_by_time_range(
                    datetime.now() - timedelta(hours=1), datetime.now(), None, limit
                )

            logger.debug(f"获取检测记录: {len(records)}条")
            return records

        except Exception as e:
            logger.error(f"获取检测记录失败: {e}")
            raise

    async def get_detection_statistics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取检测统计信息

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = await self.repository.get_statistics(
                camera_id, start_time, end_time
            )

            # 添加检测器和跟踪器统计
            detector_info = self.detector.get_model_info()
            tracker_stats = self.tracker.get_track_statistics()

            stats.update(
                {
                    "detector": {
                        "type": detector_info["type"],
                        "available": self.detector.is_available(),
                        "confidence_threshold": self.detector.get_confidence_threshold(),
                    },
                    "tracker": {
                        "type": tracker_stats["tracker_type"],
                        "track_count": self.tracker.get_track_count(),
                    },
                    "repository": {"type": self.repository_type},
                }
            )

            logger.debug(f"获取检测统计信息: {stats}")
            return stats

        except Exception as e:
            logger.error(f"获取检测统计信息失败: {e}")
            raise

    def switch_repository(self, repository_type: str, **config) -> None:
        """
        切换仓储策略

        Args:
            repository_type: 新的仓储类型
            **config: 仓储配置
        """
        try:
            old_type = self.repository_type
            self.repository = RepositoryFactory.create_repository(
                repository_type, **config
            )
            self.repository_type = repository_type

            logger.info(f"仓储已切换: {old_type} -> {repository_type}")
        except Exception as e:
            logger.error(f"切换仓储失败: {e}")
            raise

    def switch_detector(self, detector_type: str, **config) -> None:
        """
        切换检测器策略

        Args:
            detector_type: 新的检测器类型
            **config: 检测器配置
        """
        try:
            old_type = self.detector_type
            self.detector = DetectorFactory.create_detector(detector_type, **config)
            self.detector_type = detector_type

            logger.info(f"检测器已切换: {old_type} -> {detector_type}")
        except Exception as e:
            logger.error(f"切换检测器失败: {e}")
            raise

    def switch_tracker(self, tracker_type: str, **config) -> None:
        """
        切换跟踪器策略

        Args:
            tracker_type: 新的跟踪器类型
            **config: 跟踪器配置
        """
        try:
            old_type = self.tracker_type
            self.tracker = TrackerFactory.create_tracker(tracker_type, **config)
            self.tracker_type = tracker_type

            logger.info(f"跟踪器已切换: {old_type} -> {tracker_type}")
        except Exception as e:
            logger.error(f"切换跟踪器失败: {e}")
            raise

    def get_available_repositories(self) -> List[str]:
        """获取可用的仓储列表"""
        return RepositoryFactory.get_available_repositories()

    def get_available_detectors(self) -> List[str]:
        """获取可用的检测器列表"""
        return DetectorFactory.get_available_detectors()

    def get_available_trackers(self) -> List[str]:
        """获取可用的跟踪器列表"""
        return TrackerFactory.get_available_trackers()

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "repository": {
                "type": self.repository_type,
                "available": True,  # 假设仓储总是可用的
            },
            "detector": {
                "type": self.detector_type,
                "available": self.detector.is_available(),
                "info": self.detector.get_model_info(),
            },
            "tracker": {
                "type": self.tracker_type,
                "track_count": self.tracker.get_track_count(),
                "stats": self.tracker.get_track_statistics(),
            },
        }

    async def close(self):
        """关闭服务连接"""
        try:
            if hasattr(self.repository, "close"):
                await self.repository.close()
            logger.info("检测服务仓储模式已关闭")
        except Exception as e:
            logger.warning(f"关闭检测服务时出错: {e}")


# 全局服务实例（单例模式）
_detection_service_repository_instance: Optional[DetectionServiceRepository] = None


def get_detection_service_repository() -> DetectionServiceRepository:
    """
    获取检测服务仓储模式实例（单例模式）

    Returns:
        DetectionServiceRepository: 检测服务仓储模式实例
    """
    global _detection_service_repository_instance

    if _detection_service_repository_instance is None:
        _detection_service_repository_instance = DetectionServiceRepository()
        logger.info("检测服务仓储模式单例已创建")

    return _detection_service_repository_instance


# 便捷函数
async def process_image_repository(
    image: np.ndarray,
    camera_id: str,
    frame_id: Optional[int] = None,
    repository_type: str = "postgresql",
    detector_type: str = "yolo",
    tracker_type: str = "simple_tracker",
) -> DetectionRecord:
    """
    处理图像的便捷函数

    Args:
        image: 输入图像
        camera_id: 摄像头ID
        frame_id: 帧ID（可选）
        repository_type: 仓储类型
        detector_type: 检测器类型
        tracker_type: 跟踪器类型

    Returns:
        DetectionRecord: 检测记录
    """
    service = DetectionServiceRepository(
        repository_type=repository_type,
        detector_type=detector_type,
        tracker_type=tracker_type,
    )
    return await service.process_image(image, camera_id, frame_id)
