"""
FrameMetadataManager单元测试
"""

import threading
from datetime import datetime, timedelta

import numpy as np

from src.core.frame_metadata import FrameMetadata, FrameSource
from src.core.frame_metadata_manager import FrameMetadataManager


class TestFrameMetadataManager:
    """FrameMetadataManager测试类"""

    def test_create_frame_metadata(self):
        """测试创建帧元数据"""
        manager = FrameMetadataManager(max_history=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        frame_meta = manager.create_frame_metadata(
            frame=frame,
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
        )

        assert frame_meta.frame_id is not None
        assert frame_meta.camera_id == "camera_1"
        assert frame_meta.frame_hash is not None

        # 应该能在索引中找到
        retrieved = manager.get_frame_metadata(frame_meta.frame_id)
        assert retrieved is not None
        assert retrieved.frame_id == frame_meta.frame_id

    def test_update_detection_results(self):
        """测试更新检测结果"""
        manager = FrameMetadataManager(max_history=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        frame_meta = manager.create_frame_metadata(
            frame=frame,
            camera_id="camera_1",
        )

        person_detections = [{"class": "person", "confidence": 0.9}]
        hairnet_results = [{"has_hairnet": True, "confidence": 0.8}]

        updated = manager.update_detection_results(
            frame_meta.frame_id,
            person_detections=person_detections,
            hairnet_results=hairnet_results,
        )

        assert updated is not None
        assert len(updated.person_detections) == 1
        assert len(updated.hairnet_results) == 1

        # 验证索引已更新
        retrieved = manager.get_frame_metadata(frame_meta.frame_id)
        assert retrieved is not None
        assert len(retrieved.person_detections) == 1

    def test_update_state(self):
        """测试更新状态"""
        manager = FrameMetadataManager(max_history=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        frame_meta = manager.create_frame_metadata(
            frame=frame,
            camera_id="camera_1",
        )

        updated = manager.update_state(
            frame_meta.frame_id,
            detection_state="violation",
            state_confidence=0.85,
        )

        assert updated is not None
        assert updated.detection_state == "violation"
        assert updated.state_confidence == 0.85

    def test_get_frames_by_timestamp_range(self):
        """测试根据时间范围获取帧"""
        manager = FrameMetadataManager(max_history=100)

        base_time = datetime.utcnow()
        frames_meta = []

        # 创建多个帧
        for i in range(5):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            timestamp = base_time + timedelta(seconds=i)
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i}",
                timestamp=timestamp,
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
            )
            manager.frame_index[frame_meta.frame_id] = frame_meta
            manager.timestamp_index[manager._round_timestamp(timestamp)] = [
                frame_meta.frame_id
            ]
            frames_meta.append(frame_meta)

        # 查询时间范围内的帧
        start = base_time + timedelta(seconds=1)
        end = base_time + timedelta(seconds=3)
        results = manager.get_frames_by_timestamp_range(start, end)

        assert len(results) >= 2  # 至少包含2个帧

    def test_get_frames_by_camera(self):
        """测试根据摄像头获取帧"""
        manager = FrameMetadataManager(max_history=100)

        # 创建多个摄像头的帧
        for camera_id in ["camera_1", "camera_2"]:
            for i in range(3):
                frame = np.zeros((100, 100, 3), dtype=np.uint8)
                frame_meta = manager.create_frame_metadata(
                    frame=frame,
                    camera_id=camera_id,
                )

        # 查询特定摄像头的帧
        results = manager.get_frames_by_camera("camera_1")
        assert len(results) == 3
        assert all(r.camera_id == "camera_1" for r in results)

    def test_thread_safety(self):
        """测试线程安全"""
        manager = FrameMetadataManager(max_history=1000)
        results = []
        errors = []

        def create_frames(thread_id: int, count: int):
            """创建帧的线程函数"""
            try:
                for i in range(count):
                    frame = np.zeros((100, 100, 3), dtype=np.uint8)
                    frame_meta = manager.create_frame_metadata(
                        frame=frame,
                        camera_id=f"camera_{thread_id}",
                    )
                    results.append(frame_meta.frame_id)
            except Exception as e:
                errors.append(e)

        # 启动多个线程
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=create_frames, args=(thread_id, 10))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0

        # 验证所有帧ID都是唯一的
        assert len(results) == len(set(results))

        # 验证统计信息
        stats = manager.get_stats()
        assert stats["total_frames"] == 50  # 5个线程 * 10个帧

    def test_clear_history(self):
        """测试清理历史记录"""
        manager = FrameMetadataManager(max_history=100)

        # 创建多个帧
        for camera_id in ["camera_1", "camera_2"]:
            for i in range(5):
                frame = np.zeros((100, 100, 3), dtype=np.uint8)
                manager.create_frame_metadata(
                    frame=frame,
                    camera_id=camera_id,
                )

        # 清理特定摄像头
        manager.clear_history(camera_id="camera_1")

        stats = manager.get_stats()
        assert stats["total_frames"] == 5  # 只剩下camera_2的帧

        # 清理所有
        manager.clear_history()
        stats = manager.get_stats()
        assert stats["total_frames"] == 0

    def test_frame_id_uniqueness(self):
        """测试帧ID唯一性"""
        manager = FrameMetadataManager(max_history=100)
        frame_ids = set()

        for i in range(100):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame_meta = manager.create_frame_metadata(
                frame=frame,
                camera_id="camera_1",
            )
            frame_ids.add(frame_meta.frame_id)

        # 所有帧ID应该是唯一的
        assert len(frame_ids) == 100

    def test_update_nonexistent_frame(self):
        """测试更新不存在的帧"""
        manager = FrameMetadataManager(max_history=100)

        # 尝试更新不存在的帧
        result = manager.update_detection_results(
            "nonexistent_frame_id",
            person_detections=[{"class": "person"}],
        )

        assert result is None
