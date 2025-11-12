"""
帧跳检测器

负责：
1. 可配置的帧跳检测
2. 保持时序稳定性的前提下降低GPU负载
3. 智能帧选择（基于运动检测）
"""

import logging
from collections import deque
from typing import Any, Dict, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameSkipDetector:
    """帧跳检测器
    
    功能：
    1. 可配置的帧跳检测：每N帧检测一次
    2. 运动检测：基于帧差检测运动，只在有运动时检测
    3. 时序稳定性：确保检测结果在时间窗口内稳定
    """
    
    def __init__(
        self,
        skip_interval: int = 5,  # 每N帧检测一次
        motion_threshold: float = 0.01,  # 运动检测阈值
        enable_motion_detection: bool = True,  # 是否启用运动检测
        min_detection_interval: float = 0.1,  # 最小检测间隔（秒）
    ):
        """
        初始化帧跳检测器
        
        Args:
            skip_interval: 帧跳间隔（每N帧检测一次）
            motion_threshold: 运动检测阈值（0-1）
            enable_motion_detection: 是否启用运动检测
            min_detection_interval: 最小检测间隔（秒）
        """
        self.skip_interval = skip_interval
        self.motion_threshold = motion_threshold
        self.enable_motion_detection = enable_motion_detection
        self.min_detection_interval = min_detection_interval
        
        # 帧计数器（按摄像头）
        self.frame_counters: Dict[str, int] = {}
        
        # 上一帧缓存（用于运动检测）
        self.prev_frames: Dict[str, np.ndarray] = {}
        
        # 上次检测时间（按摄像头）
        self.last_detection_times: Dict[str, float] = {}
        
        # 检测历史（用于时序稳定性）
        self.detection_history: Dict[str, deque] = {}
        
        logger.info(
            f"FrameSkipDetector initialized: skip_interval={skip_interval}, "
            f"motion_threshold={motion_threshold}, "
            f"enable_motion_detection={enable_motion_detection}, "
            f"min_detection_interval={min_detection_interval}"
        )
    
    def should_detect(
        self,
        frame: np.ndarray,
        camera_id: str = "default",
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        判断是否应该进行检测
        
        Args:
            frame: 当前帧
            camera_id: 摄像头ID
            timestamp: 时间戳（可选）
        
        Returns:
            True表示应该检测，False表示跳过
        """
        # 初始化计数器
        is_first_frame = camera_id not in self.frame_counters
        if is_first_frame:
            self.frame_counters[camera_id] = 0
            self.last_detection_times[camera_id] = 0.0
            self.detection_history[camera_id] = deque(maxlen=10)
        
        self.frame_counters[camera_id] += 1
        frame_count = self.frame_counters[camera_id]
        
        # 检查最小检测间隔（第一帧总是允许检测）
        if not is_first_frame and timestamp is not None:
            time_since_last = timestamp - self.last_detection_times[camera_id]
            if time_since_last < self.min_detection_interval:
                return False
        
        # 基础帧跳检测：每N帧检测一次
        if frame_count % self.skip_interval == 0:
            # 如果启用运动检测，检查是否有运动
            if self.enable_motion_detection:
                has_motion = self._detect_motion(frame, camera_id)
                if has_motion:
                    # 有运动，进行检测
                    self.last_detection_times[camera_id] = timestamp or 0.0
                    self.detection_history[camera_id].append(True)
                    return True
                else:
                    # 无运动，跳过
                    self.detection_history[camera_id].append(False)
                    return False
            else:
                # 不启用运动检测，直接按间隔检测
                self.last_detection_times[camera_id] = timestamp or 0.0
                self.detection_history[camera_id].append(True)
                return True
        
        # 不在检测间隔内，跳过
        return False
    
    def _detect_motion(
        self,
        frame: np.ndarray,
        camera_id: str,
    ) -> bool:
        """
        检测帧间运动
        
        Args:
            frame: 当前帧
            camera_id: 摄像头ID
        
        Returns:
            True表示有运动，False表示无运动
        """
        if camera_id not in self.prev_frames:
            # 第一帧，保存并返回True（需要检测）
            self.prev_frames[camera_id] = frame.copy()
            return True
        
        prev_frame = self.prev_frames[camera_id]
        
        # 转换为灰度图
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
            prev_gray = prev_frame
        
        # 计算帧差
        diff = cv2.absdiff(gray, prev_gray)
        
        # 计算运动比例
        motion_ratio = np.sum(diff > 30) / (diff.shape[0] * diff.shape[1])
        
        # 更新上一帧
        self.prev_frames[camera_id] = frame.copy()
        
        # 判断是否有运动
        has_motion = motion_ratio > self.motion_threshold
        
        logger.debug(
            f"Motion detection for {camera_id}: "
            f"motion_ratio={motion_ratio:.4f}, "
            f"threshold={self.motion_threshold}, "
            f"has_motion={has_motion}"
        )
        
        return has_motion
    
    def reset(self, camera_id: Optional[str] = None):
        """重置检测器状态"""
        if camera_id:
            # 重置特定摄像头
            if camera_id in self.frame_counters:
                del self.frame_counters[camera_id]
            if camera_id in self.prev_frames:
                del self.prev_frames[camera_id]
            if camera_id in self.last_detection_times:
                del self.last_detection_times[camera_id]
            if camera_id in self.detection_history:
                del self.detection_history[camera_id]
            logger.debug(f"Reset FrameSkipDetector for camera_id={camera_id}")
        else:
            # 重置所有
            self.frame_counters.clear()
            self.prev_frames.clear()
            self.last_detection_times.clear()
            self.detection_history.clear()
            logger.info("Reset all FrameSkipDetector state")
    
    def get_stats(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        if camera_id:
            # 特定摄像头的统计
            history = self.detection_history.get(camera_id, deque())
            total = len(history)
            detected = sum(history) if history else 0
            skip_rate = 1.0 - (detected / total) if total > 0 else 0.0
            
            return {
                "camera_id": camera_id,
                "frame_count": self.frame_counters.get(camera_id, 0),
                "total_decisions": total,
                "detected_count": detected,
                "skipped_count": total - detected,
                "skip_rate": skip_rate,
                "skip_interval": self.skip_interval,
                "motion_threshold": self.motion_threshold,
            }
        else:
            # 所有摄像头的统计
            return {
                "total_cameras": len(self.frame_counters),
                "skip_interval": self.skip_interval,
                "motion_threshold": self.motion_threshold,
                "enable_motion_detection": self.enable_motion_detection,
                "cameras": {
                    cid: self.get_stats(cid)
                    for cid in self.frame_counters.keys()
                },
            }

