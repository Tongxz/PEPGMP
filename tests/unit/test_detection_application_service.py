"""
单元测试：检测应用服务

测试 DetectionApplicationService 的核心功能，包括：
- 智能保存决策
- 违规分析
- 数据转换
"""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.application.detection_application_service import (
    DetectionApplicationService,
    SavePolicy,
    SaveStrategy,
)
from src.core.optimized_detection_pipeline import DetectionResult


class TestSavePolicy:
    """测试保存策略配置"""

    def test_default_save_policy(self):
        """测试默认保存策略"""
        policy = SavePolicy()
        assert policy.strategy == SaveStrategy.SMART
        assert policy.save_interval == 30
        assert policy.normal_sample_interval == 300
        assert policy.violation_severity_threshold == 0.5
        assert policy.save_normal_summary is True

    def test_custom_save_policy(self):
        """测试自定义保存策略"""
        policy = SavePolicy(
            strategy=SaveStrategy.VIOLATIONS_ONLY,
            save_interval=60,
            normal_sample_interval=600,
            violation_severity_threshold=0.7,
            save_normal_summary=False,
        )
        assert policy.strategy == SaveStrategy.VIOLATIONS_ONLY
        assert policy.save_interval == 60
        assert policy.normal_sample_interval == 600
        assert policy.violation_severity_threshold == 0.7
        assert policy.save_normal_summary is False


