"""
同步缓存

负责：
1. 基于时间戳的帧同步
2. 队列缓存管理
3. 多模型结果聚合
4. 与FrameMetadataManager集成
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

from src.core.frame_metadata import FrameMetadata
from src.core.frame_metadata_manager import FrameMetadataManager

logger = logging.getLogger(__name__)


class SynchronizedCache:
    """同步缓存

    功能：
    1. 基于时间戳的帧同步：在时间窗口内匹配不同模型的检测结果
    2. 队列缓存管理：维护最近N帧的缓存
    3. 多模型结果聚合：将不同模型的检测结果聚合到同一帧
    """

    def __init__(
        self,
        max_size: int = 100,
        sync_window: float = 0.1,  # 同步时间窗口（秒）
        frame_metadata_manager: Optional[FrameMetadataManager] = None,
    ):
        """
        初始化同步缓存

        Args:
            max_size: 最大缓存大小
            sync_window: 同步时间窗口（秒）
            frame_metadata_manager: 帧元数据管理器（可选）
        """
        self.max_size = max_size
        self.sync_window = sync_window
        self.frame_metadata_manager = frame_metadata_manager or FrameMetadataManager()

        # 结果缓存：frame_id -> DetectionResult
        self.result_cache: Dict[str, Dict[str, Any]] = {}

        # 时间戳索引：timestamp -> [frame_ids]
        self.timestamp_index: Dict[datetime, List[str]] = {}

        # 队列缓存（LRU）
        self.cache_queue: deque = deque(maxlen=max_size)

        # 线程安全
        self.lock = Lock()

        logger.info(
            f"SynchronizedCache initialized: max_size={max_size}, "
            f"sync_window={sync_window}"
        )

    def add_detection_result(
        self,
        frame_meta: FrameMetadata,
        detection_type: str,  # 'person', 'hairnet', 'pose', 'handwash', 'sanitize'
        detection_result: Any,
    ):
        """
        添加检测结果

        Args:
            frame_meta: 帧元数据
            detection_type: 检测类型
            detection_result: 检测结果
        """
        with self.lock:
            frame_id = frame_meta.frame_id

            # 确保FrameMetadata在FrameMetadataManager中注册
            if frame_id not in self.frame_metadata_manager.frame_index:
                # 直接添加到索引（不通过create_frame_metadata，避免重复创建）
                with self.frame_metadata_manager.lock:
                    self.frame_metadata_manager.frame_index[frame_id] = frame_meta
                    self.frame_metadata_manager.history.append(frame_meta)

                    # 时间戳索引
                    timestamp_key = self.frame_metadata_manager._round_timestamp(
                        frame_meta.timestamp
                    )
                    if timestamp_key not in self.frame_metadata_manager.timestamp_index:
                        self.frame_metadata_manager.timestamp_index[timestamp_key] = []
                    self.frame_metadata_manager.timestamp_index[timestamp_key].append(
                        frame_id
                    )

                    # 摄像头索引
                    camera_id = frame_meta.camera_id
                    if camera_id not in self.frame_metadata_manager.camera_index:
                        self.frame_metadata_manager.camera_index[camera_id] = []
                    self.frame_metadata_manager.camera_index[camera_id].append(frame_id)

            # 初始化缓存条目（如果不存在）
            if frame_id not in self.result_cache:
                self.result_cache[frame_id] = {
                    "frame_meta": frame_meta,
                    "results": {},
                    "timestamp": frame_meta.timestamp,
                }
                self.cache_queue.append(frame_id)

            # 添加检测结果
            self.result_cache[frame_id]["results"][detection_type] = detection_result

            # 更新时间戳索引
            timestamp_key = self._round_timestamp(frame_meta.timestamp)
            if timestamp_key not in self.timestamp_index:
                self.timestamp_index[timestamp_key] = []
            if frame_id not in self.timestamp_index[timestamp_key]:
                self.timestamp_index[timestamp_key].append(frame_id)

            logger.debug(
                f"Added detection result: frame_id={frame_id}, "
                f"type={detection_type}"
            )

    def get_synchronized_result(
        self,
        timestamp: datetime,
        camera_id: Optional[str] = None,
    ) -> Optional[FrameMetadata]:
        """
        获取同步的检测结果

        在时间窗口内查找匹配的帧，并聚合所有检测结果

        Args:
            timestamp: 目标时间戳
            camera_id: 摄像头ID（可选）

        Returns:
            聚合后的FrameMetadata，如果未找到则返回None
        """
        with self.lock:
            # 查找时间窗口内的所有帧
            matching_frames = self._find_frames_in_window(timestamp, camera_id)

            if not matching_frames:
                return None

            # 选择最接近时间戳的帧
            best_frame_id = min(
                matching_frames,
                key=lambda fid: abs(
                    (self.result_cache[fid]["timestamp"] - timestamp).total_seconds()
                ),
            )

            # 获取该帧的所有检测结果
            cache_entry = self.result_cache.get(best_frame_id)
            if not cache_entry:
                return None

            frame_meta = cache_entry["frame_meta"]
            results = cache_entry["results"]

            # 聚合所有检测结果到FrameMetadata
            # 如果frame_meta不在FrameMetadataManager中，先注册它
            if frame_meta.frame_id not in self.frame_metadata_manager.frame_index:
                # 直接使用frame_meta，不通过manager创建（避免重复）
                pass

            # 更新检测结果
            aggregated_meta = self.frame_metadata_manager.update_detection_results(
                frame_meta.frame_id,
                person_detections=results.get("person", []),
                hairnet_results=results.get("hairnet", []),
                pose_detections=results.get("pose", []),
                handwash_results=results.get("handwash", []),
                sanitize_results=results.get("sanitize", []),
            )

            # 如果update_detection_results返回None（frame_id不存在），直接构建新的FrameMetadata
            if aggregated_meta is None:
                # 创建新的FrameMetadata，合并所有检测结果
                from src.core.frame_metadata import FrameMetadata

                aggregated_meta = FrameMetadata(
                    frame_id=frame_meta.frame_id,
                    timestamp=frame_meta.timestamp,
                    camera_id=frame_meta.camera_id,
                    source=frame_meta.source,
                    frame=frame_meta.frame,
                    frame_hash=frame_meta.frame_hash,
                    person_detections=results.get("person", []),
                    hairnet_results=results.get("hairnet", []),
                    pose_detections=results.get("pose", []),
                    handwash_results=results.get("handwash", []),
                    sanitize_results=results.get("sanitize", []),
                    processing_times=frame_meta.processing_times.copy(),
                )

            return aggregated_meta

    def _find_frames_in_window(
        self,
        timestamp: datetime,
        camera_id: Optional[str] = None,
    ) -> List[str]:
        """在时间窗口内查找匹配的帧"""
        matching_frames = []

        # 计算时间窗口
        window_start = timestamp - timedelta(seconds=self.sync_window)
        window_end = timestamp + timedelta(seconds=self.sync_window)

        # 遍历时间戳索引
        for ts_key, frame_ids in self.timestamp_index.items():
            if window_start <= ts_key <= window_end:
                for frame_id in frame_ids:
                    cache_entry = self.result_cache.get(frame_id)
                    if cache_entry:
                        frame_meta = cache_entry["frame_meta"]
                        # 检查摄像头ID（如果提供）
                        if camera_id is None or frame_meta.camera_id == camera_id:
                            matching_frames.append(frame_id)

        return matching_frames

    def _round_timestamp(self, timestamp: datetime) -> datetime:
        """将时间戳四舍五入到同步窗口"""
        seconds = timestamp.timestamp()
        rounded = round(seconds / self.sync_window) * self.sync_window
        return datetime.fromtimestamp(rounded)

    def clear_cache(self, camera_id: Optional[str] = None):
        """清理缓存"""
        with self.lock:
            if camera_id:
                # 清理特定摄像头的缓存
                to_remove = []
                for frame_id, cache_entry in self.result_cache.items():
                    frame_meta = cache_entry["frame_meta"]
                    if frame_meta.camera_id == camera_id:
                        to_remove.append(frame_id)

                for frame_id in to_remove:
                    del self.result_cache[frame_id]
                    # 从时间戳索引中移除
                    for ts_key, frame_ids in list(self.timestamp_index.items()):
                        if frame_id in frame_ids:
                            frame_ids.remove(frame_id)
                            if not frame_ids:
                                del self.timestamp_index[ts_key]
            else:
                # 清理所有缓存
                self.result_cache.clear()
                self.timestamp_index.clear()
                self.cache_queue.clear()

        logger.info(f"Cleared cache for camera_id={camera_id or 'all'}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            return {
                "cached_frames": len(self.result_cache),
                "queue_size": len(self.cache_queue),
                "timestamp_keys": len(self.timestamp_index),
                "max_size": self.max_size,
                "sync_window": self.sync_window,
            }
