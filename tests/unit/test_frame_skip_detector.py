"""
FrameSkipDetector单元测试
"""

import numpy as np

from src.core.frame_skip_detector import FrameSkipDetector


class TestFrameSkipDetector:
    """FrameSkipDetector测试类"""

    def test_initialization(self):
        """测试初始化"""
        detector = FrameSkipDetector(
            skip_interval=5,
            motion_threshold=0.01,
            enable_motion_detection=True,
        )

        assert detector.skip_interval == 5
        assert detector.motion_threshold == 0.01
        assert detector.enable_motion_detection is True

    def test_skip_interval(self):
        """测试帧跳间隔"""
        detector = FrameSkipDetector(skip_interval=5, enable_motion_detection=False)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # 前4帧应该跳过
        for i in range(1, 5):
            assert detector.should_detect(frame, "camera_1") is False

        # 第5帧应该检测
        assert detector.should_detect(frame, "camera_1") is True

        # 第6-9帧应该跳过
        for i in range(6, 10):
            assert detector.should_detect(frame, "camera_1") is False

        # 第10帧应该检测
        assert detector.should_detect(frame, "camera_1") is True

    def test_motion_detection(self):
        """测试运动检测"""
        detector = FrameSkipDetector(
            skip_interval=1,  # 每帧都检查
            motion_threshold=0.01,
            enable_motion_detection=True,
        )

        # 第一帧（无运动，但应该检测）
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        assert detector.should_detect(frame1, "camera_1") is True

        # 第二帧（相同，无运动）
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        assert detector.should_detect(frame2, "camera_1") is False

        # 第三帧（有运动）
        frame3 = np.ones((100, 100, 3), dtype=np.uint8) * 255
        assert detector.should_detect(frame3, "camera_1") is True

    def test_min_detection_interval(self):
        """测试最小检测间隔"""
        detector = FrameSkipDetector(
            skip_interval=1,
            enable_motion_detection=False,
            min_detection_interval=0.1,
        )
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # 第一次检测
        assert detector.should_detect(frame, "camera_1", timestamp=0.0) is True

        # 间隔太短，应该跳过
        assert detector.should_detect(frame, "camera_1", timestamp=0.05) is False

        # 间隔足够，应该检测
        assert detector.should_detect(frame, "camera_1", timestamp=0.15) is True

    def test_reset(self):
        """测试重置"""
        detector = FrameSkipDetector(skip_interval=5)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # 添加一些帧
        for i in range(10):
            detector.should_detect(frame, "camera_1")

        # 重置
        detector.reset("camera_1")

        # 计数器应该重置
        assert detector.frame_counters.get("camera_1", 0) == 0

    def test_get_stats(self):
        """测试获取统计信息"""
        detector = FrameSkipDetector(skip_interval=5, enable_motion_detection=False)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # 添加一些帧
        for i in range(10):
            detector.should_detect(frame, "camera_1")

        stats = detector.get_stats("camera_1")
        assert stats["frame_count"] == 10
        assert stats["skip_interval"] == 5
        assert "skip_rate" in stats
