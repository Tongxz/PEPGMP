"""
SynchronizedCache单元测试
"""

import pytest
from datetime import datetime, timedelta

import numpy as np

from src.core.frame_metadata import FrameMetadata, FrameSource
from src.core.frame_metadata_manager import FrameMetadataManager
from src.core.synchronized_cache import SynchronizedCache


class TestSynchronizedCache:
    """SynchronizedCache测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        cache = SynchronizedCache(
            max_size=100,
            sync_window=0.1,
        )
        
        assert cache.max_size == 100
        assert cache.sync_window == 0.1
    
    def test_add_detection_result(self):
        """测试添加检测结果"""
        cache = SynchronizedCache(max_size=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=datetime.utcnow(),
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            frame=frame,
        )
        
        person_detections = [{"class": "person", "confidence": 0.9}]
        cache.add_detection_result(frame_meta, "person", person_detections)
        
        # 验证结果已添加
        assert "frame_1" in cache.result_cache
        assert "person" in cache.result_cache["frame_1"]["results"]
    
    def test_get_synchronized_result(self):
        """测试获取同步结果"""
        cache = SynchronizedCache(max_size=100, sync_window=0.1)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        base_time = datetime.utcnow()
        
        # 创建帧并添加检测结果
        frame_meta = FrameMetadata(
            frame_id="frame_1",
            timestamp=base_time,
            camera_id="camera_1",
            source=FrameSource.REALTIME_STREAM,
            frame=frame,
        )
        
        person_detections = [{"class": "person", "confidence": 0.9}]
        hairnet_results = [{"has_hairnet": True, "confidence": 0.8}]
        
        cache.add_detection_result(frame_meta, "person", person_detections)
        cache.add_detection_result(frame_meta, "hairnet", hairnet_results)
        
        # 获取同步结果
        result = cache.get_synchronized_result(base_time, camera_id="camera_1")
        
        assert result is not None
        assert len(result.person_detections) == 1
        assert len(result.hairnet_results) == 1
    
    def test_sync_window(self):
        """测试时间窗口同步"""
        cache = SynchronizedCache(max_size=100, sync_window=0.1)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        base_time = datetime.utcnow()
        
        # 创建多个时间戳接近的帧
        for i in range(3):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=base_time + timedelta(seconds=i * 0.05),  # 在窗口内
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
                frame=frame,
            )
            cache.add_detection_result(
                frame_meta, "person", [{"class": "person", "confidence": 0.9}]
            )
        
        # 查询应该能找到匹配的帧
        result = cache.get_synchronized_result(base_time + timedelta(seconds=0.05))
        assert result is not None
    
    def test_clear_cache(self):
        """测试清理缓存"""
        cache = SynchronizedCache(max_size=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # 添加多个摄像头的帧
        for camera_id in ["camera_1", "camera_2"]:
            frame_meta = FrameMetadata(
                frame_id=f"frame_{camera_id}",
                timestamp=datetime.utcnow(),
                camera_id=camera_id,
                source=FrameSource.REALTIME_STREAM,
                frame=frame,
            )
            cache.add_detection_result(
                frame_meta, "person", [{"class": "person"}]
            )
        
        # 清理特定摄像头
        cache.clear_cache(camera_id="camera_1")
        
        stats = cache.get_stats()
        assert stats["cached_frames"] == 1  # 只剩下camera_2的帧
        
        # 清理所有
        cache.clear_cache()
        stats = cache.get_stats()
        assert stats["cached_frames"] == 0
    
    def test_get_stats(self):
        """测试获取统计信息"""
        cache = SynchronizedCache(max_size=100)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # 添加一些数据
        for i in range(3):
            frame_meta = FrameMetadata(
                frame_id=f"frame_{i+1}",
                timestamp=datetime.utcnow(),
                camera_id="camera_1",
                source=FrameSource.REALTIME_STREAM,
                frame=frame,
            )
            cache.add_detection_result(
                frame_meta, "person", [{"class": "person"}]
            )
        
        stats = cache.get_stats()
        assert stats["cached_frames"] == 3
        assert stats["max_size"] == 100
        assert stats["sync_window"] == 0.1

