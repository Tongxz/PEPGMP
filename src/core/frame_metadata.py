"""
帧元数据 - 统一的数据载体

用于确保帧ID、时间戳和检测结果的一致性，支持：
- 状态保持（任务1.1）
- 异步处理（任务1.3）
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class FrameSource(Enum):
    """帧来源"""

    REALTIME_STREAM = "realtime_stream"
    VIDEO_FILE = "video_file"
    IMAGE_FILE = "image_file"
    API_REQUEST = "api_request"


@dataclass(frozen=True)  # 不可变，保证线程安全
class FrameMetadata:
    """帧元数据 - 统一的数据载体

    所有检测相关的数据都通过此载体传递，确保：
    1. 帧ID和时间戳一致性
    2. 检测结果可追溯
    3. 状态管理可关联
    4. 异步处理安全

    使用frozen=True保证不可变性，支持线程安全。
    """

    # 核心标识（不可变）
    frame_id: str  # 全局唯一帧ID
    timestamp: datetime  # 帧时间戳（精确到微秒）
    camera_id: str  # 摄像头ID
    source: FrameSource  # 帧来源

    # 帧数据
    frame: Optional[np.ndarray] = None  # 原始帧数据（可选，可能很大）
    frame_hash: Optional[str] = None  # 帧哈希值（用于缓存）

    # 检测结果（可变，通过方法更新）
    person_detections: List[Dict] = field(default_factory=list)
    hairnet_results: List[Dict] = field(default_factory=list)
    pose_detections: List[Dict] = field(default_factory=list)
    handwash_results: List[Dict] = field(default_factory=list)
    sanitize_results: List[Dict] = field(default_factory=list)

    # 状态信息
    detection_state: Optional[str] = None  # 检测状态（normal, violation, transition）
    state_confidence: float = 0.0  # 状态置信度

    # 处理信息
    processing_times: Dict[str, float] = field(default_factory=dict)
    processing_stage: str = "pending"  # pending, processing, completed, failed

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后处理：确保frame_id唯一性"""
        if not self.frame_id:
            # 使用object.__setattr__因为frozen=True
            object.__setattr__(self, "frame_id", str(uuid.uuid4()))

    def with_detection_results(
        self,
        person_detections: Optional[List[Dict]] = None,
        hairnet_results: Optional[List[Dict]] = None,
        pose_detections: Optional[List[Dict]] = None,
        handwash_results: Optional[List[Dict]] = None,
        sanitize_results: Optional[List[Dict]] = None,
    ) -> "FrameMetadata":
        """创建包含检测结果的新实例（不可变对象需要创建新实例）"""
        return FrameMetadata(
            frame_id=self.frame_id,
            timestamp=self.timestamp,
            camera_id=self.camera_id,
            source=self.source,
            frame=self.frame,
            frame_hash=self.frame_hash,
            person_detections=person_detections
            if person_detections is not None
            else self.person_detections,
            hairnet_results=hairnet_results
            if hairnet_results is not None
            else self.hairnet_results,
            pose_detections=pose_detections
            if pose_detections is not None
            else self.pose_detections,
            handwash_results=handwash_results
            if handwash_results is not None
            else self.handwash_results,
            sanitize_results=sanitize_results
            if sanitize_results is not None
            else self.sanitize_results,
            detection_state=self.detection_state,
            state_confidence=self.state_confidence,
            processing_times=self.processing_times,
            processing_stage=self.processing_stage,
            metadata=self.metadata,
        )

    def with_state(
        self,
        detection_state: str,
        state_confidence: float,
    ) -> "FrameMetadata":
        """创建包含状态信息的新实例"""
        return FrameMetadata(
            frame_id=self.frame_id,
            timestamp=self.timestamp,
            camera_id=self.camera_id,
            source=self.source,
            frame=self.frame,
            frame_hash=self.frame_hash,
            person_detections=self.person_detections,
            hairnet_results=self.hairnet_results,
            pose_detections=self.pose_detections,
            handwash_results=self.handwash_results,
            sanitize_results=self.sanitize_results,
            detection_state=detection_state,
            state_confidence=state_confidence,
            processing_times=self.processing_times,
            processing_stage=self.processing_stage,
            metadata=self.metadata,
        )

    def with_processing_stage(
        self,
        processing_stage: str,
    ) -> "FrameMetadata":
        """创建包含处理阶段信息的新实例"""
        return FrameMetadata(
            frame_id=self.frame_id,
            timestamp=self.timestamp,
            camera_id=self.camera_id,
            source=self.source,
            frame=self.frame,
            frame_hash=self.frame_hash,
            person_detections=self.person_detections,
            hairnet_results=self.hairnet_results,
            pose_detections=self.pose_detections,
            handwash_results=self.handwash_results,
            sanitize_results=self.sanitize_results,
            detection_state=self.detection_state,
            state_confidence=self.state_confidence,
            processing_times=self.processing_times,
            processing_stage=processing_stage,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "camera_id": self.camera_id,
            "source": self.source.value,
            "frame_hash": self.frame_hash,
            "person_detections": self.person_detections,
            "hairnet_results": self.hairnet_results,
            "pose_detections": self.pose_detections,
            "handwash_results": self.handwash_results,
            "sanitize_results": self.sanitize_results,
            "detection_state": self.detection_state,
            "state_confidence": self.state_confidence,
            "processing_times": self.processing_times,
            "processing_stage": self.processing_stage,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrameMetadata":
        """从字典创建（用于反序列化）"""
        return cls(
            frame_id=data["frame_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            camera_id=data["camera_id"],
            source=FrameSource(data["source"]),
            frame_hash=data.get("frame_hash"),
            person_detections=data.get("person_detections", []),
            hairnet_results=data.get("hairnet_results", []),
            pose_detections=data.get("pose_detections", []),
            handwash_results=data.get("handwash_results", []),
            sanitize_results=data.get("sanitize_results", []),
            detection_state=data.get("detection_state"),
            state_confidence=data.get("state_confidence", 0.0),
            processing_times=data.get("processing_times", {}),
            processing_stage=data.get("processing_stage", "pending"),
            metadata=data.get("metadata", {}),
        )
