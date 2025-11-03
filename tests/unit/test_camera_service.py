"""CameraService单元测试."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.repositories.camera_repository import ICameraRepository
from src.domain.services.camera_service import CameraService


class MockCameraRepository(ICameraRepository):
    """模拟摄像头仓储."""

    def __init__(self):
        self._cameras: dict[str, Camera] = {}

    async def save(self, camera: Camera) -> str:
        self._cameras[camera.id] = camera
        return camera.id

    async def find_by_id(self, camera_id: str) -> Camera | None:
        return self._cameras.get(camera_id)

    async def find_by_region_id(self, region_id: str) -> list[Camera]:
        return [c for c in self._cameras.values() if c.region_id == region_id]

    async def find_all(self) -> list[Camera]:
        return list(self._cameras.values())

    async def find_active(self) -> list[Camera]:
        return [c for c in self._cameras.values() if c.status == CameraStatus.ACTIVE]

    async def count(self) -> int:
        return len(self._cameras)

    async def delete_by_id(self, camera_id: str) -> bool:
        if camera_id in self._cameras:
            del self._cameras[camera_id]
            return True
        return False

    async def exists(self, camera_id: str) -> bool:
        return camera_id in self._cameras


@pytest.fixture
def mock_repository():
    """创建模拟仓储."""
    return MockCameraRepository()


@pytest.fixture
def temp_yaml_file():
    """创建临时YAML文件."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml_path = f.name
        yaml.dump({"cameras": []}, f)
    yield yaml_path
    if os.path.exists(yaml_path):
        os.unlink(yaml_path)


@pytest.fixture
def camera_service(mock_repository, temp_yaml_file):
    """创建CameraService实例."""
    return CameraService(mock_repository, temp_yaml_file)


@pytest.mark.asyncio
class TestCameraServiceCreate:
    """测试CameraService.create_camera方法."""

    async def test_create_camera_success(self, camera_service):
        """测试成功创建摄像头."""
        camera_data = {
            "id": "test_cam_001",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "location": "测试位置",
            "active": True,
        }

        result = await camera_service.create_camera(camera_data)

        assert result["ok"] is True
        assert "camera" in result
        assert result["camera"]["id"] == "test_cam_001"
        assert result["camera"]["name"] == "测试摄像头"

        # 验证仓储中已保存
        saved_camera = await camera_service.camera_repository.find_by_id("test_cam_001")
        assert saved_camera is not None
        assert saved_camera.name == "测试摄像头"

        # 验证YAML文件中已保存
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            assert len(cameras) == 1
            assert cameras[0]["id"] == "test_cam_001"
            assert cameras[0]["source"] == "rtsp://example.com/stream"

    async def test_create_camera_missing_required_fields(self, camera_service):
        """测试缺少必填字段."""
        camera_data = {
            "id": "test_cam_002",
            "name": "测试摄像头",
            # 缺少source字段
        }

        with pytest.raises(ValueError, match="缺少必填字段: source"):
            await camera_service.create_camera(camera_data)

    async def test_create_camera_duplicate_id(self, camera_service):
        """测试创建重复ID的摄像头."""
        camera_data = {
            "id": "test_cam_003",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }

        # 第一次创建
        await camera_service.create_camera(camera_data)

        # 第二次创建（应该失败）
        with pytest.raises(ValueError, match="摄像头ID已存在"):
            await camera_service.create_camera(camera_data)

    async def test_create_camera_with_metadata(self, camera_service):
        """测试创建包含元数据的摄像头."""
        camera_data = {
            "id": "test_cam_004",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "regions_file": "config/regions.json",
            "profile": "accurate",
            "device": "auto",
            "active": True,
        }

        result = await camera_service.create_camera(camera_data)

        assert result["ok"] is True

        # 验证YAML中包含所有字段
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            assert len(cameras) == 1
            assert cameras[0]["source"] == "rtsp://example.com/stream"
            assert cameras[0]["regions_file"] == "config/regions.json"
            assert cameras[0]["profile"] == "accurate"

    async def test_create_camera_inactive(self, camera_service):
        """测试创建非活跃摄像头."""
        camera_data = {
            "id": "test_cam_005",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "active": False,
        }

        result = await camera_service.create_camera(camera_data)

        assert result["ok"] is True

        # 验证状态为INACTIVE
        saved_camera = await camera_service.camera_repository.find_by_id("test_cam_005")
        assert saved_camera.status == CameraStatus.INACTIVE

    async def test_create_camera_without_yaml(self, mock_repository):
        """测试在没有YAML文件的情况下创建摄像头."""
        service = CameraService(mock_repository, None)

        camera_data = {
            "id": "test_cam_006",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }

        result = await service.create_camera(camera_data)

        assert result["ok"] is True
        assert result["camera"]["id"] == "test_cam_006"


