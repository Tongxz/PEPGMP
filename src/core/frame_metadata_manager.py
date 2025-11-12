"""
帧元数据管理器

负责：
1. 生成和管理帧ID
2. 维护帧元数据索引
3. 确保时间戳同步
4. 支持异步处理（线程安全）
"""

import hashlib
import logging
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

import numpy as np

from src.core.frame_metadata import FrameMetadata, FrameSource

logger = logging.getLogger(__name__)


class FrameMetadataManager:
    """帧元数据管理器

    负责：
    1. 生成和管理帧ID
    2. 维护帧元数据索引
    3. 确保时间戳同步
    4. 支持异步处理（线程安全）
    """

    def __init__(
        self,
        max_history: int = 1000,  # 最大历史记录数
        sync_window: float = 0.1,  # 同步时间窗口（秒）
    ):
        self.max_history = max_history
        self.sync_window = sync_window

        # 索引结构
        self.frame_index: Dict[str, FrameMetadata] = {}  # frame_id -> FrameMetadata
        self.timestamp_index: Dict[datetime, List[str]] = {}  # timestamp -> [frame_ids]
        self.camera_index: Dict[str, List[str]] = {}  # camera_id -> [frame_ids]

        # 历史记录（LRU）
        self.history: deque = deque(maxlen=max_history)

        # 线程安全
        self.lock = Lock()

        # 帧ID生成器
        self.frame_counter: Dict[str, int] = {}  # camera_id -> counter

        logger.info(
            f"FrameMetadataManager initialized: max_history={max_history}, "
            f"sync_window={sync_window}"
        )

    def create_frame_metadata(
        self,
        frame: np.ndarray,
        camera_id: str,
        source: FrameSource = FrameSource.REALTIME_STREAM,
        timestamp: Optional[datetime] = None,
    ) -> FrameMetadata:
        """创建帧元数据"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # 生成唯一帧ID
        with self.lock:
            if camera_id not in self.frame_counter:
                self.frame_counter[camera_id] = 0
            self.frame_counter[camera_id] += 1

            frame_id = (
                f"{camera_id}_{self.frame_counter[camera_id]}_"
                f"{timestamp.timestamp():.6f}"
            )

        # 生成帧哈希
        frame_hash = self._generate_frame_hash(frame)

        # 创建帧元数据
        frame_meta = FrameMetadata(
            frame_id=frame_id,
            timestamp=timestamp,
            camera_id=camera_id,
            source=source,
            frame=frame,  # 可选：可以只保存哈希，不保存完整帧
            frame_hash=frame_hash,
        )

        # 添加到索引
        with self.lock:
            self.frame_index[frame_id] = frame_meta
            self.history.append(frame_meta)

            # 时间戳索引（使用时间窗口）
            timestamp_key = self._round_timestamp(timestamp)
            if timestamp_key not in self.timestamp_index:
                self.timestamp_index[timestamp_key] = []
            self.timestamp_index[timestamp_key].append(frame_id)

            # 摄像头索引
            if camera_id not in self.camera_index:
                self.camera_index[camera_id] = []
            self.camera_index[camera_id].append(frame_id)

        logger.debug(
            f"Created FrameMetadata: frame_id={frame_id}, camera_id={camera_id}"
        )
        return frame_meta

    def update_detection_results(
        self,
        frame_id: str,
        person_detections: Optional[List[Dict]] = None,
        hairnet_results: Optional[List[Dict]] = None,
        pose_detections: Optional[List[Dict]] = None,
        handwash_results: Optional[List[Dict]] = None,
        sanitize_results: Optional[List[Dict]] = None,
    ) -> Optional[FrameMetadata]:
        """更新检测结果"""
        with self.lock:
            if frame_id not in self.frame_index:
                logger.warning(f"Frame {frame_id} not found in index")
                return None

            old_meta = self.frame_index[frame_id]
            new_meta = old_meta.with_detection_results(
                person_detections=person_detections,
                hairnet_results=hairnet_results,
                pose_detections=pose_detections,
                handwash_results=handwash_results,
                sanitize_results=sanitize_results,
            )

            # 更新索引
            self.frame_index[frame_id] = new_meta

            # 更新历史记录
            for i, meta in enumerate(self.history):
                if meta.frame_id == frame_id:
                    self.history[i] = new_meta
                    break

        logger.debug(f"Updated detection results for frame_id={frame_id}")
        return new_meta

    def update_state(
        self,
        frame_id: str,
        detection_state: str,
        state_confidence: float,
    ) -> Optional[FrameMetadata]:
        """更新状态信息"""
        with self.lock:
            if frame_id not in self.frame_index:
                logger.warning(f"Frame {frame_id} not found in index")
                return None

            old_meta = self.frame_index[frame_id]
            new_meta = old_meta.with_state(
                detection_state=detection_state,
                state_confidence=state_confidence,
            )

            self.frame_index[frame_id] = new_meta

            # 更新历史记录
            for i, meta in enumerate(self.history):
                if meta.frame_id == frame_id:
                    self.history[i] = new_meta
                    break

        logger.debug(
            f"Updated state for frame_id={frame_id}: "
            f"state={detection_state}, confidence={state_confidence:.3f}"
        )
        return new_meta

    def update_processing_stage(
        self,
        frame_id: str,
        processing_stage: str,
    ) -> Optional[FrameMetadata]:
        """更新处理阶段"""
        with self.lock:
            if frame_id not in self.frame_index:
                logger.warning(f"Frame {frame_id} not found in index")
                return None

            old_meta = self.frame_index[frame_id]
            new_meta = old_meta.with_processing_stage(processing_stage)

            self.frame_index[frame_id] = new_meta

            # 更新历史记录
            for i, meta in enumerate(self.history):
                if meta.frame_id == frame_id:
                    self.history[i] = new_meta
                    break

        return new_meta

    def get_frame_metadata(self, frame_id: str) -> Optional[FrameMetadata]:
        """根据frame_id获取帧元数据"""
        with self.lock:
            return self.frame_index.get(frame_id)

    def get_frames_by_timestamp_range(
        self,
        start: datetime,
        end: datetime,
        camera_id: Optional[str] = None,
    ) -> List[FrameMetadata]:
        """根据时间范围获取帧元数据"""
        result = []

        with self.lock:
            # 遍历时间戳索引
            for timestamp_key, frame_ids in self.timestamp_index.items():
                if start <= timestamp_key <= end:
                    for frame_id in frame_ids:
                        frame_meta = self.frame_index.get(frame_id)
                        if frame_meta:
                            if camera_id is None or frame_meta.camera_id == camera_id:
                                result.append(frame_meta)

        # 按时间戳排序
        result.sort(key=lambda x: x.timestamp)
        return result

    def get_frames_by_camera(
        self,
        camera_id: str,
        limit: Optional[int] = None,
    ) -> List[FrameMetadata]:
        """根据摄像头ID获取帧元数据"""
        result = []

        with self.lock:
            frame_ids = self.camera_index.get(camera_id, [])
            if limit:
                frame_ids = frame_ids[-limit:]  # 取最近的N个

            for frame_id in frame_ids:
                frame_meta = self.frame_index.get(frame_id)
                if frame_meta:
                    result.append(frame_meta)

        # 按时间戳排序
        result.sort(key=lambda x: x.timestamp)
        return result

    def _generate_frame_hash(self, frame: np.ndarray) -> str:
        """生成帧哈希值"""
        try:
            h, w = frame.shape[:2]
            # 采样像素点（避免计算整个帧的哈希）
            sample_pixels = frame[:: max(h // 10, 1), :: max(w // 10, 1)].flatten()[
                :100
            ]
            hash_obj = hashlib.md5(sample_pixels.tobytes(), usedforsecurity=False)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to generate frame hash: {e}")
            return ""

    def _round_timestamp(self, timestamp: datetime) -> datetime:
        """将时间戳四舍五入到同步窗口"""
        # 将时间戳四舍五入到最近的sync_window秒
        seconds = timestamp.timestamp()
        rounded = round(seconds / self.sync_window) * self.sync_window
        return datetime.fromtimestamp(rounded)

    def clear_history(self, camera_id: Optional[str] = None):
        """清理历史记录"""
        with self.lock:
            if camera_id:
                # 清理特定摄像头的历史
                frame_ids = self.camera_index.get(camera_id, [])
                for frame_id in frame_ids:
                    self.frame_index.pop(frame_id, None)
                    # 从时间戳索引中移除
                    for timestamp_key, ids in list(self.timestamp_index.items()):
                        if frame_id in ids:
                            ids.remove(frame_id)
                            if not ids:
                                del self.timestamp_index[timestamp_key]
                self.camera_index[camera_id] = []
            else:
                # 清理所有历史
                self.frame_index.clear()
                self.timestamp_index.clear()
                self.camera_index.clear()
                self.history.clear()

        logger.info(f"Cleared history for camera_id={camera_id or 'all'}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                "total_frames": len(self.frame_index),
                "history_size": len(self.history),
                "cameras": len(self.camera_index),
                "timestamp_keys": len(self.timestamp_index),
                "frame_counters": dict(self.frame_counter),
            }
