"""
优化检测管道集成测试

测试所有优化功能协同工作
"""

import logging

import numpy as np
import pytest

from src.core.behavior import BehaviorRecognizer
from src.core.frame_metadata import FrameSource
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.detector import HumanDetector

logger = logging.getLogger(__name__)


class TestOptimizedPipelineIntegration:
    """优化检测管道集成测试类"""

    @pytest.fixture
    def test_image(self):
        """创建测试图像"""
        image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        return image

    @pytest.fixture
    def optimized_pipeline(self):
        """创建优化的检测管道"""
        human_detector = HumanDetector()
        behavior_recognizer = BehaviorRecognizer()

        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            behavior_recognizer=behavior_recognizer,
            enable_cache=True,
            enable_state_management=True,
            enable_async=False,  # 暂时禁用异步（需要异步环境）
        )
        return pipeline

    def test_end_to_end_detection(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试端到端检测流程"""
        # 执行完整检测
        result = optimized_pipeline.detect_comprehensive(
            test_image,
            enable_hairnet=True,
            enable_handwash=True,
            enable_sanitize=True,
        )

        # 验证结果结构
        assert result is not None
        assert hasattr(result, "person_detections")
        assert hasattr(result, "hairnet_results")
        assert hasattr(result, "handwash_results")
        assert hasattr(result, "sanitize_results")
        assert hasattr(result, "processing_times")

        # 验证处理时间记录
        assert "total" in result.processing_times
        assert result.processing_times["total"] > 0

    def test_frame_metadata_integration(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试FrameMetadata集成"""
        # 验证FrameMetadataManager已初始化
        assert optimized_pipeline.frame_metadata_manager is not None

        # 创建FrameMetadata
        frame_meta = optimized_pipeline.frame_metadata_manager.create_frame_metadata(
            frame=test_image,
            camera_id="test_camera",
            source=FrameSource.REALTIME_STREAM,
        )

        # 验证FrameMetadata
        assert frame_meta is not None
        assert frame_meta.camera_id == "test_camera"
        assert frame_meta.frame_id is not None
        assert frame_meta.timestamp is not None

    def test_state_management_integration(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试状态管理集成"""
        # 验证StateManager已初始化
        if optimized_pipeline.enable_state_management:
            assert optimized_pipeline.state_manager is not None

            # 执行多次检测，验证状态管理
            for i in range(5):
                result = optimized_pipeline.detect_comprehensive(
                    test_image,
                    enable_hairnet=True,
                )

                # 验证检测结果
                assert result is not None

    def test_roi_optimization_integration(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试ROI优化集成"""
        # 执行检测（ROI优化自动启用）
        result = optimized_pipeline.detect_comprehensive(
            test_image,
            enable_hairnet=True,
            enable_handwash=True,
        )

        # 验证检测结果
        assert result is not None
        assert result.person_detections is not None
        assert result.hairnet_results is not None

        # 验证处理时间记录
        if "hairnet_detection" in result.processing_times:
            hairnet_time = result.processing_times["hairnet_detection"]
            logger.info(f"发网检测耗时: {hairnet_time:.3f}s")

    def test_cache_integration(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试缓存集成"""
        # 第一次检测（缓存未命中）
        result1 = optimized_pipeline.detect_comprehensive(
            test_image,
            force_refresh=False,
        )
        time1 = result1.processing_times.get("total", 0)

        # 第二次检测（应该命中缓存）
        result2 = optimized_pipeline.detect_comprehensive(
            test_image,
            force_refresh=False,
        )
        time2 = result2.processing_times.get("total", 0)

        logger.info(f"第一次检测耗时: {time1:.3f}s")
        logger.info(f"第二次检测耗时: {time2:.3f}s")

        # 验证缓存生效（第二次应该更快）
        if optimized_pipeline.enable_cache:
            assert time2 <= time1, "缓存应该使第二次检测更快"

    def test_backward_compatibility(
        self,
        test_image,
        optimized_pipeline,
    ):
        """测试向后兼容性"""
        # 使用旧的API调用方式
        result = optimized_pipeline.detect(
            test_image,
            enable_hairnet=True,
            enable_handwash=True,
            enable_sanitize=True,
        )

        # 验证结果格式兼容
        assert result is not None
        assert hasattr(result, "person_detections")
        assert isinstance(result.person_detections, list)
