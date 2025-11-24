"""
接口层单元测试
测试接口定义的正确性和一致性
"""

from datetime import datetime

import pytest

from src.interfaces.detection.detector_interface import (
    DetectedObject,
    DetectionError,
    DetectionResult,
    IDetector,
)
from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
    RepositoryError,
)
from src.interfaces.tracking.tracker_interface import (
    ITracker,
    Track,
    TrackingError,
    TrackingResult,
)


class TestDetectedObject:
    """测试DetectedObject类"""

    def test_detected_object_creation(self):
        """测试DetectedObject创建"""
        obj = DetectedObject(
            class_id=0,
            class_name="person",
            confidence=0.95,
            bbox=[100, 100, 200, 200],
            track_id=1,
        )

        assert obj.class_id == 0
        assert obj.class_name == "person"
        assert obj.confidence == 0.95
        assert obj.bbox == [100, 100, 200, 200]
        assert obj.track_id == 1


class TestDetectionResult:
    """测试DetectionResult类"""

    def test_detection_result_creation(self):
        """测试DetectionResult创建"""
        objects = [
            DetectedObject(0, "person", 0.95, [100, 100, 200, 200]),
            DetectedObject(1, "car", 0.87, [300, 300, 400, 400]),
        ]

        result = DetectionResult(
            objects=objects, processing_time=0.05, frame_id=1, timestamp=datetime.now()
        )

        assert result.object_count == 2
        assert result.confidence_score == (0.95 + 0.87) / 2
        assert len(result.get_objects_by_class("person")) == 1
        assert len(result.get_high_confidence_objects(0.9)) == 1


class TestTrack:
    """测试Track类"""

    def test_track_creation(self):
        """测试Track创建"""
        track = Track(
            track_id=1,
            class_id=0,
            class_name="person",
            bbox=[100, 100, 200, 200],
            confidence=0.95,
            age=10,
            hits=8,
            time_since_update=0,
            state="confirmed",
        )

        assert track.is_confirmed
        assert not track.is_deleted


class TestTrackingResult:
    """测试TrackingResult类"""

    def test_tracking_result_creation(self):
        """测试TrackingResult创建"""
        tracks = [
            Track(1, 0, "person", [100, 100, 200, 200], 0.95, 10, 8, 0, "confirmed"),
            Track(2, 1, "car", [300, 300, 400, 400], 0.87, 5, 3, 0, "tentative"),
        ]

        result = TrackingResult(
            tracks=tracks, frame_id=1, processing_time=0.02, timestamp=datetime.now()
        )

        assert len(result.confirmed_tracks) == 1
        assert len(result.active_tracks) == 2
        assert result.get_track_by_id(1) is not None
        assert result.get_track_by_id(3) is None


class TestDetectionRecord:
    """测试DetectionRecord类"""

    def test_detection_record_creation(self):
        """测试DetectionRecord创建"""
        record = DetectionRecord(
            id="test-id",
            camera_id="cam1",
            objects=[{"class": "person", "confidence": 0.95}],
            timestamp=datetime.now(),
            confidence=0.95,
            processing_time=0.05,
        )

        assert record.id == "test-id"
        assert record.camera_id == "cam1"
        assert record.confidence == 0.95

    def test_detection_record_to_dict(self):
        """测试DetectionRecord转换为字典"""
        record = DetectionRecord(
            id="test-id",
            camera_id="cam1",
            objects=[{"class": "person", "confidence": 0.95}],
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            confidence=0.95,
            processing_time=0.05,
        )

        data = record.to_dict()
        assert data["id"] == "test-id"
        assert data["camera_id"] == "cam1"
        assert data["confidence"] == 0.95

    def test_detection_record_from_dict(self):
        """测试从字典创建DetectionRecord"""
        data = {
            "id": "test-id",
            "camera_id": "cam1",
            "objects": [{"class": "person", "confidence": 0.95}],
            "timestamp": "2025-01-01T12:00:00",
            "confidence": 0.95,
            "processing_time": 0.05,
        }

        record = DetectionRecord.from_dict(data)
        assert record.id == "test-id"
        assert record.camera_id == "cam1"
        assert record.confidence == 0.95


class TestInterfaces:
    """测试接口定义"""

    def test_detector_interface_abstract(self):
        """测试IDetector接口是抽象的"""
        with pytest.raises(TypeError):
            IDetector()

    def test_tracker_interface_abstract(self):
        """测试ITracker接口是抽象的"""
        with pytest.raises(TypeError):
            ITracker()

    def test_repository_interface_abstract(self):
        """测试IDetectionRepository接口是抽象的"""
        with pytest.raises(TypeError):
            IDetectionRepository()


class TestExceptions:
    """测试异常类"""

    def test_detection_error(self):
        """测试DetectionError异常"""
        error = DetectionError("Test error", "TEST_ERROR")
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"

    def test_tracking_error(self):
        """测试TrackingError异常"""
        error = TrackingError("Test error", "TEST_ERROR")
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"

    def test_repository_error(self):
        """测试RepositoryError异常"""
        error = RepositoryError("Test error", "TEST_ERROR")
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"


if __name__ == "__main__":
    pytest.main([__file__])
