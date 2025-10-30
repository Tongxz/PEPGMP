"""
领域模型单元测试
测试领域实体、值对象、服务等
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.events.detection_events import (
    DetectionCreatedEvent,
    ViolationDetectedEvent,
)
from src.domain.services.detection_service import DetectionService
from src.domain.services.violation_service import (
    ViolationService,
    ViolationSeverity,
    ViolationType,
)
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp


class TestBoundingBox:
    """测试边界框值对象"""

    def test_bounding_box_creation(self):
        """测试边界框创建"""
        bbox = BoundingBox(10, 20, 30, 40)

        assert bbox.x1 == 10
        assert bbox.y1 == 20
        assert bbox.x2 == 30
        assert bbox.y2 == 40
        assert bbox.width == 20
        assert bbox.height == 20
        assert bbox.area == 400

    def test_bounding_box_validation(self):
        """测试边界框验证"""
        # 测试无效边界框
        with pytest.raises(ValueError):
            BoundingBox(30, 20, 10, 40)  # x1 >= x2

        with pytest.raises(ValueError):
            BoundingBox(10, 40, 30, 20)  # y1 >= y2

        with pytest.raises(ValueError):
            BoundingBox(-10, 20, 30, 40)  # 负坐标

    def test_bounding_box_center(self):
        """测试边界框中心点"""
        bbox = BoundingBox(0, 0, 100, 100)
        center = bbox.center

        assert center == (50.0, 50.0)

    def test_bounding_box_iou(self):
        """测试IoU计算"""
        bbox1 = BoundingBox(0, 0, 100, 100)
        bbox2 = BoundingBox(50, 50, 150, 150)

        iou = bbox1.calculate_iou(bbox2)
        assert 0 < iou < 1

        # 完全重叠
        bbox3 = BoundingBox(0, 0, 100, 100)
        iou_same = bbox1.calculate_iou(bbox3)
        assert iou_same == 1.0

    def test_bounding_box_contains_point(self):
        """测试点包含检查"""
        bbox = BoundingBox(10, 20, 30, 40)

        assert bbox.contains_point(20, 30) is True
        assert bbox.contains_point(5, 30) is False
        assert bbox.contains_point(20, 10) is False


class TestConfidence:
    """测试置信度值对象"""

    def test_confidence_creation(self):
        """测试置信度创建"""
        conf = Confidence(0.8)
        assert conf.value == 0.8
        assert conf.is_high is True
        assert conf.is_medium is False
        assert conf.is_low is False

    def test_confidence_validation(self):
        """测试置信度验证"""
        with pytest.raises(ValueError):
            Confidence(1.5)  # 超出范围

        with pytest.raises(ValueError):
            Confidence(-0.1)  # 负值

    def test_confidence_operations(self):
        """测试置信度运算"""
        conf1 = Confidence(0.6)
        conf2 = Confidence(0.3)

        # 加法
        result = conf1 + conf2
        assert abs(result.value - 0.9) < 1e-9

        # 乘法
        result = conf1 * conf2
        assert result.value == 0.18

        # 比较
        assert conf1 > conf2
        assert conf1 >= conf2
        assert conf2 < conf1
        assert conf2 <= conf1


class TestTimestamp:
    """测试时间戳值对象"""

    def test_timestamp_creation(self):
        """测试时间戳创建"""
        timestamp = Timestamp.now()
        assert isinstance(timestamp.value, datetime)

    def test_timestamp_from_iso(self):
        """测试从ISO字符串创建"""
        iso_string = "2024-01-01T12:00:00"
        timestamp = Timestamp.from_iso(iso_string)
        assert timestamp.iso_string == iso_string

    def test_timestamp_operations(self):
        """测试时间戳运算"""
        timestamp1 = Timestamp.from_iso("2024-01-01T12:00:00")
        timestamp2 = Timestamp.from_iso("2024-01-01T12:05:00")

        assert timestamp1.is_before(timestamp2)
        assert timestamp2.is_after(timestamp1)

        # 添加时间
        new_timestamp = timestamp1.add_minutes(5)
        assert new_timestamp.is_same_time(timestamp2, tolerance_seconds=1)


class TestDetectedObject:
    """测试检测对象实体"""

    def test_detected_object_creation(self):
        """测试检测对象创建"""
        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.8)

        obj = DetectedObject(
            class_id=0, class_name="person", confidence=confidence, bbox=bbox
        )

        assert obj.class_name == "person"
        assert obj.is_person is True
        assert obj.is_vehicle is False
        assert obj.is_high_confidence is True

    def test_detected_object_properties(self):
        """测试检测对象属性"""
        bbox = BoundingBox(0, 0, 100, 100)
        confidence = Confidence(0.6)

        obj = DetectedObject(
            class_id=0, class_name="person", confidence=confidence, bbox=bbox
        )

        assert obj.area == 10000
        assert obj.center == (50.0, 50.0)
        assert obj.is_medium_confidence is True

    def test_detected_object_same_object(self):
        """测试同一对象判断"""
        bbox1 = BoundingBox(10, 10, 20, 20)
        bbox2 = BoundingBox(12, 12, 22, 22)
        confidence = Confidence(0.8)

        obj1 = DetectedObject(0, "person", confidence, bbox1)
        obj2 = DetectedObject(0, "person", confidence, bbox2)

        assert obj1.is_same_object(obj2, iou_threshold=0.3) is True


class TestDetectionRecord:
    """测试检测记录实体"""

    def test_detection_record_creation(self):
        """测试检测记录创建"""
        record = DetectionRecord(id="test_001", camera_id="cam1")

        assert record.id == "test_001"
        assert record.camera_id == "cam1"
        assert record.object_count == 0
        assert record.person_count == 0

    def test_detection_record_add_object(self):
        """测试添加检测对象"""
        record = DetectionRecord(id="test_001", camera_id="cam1")

        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.8)
        obj = DetectedObject(0, "person", confidence, bbox)

        record.add_object(obj)

        assert record.object_count == 1
        assert record.person_count == 1
        assert record.average_confidence == 0.8

    def test_detection_record_quality_analysis(self):
        """测试检测记录质量分析"""
        record = DetectionRecord(id="test_001", camera_id="cam1")

        # 添加高置信度对象
        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.9)
        obj = DetectedObject(0, "person", confidence, bbox)
        record.add_object(obj)

        assert record.average_confidence == 0.9
        assert len(record.high_confidence_objects) == 1
        assert len(record.medium_confidence_objects) == 0
        assert len(record.low_confidence_objects) == 0


class TestCamera:
    """测试摄像头实体"""

    def test_camera_creation(self):
        """测试摄像头创建"""
        camera = Camera(id="cam1", name="Camera 1", location="Building A")

        assert camera.id == "cam1"
        assert camera.name == "Camera 1"
        assert camera.location == "Building A"
        assert camera.status == CameraStatus.INACTIVE
        assert camera.is_active is False

    def test_camera_activation(self):
        """测试摄像头激活"""
        camera = Camera(id="cam1", name="Camera 1", location="Building A")

        camera.activate()
        assert camera.is_active is True
        assert camera.status == CameraStatus.ACTIVE

    def test_camera_capabilities(self):
        """测试摄像头能力"""
        camera = Camera(
            id="cam1",
            name="Camera 1",
            location="Building A",
            camera_type=CameraType.PTZ,
            resolution=(1920, 1080),
            fps=30,
        )

        capabilities = camera.get_capabilities()
        assert "pan_tilt_zoom" in capabilities
        assert "high_resolution" in capabilities
        assert "high_fps" in capabilities


class TestDetectionService:
    """测试检测领域服务"""

    def test_analyze_detection_quality(self):
        """测试检测质量分析"""
        service = DetectionService()

        # 创建测试记录
        record = DetectionRecord(id="test_001", camera_id="cam1")
        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.8)
        obj = DetectedObject(0, "person", confidence, bbox)
        record.add_object(obj)

        analysis = service.analyze_detection_quality(record)

        assert "overall_quality" in analysis
        assert "confidence_score" in analysis
        assert "quality_issues" in analysis
        assert "recommendations" in analysis

    def test_calculate_detection_statistics(self):
        """测试检测统计计算"""
        service = DetectionService()

        # 创建测试记录
        records = []
        for i in range(3):
            record = DetectionRecord(id=f"test_{i:03d}", camera_id="cam1")
            bbox = BoundingBox(10, 20, 30, 40)
            confidence = Confidence(0.7 + i * 0.1)
            obj = DetectedObject(0, "person", confidence, bbox)
            record.add_object(obj)
            records.append(record)

        stats = service.calculate_detection_statistics(records)

        assert stats["total_records"] == 3
        assert stats["total_objects"] == 3
        assert "average_confidence" in stats
        assert "object_distribution" in stats


class TestViolationService:
    """测试违规检测服务"""

    def test_violation_service_initialization(self):
        """测试违规服务初始化"""
        service = ViolationService()

        assert "no_safety_helmet" in service.violation_rules
        assert "no_safety_vest" in service.violation_rules
        assert "crowding" in service.violation_rules

    def test_detect_violations(self):
        """测试违规检测"""
        service = ViolationService()

        # 创建测试记录
        record = DetectionRecord(id="test_001", camera_id="cam1")
        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.8)
        obj = DetectedObject(0, "person", confidence, bbox)
        record.add_object(obj)

        violations = service.detect_violations(record)

        # 应该检测到未戴安全帽违规
        assert len(violations) > 0
        assert any(
            v.violation_type == ViolationType.NO_SAFETY_HELMET for v in violations
        )

    def test_get_violation_statistics(self):
        """测试违规统计"""
        service = ViolationService()

        # 创建测试违规
        violations = []
        for i in range(3):
            violation = Mock()
            violation.violation_type = ViolationType.NO_SAFETY_HELMET
            violation.severity = ViolationSeverity.HIGH
            violation.camera_id = "cam1"
            violation.timestamp = datetime.now()
            violations.append(violation)

        stats = service.get_violation_statistics(violations)

        assert stats["total_violations"] == 3
        assert "violation_types" in stats
        assert "severity_distribution" in stats


class TestDetectionEvents:
    """测试检测事件"""

    def test_detection_created_event(self):
        """测试检测创建事件"""
        record = DetectionRecord(id="test_001", camera_id="cam1")

        event = DetectionCreatedEvent.from_detection_record(record)

        assert event.detection_id == "test_001"
        assert event.camera_id == "cam1"
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "detection_created"

    def test_violation_detected_event(self):
        """测试违规检测事件"""
        # 创建模拟违规
        violation = Mock()
        violation.id = "violation_001"
        violation.violation_type = ViolationType.NO_SAFETY_HELMET
        violation.severity = ViolationSeverity.HIGH
        violation.camera_id = "cam1"
        violation.timestamp = datetime.now()
        violation.confidence = Confidence(0.8)
        violation.description = "未戴安全帽"
        violation.metadata = {}

        # 创建模拟检测对象
        detected_object = Mock()
        detected_object.track_id = 123
        violation.detected_object = detected_object

        event = ViolationDetectedEvent.from_violation(violation)

        assert event.violation_id == "violation_001"
        assert event.violation_type == "no_safety_helmet"
        assert event.severity == "high"
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "violation_detected"


if __name__ == "__main__":
    pytest.main([__file__])
