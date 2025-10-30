"""
依赖注入单元测试
测试服务容器的功能
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from src.container.service_container import ServiceContainer
from src.interfaces.detection.detector_interface import (
    DetectedObject,
    DetectionResult,
    IDetector,
)
from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)
from src.interfaces.tracking.tracker_interface import ITracker, Track, TrackingResult


class TestServiceContainer:
    """测试服务容器"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.container = ServiceContainer()

    def test_register_singleton(self):
        """测试注册单例服务"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        self.container.register_singleton(IDetector, MockDetector)
        assert self.container.is_registered(IDetector)

    def test_register_factory(self):
        """测试注册工厂服务"""

        def create_detector():
            class MockDetector(IDetector):
                async def detect(self, image):
                    return DetectionResult([], 0.0)

                def get_model_info(self):
                    return {"type": "mock"}

                def is_available(self):
                    return True

                def get_supported_classes(self):
                    return ["person"]

                def set_confidence_threshold(self, threshold):
                    pass

                def get_confidence_threshold(self):
                    return 0.5

            return MockDetector()

        self.container.register_factory(IDetector, create_detector)
        assert self.container.is_registered(IDetector)

    def test_register_instance(self):
        """测试注册实例"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        instance = MockDetector()
        self.container.register_instance(IDetector, instance)
        assert self.container.is_registered(IDetector)

    def test_get_singleton_service(self):
        """测试获取单例服务"""

        class MockDetector(IDetector):
            def __init__(self):
                self.created_at = datetime.now()

            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        self.container.register_singleton(IDetector, MockDetector)

        # 获取两次，应该是同一个实例
        service1 = self.container.get(IDetector)
        service2 = self.container.get(IDetector)

        assert service1 is service2
        assert isinstance(service1, MockDetector)

    def test_get_factory_service(self):
        """测试获取工厂服务"""

        class MockDetector(IDetector):
            def __init__(self):
                self.created_at = datetime.now()

            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        def create_detector():
            return MockDetector()

        self.container.register_factory(IDetector, create_detector)

        # 获取两次，应该是不同的实例
        service1 = self.container.get(IDetector)
        service2 = self.container.get(IDetector)

        assert service1 is not service2
        assert isinstance(service1, MockDetector)
        assert isinstance(service2, MockDetector)

    def test_get_instance_service(self):
        """测试获取实例服务"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        instance = MockDetector()
        self.container.register_instance(IDetector, instance)

        # 获取的应该是同一个实例
        service = self.container.get(IDetector)
        assert service is instance

    def test_get_unregistered_service(self):
        """测试获取未注册的服务"""
        with pytest.raises(ValueError, match="未找到服务"):
            self.container.get(IDetector)

    def test_get_registered_services(self):
        """测试获取已注册服务列表"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        self.container.register_singleton(IDetector, MockDetector)
        services = self.container.get_registered_services()

        assert "IDetector" in services
        assert "Singleton -> MockDetector" in services["IDetector"]

    def test_clear_cache(self):
        """测试清空缓存"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        self.container.register_singleton(IDetector, MockDetector)

        # 获取服务，创建单例
        service1 = self.container.get(IDetector)

        # 清空缓存
        self.container.clear_cache()

        # 再次获取，应该是新实例
        service2 = self.container.get(IDetector)
        assert service1 is not service2

    def test_reset(self):
        """测试重置容器"""

        class MockDetector(IDetector):
            async def detect(self, image):
                return DetectionResult([], 0.0)

            def get_model_info(self):
                return {"type": "mock"}

            def is_available(self):
                return True

            def get_supported_classes(self):
                return ["person"]

            def set_confidence_threshold(self, threshold):
                pass

            def get_confidence_threshold(self):
                return 0.5

        self.container.register_singleton(IDetector, MockDetector)
        assert self.container.is_registered(IDetector)

        self.container.reset()
        assert not self.container.is_registered(IDetector)


class TestDetectionServiceDI:
    """测试依赖注入的检测服务"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建模拟服务
        self.mock_detector = Mock(spec=IDetector)
        self.mock_tracker = Mock(spec=ITracker)
        self.mock_repository = Mock(spec=IDetectionRepository)

        # 配置模拟行为
        self.mock_detector.get_model_info.return_value = {"type": "mock"}
        self.mock_detector.is_available.return_value = True
        self.mock_detector.get_supported_classes.return_value = ["person"]
        self.mock_detector.get_confidence_threshold.return_value = 0.5

        self.mock_tracker.get_track_count.return_value = 0

        # 创建容器并注册模拟服务
        self.container = ServiceContainer()
        self.container.register_instance(IDetector, self.mock_detector)
        self.container.register_instance(ITracker, self.mock_tracker)
        self.container.register_instance(IDetectionRepository, self.mock_repository)

    def test_detection_service_initialization(self):
        """测试检测服务初始化"""
        # 临时替换全局容器
        import src.container.service_container
        from src.services.detection_service_di import DetectionServiceDI

        original_container = src.container.service_container.container
        src.container.service_container.container = self.container

        try:
            service = DetectionServiceDI()
            assert service.detector is self.mock_detector
            assert service.tracker is self.mock_tracker
            assert service.repository is self.mock_repository
        finally:
            # 恢复原始容器
            src.container.service_container.container = original_container

    @pytest.mark.asyncio
    async def test_process_image(self):
        """测试处理图像"""
        from src.services.detection_service_di import DetectionServiceDI

        # 配置模拟行为
        detection_result = DetectionResult(
            objects=[DetectedObject(0, "person", 0.95, [100, 100, 200, 200])],
            processing_time=0.05,
            frame_id=1,
            timestamp=datetime.now(),
        )
        self.mock_detector.detect = AsyncMock(return_value=detection_result)

        tracking_result = TrackingResult(
            tracks=[
                Track(1, 0, "person", [100, 100, 200, 200], 0.95, 1, 1, 0, "confirmed")
            ],
            frame_id=1,
            processing_time=0.01,
        )
        self.mock_tracker.track = AsyncMock(return_value=tracking_result)
        self.mock_repository.save = AsyncMock(return_value="test-id")

        # 临时替换全局容器
        import src.container.service_container

        original_container = src.container.service_container.container
        src.container.service_container.container = self.container

        try:
            service = DetectionServiceDI()
            image = np.zeros((480, 640, 3), dtype=np.uint8)
            result = await service.process_image(image, "cam1", 1)

            assert result is detection_result
            self.mock_detector.detect.assert_called_once_with(image)
            self.mock_tracker.track.assert_called_once()
            self.mock_repository.save.assert_called_once()
        finally:
            # 恢复原始容器
            src.container.service_container.container = original_container


if __name__ == "__main__":
    pytest.main([__file__])
