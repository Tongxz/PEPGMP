"""
策略模式单元测试
测试检测器和跟踪器策略的实现
"""

from unittest.mock import Mock

import numpy as np
import pytest

from src.strategies.detection.detector_factory import DetectorFactory
from src.strategies.detection.mediapipe_strategy import MediaPipeStrategy
from src.strategies.detection.yolo_strategy import YOLOStrategy
from src.strategies.tracking.simple_tracker_strategy import SimpleTrackerStrategy
from src.strategies.tracking.tracker_factory import TrackerFactory


class TestYOLOStrategy:
    """测试YOLO策略"""

    def test_yolo_strategy_initialization(self):
        """测试YOLO策略初始化"""
        strategy = YOLOStrategy(
            model_path="test.pt", device="cpu", confidence_threshold=0.7
        )

        assert strategy.model_path == "test.pt"
        assert strategy.device == "cpu"
        assert strategy.confidence_threshold == 0.7
        assert not strategy._model_loaded

    def test_yolo_strategy_device_auto(self):
        """测试自动设备选择"""
        strategy = YOLOStrategy(model_path="test.pt", device="auto")
        # 应该选择CPU作为默认设备
        assert strategy.device in ["cpu", "cuda", "mps"]

    def test_yolo_strategy_confidence_threshold(self):
        """测试置信度阈值设置"""
        strategy = YOLOStrategy(model_path="test.pt")

        # 测试有效阈值
        strategy.set_confidence_threshold(0.8)
        assert strategy.get_confidence_threshold() == 0.8

        # 测试无效阈值
        with pytest.raises(ValueError):
            strategy.set_confidence_threshold(1.5)

        with pytest.raises(ValueError):
            strategy.set_confidence_threshold(-0.1)

    def test_yolo_strategy_model_info(self):
        """测试模型信息获取"""
        strategy = YOLOStrategy(model_path="test.pt")
        info = strategy.get_model_info()

        assert info["type"] == "YOLO"
        assert info["model_path"] == "test.pt"
        assert info["confidence_threshold"] == 0.5
        assert not info["loaded"]

    def test_yolo_strategy_availability(self):
        """测试YOLO策略可用性"""
        strategy = YOLOStrategy(model_path="nonexistent.pt")

        # 模型文件不存在，应该不可用
        assert not strategy.is_available()

        # 测试存在的模型文件
        strategy = YOLOStrategy(model_path="test.pt")
        # 由于没有实际安装ultralytics，这里会返回False
        # 在实际环境中，如果安装了依赖，应该返回True
        assert isinstance(strategy.is_available(), bool)


class TestMediaPipeStrategy:
    """测试MediaPipe策略"""

    def test_mediapipe_strategy_initialization(self):
        """测试MediaPipe策略初始化"""
        strategy = MediaPipeStrategy(model_complexity=2, confidence_threshold=0.8)

        assert strategy.model_complexity == 2
        assert strategy.confidence_threshold == 0.8
        assert not strategy._model_loaded

    def test_mediapipe_strategy_confidence_threshold(self):
        """测试置信度阈值设置"""
        strategy = MediaPipeStrategy()

        # 测试有效阈值
        strategy.set_confidence_threshold(0.9)
        assert strategy.get_confidence_threshold() == 0.9

        # 测试无效阈值
        with pytest.raises(ValueError):
            strategy.set_confidence_threshold(2.0)

    def test_mediapipe_strategy_model_info(self):
        """测试模型信息获取"""
        strategy = MediaPipeStrategy()
        info = strategy.get_model_info()

        assert info["type"] == "MediaPipe"
        assert info["model_complexity"] == 1
        assert info["confidence_threshold"] == 0.5
        assert not info["loaded"]

    def test_mediapipe_strategy_availability(self):
        """测试MediaPipe策略可用性"""
        strategy = MediaPipeStrategy()

        # 由于没有实际安装mediapipe，这里会返回False
        # 在实际环境中，如果安装了依赖，应该返回True
        assert isinstance(strategy.is_available(), bool)


class TestDetectorFactory:
    """测试检测器工厂"""

    def test_create_yolo_detector(self):
        """测试创建YOLO检测器"""
        detector = DetectorFactory.create_detector(
            "yolo", model_path="test.pt", device="cpu"
        )

        assert isinstance(detector, YOLOStrategy)
        assert detector.model_path == "test.pt"
        assert detector.device == "cpu"

    def test_create_mediapipe_detector(self):
        """测试创建MediaPipe检测器"""
        detector = DetectorFactory.create_detector("mediapipe", model_complexity=1)

        assert isinstance(detector, MediaPipeStrategy)
        assert detector.model_complexity == 1

    def test_create_unsupported_detector(self):
        """测试创建不支持的检测器"""
        with pytest.raises(ValueError, match="不支持的检测器类型"):
            DetectorFactory.create_detector("unsupported")

    def test_get_available_detectors(self):
        """测试获取可用检测器列表"""
        available = DetectorFactory.get_available_detectors()

        # 应该包含simple_tracker（总是可用）
        assert isinstance(available, list)
        # 具体内容取决于环境依赖

    def test_get_detector_info(self):
        """测试获取检测器信息"""
        info = DetectorFactory.get_detector_info("yolo")

        assert info["type"] == "yolo"
        assert info["class"] == "YOLOStrategy"
        assert "YOLO" in info["description"]

    def test_register_strategy(self):
        """测试注册新策略"""

        class MockDetector:
            def __init__(self):
                pass

        # 这应该失败，因为MockDetector没有实现IDetector接口
        with pytest.raises(ValueError):
            DetectorFactory.register_strategy("mock", MockDetector)

    def test_create_detector_from_config(self):
        """测试从配置创建检测器"""
        from src.strategies.detection.detector_factory import (
            create_detector_from_config,
        )

        config = {"type": "yolo", "model_path": "test.pt", "device": "cpu"}

        detector = create_detector_from_config(config)
        assert isinstance(detector, YOLOStrategy)


