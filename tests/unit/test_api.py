"""API接口测试模块.

测试FastAPI应用程序的各个端点.
"""
import io
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api.app import app
from src.services.region_service import get_region_service


class TestAPIEndpoints:
    """API端点测试类."""

    def setup_method(self):
        """测试方法设置."""
        self.client = TestClient(app)
        # 清除之前的依赖覆盖
        app.dependency_overrides.clear()

    def teardown_method(self):
        """测试方法清理."""
        # 清除依赖覆盖
        app.dependency_overrides.clear()

    def test_health_check(self):
        """测试健康检查端点."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_redirect(self):
        """测试根路径重定向."""
        response = self.client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/frontend/index.html"

    def test_detect_image_endpoint(self):
        """测试图像检测端点."""
        # 模拟检测应用服务
        from src.api.dependencies import get_detection_app_service
        from src.application.detection_application_service import (
            DetectionApplicationService,
        )

        async def mock_process_image_detection(*args, **kwargs):
            return {
                "ok": True,
                "detection_id": "test_detection_123",
                "filename": "test.jpg",
                "detection_type": "image",
                "result": {
                    "person_count": 2,
                    "has_violations": False,
                    "hairnet_results": [],
                },
                "saved_to_db": True,
                "status": "success",
            }

        mock_app_service = Mock(spec=DetectionApplicationService)
        mock_app_service.process_image_detection = mock_process_image_detection
        app.dependency_overrides[get_detection_app_service] = lambda: mock_app_service

        # 创建测试图像文件
        test_image_data = b"fake_image_data"
        files = {"file": ("test.jpg", io.BytesIO(test_image_data), "image/jpeg")}

        response = self.client.post("/api/v1/detect/image", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["filename"] == "test.jpg"
        assert "detection_id" in result
        assert "result" in result

    def test_detect_hairnet_endpoint(self):
        """测试发网检测端点."""
        # 模拟检测应用服务
        from src.api.dependencies import get_detection_app_service
        from src.application.detection_application_service import (
            DetectionApplicationService,
        )

        async def mock_process_image_detection(*args, **kwargs):
            return {
                "ok": True,
                "detection_id": "test_detection_123",
                "filename": "test.jpg",
                "detection_type": "hairnet",
                "result": {
                    "person_count": 2,
                    "has_violations": False,
                    "hairnet_results": [{"person_id": 1, "hairnet_detected": True}],
                },
                "saved_to_db": True,
                "status": "success",
            }

        mock_app_service = Mock(spec=DetectionApplicationService)
        mock_app_service.process_image_detection = mock_process_image_detection
        app.dependency_overrides[get_detection_app_service] = lambda: mock_app_service

        # 创建测试图像文件
        test_image_data = b"fake_image_data"
        files = {"file": ("test.jpg", io.BytesIO(test_image_data), "image/jpeg")}

        response = self.client.post("/api/v1/detect/hairnet", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["filename"] == "test.jpg"
        assert result["detection_type"] == "hairnet"
        assert "results" in result

    def test_detect_image_no_file(self):
        """测试图像检测端点无文件情况."""
        response = self.client.post("/api/v1/detect/image")
        assert response.status_code == 422  # Unprocessable Entity

    def test_detect_hairnet_no_file(self):
        """测试发网检测端点无文件情况."""
        response = self.client.post("/api/v1/detect/hairnet")
        assert response.status_code == 422  # Unprocessable Entity

    def test_detect_image_no_pipeline(self):
        """测试图像检测端点管道未初始化情况."""
        # 模拟应用服务未初始化
        from src.api.dependencies import get_detection_app_service

        app.dependency_overrides[get_detection_app_service] = lambda: None

        test_image_data = b"fake_image_data"
        files = {"file": ("test.jpg", io.BytesIO(test_image_data), "image/jpeg")}

        response = self.client.post("/api/v1/detect/image", files=files)

        assert response.status_code == 500
        assert "检测服务未初始化" in response.json()["detail"]

    def test_detect_hairnet_no_pipeline(self):
        """测试发网检测端点管道未初始化情况."""
        # 模拟应用服务未初始化
        from src.api.dependencies import get_detection_app_service

        app.dependency_overrides[get_detection_app_service] = lambda: None

        test_image_data = b"fake_image_data"
        files = {"file": ("test.jpg", io.BytesIO(test_image_data), "image/jpeg")}

        response = self.client.post("/api/v1/detect/hairnet", files=files)

        assert response.status_code == 500
        assert "检测服务未初始化" in response.json()["detail"]

    def test_realtime_statistics_endpoint(self):
        """测试实时统计端点."""
        # 模拟区域服务
        mock_region_service = Mock()
        app.dependency_overrides[get_region_service] = lambda: mock_region_service

        response = self.client.get("/api/v1/statistics/realtime")

        assert response.status_code == 200
        result = response.json()

        # 验证返回数据结构
        assert "timestamp" in result
        assert "system_status" in result
        assert "detection_stats" in result
        assert "region_stats" in result
        assert "performance_metrics" in result
        assert "alerts" in result

        # 验证检测统计数据结构
        detection_stats = result["detection_stats"]
        assert "total_detections_today" in detection_stats
        assert "handwashing_detections" in detection_stats
        assert "disinfection_detections" in detection_stats
        assert "hairnet_detections" in detection_stats
        assert "violation_count" in detection_stats

    def test_realtime_statistics_no_region_service(self):
        """测试实时统计端点无区域服务情况."""
        app.dependency_overrides[get_region_service] = lambda: None
        response = self.client.get("/api/v1/statistics/realtime")

        assert response.status_code == 200
        result = response.json()
        assert result["system_status"] == "active"

    def test_statistics_endpoint(self):
        """测试统计信息端点."""
        mock_region_service = Mock()
        app.dependency_overrides[get_region_service] = lambda: mock_region_service

        response = self.client.get("/api/v1/statistics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "counts_by_type" in data

    def test_violations_endpoint(self):
        """测试违规记录端点."""
        mock_region_service = Mock()
        app.dependency_overrides[get_region_service] = lambda: mock_region_service

        response = self.client.get("/api/v1/records/violations")
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data
        assert "total" in data


class TestAPIErrorHandling:
    """API错误处理测试类."""

    def setup_method(self):
        """测试方法设置."""
        self.client = TestClient(app)

    def test_invalid_endpoint(self):
        """测试无效端点."""
        response = self.client.get("/api/v1/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试不允许的HTTP方法."""
        response = self.client.put("/health")
        assert response.status_code == 405