class TestDetectionApplicationService:
    """测试检测应用服务"""

    @pytest.fixture
    def mock_pipeline(self):
        """创建模拟检测管道"""
        pipeline = Mock()
        # 创建模拟检测结果
        detection_result = DetectionResult(
            person_detections=[
                {
                    "bbox": [100, 100, 200, 200],
                    "confidence": 0.9,
                    "track_id": 1,
                }
            ],
            hairnet_results=[
                {
                    "has_hairnet": False,  # 违规：未戴发网
                    "confidence": 0.8,
                    "track_id": 1,
                    "bbox": [100, 100, 120, 120],
                }
            ],
            handwash_results=[],
            sanitize_results=[],
            annotated_image=None,
            processing_times={},  # 添加缺失的参数
        )
        pipeline.detect_comprehensive.return_value = detection_result
        return pipeline

    @pytest.fixture
    def mock_domain_service(self):
        """创建模拟领域服务"""
        service = AsyncMock()
        # 模拟返回检测记录
        mock_record = Mock()
        mock_record.id = "test_detection_123"
        mock_record.metadata = {
            "quality_analysis": {"score": 0.85},
            "violations": [{"type": "no_hairnet"}],
        }
        service.process_detection.return_value = mock_record
        return service

    @pytest.fixture
    def app_service(self, mock_pipeline, mock_domain_service):
        """创建应用服务实例"""
        save_policy = SavePolicy(strategy=SaveStrategy.SMART)
        return DetectionApplicationService(
            detection_pipeline=mock_pipeline,
            detection_domain_service=mock_domain_service,
            save_policy=save_policy,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试违规分析
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_analyze_violations_no_violations(self, app_service):
        """测试无违规情况"""
        detection_result = DetectionResult(
            person_detections=[{"bbox": [0, 0, 100, 100]}],
            hairnet_results=[{"has_hairnet": True}],
            handwash_results=[],
            sanitize_results=[],
            annotated_image=None,
            processing_times={},
        )

        has_violations, severity = app_service._analyze_violations(detection_result)
        assert has_violations is False
        assert severity == 0.0

    def test_analyze_violations_with_hairnet_violation(self, app_service):
        """测试发网违规"""
        detection_result = DetectionResult(
            person_detections=[{"bbox": [0, 0, 100, 100]}],
            hairnet_results=[{"has_hairnet": False, "confidence": 0.9}],
            handwash_results=[],
            sanitize_results=[],
            annotated_image=None,
            processing_times={},
        )

        has_violations, severity = app_service._analyze_violations(detection_result)
        assert has_violations is True
        assert severity == 0.8  # 发网违规严重程度

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试智能保存决策
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_should_save_all_strategy(self, app_service):
        """测试ALL策略 - 按间隔保存所有"""
        app_service.save_policy.strategy = SaveStrategy.ALL
        app_service.save_policy.save_interval = 30

        # 第30帧应该保存
        assert app_service._should_save_detection(30, False, 0.0) is True
        # 第31帧不应该保存
        assert app_service._should_save_detection(31, False, 0.0) is False
        # 第60帧应该保存
        assert app_service._should_save_detection(60, False, 0.0) is True

    def test_should_save_violations_only_strategy(self, app_service):
        """测试VIOLATIONS_ONLY策略 - 仅保存违规"""
        app_service.save_policy.strategy = SaveStrategy.VIOLATIONS_ONLY
        app_service.save_policy.violation_severity_threshold = 0.5

        # 无违规不保存
        assert app_service._should_save_detection(1, False, 0.0) is False
        # 有违规但严重程度低于阈值不保存
        assert app_service._should_save_detection(1, True, 0.3) is False
        # 有违规且严重程度高于阈值保存
        assert app_service._should_save_detection(1, True, 0.7) is True

    def test_should_save_smart_strategy(self, app_service):
        """测试SMART策略 - 智能保存"""
        app_service.save_policy.strategy = SaveStrategy.SMART
        app_service.save_policy.normal_sample_interval = 300
        app_service.save_policy.violation_severity_threshold = 0.5

        # 违规必保存
        assert app_service._should_save_detection(1, True, 0.7) is True
        # 正常样本采样间隔保存
        assert app_service._should_save_detection(300, False, 0.0) is True
        # 其他情况不保存
        assert app_service._should_save_detection(150, False, 0.0) is False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试数据转换
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_convert_to_domain_format(self, app_service):
        """测试检测结果转换为领域模型格式"""
        detection_result = DetectionResult(
            person_detections=[
                {
                    "bbox": [100, 100, 200, 200],
                    "confidence": 0.9,
                    "track_id": 1,
                }
            ],
            hairnet_results=[
                {
                    "has_hairnet": False,
                    "confidence": 0.8,
                    "track_id": 1,
                    "bbox": [100, 100, 120, 120],
                }
            ],
            handwash_results=[],
            sanitize_results=[],
            annotated_image=None,
            processing_times={},
        )

        objects = app_service._convert_to_domain_format(detection_result)

        # 应该有2个对象：人体 + 发网
        assert len(objects) == 2

        # 检查人体检测对象
        person_obj = objects[0]
        assert person_obj["class_name"] == "person"
        assert person_obj["confidence"] == 0.9
        assert person_obj["track_id"] == 1

        # 检查发网检测对象
        hairnet_obj = objects[1]
        assert hairnet_obj["class_name"] == "no_hairnet"
        assert hairnet_obj["confidence"] == 0.8
        assert hairnet_obj["metadata"]["has_hairnet"] is False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试单张图片检测
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_process_image_detection(
        self, app_service, mock_pipeline, mock_domain_service
    ):
        """测试单张图片检测"""
        # 创建模拟图像字节
        image_bytes = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8).tobytes()

        with patch("cv2.imdecode") as mock_imdecode:
            mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

            result = await app_service.process_image_detection(
                camera_id="test_cam",
                image_bytes=image_bytes,
                save_to_db=True,
            )

            # 验证结果
            assert result["ok"] is True
            assert result["camera_id"] == "test_cam"
            assert result["detection_id"] == "test_detection_123"
            assert result["saved_to_db"] is True
            assert "result" in result
            assert result["result"]["has_violations"] is True

            # 验证调用
            mock_pipeline.detect_comprehensive.assert_called_once()
            mock_domain_service.process_detection.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_image_detection_no_save(
        self, app_service, mock_pipeline, mock_domain_service
    ):
        """测试单张图片检测（不保存）"""
        image_bytes = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8).tobytes()

        with patch("cv2.imdecode") as mock_imdecode:
            mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

            result = await app_service.process_image_detection(
                camera_id="test_cam",
                image_bytes=image_bytes,
                save_to_db=False,
            )

            # 验证结果
            assert result["ok"] is True
            assert result["saved_to_db"] is False
            assert result["detection_id"].startswith("temp_")

            # 验证不调用领域服务
            mock_domain_service.process_detection.assert_not_called()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试实时流检测
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_process_realtime_stream_with_violation(
        self, app_service, mock_pipeline, mock_domain_service
    ):
        """测试实时流检测（有违规）"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 设置为SMART策略
        app_service.save_policy.strategy = SaveStrategy.SMART
        app_service.save_policy.violation_severity_threshold = 0.5

        result = await app_service.process_realtime_stream(
            camera_id="test_cam", frame=frame, frame_count=1
        )

        # 验证结果
        assert result["ok"] is True
        assert result["camera_id"] == "test_cam"
        assert result["frame_count"] == 1
        assert result["result"]["has_violations"] is True
        # 违规应该被保存（SMART策略）
        assert result["saved_to_db"] is True
        assert result["save_reason"] is not None

    @pytest.mark.asyncio
    async def test_process_realtime_stream_no_violation(
        self, app_service, mock_pipeline, mock_domain_service
    ):
        """测试实时流检测（无违规）"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 修改模拟管道返回无违规结果
        detection_result = DetectionResult(
            person_detections=[{"bbox": [0, 0, 100, 100]}],
            hairnet_results=[{"has_hairnet": True}],
            handwash_results=[],
            sanitize_results=[],
            annotated_image=None,
            processing_times={},
        )
        mock_pipeline.detect_comprehensive.return_value = detection_result

        # 设置为VIOLATIONS_ONLY策略
        app_service.save_policy.strategy = SaveStrategy.VIOLATIONS_ONLY

        result = await app_service.process_realtime_stream(
            camera_id="test_cam", frame=frame, frame_count=1
        )

        # 验证结果
        assert result["ok"] is True
        assert result["result"]["has_violations"] is False
        # 无违规不应该被保存（VIOLATIONS_ONLY策略）
        assert result["saved_to_db"] is False
        assert result["detection_id"] is None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 测试保存原因追踪
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_save_reason_violation(self, app_service):
        """测试保存原因（违规）"""
        app_service.save_policy.strategy = SaveStrategy.SMART

        reason = app_service._get_save_reason(
            frame_count=1, has_violations=True, violation_severity=0.8, was_saved=True
        )

        assert reason is not None
        assert "violation_detected" in reason
        assert "0.80" in reason

    def test_get_save_reason_normal_sample(self, app_service):
        """测试保存原因（正常样本）"""
        app_service.save_policy.strategy = SaveStrategy.SMART
        app_service.save_policy.normal_sample_interval = 300

        reason = app_service._get_save_reason(
            frame_count=300,
            has_violations=False,
            violation_severity=0.0,
            was_saved=True,
        )

        assert reason is not None
        assert "normal_sample" in reason
        assert "300" in reason

    def test_get_save_reason_not_saved(self, app_service):
        """测试保存原因（未保存）"""
        reason = app_service._get_save_reason(
            frame_count=1, has_violations=False, violation_severity=0.0, was_saved=False
        )

        assert reason is None


class TestSaveStrategyEnum:
    """测试保存策略枚举"""

    def test_save_strategy_values(self):
        """测试保存策略枚举值"""
        assert SaveStrategy.ALL.value == "all"
        assert SaveStrategy.VIOLATIONS_ONLY.value == "violations_only"
        assert SaveStrategy.INTERVAL.value == "interval"
        assert SaveStrategy.SMART.value == "smart"

    def test_save_strategy_from_string(self):
        """测试从字符串创建保存策略"""
        assert SaveStrategy["ALL"] == SaveStrategy.ALL
        assert SaveStrategy["VIOLATIONS_ONLY"] == SaveStrategy.VIOLATIONS_ONLY
        assert SaveStrategy["INTERVAL"] == SaveStrategy.INTERVAL
        assert SaveStrategy["SMART"] == SaveStrategy.SMART