@pytest.mark.asyncio
class TestCameraServiceUpdate:
    """测试CameraService.update_camera方法."""

    async def test_update_camera_success(self, camera_service):
        """测试成功更新摄像头."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_update",
            "name": "原始名称",
            "source": "rtsp://example.com/stream",
        }
        await camera_service.create_camera(camera_data)

        # 更新摄像头
        updates = {"name": "更新后的名称", "location": "新位置"}

        result = await camera_service.update_camera("test_cam_update", updates)

        assert result["status"] == "success"
        assert "camera" in result
        assert result["camera"]["name"] == "更新后的名称"
        assert result["camera"]["location"] == "新位置"

        # 验证仓储中已更新
        updated_camera = await camera_service.camera_repository.find_by_id("test_cam_update")
        assert updated_camera.name == "更新后的名称"
        assert updated_camera.location == "新位置"

    async def test_update_camera_not_found(self, camera_service):
        """测试更新不存在的摄像头."""
        updates = {"name": "更新后的名称"}

        with pytest.raises(ValueError, match="摄像头不存在"):
            await camera_service.update_camera("nonexistent_cam", updates)

    async def test_update_camera_source(self, camera_service):
        """测试更新摄像头source."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_source",
            "name": "测试摄像头",
            "source": "rtsp://old.com/stream",
        }
        await camera_service.create_camera(camera_data)

        # 更新source
        updates = {"source": "rtsp://new.com/stream"}

        result = await camera_service.update_camera("test_cam_source", updates)

        assert result["status"] == "success"

        # 验证YAML中已更新
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            cam = next((c for c in cameras if c["id"] == "test_cam_source"), None)
            assert cam is not None
            assert cam["source"] == "rtsp://new.com/stream"

    async def test_update_camera_status(self, camera_service):
        """测试更新摄像头状态."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_status",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "active": True,
        }
        await camera_service.create_camera(camera_data)

        # 更新状态
        updates = {"active": False}

        result = await camera_service.update_camera("test_cam_status", updates)

        assert result["status"] == "success"

        # 验证状态已更新
        updated_camera = await camera_service.camera_repository.find_by_id("test_cam_status")
        assert updated_camera.status == CameraStatus.INACTIVE

    async def test_update_camera_add_to_yaml_if_not_exists(self, camera_service):
        """测试更新YAML中不存在的摄像头（应该添加）."""
        # 直接在仓储中创建，但不添加到YAML
        camera = Camera(
            id="test_cam_new",
            name="测试摄像头",
            location="测试位置",
        )
        camera.metadata["source"] = "rtsp://example.com/stream"
        await camera_service.camera_repository.save(camera)

        # 更新（应该添加到YAML）
        updates = {"name": "更新后的名称"}

        result = await camera_service.update_camera("test_cam_new", updates)

        assert result["status"] == "success"

        # 验证YAML中已添加
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            cam = next((c for c in cameras if c["id"] == "test_cam_new"), None)
            assert cam is not None


@pytest.mark.asyncio
class TestCameraServiceDelete:
    """测试CameraService.delete_camera方法."""

    async def test_delete_camera_success(self, camera_service):
        """测试成功删除摄像头."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_delete",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }
        await camera_service.create_camera(camera_data)

        # 删除摄像头
        result = await camera_service.delete_camera("test_cam_delete")

        assert result["status"] == "success"

        # 验证仓储中已删除
        deleted_camera = await camera_service.camera_repository.find_by_id("test_cam_delete")
        assert deleted_camera is None

        # 验证YAML中已删除
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            cam = next((c for c in cameras if c["id"] == "test_cam_delete"), None)
            assert cam is None

    async def test_delete_camera_not_found(self, camera_service):
        """测试删除不存在的摄像头."""
        with pytest.raises(ValueError, match="摄像头不存在"):
            await camera_service.delete_camera("nonexistent_cam")

    async def test_delete_camera_without_yaml(self, mock_repository):
        """测试在没有YAML文件的情况下删除摄像头."""
        # 先创建摄像头
        camera = Camera(
            id="test_cam_no_yaml",
            name="测试摄像头",
            location="测试位置",
        )
        await mock_repository.save(camera)

        service = CameraService(mock_repository, None)

        # 删除摄像头
        result = await service.delete_camera("test_cam_no_yaml")

        assert result["status"] == "success"

        # 验证仓储中已删除
        deleted_camera = await mock_repository.find_by_id("test_cam_no_yaml")
        assert deleted_camera is None


