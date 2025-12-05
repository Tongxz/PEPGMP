"""
StateManager单元测试
"""

from datetime import datetime

import numpy as np

from src.core.frame_metadata import FrameMetadata, FrameSource
from src.core.frame_metadata_manager import FrameMetadataManager
from src.core.state_manager import StateManager


class TestStateManager:
    """StateManager测试类"""

    def test_initialization(self):
        """测试初始化"""
        manager = StateManager(
            stability_frames=5,
            confidence_threshold=0.7,
        )

        assert manager.stability_frames == 5
        assert manager.confidence_threshold == 0.7
        assert len(manager.states) == 0

    def test_update_state_normal(self):
        """测试更新正常状态"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        # 低置信度（正常状态）
        stable_state, stable_confidence = manager.update_state(
            frame_meta, current_confidence=0.3
        )

        assert stable_state in ["normal", "transition"]
        assert stable_confidence < 0.7

    def test_update_state_violation(self):
        """测试更新违规状态"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        # 高置信度（违规状态）- 使用相同的track_id
        for i in range(3):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=datetime.utcnow(),
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
                metadata={"track_id": "track_1"},  # 使用相同的track_id
            )
            stable_state, stable_confidence = manager.update_state(
                frame_meta, current_confidence=0.9
            )

        # 连续3帧高置信度，应该判定为稳定的违规状态
        assert stable_state == "violation"
        assert stable_confidence >= 0.7

    def test_stability_check(self):
        """测试稳定性检查"""
        manager = StateManager(
            stability_frames=5,
            confidence_threshold=0.7,
        )

        # 连续5帧高置信度 - 使用相同的track_id
        for i in range(5):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=datetime.utcnow(),
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
                metadata={"track_id": "track_1"},  # 使用相同的track_id
            )
            stable_state, stable_confidence = manager.update_state(
                frame_meta, current_confidence=0.8
            )

        # 应该判定为稳定的违规状态
        assert stable_state == "violation"
        assert stable_confidence >= 0.7

    def test_event_boundary_detection(self):
        """测试事件边界检测"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
            transition_threshold=0.3,
        )

        # 先发送低置信度帧
        for i in range(3):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=datetime.utcnow(),
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
            )
            manager.update_state(frame_meta, current_confidence=0.3)

        # 突然切换到高置信度（应该检测到事件边界）
        frame_meta = FrameMetadata(
            frame_id="frame_4",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )
        stable_state, _ = manager.update_state(frame_meta, current_confidence=0.9)

        # 应该检测到状态转换
        state = manager.get_state(frame_meta.frame_id)
        assert state is not None
        assert state.state_type == "violation"

    def test_with_frame_metadata_manager(self):
        """测试与FrameMetadataManager集成"""
        frame_manager = FrameMetadataManager(max_history=100)
        state_manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
            frame_metadata_manager=frame_manager,
        )

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame_meta = frame_manager.create_frame_metadata(
            frame=frame,
            camera_id="camera_1",
        )

        # 更新状态
        stable_state, stable_confidence = state_manager.update_state(
            frame_meta, current_confidence=0.8
        )

        # 验证FrameMetadata已更新
        updated_meta = frame_manager.get_frame_metadata(frame_meta.frame_id)
        assert updated_meta is not None
        assert updated_meta.detection_state == stable_state
        assert updated_meta.state_confidence == stable_confidence

    def test_track_id_from_metadata(self):
        """测试从metadata获取track_id"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            metadata={"track_id": "track_123"},
        )

        manager.update_state(frame_meta, current_confidence=0.8)

        # 应该使用metadata中的track_id
        state = manager.get_state("track_123")
        assert state is not None

    def test_clear_state(self):
        """测试清除状态"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            metadata={"track_id": "track_123"},
        )

        manager.update_state(frame_meta, current_confidence=0.8)
        assert manager.get_state("track_123") is not None

        manager.clear_state("track_123")
        assert manager.get_state("track_123") is None

    def test_clear_all_states(self):
        """测试清除所有状态"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        # 创建多个状态
        for i in range(3):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=datetime.utcnow(),
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
                metadata={"track_id": f"track_{i+1}"},
            )
            manager.update_state(frame_meta, current_confidence=0.8)

        assert len(manager.states) == 3

        manager.clear_all_states()
        assert len(manager.states) == 0

    def test_get_stats(self):
        """测试获取统计信息"""
        manager = StateManager(
            stability_frames=3,
            confidence_threshold=0.7,
        )

        # 创建状态
        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            metadata={"track_id": "track_123"},
        )
        manager.update_state(frame_meta, current_confidence=0.8)

        stats = manager.get_stats()
        assert stats["total_tracks"] == 1
        assert stats["stability_frames"] == 3
        assert stats["confidence_threshold"] == 0.7
        assert "track_123" in stats["states"]
