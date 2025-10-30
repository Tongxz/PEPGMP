"""
使用策略模式的检测服务
演示如何使用策略模式重构现有服务
"""

import logging
import time
from typing import Any, Dict, Optional

import numpy as np

from src.interfaces.detection.detector_interface import DetectionResult, IDetector
from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
)
from src.interfaces.tracking.tracker_interface import ITracker
from src.strategies.detection.detector_factory import DetectorFactory
from src.strategies.tracking.tracker_factory import TrackerFactory

logger = logging.getLogger(__name__)


class DetectionServiceStrategy:
    """使用策略模式的检测服务"""

    def __init__(
        self,
        detector_type: str = "yolo",
        tracker_type: str = "simple_tracker",
        detector_config: Optional[Dict[str, Any]] = None,
        tracker_config: Optional[Dict[str, Any]] = None,
        repository: Optional[IDetectionRepository] = None,
    ):
        """
        初始化检测服务

        Args:
            detector_type: 检测器类型
            tracker_type: 跟踪器类型
            detector_config: 检测器配置
            tracker_config: 跟踪器配置
            repository: 仓储实例
        """
        self.detector_type = detector_type
        self.tracker_type = tracker_type
        self.repository = repository

        # 默认配置
        default_detector_config = detector_config or {}
        default_tracker_config = tracker_config or {}

        # 创建检测器策略
        self.detector: IDetector = DetectorFactory.create_detector(
            detector_type, **default_detector_config
        )

        # 创建跟踪器策略
        self.tracker: ITracker = TrackerFactory.create_tracker(
            tracker_type, **default_tracker_config
        )

        logger.info(f"检测服务策略初始化完成: {detector_type} + {tracker_type}")
        self._log_service_info()

    def _log_service_info(self):
        """记录服务信息"""
        detector_info = self.detector.get_model_info()
        tracker_stats = self.tracker.get_track_statistics()

        logger.info(f"检测器: {detector_info['type']}, 可用: {self.detector.is_available()}")
        logger.info(
            f"跟踪器: {tracker_stats['tracker_type']}, 轨迹数: {self.tracker.get_track_count()}"
        )

    async def process_image(
        self, image: np.ndarray, camera_id: str, frame_id: Optional[int] = None
    ) -> DetectionResult:
        """
        处理图像 - 使用策略模式

        Args:
            image: 输入图像
            camera_id: 摄像头ID
            frame_id: 帧ID（可选）

        Returns:
            DetectionResult: 检测结果
        """
        start_time = time.time()

        try:
            # 1. 检测
            logger.debug(f"开始检测图像，摄像头: {camera_id}, 检测器: {self.detector_type}")
            detection_result = await self.detector.detect(image)
            detection_result.frame_id = frame_id

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

            # 3. 保存记录（如果有仓储）
            if self.repository:
                record = DetectionRecord(
                    id=f"{camera_id}_{int(time.time() * 1000)}",
                    camera_id=camera_id,
                    objects=[obj.__dict__ for obj in detection_result.objects],
                    timestamp=detection_result.timestamp or time.time(),
                    confidence=detection_result.confidence_score,
                    processing_time=detection_result.processing_time,
                    frame_id=frame_id,
                )

                await self.repository.save(record)
                logger.debug(f"检测记录已保存: {record.id}")

            # 4. 记录处理时间
            total_time = time.time() - start_time
            logger.info(
                f"图像处理完成，摄像头: {camera_id}, 对象数: {len(detection_result.objects)}, 总时间: {total_time:.3f}s"
            )

            return detection_result

        except Exception as e:
            logger.error(f"图像处理失败，摄像头: {camera_id}, 错误: {e}")
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

    def get_available_detectors(self) -> list:
        """获取可用的检测器列表"""
        return DetectorFactory.get_available_detectors()

    def get_available_trackers(self) -> list:
        """获取可用的跟踪器列表"""
        return TrackerFactory.get_available_trackers()

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
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
            "repository": {"available": self.repository is not None},
        }

    def update_detector_threshold(self, threshold: float) -> None:
        """更新检测器阈值"""
        try:
            self.detector.set_confidence_threshold(threshold)
            logger.info(f"检测器阈值已更新: {threshold}")
        except Exception as e:
            logger.error(f"更新检测器阈值失败: {e}")
            raise

    def reset_tracker(self) -> None:
        """重置跟踪器"""
        try:
            self.tracker.reset()
            logger.info("跟踪器已重置")
        except Exception as e:
            logger.error(f"重置跟踪器失败: {e}")
            raise


# 全局服务实例（单例模式）
_detection_service_strategy_instance: Optional[DetectionServiceStrategy] = None


def get_detection_service_strategy() -> DetectionServiceStrategy:
    """
    获取检测服务策略实例（单例模式）

    Returns:
        DetectionServiceStrategy: 检测服务策略实例
    """
    global _detection_service_strategy_instance

    if _detection_service_strategy_instance is None:
        _detection_service_strategy_instance = DetectionServiceStrategy()
        logger.info("检测服务策略单例已创建")

    return _detection_service_strategy_instance


# 便捷函数
async def process_image_strategy(
    image: np.ndarray,
    camera_id: str,
    frame_id: Optional[int] = None,
    detector_type: str = "yolo",
    tracker_type: str = "simple_tracker",
) -> DetectionResult:
    """
    处理图像的便捷函数

    Args:
        image: 输入图像
        camera_id: 摄像头ID
        frame_id: 帧ID（可选）
        detector_type: 检测器类型
        tracker_type: 跟踪器类型

    Returns:
        DetectionResult: 检测结果
    """
    service = DetectionServiceStrategy(
        detector_type=detector_type, tracker_type=tracker_type
    )
    return await service.process_image(image, camera_id, frame_id)
