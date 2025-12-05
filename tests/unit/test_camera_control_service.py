"""摄像头控制服务单元测试."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.camera_control_service import CameraControlService
from src.domain.services.camera_service import CameraService


@pytest.fixture
def mock_camera_service():
    """创建Mock摄像头服务."""
    from src.domain.entities.camera import Camera, CameraStatus
    from src.domain.repositories.camera_repository import ICameraRepository

    # 创建Mock仓储
    mock_repo = MagicMock(spec=ICameraRepository)
    mock_repo.find_by_id = AsyncMock(
        return_value=Camera(
            id="camera_001",
            name="测试摄像头",
            location="测试位置",
            status=CameraStatus.ACTIVE,
            region_id="region_001",
        )
    )
    mock_repo.find_all = AsyncMock(return_value=[])

    # 创建Mock服务
    service = MagicMock(spec=CameraService)
    service.camera_repository = mock_repo
    service.update_camera = AsyncMock()
    return service


@pytest.fixture
def mock_scheduler():
    """创建Mock调度器."""
    scheduler = MagicMock()

    # 默认返回值
    scheduler.start_detection = MagicMock(
        return_value={"ok": True, "pid": 12345, "log": "/tmp/log.txt"}
    )
    scheduler.stop_detection = MagicMock(return_value={"ok": True})
    scheduler.restart_detection = MagicMock(
        return_value={"ok": True, "pid": 12346, "log": "/tmp/log.txt"}
    )
    scheduler.get_status = MagicMock(
        return_value={"running": False, "pid": None, "log": None}
    )
    scheduler.status = MagicMock(
        return_value={"running": True, "pid": 12345, "log": "/tmp/log.txt"}
    )
    scheduler.get_batch_status = MagicMock(return_value={})  # 默认返回空字典，表示没有运行中的摄像头

    return scheduler


@pytest.fixture
def camera_control_service(mock_camera_service, mock_scheduler):
    """创建摄像头控制服务."""
    return CameraControlService(mock_camera_service, mock_scheduler)


class TestStartCamera:
    """测试启动摄像头."""

    @pytest.mark.asyncio
    async def test_start_camera_success(self, camera_control_service, mock_scheduler):
        """测试成功启动摄像头."""
        camera_id = "camera_001"

        result = await camera_control_service.start_camera(camera_id)

        assert result["ok"] is True
        assert "pid" in result
        # start_detection接收camera_id和camera_config两个参数
        mock_scheduler.start_detection.assert_called_once()
        call_args = mock_scheduler.start_detection.call_args
        assert call_args[0][0] == camera_id
        assert isinstance(call_args[0][1], dict)

    @pytest.mark.asyncio
    async def test_start_camera_failure(self, camera_control_service, mock_scheduler):
        """测试启动摄像头失败."""
        camera_id = "camera_001"
        mock_scheduler.start_detection.return_value = {"ok": False, "error": "摄像头不存在"}

        with pytest.raises(ValueError):
            await camera_control_service.start_camera(camera_id)


class TestStopCamera:
    """测试停止摄像头."""

    def test_stop_camera_success(self, camera_control_service, mock_scheduler):
        """测试成功停止摄像头."""
        camera_id = "camera_001"
        # 设置摄像头为运行状态
        mock_scheduler.get_status.return_value = {
            "running": True,
            "pid": 12345,
            "log": "/tmp/log.txt",
        }

        result = camera_control_service.stop_camera(camera_id)

        assert result["ok"] is True
        mock_scheduler.stop_detection.assert_called_once_with(camera_id)

    def test_stop_camera_failure(self, camera_control_service, mock_scheduler):
        """测试停止摄像头失败."""
        camera_id = "camera_001"
        # 设置摄像头为运行状态
        mock_scheduler.get_status.return_value = {
            "running": True,
            "pid": 12345,
            "log": "/tmp/log.txt",
        }
        mock_scheduler.stop_detection.return_value = {"ok": False, "error": "停止失败"}

        with pytest.raises(ValueError):
            camera_control_service.stop_camera(camera_id)


class TestRestartCamera:
    """测试重启摄像头."""

    @pytest.mark.asyncio
    async def test_restart_camera_success(self, camera_control_service, mock_scheduler):
        """测试成功重启摄像头."""
        camera_id = "camera_001"

        result = await camera_control_service.restart_camera(camera_id)

        assert result["ok"] is True
        assert "pid" in result
        # restart_detection接收camera_id和camera_config两个参数
        mock_scheduler.restart_detection.assert_called_once()
        call_args = mock_scheduler.restart_detection.call_args
        assert call_args[0][0] == camera_id
        assert isinstance(call_args[0][1], dict)

    @pytest.mark.asyncio
    async def test_restart_camera_failure(self, camera_control_service, mock_scheduler):
        """测试重启摄像头失败."""
        camera_id = "camera_001"
        mock_scheduler.restart_detection.return_value = {"ok": False, "error": "重启失败"}

        with pytest.raises(ValueError):
            await camera_control_service.restart_camera(camera_id)


class TestGetCameraStatus:
    """测试获取摄像头状态."""

    def test_get_camera_status_success(self, camera_control_service, mock_scheduler):
        """测试成功获取摄像头状态."""
        camera_id = "camera_001"
        # 设置返回运行状态
        mock_scheduler.get_status.return_value = {
            "running": True,
            "pid": 12345,
            "log": "/tmp/log.txt",
        }

        result = camera_control_service.get_camera_status(camera_id)

        assert "running" in result
        assert result["running"] is True
        mock_scheduler.get_status.assert_called_once_with(camera_id)

    def test_get_camera_status_exception(self, camera_control_service, mock_scheduler):
        """测试获取摄像头状态异常."""
        camera_id = "camera_001"
        mock_scheduler.get_status.side_effect = Exception("连接失败")

        with pytest.raises(ValueError, match="获取摄像头状态失败"):
            camera_control_service.get_camera_status(camera_id)


class TestGetBatchStatus:
    """测试批量状态查询."""

    def test_get_batch_status_with_ids(self, camera_control_service, mock_scheduler):
        """测试批量状态查询（指定ID列表）."""
        camera_ids = ["camera_001", "camera_002"]
        # 设置批量状态返回
        mock_scheduler.get_batch_status.return_value = {
            "camera_001": {"running": True, "pid": 12345},
            "camera_002": {"running": False, "pid": None},
        }

        result = camera_control_service.get_batch_status(camera_ids)

        assert "camera_001" in result
        assert "camera_002" in result
        mock_scheduler.get_batch_status.assert_called_once_with(camera_ids)

    def test_get_batch_status_all(self, camera_control_service, mock_scheduler):
        """测试批量状态查询（查询所有）."""
        # 根据实现，如果camera_ids为None，应该返回空字典
        result = camera_control_service.get_batch_status(None)

        assert isinstance(result, dict)
        # 根据实现，None或空列表会返回空字典，不会调用scheduler
        assert result == {}

    def test_get_batch_status_exception(self, camera_control_service, mock_scheduler):
        """测试批量状态查询异常."""
        camera_ids = ["camera_001", "camera_002"]
        mock_scheduler.get_batch_status.side_effect = Exception("查询失败")

        with pytest.raises(ValueError, match="批量状态查询失败"):
            camera_control_service.get_batch_status(camera_ids)


class TestActivateCamera:
    """测试激活摄像头."""

    @pytest.mark.asyncio
    async def test_activate_camera_success(
        self, camera_control_service, mock_camera_service
    ):
        """测试成功激活摄像头."""
        camera_id = "camera_001"
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.activate_camera(camera_id)

        assert result["ok"] is True
        assert result["camera_id"] == camera_id
        assert result["active"] is True
        mock_camera_service.update_camera.assert_called_once_with(
            camera_id, {"active": True}
        )

    @pytest.mark.asyncio
    async def test_activate_camera_not_found(
        self, camera_control_service, mock_camera_service
    ):
        """测试激活不存在的摄像头."""
        camera_id = "camera_999"
        mock_camera_service.update_camera.side_effect = ValueError("摄像头不存在: camera_999")

        with pytest.raises(ValueError, match="摄像头不存在"):
            await camera_control_service.activate_camera(camera_id)


class TestDeactivateCamera:
    """测试停用摄像头."""

    @pytest.mark.asyncio
    async def test_deactivate_camera_success_not_running(
        self, camera_control_service, mock_camera_service, mock_scheduler
    ):
        """测试成功停用摄像头（未运行）."""
        camera_id = "camera_001"
        mock_scheduler.status.return_value = {"running": False}
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.deactivate_camera(camera_id)

        assert result["ok"] is True
        assert result["camera_id"] == camera_id
        assert result["active"] is False
        assert result["stopped"] is False
        mock_camera_service.update_camera.assert_called_once_with(
            camera_id, {"active": False, "auto_start": False}
        )

    @pytest.mark.asyncio
    async def test_deactivate_camera_success_running(
        self, camera_control_service, mock_camera_service, mock_scheduler
    ):
        """测试成功停用摄像头（正在运行）."""
        camera_id = "camera_001"
        mock_scheduler.status.return_value = {"running": True}
        mock_scheduler.stop_detection.return_value = {"ok": True}
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.deactivate_camera(camera_id)

        assert result["ok"] is True
        assert result["active"] is False
        assert result["stopped"] is True
        mock_scheduler.stop_detection.assert_called_once_with(camera_id)
        mock_camera_service.update_camera.assert_called_once_with(
            camera_id, {"active": False, "auto_start": False}
        )

    @pytest.mark.asyncio
    async def test_deactivate_camera_stop_failure(
        self, camera_control_service, mock_camera_service, mock_scheduler
    ):
        """测试停用摄像头时停止失败（应该继续停用）."""
        camera_id = "camera_001"
        mock_scheduler.status.return_value = {"running": True}
        mock_scheduler.stop_detection.return_value = {"ok": False}
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.deactivate_camera(camera_id)

        assert result["ok"] is True
        assert result["stopped"] is False  # 停止失败，但标记为未停止


class TestToggleAutoStart:
    """测试切换自动启动."""

    @pytest.mark.asyncio
    async def test_toggle_auto_start_enable(
        self, camera_control_service, mock_camera_service
    ):
        """测试启用自动启动."""
        camera_id = "camera_001"
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.toggle_auto_start(camera_id, True)

        assert result["ok"] is True
        assert result["camera_id"] == camera_id
        assert result["auto_start"] is True
        mock_camera_service.update_camera.assert_called_once_with(
            camera_id, {"auto_start": True}
        )

    @pytest.mark.asyncio
    async def test_toggle_auto_start_disable(
        self, camera_control_service, mock_camera_service
    ):
        """测试禁用自动启动."""
        camera_id = "camera_001"
        mock_camera_service.update_camera.return_value = {"status": "success"}

        result = await camera_control_service.toggle_auto_start(camera_id, False)

        assert result["ok"] is True
        assert result["auto_start"] is False

    @pytest.mark.asyncio
    async def test_toggle_auto_start_not_found(
        self, camera_control_service, mock_camera_service
    ):
        """测试切换不存在的摄像头的自动启动."""
        camera_id = "camera_999"
        mock_camera_service.update_camera.side_effect = ValueError("摄像头不存在: camera_999")

        with pytest.raises(ValueError, match="摄像头不存在"):
            await camera_control_service.toggle_auto_start(camera_id, True)


class TestGetCameraLogs:
    """测试获取摄像头日志."""

    def test_get_camera_logs_success(
        self, camera_control_service, mock_scheduler, tmp_path
    ):
        """测试成功获取摄像头日志."""
        camera_id = "camera_001"
        log_file = tmp_path / "camera.log"
        log_file.write_text("日志行1\n日志行2\n日志行3\n")
        mock_scheduler.status.return_value = {"log": str(log_file)}

        result = camera_control_service.get_camera_logs(camera_id, lines=2)

        assert result["camera_id"] == camera_id
        assert result["log_file"] == str(log_file)
        assert len(result["lines"]) == 2
        assert result["lines"][0] == "日志行2"
        assert result["lines"][1] == "日志行3"

    def test_get_camera_logs_not_configured(
        self, camera_control_service, mock_scheduler
    ):
        """测试日志文件未配置."""
        camera_id = "camera_001"
        mock_scheduler.status.return_value = {}

        with pytest.raises(ValueError, match="日志文件未配置"):
            camera_control_service.get_camera_logs(camera_id)

    def test_get_camera_logs_file_not_found(
        self, camera_control_service, mock_scheduler, tmp_path
    ):
        """测试日志文件不存在."""
        camera_id = "camera_001"
        log_file = tmp_path / "nonexistent.log"
        mock_scheduler.status.return_value = {"log": str(log_file)}

        result = camera_control_service.get_camera_logs(camera_id)

        assert result["camera_id"] == camera_id
        assert result["lines"] == []
        assert "message" in result


class TestRefreshAllCameras:
    """测试刷新所有摄像头."""

    def test_refresh_all_cameras_success(self, camera_control_service):
        """测试成功刷新所有摄像头."""
        result = camera_control_service.refresh_all_cameras()

        assert result["status"] == "success"
        assert "message" in result
        assert "timestamp" in result
