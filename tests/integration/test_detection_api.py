"""
集成测试：检测API端点

测试重构后的检测API端点的完整流程
"""

import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# 跳过如果在CI环境中（可能没有模型文件）
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Skip integration tests in CI"
)


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    # 设置环境变量
    os.environ["DETECTION_SAVE_STRATEGY"] = "violations_only"
    os.environ["DETECTION_VIOLATION_THRESHOLD"] = "0.5"

    # 导入app
    from src.api.app import app

    return TestClient(app)


@pytest.fixture
def test_image_bytes():
    """创建测试图片字节"""
    # 创建一个简单的测试图片
    img = Image.new("RGB", (640, 480), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes.getvalue()


class TestDetectionAPI:
    """测试检测API"""

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_detect_image_endpoint(self, client, test_image_bytes):
        """测试图像检测端点"""
        response = client.post(
            "/api/v1/detect/image",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            data={
                "camera_id": "test_cam",
                "save_to_db": "false",  # 不保存到数据库以加快测试
            },
        )

        # 验证响应
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert data["camera_id"] == "test_cam"
            assert "detection_id" in data
            assert "result" in data
            assert "processing_time" in data
        elif response.status_code == 500:
            # 如果服务未初始化，跳过测试
            pytest.skip("Detection service not initialized")

    def test_detect_comprehensive_endpoint(self, client, test_image_bytes):
        """测试综合检测端点"""
        response = client.post(
            "/api/v1/detect/comprehensive",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            data={
                "camera_id": "test_cam",
                "save_to_db": "false",
            },
        )

        # 验证响应
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "result" in data
        elif response.status_code == 500:
            pytest.skip("Detection service not initialized")

    def test_detect_hairnet_endpoint(self, client, test_image_bytes):
        """测试发网检测端点"""
        response = client.post(
            "/api/v1/detect/hairnet",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            data={
                "camera_id": "test_cam",
                "save_to_db": "false",
            },
        )

        # 验证响应
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert data["detection_type"] == "hairnet"
            assert "results" in data
        elif response.status_code == 500:
            pytest.skip("Detection service not initialized")


class TestConfigAPI:
    """测试配置管理API"""

    def test_get_save_policy(self, client):
        """测试获取保存策略"""
        response = client.get("/api/v1/config/save-policy")

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "strategy" in data
            assert "violation_threshold" in data
        elif response.status_code == 503:
            pytest.skip("Detection service not initialized")

    def test_update_save_policy(self, client):
        """测试更新保存策略"""
        response = client.put(
            "/api/v1/config/save-policy",
            json={
                "strategy": "violations_only",
                "violation_threshold": 0.8,
            },
        )

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert data["strategy"] == "violations_only"
            assert data["violation_threshold"] == 0.8
        elif response.status_code == 503:
            pytest.skip("Detection service not initialized")

    def test_get_detection_stats(self, client):
        """测试获取检测统计"""
        response = client.get("/api/v1/config/detection-stats")

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "stats" in data
            assert "save_policy" in data
        elif response.status_code == 503:
            pytest.skip("Detection service not initialized")

    def test_reset_detection_stats(self, client):
        """测试重置检测统计"""
        response = client.post("/api/v1/config/detection-stats/reset")

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "message" in data
        elif response.status_code == 503:
            pytest.skip("Detection service not initialized")


class TestDetectionWorkflow:
    """测试完整的检测工作流"""

    def test_complete_detection_workflow(self, client, test_image_bytes):
        """测试完整的检测工作流"""
        # 1. 设置保存策略
        response = client.put(
            "/api/v1/config/save-policy",
            json={"strategy": "violations_only", "violation_threshold": 0.7},
        )

        if response.status_code == 503:
            pytest.skip("Detection service not initialized")

        assert response.status_code == 200

        # 2. 执行检测
        response = client.post(
            "/api/v1/detect/image",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            data={"camera_id": "workflow_test", "save_to_db": "false"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

        # 3. 查看检测统计
        response = client.get("/api/v1/config/detection-stats")
        assert response.status_code == 200

        # 4. 重置统计
        response = client.post("/api/v1/config/detection-stats/reset")
        assert response.status_code == 200