@pytest.mark.asyncio
class TestCameraServiceYAML:
    """测试CameraService的YAML文件操作."""

    async def test_yaml_atomic_write(self, camera_service):
        """测试YAML原子写操作."""
        # 创建多个摄像头
        for i in range(3):
            camera_data = {
                "id": f"test_cam_{i}",
                "name": f"测试摄像头{i}",
                "source": f"rtsp://example.com/stream{i}",
            }
            await camera_service.create_camera(camera_data)

        # 验证所有摄像头都在YAML中
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            assert len(cameras) == 3

    async def test_yaml_read_error_handling(self, mock_repository, tmp_path):
        """测试YAML读取错误处理."""
        # 使用临时目录创建YAML文件路径
        yaml_path = tmp_path / "cameras.yaml"
        service = CameraService(mock_repository, str(yaml_path))

        camera_data = {
            "id": "test_cam_error",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }

        # 应该能正常创建（会创建目录和文件）
        result = await service.create_camera(camera_data)
        assert result["ok"] is True

    async def test_yaml_invalid_format_handling(self, mock_repository, temp_yaml_file):
        """测试YAML格式错误处理."""
        # 写入无效格式的YAML
        with open(temp_yaml_file, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content: [unclosed")

        service = CameraService(mock_repository, temp_yaml_file)

        # 读取应该能处理错误（返回空列表）
        config = service._read_yaml_config()
        assert config.get("cameras") == []

    async def test_yaml_preserves_metadata_fields(self, camera_service):
        """测试YAML保留元数据字段."""
        camera_data = {
            "id": "test_cam_meta",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "regions_file": "config/regions.json",
            "profile": "accurate",
            "device": "auto",
            "imgsz": "auto",
            "auto_tune": True,
            "auto_start": False,
            "env": {"KEY": "value"},
        }

        await camera_service.create_camera(camera_data)

        # 验证YAML中包含所有元数据字段
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            cameras = yaml_data.get("cameras", [])
            cam = cameras[0]
            assert cam["source"] == "rtsp://example.com/stream"
            assert cam["regions_file"] == "config/regions.json"
            assert cam["profile"] == "accurate"
            assert cam["device"] == "auto"
            assert cam.get("env") == {"KEY": "value"}


@pytest.mark.asyncio
class TestCameraServiceEdgeCases:
    """测试CameraService的边缘情况."""

    async def test_create_camera_with_default_values(self, camera_service):
        """测试使用默认值创建摄像头."""
        camera_data = {
            "id": "test_cam_default",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            # 不提供location、resolution、fps等
        }

        result = await camera_service.create_camera(camera_data)

        assert result["ok"] is True

        # 验证默认值
        saved_camera = await camera_service.camera_repository.find_by_id("test_cam_default")
        assert saved_camera.location == "unknown"
        assert saved_camera.resolution == (1920, 1080)
        assert saved_camera.fps == 25

    async def test_update_camera_partial_fields(self, camera_service):
        """测试部分字段更新."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_partial",
            "name": "原始名称",
            "source": "rtsp://original.com/stream",
            "location": "原始位置",
        }
        await camera_service.create_camera(camera_data)

        # 只更新name
        updates = {"name": "新名称"}

        result = await camera_service.update_camera("test_cam_partial", updates)

        assert result["status"] == "success"

        # 验证只有name更新，其他字段保持不变
        updated_camera = await camera_service.camera_repository.find_by_id("test_cam_partial")
        assert updated_camera.name == "新名称"
        assert updated_camera.location == "原始位置"

    async def test_create_camera_resolution_as_list(self, camera_service):
        """测试分辨率作为列表传入."""
        camera_data = {
            "id": "test_cam_res",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "resolution": [1280, 720],
        }

        result = await camera_service.create_camera(camera_data)

        assert result["ok"] is True

        saved_camera = await camera_service.camera_repository.find_by_id("test_cam_res")
        assert saved_camera.resolution == (1280, 720)

    async def test_update_camera_resolution_as_list(self, camera_service):
        """测试更新分辨率为列表."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_res_update",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
            "resolution": [1920, 1080],
        }
        await camera_service.create_camera(camera_data)

        # 更新分辨率
        updates = {"resolution": [1280, 720]}

        result = await camera_service.update_camera("test_cam_res_update", updates)

        assert result["status"] == "success"

        updated_camera = await camera_service.camera_repository.find_by_id("test_cam_res_update")
        assert updated_camera.resolution == (1280, 720)

    async def test_read_yaml_config_invalid_cameras_type(self, mock_repository, temp_yaml_file):
        """测试读取YAML配置时cameras字段不是列表的情况."""
        # 写入无效格式的YAML（cameras不是列表）
        with open(temp_yaml_file, "w", encoding="utf-8") as f:
            f.write("cameras: invalid\n")

        service = CameraService(mock_repository, temp_yaml_file)

        # 读取应该能处理错误（返回空列表）
        config = service._read_yaml_config()
        assert isinstance(config.get("cameras"), list)
        assert len(config.get("cameras", [])) == 0

    async def test_write_yaml_config_without_path(self, mock_repository):
        """测试在没有YAML路径的情况下写入配置."""
        service = CameraService(mock_repository, None)

        with pytest.raises(ValueError, match="摄像头YAML配置文件路径未配置"):
            service._write_yaml_config({"cameras": []})

    async def test_create_camera_duplicate_in_yaml(self, camera_service):
        """测试在YAML中创建重复ID的摄像头."""
        camera_data = {
            "id": "test_cam_dup",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }

        # 第一次创建
        await camera_service.create_camera(camera_data)

        # 直接在YAML中添加相同ID（模拟YAML已被外部修改的情况）
        # 先读取当前YAML
        with open(camera_service.cameras_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        
        # 添加重复ID
        yaml_data["cameras"].append({"id": "test_cam_dup", "name": "重复", "source": "rtsp://dup.com/stream"})
        
        with open(camera_service.cameras_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_data, f)

        # 第二次创建（应该失败，因为YAML中已存在，虽然数据库中不存在）
        # 注意：这种情况下，如果数据库中不存在但YAML中存在，create_camera会检查YAML
        # 但由于我们已经在数据库中创建了，所以会先检查数据库，数据库检查会失败
        # 但我们需要测试YAML检查逻辑，所以需要先从数据库中删除
        await camera_service.camera_repository.delete_by_id("test_cam_dup")
        
        # 现在YAML中有但数据库中无，创建应该失败
        with pytest.raises(ValueError, match="摄像头ID在配置文件中已存在"):
            await camera_service.create_camera(camera_data)

    async def test_create_camera_exception_handling(self, camera_service):
        """测试创建摄像头时的异常处理."""
        # 测试非ValueError的异常情况（例如仓储错误）
        camera_data = {
            "id": "test_cam_exception",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }

        # 模拟仓储异常
        original_save = camera_service.camera_repository.save
        
        async def mock_save_error(camera):
            raise RuntimeError("仓储保存失败")
        
        camera_service.camera_repository.save = mock_save_error

        try:
            with pytest.raises(RuntimeError, match="仓储保存失败"):
                await camera_service.create_camera(camera_data)
        finally:
            camera_service.camera_repository.save = original_save

    async def test_update_camera_exception_handling(self, camera_service):
        """测试更新摄像头时的异常处理."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_update_ex",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }
        await camera_service.create_camera(camera_data)

        # 模拟仓储异常
        original_save = camera_service.camera_repository.save
        
        async def mock_save_error(camera):
            raise RuntimeError("仓储保存失败")
        
        camera_service.camera_repository.save = mock_save_error

        try:
            with pytest.raises(RuntimeError, match="仓储保存失败"):
                await camera_service.update_camera("test_cam_update_ex", {"name": "新名称"})
        finally:
            camera_service.camera_repository.save = original_save

    async def test_delete_camera_exception_handling(self, camera_service):
        """测试删除摄像头时的异常处理."""
        # 先创建摄像头
        camera_data = {
            "id": "test_cam_delete_ex",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }
        await camera_service.create_camera(camera_data)

        # 模拟仓储异常
        original_delete = camera_service.camera_repository.delete_by_id
        
        async def mock_delete_error(camera_id):
            raise RuntimeError("仓储删除失败")
        
        camera_service.camera_repository.delete_by_id = mock_delete_error

        try:
            with pytest.raises(RuntimeError, match="仓储删除失败"):
                await camera_service.delete_camera("test_cam_delete_ex")
        finally:
            camera_service.camera_repository.delete_by_id = original_delete

    async def test_update_camera_without_save_attr(self, mock_repository, temp_yaml_file):
        """测试更新摄像头时仓储不支持save方法."""
        from unittest.mock import Mock
        
        # 创建一个没有save方法的mock仓储
        class MockRepoWithoutSave(MockCameraRepository):
            def __init__(self):
                super().__init__()
                # 移除save方法
                if hasattr(self, "save"):
                    self.__dict__.pop("save", None)
        
        no_save_repo = MockRepoWithoutSave()
        service = CameraService(no_save_repo, temp_yaml_file)
        
        # 创建摄像头（需要在mock中手动添加save方法，因为create需要）
        # 需要绑定方法到实例
        no_save_repo.save = lambda camera: MockCameraRepository.save(no_save_repo, camera)
        camera_data = {
            "id": "test_cam_no_save",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }
        await service.create_camera(camera_data)
        
        # 再次移除save方法
        if hasattr(no_save_repo, "save"):
            delattr(no_save_repo, "save")
        
        # 更新应该仍然成功（跳过数据库保存，但会更新YAML）
        result = await service.update_camera("test_cam_no_save", {"name": "新名称"})
        assert result["status"] == "success"

    async def test_delete_camera_without_delete_attr(self, mock_repository, temp_yaml_file):
        """测试删除摄像头时仓储不支持delete_by_id方法."""
        # 创建一个没有delete_by_id方法的mock仓储
        class MockRepoWithoutDelete(MockCameraRepository):
            def __init__(self):
                super().__init__()
                # 移除delete_by_id方法
                if hasattr(self, "delete_by_id"):
                    self.__dict__.pop("delete_by_id", None)
        
        no_delete_repo = MockRepoWithoutDelete()
        service = CameraService(no_delete_repo, temp_yaml_file)
        
        # 创建摄像头
        camera_data = {
            "id": "test_cam_no_delete",
            "name": "测试摄像头",
            "source": "rtsp://example.com/stream",
        }
        await service.create_camera(camera_data)
        
        # 删除应该仍然成功（跳过数据库删除，但会从YAML删除）
        result = await service.delete_camera("test_cam_no_delete")
        assert result["status"] == "success"

