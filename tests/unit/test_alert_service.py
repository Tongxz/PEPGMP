"""AlertService单元测试."""


import pytest

from src.domain.entities.alert import Alert
from src.domain.repositories.alert_repository import IAlertRepository
from src.domain.services.alert_service import AlertService


class MockAlertRepository(IAlertRepository):
    """模拟告警仓储."""

    def __init__(self):
        self._alerts: list[Alert] = []

    async def find_by_id(self, alert_id: int) -> Alert | None:
        return next((a for a in self._alerts if a.id == alert_id), None)

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        camera_id: str | None = None,
        alert_type: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> list[Alert]:
        result = self._alerts.copy()
        if camera_id:
            result = [a for a in result if a.camera_id == camera_id]
        if alert_type:
            result = [a for a in result if a.alert_type == alert_type]

        # 排序
        if sort_by == "timestamp":
            reverse = sort_order == "desc"
            result.sort(key=lambda a: a.timestamp, reverse=reverse)

        # 分页
        return result[offset : offset + limit]

    async def count(
        self,
        camera_id: str | None = None,
        alert_type: str | None = None,
    ) -> int:
        result = self._alerts.copy()
        if camera_id:
            result = [a for a in result if a.camera_id == camera_id]
        if alert_type:
            result = [a for a in result if a.alert_type == alert_type]
        return len(result)

    async def save(self, alert: Alert) -> int:
        alert.id = len(self._alerts) + 1
        self._alerts.append(alert)
        return alert.id


@pytest.fixture
def mock_repository():
    """创建模拟仓储."""
    return MockAlertRepository()


@pytest.fixture
def alert_service(mock_repository):
    """创建AlertService实例."""
    return AlertService(mock_repository)


@pytest.mark.asyncio
class TestAlertService:
    """测试AlertService."""

    async def test_get_alert_history_success(self, alert_service):
        """测试成功获取告警历史."""
        # 创建测试数据
        from datetime import datetime

        alert1 = Alert(
            id=1,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警1",
            timestamp=datetime.now(),
        )
        alert2 = Alert(
            id=2,
            camera_id="cam2",
            alert_type="error",
            message="测试告警2",
            timestamp=datetime.now(),
        )
        await alert_service.alert_repository.save(alert1)
        await alert_service.alert_repository.save(alert2)

        result = await alert_service.get_alert_history(limit=10)

        assert "count" in result
        assert "items" in result
        assert result["count"] == 2
        assert len(result["items"]) == 2

    async def test_get_alert_history_with_camera_filter(self, alert_service):
        """测试按camera_id过滤告警历史."""
        from datetime import datetime

        alert1 = Alert(
            id=1,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警1",
            timestamp=datetime.now(),
        )
        alert2 = Alert(
            id=2,
            camera_id="cam2",
            alert_type="violation",
            message="测试告警2",
            timestamp=datetime.now(),
        )
        await alert_service.alert_repository.save(alert1)
        await alert_service.alert_repository.save(alert2)

        result = await alert_service.get_alert_history(limit=10, camera_id="cam1")

        assert result["count"] == 1
        assert result["items"][0]["camera_id"] == "cam1"

    async def test_get_alert_history_with_type_filter(self, alert_service):
        """测试按alert_type过滤告警历史."""
        from datetime import datetime

        alert1 = Alert(
            id=1,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警1",
            timestamp=datetime.now(),
        )
        alert2 = Alert(
            id=2,
            camera_id="cam2",
            alert_type="error",
            message="测试告警2",
            timestamp=datetime.now(),
        )
        await alert_service.alert_repository.save(alert1)
        await alert_service.alert_repository.save(alert2)

        result = await alert_service.get_alert_history(limit=10, alert_type="violation")

        assert result["count"] == 1
        assert result["items"][0]["alert_type"] == "violation"

    async def test_get_alert_history_empty(self, alert_service):
        """测试空告警历史."""
        result = await alert_service.get_alert_history(limit=10)

        assert result["count"] == 0
        assert len(result["items"]) == 0

    async def test_create_alert_success(self, alert_service):
        """测试成功创建告警."""
        from datetime import datetime

        alert = Alert(
            id=0,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警",
            timestamp=datetime.now(),
        )

        alert_id = await alert_service.alert_repository.save(alert)

        assert alert_id > 0

        # 验证告警已保存
        saved_alert = await alert_service.alert_repository.find_by_id(alert_id)
        assert saved_alert is not None
        assert saved_alert.message == "测试告警"

    async def test_create_alert_with_details(self, alert_service):
        """测试创建带详情的告警."""
        from datetime import datetime

        alert = Alert(
            id=0,
            camera_id="cam1",
            alert_type="violation",
            message="测试告警",
            timestamp=datetime.now(),
            details={"severity": "high", "location": "zone1"},
        )

        alert_id = await alert_service.alert_repository.save(alert)

        assert alert_id > 0

        saved_alert = await alert_service.alert_repository.find_by_id(alert_id)
        assert saved_alert.details == {"severity": "high", "location": "zone1"}

    async def test_get_alert_history_exception_handling(self, alert_service):
        """测试获取告警历史时的异常处理."""
        # 模拟仓储异常
        original_find_all = alert_service.alert_repository.find_all

        async def mock_find_all_error(*args, **kwargs):
            raise RuntimeError("查询失败")

        alert_service.alert_repository.find_all = mock_find_all_error

        try:
            with pytest.raises(RuntimeError, match="查询失败"):
                await alert_service.get_alert_history()
        finally:
            alert_service.alert_repository.find_all = original_find_all
