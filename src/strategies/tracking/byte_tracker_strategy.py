"""
ByteTracker跟踪策略实现
使用ByteTracker进行多目标跟踪
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

from src.interfaces.tracking.tracker_interface import (
    ITracker,
    Track,
    TrackingError,
    TrackingResult,
)

logger = logging.getLogger(__name__)


class ByteTrackerStrategy(ITracker):
    """ByteTracker跟踪策略"""

    def __init__(
        self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3
    ):
        """
        初始化ByteTracker策略

        Args:
            max_age: 轨迹最大年龄
            min_hits: 轨迹确认所需的最小匹配次数
            iou_threshold: IoU阈值
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracker = None
        self.frame_id = 0
        self._model_loaded = False

        logger.info(f"ByteTracker策略初始化: max_age={max_age}, min_hits={min_hits}")

    def _load_model(self):
        """延迟加载模型"""
        if self._model_loaded:
            return

        try:
            from byte_tracker import BYTETracker

            logger.info("加载ByteTracker模型")
            self.tracker = BYTETracker(
                frame_rate=30,  # 假设30fps
                track_thresh=self.iou_threshold,
                track_buffer=self.max_age,
                match_thresh=self.iou_threshold,
                mot20=False,
            )

            self._model_loaded = True
            logger.info("ByteTracker模型加载成功")

        except ImportError as e:
            raise TrackingError(f"ByteTracker依赖未安装: {e}")
        except Exception as e:
            raise TrackingError(f"ByteTracker模型加载失败: {e}")

    async def track(
        self, detections: List[Dict[str, Any]], frame: np.ndarray
    ) -> TrackingResult:
        """
        跟踪检测到的对象

        Args:
            detections: 检测结果列表
            frame: 当前帧图像

        Returns:
            TrackingResult: 跟踪结果
        """
        if not self._model_loaded:
            self._load_model()

        start_time = time.time()

        try:
            # 转换检测结果为ByteTracker格式
            detections_array = self._convert_detections(detections)

            # 执行跟踪
            online_targets = self.tracker.update(detections_array, frame)

            # 解析跟踪结果
            tracks = []
            for target in online_targets:
                track = Track(
                    track_id=int(target.track_id),
                    class_id=int(target.class_id) if hasattr(target, "class_id") else 0,
                    class_name="object",  # ByteTracker不直接提供类别名称
                    bbox=target.tlwh.tolist(),  # [x, y, w, h]
                    confidence=float(target.score) if hasattr(target, "score") else 1.0,
                    age=1,  # ByteTracker内部管理年龄
                    hits=1,  # ByteTracker内部管理匹配次数
                    time_since_update=0,
                    state="confirmed" if target.track_id > 0 else "tentative",
                )
                tracks.append(track)

            self.frame_id += 1
            processing_time = time.time() - start_time

            result = TrackingResult(
                tracks=tracks,
                frame_id=self.frame_id,
                processing_time=processing_time,
                timestamp=datetime.now(),
            )

            logger.debug(
                f"ByteTracker跟踪完成: {len(tracks)}个轨迹, 耗时: {processing_time:.3f}s"
            )
            return result

        except Exception as e:
            logger.error(f"ByteTracker跟踪失败: {e}")
            raise TrackingError(f"ByteTracker跟踪失败: {e}")

    def _convert_detections(self, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        转换检测结果为ByteTracker格式

        Args:
            detections: 检测结果列表

        Returns:
            np.ndarray: ByteTracker格式的检测结果
        """
        if not detections:
            return np.empty((0, 5))

        detections_array = []
        for det in detections:
            # 假设检测结果包含bbox和confidence
            bbox = det.get("bbox", [0, 0, 0, 0])
            confidence = det.get("confidence", 0.0)

            # 转换bbox格式: [x1, y1, x2, y2] -> [x, y, w, h]
            x1, y1, x2, y2 = bbox
            x, y, w, h = x1, y1, x2 - x1, y2 - y1

            detections_array.append([x, y, w, h, confidence])

        return np.array(detections_array)

    def reset(self) -> None:
        """重置跟踪器状态"""
        self.frame_id = 0
        if self.tracker:
            # ByteTracker没有直接的reset方法，重新创建实例
            self._model_loaded = False
            self._load_model()
        logger.info("ByteTracker已重置")

    def get_track_count(self) -> int:
        """获取当前跟踪的轨迹数量"""
        if not self.tracker:
            return 0

        # ByteTracker没有直接的方法获取轨迹数量
        # 这里返回一个估计值
        return len(getattr(self.tracker, "tracked_stracks", []))

    def get_track_statistics(self) -> Dict[str, Any]:
        """获取跟踪统计信息"""
        return {
            "tracker_type": "ByteTracker",
            "max_age": self.max_age,
            "min_hits": self.min_hits,
            "iou_threshold": self.iou_threshold,
            "frame_id": self.frame_id,
            "track_count": self.get_track_count(),
            "model_loaded": self._model_loaded,
        }

    def set_max_age(self, max_age: int) -> None:
        """设置轨迹最大年龄"""
        self.max_age = max_age
        logger.info(f"ByteTracker最大年龄已更新: {max_age}")

    def set_min_hits(self, min_hits: int) -> None:
        """设置轨迹确认所需的最小匹配次数"""
        self.min_hits = min_hits
        logger.info(f"ByteTracker最小匹配次数已更新: {min_hits}")
