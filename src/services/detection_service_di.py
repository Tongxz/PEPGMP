"""
使用依赖注入的检测服务
演示如何使用依赖注入容器重构现有服务
"""

import logging
import time
from typing import Optional

import numpy as np

from src.container.service_container import get_service
from src.interfaces.detection.detector_interface import DetectionResult, IDetector
from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
)
from src.interfaces.tracking.tracker_interface import ITracker

logger = logging.getLogger(__name__)


class DetectionServiceDI:
    """使用依赖注入的检测服务"""

    def __init__(self):
        """通过依赖注入获取服务"""
        self.detector: IDetector = get_service(IDetector)
        self.tracker: ITracker = get_service(ITracker)
        self.repository: IDetectionRepository = get_service(IDetectionRepository)

        logger.info("检测服务DI初始化完成")
        self._log_service_info()

    def _log_service_info(self):
        """记录服务信息"""
        logger.info(f"检测器: {self.detector.get_model_info()}")
        logger.info(f"检测器可用: {self.detector.is_available()}")
        logger.info(f"跟踪器轨迹数: {self.tracker.get_track_count()}")

    async def process_image(
        self, image: np.ndarray, camera_id: str, frame_id: Optional[int] = None
    ) -> DetectionResult:
        """
        处理图像 - 使用依赖注入的服务

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
            logger.debug(f"开始检测图像，摄像头: {camera_id}")
            detection_result = await self.detector.detect(image)
            detection_result.frame_id = frame_id

            # 2. 跟踪
            if detection_result.objects:
                logger.debug(f"开始跟踪 {len(detection_result.objects)} 个对象")
                tracking_result = await self.tracker.track(
                    [obj.__dict__ for obj in detection_result.objects], image
                )

                # 将跟踪ID添加到检测对象
                for i, track in enumerate(tracking_result.tracks):
                    if i < len(detection_result.objects):
                        detection_result.objects[i].track_id = track.track_id

            # 3. 保存记录
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

    async def get_detection_history(self, camera_id: str, limit: int = 100) -> list:
        """
        获取检测历史记录

        Args:
            camera_id: 摄像头ID
            limit: 限制数量

        Returns:
            list: 检测记录列表
        """
        try:
            records = await self.repository.find_by_camera_id(camera_id, limit)
            logger.info(f"获取到 {len(records)} 条检测记录，摄像头: {camera_id}")
            return records
        except Exception as e:
            logger.error(f"获取检测历史失败，摄像头: {camera_id}, 错误: {e}")
            raise

    async def get_detection_statistics(self, camera_id: str) -> dict:
        """
        获取检测统计信息

        Args:
            camera_id: 摄像头ID

        Returns:
            dict: 统计信息
        """
        try:
            stats = await self.repository.get_statistics(camera_id=camera_id)
            logger.info(f"获取检测统计信息，摄像头: {camera_id}")
            return stats
        except Exception as e:
            logger.error(f"获取检测统计失败，摄像头: {camera_id}, 错误: {e}")
            raise

    def reset_tracker(self):
        """重置跟踪器"""
        try:
            self.tracker.reset()
            logger.info("跟踪器已重置")
        except Exception as e:
            logger.error(f"重置跟踪器失败: {e}")
            raise

    def update_detector_threshold(self, threshold: float):
        """更新检测器阈值"""
        try:
            self.detector.set_confidence_threshold(threshold)
            logger.info(f"检测器阈值已更新: {threshold}")
        except Exception as e:
            logger.error(f"更新检测器阈值失败: {e}")
            raise


# 全局服务实例（单例模式）
_detection_service_instance: Optional[DetectionServiceDI] = None


def get_detection_service() -> DetectionServiceDI:
    """
    获取检测服务实例（单例模式）

    Returns:
        DetectionServiceDI: 检测服务实例
    """
    global _detection_service_instance

    if _detection_service_instance is None:
        _detection_service_instance = DetectionServiceDI()
        logger.info("检测服务单例已创建")

    return _detection_service_instance


# 便捷函数
async def process_image_di(
    image: np.ndarray, camera_id: str, frame_id: Optional[int] = None
) -> DetectionResult:
    """
    处理图像的便捷函数

    Args:
        image: 输入图像
        camera_id: 摄像头ID
        frame_id: 帧ID（可选）

    Returns:
        DetectionResult: 检测结果
    """
    service = get_detection_service()
    return await service.process_image(image, camera_id, frame_id)
