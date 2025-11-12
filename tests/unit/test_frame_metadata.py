"""
FrameMetadata单元测试
"""

from datetime import datetime

import numpy as np
import pytest

from src.core.frame_metadata import FrameMetadata, FrameSource


class TestFrameMetadata:
    """FrameMetadata测试类"""

    def test_create_frame_metadata(self):
        """测试创建帧元数据"""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame_meta = FrameMetadata(
            frame_id="test_frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            frame=frame,
        )

        assert frame_meta.frame_id == "test_frame_1"
        assert frame_meta.camera_id == "camera_1"
        assert frame_meta.source == FrameSource.REALTIME_STREAM
        assert frame_meta.frame is not None

    def test_immutability(self):
        """测试不可变性"""
        frame_meta = FrameMetadata(
            frame_id="test_frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        # 尝试修改应该失败
        with pytest.raises(Exception):
            frame_meta.frame_id = "new_id"

    def test_auto_generate_frame_id(self):
        """测试自动生成frame_id"""
        frame_meta = FrameMetadata(
            frame_id="",  # 空字符串，应该自动生成
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        assert frame_meta.frame_id != ""
        assert len(frame_meta.frame_id) > 0

    def test_with_detection_results(self):
        """测试更新检测结果"""
        frame_meta = FrameMetadata(
            frame_id="test_frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        person_detections = [{"class": "person", "confidence": 0.9}]
        hairnet_results = [{"has_hairnet": True, "confidence": 0.8}]

        new_meta = frame_meta.with_detection_results(
            person_detections=person_detections,
            hairnet_results=hairnet_results,
        )

        # 新实例应该有新的检测结果
        assert len(new_meta.person_detections) == 1
        assert len(new_meta.hairnet_results) == 1

        # 原实例不应该改变
        assert len(frame_meta.person_detections) == 0
        assert len(frame_meta.hairnet_results) == 0

    def test_with_state(self):
        """测试更新状态"""
        frame_meta = FrameMetadata(
            frame_id="test_frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        new_meta = frame_meta.with_state(
            detection_state="violation",
            state_confidence=0.85,
        )

        assert new_meta.detection_state == "violation"
        assert new_meta.state_confidence == 0.85

        # 原实例不应该改变
        assert frame_meta.detection_state is None
        assert frame_meta.state_confidence == 0.0

    def test_serialization(self):
        """测试序列化和反序列化"""
        frame_meta = FrameMetadata(
            frame_id="test_frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            person_detections=[{"class": "person"}],
            detection_state="normal",
            state_confidence=0.9,
        )

        # 序列化
        data = frame_meta.to_dict()
        assert data["frame_id"] == "test_frame_1"
        assert data["camera_id"] == "camera_1"
        assert data["source"] == "realtime_stream"
        assert len(data["person_detections"]) == 1
        assert data["detection_state"] == "normal"
        assert data["state_confidence"] == 0.9

        # 反序列化
        restored = FrameMetadata.from_dict(data)
        assert restored.frame_id == frame_meta.frame_id
        assert restored.camera_id == frame_meta.camera_id
        assert restored.source == frame_meta.source
        assert len(restored.person_detections) == 1
        assert restored.detection_state == "normal"
        assert restored.state_confidence == 0.9