class TestSimpleTrackerStrategy:
    """测试简单跟踪策略"""

    def test_simple_tracker_initialization(self):
        """测试简单跟踪策略初始化"""
        tracker = SimpleTrackerStrategy(max_age=50, min_hits=5, iou_threshold=0.4)

        assert tracker.max_age == 50
        assert tracker.min_hits == 5
        assert tracker.iou_threshold == 0.4
        assert tracker.frame_id == 0
        assert tracker.next_id == 1

    def test_simple_tracker_reset(self):
        """测试跟踪器重置"""
        tracker = SimpleTrackerStrategy()

        # 添加一些轨迹
        tracker.tracks.append(Mock())
        tracker.next_id = 10
        tracker.frame_id = 5

        # 重置
        tracker.reset()

        assert len(tracker.tracks) == 0
        assert tracker.next_id == 1
        assert tracker.frame_id == 0

    def test_simple_tracker_track_count(self):
        """测试轨迹数量获取"""
        tracker = SimpleTrackerStrategy()

        assert tracker.get_track_count() == 0

        # 添加轨迹
        tracker.tracks.append(Mock())
        tracker.tracks.append(Mock())

        assert tracker.get_track_count() == 2

    def test_simple_tracker_statistics(self):
        """测试跟踪统计信息"""
        tracker = SimpleTrackerStrategy()
        stats = tracker.get_track_statistics()

        assert stats["tracker_type"] == "SimpleTracker"
        assert stats["max_age"] == 30
        assert stats["min_hits"] == 3
        assert stats["total_tracks"] == 0

    def test_simple_tracker_parameter_update(self):
        """测试参数更新"""
        tracker = SimpleTrackerStrategy()

        tracker.set_max_age(100)
        assert tracker.max_age == 100

        tracker.set_min_hits(10)
        assert tracker.min_hits == 10

    @pytest.mark.asyncio
    async def test_simple_tracker_track_empty_detections(self):
        """测试空检测结果的跟踪"""
        tracker = SimpleTrackerStrategy()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = await tracker.track([], frame)

        assert result.frame_id == 1
        assert len(result.tracks) == 0
        assert result.processing_time >= 0

    @pytest.mark.asyncio
    async def test_simple_tracker_track_with_detections(self):
        """测试有检测结果的跟踪"""
        tracker = SimpleTrackerStrategy()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        detections = [
            {
                "class_id": 0,
                "class_name": "person",
                "bbox": [100, 100, 200, 200],
                "confidence": 0.9,
            }
        ]

        result = await tracker.track(detections, frame)

        assert result.frame_id == 1
        assert len(result.tracks) == 1
        assert result.tracks[0].track_id == 1
        assert result.tracks[0].class_name == "person"


class TestTrackerFactory:
    """测试跟踪器工厂"""

    def test_create_simple_tracker(self):
        """测试创建简单跟踪器"""
        tracker = TrackerFactory.create_tracker(
            "simple_tracker", max_age=50, min_hits=5
        )

        assert isinstance(tracker, SimpleTrackerStrategy)
        assert tracker.max_age == 50
        assert tracker.min_hits == 5

    def test_create_unsupported_tracker(self):
        """测试创建不支持的跟踪器"""
        with pytest.raises(ValueError, match="不支持的跟踪器类型"):
            TrackerFactory.create_tracker("unsupported")

    def test_get_available_trackers(self):
        """测试获取可用跟踪器列表"""
        available = TrackerFactory.get_available_trackers()

        # 应该包含simple_tracker（总是可用）
        assert "simple_tracker" in available
        assert isinstance(available, list)

    def test_get_tracker_info(self):
        """测试获取跟踪器信息"""
        info = TrackerFactory.get_tracker_info("simple_tracker")

        assert info["type"] == "simple_tracker"
        assert info["class"] == "SimpleTrackerStrategy"

    def test_create_tracker_from_config(self):
        """测试从配置创建跟踪器"""
        from src.strategies.tracking.tracker_factory import create_tracker_from_config

        config = {"type": "simple_tracker", "max_age": 50, "min_hits": 5}

        tracker = create_tracker_from_config(config)
        assert isinstance(tracker, SimpleTrackerStrategy)


class TestIoUComputation:
    """测试IoU计算"""

    def test_compute_iou_overlapping(self):
        """测试重叠边界框的IoU计算"""
        tracker = SimpleTrackerStrategy()

        # 完全重叠
        bbox1 = [0, 0, 100, 100]  # [x, y, w, h]
        bbox2 = [0, 0, 100, 100]
        iou = tracker._compute_iou(bbox1, bbox2)
        assert iou == 1.0

        # 部分重叠
        bbox1 = [0, 0, 100, 100]
        bbox2 = [50, 50, 100, 100]
        iou = tracker._compute_iou(bbox1, bbox2)
        assert 0 < iou < 1

        # 不重叠
        bbox1 = [0, 0, 100, 100]
        bbox2 = [200, 200, 100, 100]
        iou = tracker._compute_iou(bbox1, bbox2)
        assert iou == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
