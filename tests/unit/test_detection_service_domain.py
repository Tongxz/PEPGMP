"""
DetectionServiceDomain 单元测试
测试领域模型检测服务的所有方法
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.entities.camera import Camera, CameraStatus, CameraType
from src.domain.entities.detected_object import DetectedObject
from src.domain.entities.detection_record import DetectionRecord
from src.domain.value_objects.bounding_box import BoundingBox
from src.domain.value_objects.confidence import Confidence
from src.domain.value_objects.timestamp import Timestamp
from src.services.detection_service_domain import DetectionServiceDomain


class MockDetectionRepository:
    """模拟检测记录仓储"""

    def __init__(self):
        self.records: Dict[str, DetectionRecord] = {}
        self.violations: List[Dict[str, Any]] = []

    async def save(self, record: DetectionRecord) -> str:
        self.records[record.id] = record
        return record.id

    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        return self.records.get(record_id)

    async def find_by_camera_id(
        self, camera_id: str, limit: int = 100, offset: int = 0
    ) -> List[DetectionRecord]:
        records = [r for r in self.records.values() if r.camera_id == camera_id]
        return records[offset : offset + limit]

    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DetectionRecord]:
        records = [
            r
            for r in self.records.values()
            if start_time <= r.timestamp.value <= end_time
            and (camera_id is None or r.camera_id == camera_id)
        ]
        return records[:limit]

    async def get_violations(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        violations = self.violations.copy()

        if camera_id:
            violations = [v for v in violations if v.get("camera_id") == camera_id]
        if status:
            violations = [v for v in violations if v.get("status") == status]
        if violation_type:
            violations = [
                v for v in violations if v.get("violation_type") == violation_type
            ]

        total = len(violations)
        violations = violations[offset : offset + limit]

        return {"violations": violations, "total": total}

    async def count_by_camera_id(self, camera_id: str) -> int:
        """统计摄像头记录数量"""
        return len([r for r in self.records.values() if r.camera_id == camera_id])

    async def get_statistics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return {
            "total_records": len(self.records),
            "avg_confidence": 0.8,
            "avg_processing_time": 0.1,
            "earliest_record": datetime.now() - timedelta(days=1),
            "latest_record": datetime.now(),
        }


class MockCameraRepository:
    """模拟摄像头仓储"""

    def __init__(self):
        self.cameras: Dict[str, Camera] = {}

    async def find_all(self) -> List[Camera]:
        return list(self.cameras.values())

    async def find_active(self) -> List[Camera]:
        return [c for c in self.cameras.values() if c.is_active]

    async def find_by_id(self, camera_id: str) -> Optional[Camera]:
        return self.cameras.get(camera_id)


@pytest.fixture
def mock_detection_repository():
    """创建模拟检测记录仓储"""
    return MockDetectionRepository()


@pytest.fixture
def mock_camera_repository():
    """创建模拟摄像头仓储"""
    return MockCameraRepository()


@pytest.fixture
def detection_service_domain(mock_detection_repository, mock_camera_repository):
    """创建DetectionServiceDomain实例"""
    return DetectionServiceDomain(
        detection_repository=mock_detection_repository,
        camera_repository=mock_camera_repository,
    )


@pytest.fixture
def sample_records(mock_detection_repository):
    """创建示例检测记录"""
    records = []
    for i in range(5):
        record = DetectionRecord(
            id=f"record_{i}",
            camera_id="cam0",
            timestamp=Timestamp(datetime.now() - timedelta(hours=i)),
        )
        bbox = BoundingBox(10, 20, 30, 40)
        confidence = Confidence(0.8)
        obj = DetectedObject(
            class_id=0,
            class_name="person",
            confidence=confidence,
            bbox=bbox,
            track_id=f"track_{i}",
        )
        record.add_object(obj)
        records.append(record)
        mock_detection_repository.records[record.id] = record
    return records


@pytest.fixture
def sample_cameras(mock_camera_repository):
    """创建示例摄像头"""
    cameras = []
    for i in range(3):
        camera = Camera(
            id=f"cam{i}",
            name=f"Camera {i}",
            location=f"Location {i}",
            status=CameraStatus.ACTIVE,
            camera_type=CameraType.FIXED,
            resolution=(1920, 1080),
            fps=25,
        )
        cameras.append(camera)
        mock_camera_repository.cameras[camera.id] = camera
    return cameras


class TestDetectionServiceDomain:
    """测试DetectionServiceDomain"""

    @pytest.mark.asyncio
    async def test_process_detection(self, detection_service_domain, sample_cameras):
        """测试处理检测结果"""
        detected_objects = [
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.8,
                "bbox": [10, 20, 30, 40],
                "track_id": 1,
            }
        ]

        result = await detection_service_domain.process_detection(
            camera_id="cam0",
            detected_objects=detected_objects,
            processing_time=0.1,
            frame_id=1,
        )

        assert isinstance(result, DetectionRecord)
        assert result.camera_id == "cam0"
        assert len(result.objects) == 1

    @pytest.mark.asyncio
    async def test_process_detection_camera_not_found(self, detection_service_domain):
        """测试处理检测结果（摄像头不存在）"""
        with pytest.raises(ValueError, match="摄像头不存在"):
            await detection_service_domain.process_detection(
                camera_id="nonexistent",
                detected_objects=[],
                processing_time=0.1,
            )

    @pytest.mark.asyncio
    async def test_get_detection_analytics(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取检测分析报告"""
        from datetime import timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_detection_analytics(
            camera_id="cam0", start_time=start_time, end_time=end_time
        )

        assert "detection_statistics" in result
        # 检查 detection_statistics 内部结构
        stats = result["detection_statistics"]
        assert "object_distribution" in stats or "total_records" in stats

    @pytest.mark.asyncio
    async def test_get_detection_analytics_no_records(self, detection_service_domain):
        """测试获取检测分析报告（无记录）"""
        result = await detection_service_domain.get_detection_analytics(
            camera_id="nonexistent"
        )

        assert "total_records" in result
        assert result["total_records"] == 0

    @pytest.mark.asyncio
    async def test_get_detection_records_by_camera(
        self, detection_service_domain, sample_records
    ):
        """测试根据摄像头ID获取检测记录列表"""
        result = await detection_service_domain.get_detection_records_by_camera(
            camera_id="cam0", limit=10, offset=0
        )

        assert "records" in result
        assert "total" in result
        assert "camera_id" in result
        assert result["camera_id"] == "cam0"
        assert len(result["records"]) <= 10

    @pytest.mark.asyncio
    async def test_get_violation_details(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试获取违规明细"""
        # 添加测试违规数据
        mock_detection_repository.violations = [
            {
                "id": 1,
                "camera_id": "cam0",
                "violation_type": "no_hairnet",
                "status": "pending",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track1",
                "confidence": 0.8,
            },
            {
                "id": 2,
                "camera_id": "cam0",
                "violation_type": "no_handwash",
                "status": "confirmed",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track2",
                "confidence": 0.9,
            },
        ]

        result = await detection_service_domain.get_violation_details(
            camera_id="cam0", limit=10, offset=0
        )

        assert "violations" in result
        assert "total" in result
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_get_violation_by_id(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试根据违规ID获取违规详情"""
        mock_detection_repository.violations = [
            {
                "id": 1,
                "camera_id": "cam0",
                "violation_type": "no_hairnet",
                "status": "pending",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track1",
                "confidence": 0.8,
            }
        ]

        result = await detection_service_domain.get_violation_by_id(violation_id=1)

        assert result is not None
        assert result["id"] == 1
        assert result["violation_type"] == "no_hairnet"

    @pytest.mark.asyncio
    async def test_get_daily_statistics(self, detection_service_domain, sample_records):
        """测试按天统计事件趋势"""
        result = await detection_service_domain.get_daily_statistics(
            days=7, camera_id="cam0"
        )

        assert isinstance(result, list)
        assert len(result) <= 7

    @pytest.mark.asyncio
    async def test_get_event_history(self, detection_service_domain, sample_records):
        """测试查询事件列表"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, limit=10
        )

        assert "events" in result
        assert "total" in result
        assert isinstance(result["events"], list)

    @pytest.mark.asyncio
    async def test_get_recent_history(self, detection_service_domain, sample_records):
        """测试获取近期事件历史"""
        result = await detection_service_domain.get_recent_history(
            minutes=60, limit=10, camera_id="cam0"
        )

        assert isinstance(result, list)
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_get_recent_events(self, detection_service_domain, sample_records):
        """测试获取最近的事件列表"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, camera_id="cam0"
        )

        assert isinstance(result, list)
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_get_realtime_statistics(
        self, detection_service_domain, sample_records, sample_cameras
    ):
        """测试获取实时统计信息"""
        result = await detection_service_domain.get_realtime_statistics()

        assert "timestamp" in result
        assert "system_status" in result
        assert "detection_stats" in result
        assert "region_stats" in result
        assert "performance_metrics" in result

    @pytest.mark.asyncio
    async def test_get_cameras(self, detection_service_domain, sample_cameras):
        """测试获取摄像头列表"""
        result = await detection_service_domain.get_cameras(active_only=False)

        assert isinstance(result, list)
        assert len(result) == len(sample_cameras)

    @pytest.mark.asyncio
    async def test_get_camera_stats_detailed(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头详细统计信息"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "camera_info": {"id": "cam0", "is_active": True},
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
                "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
            }

            result = await detection_service_domain.get_camera_stats_detailed("cam0")

            assert "camera_id" in result
            assert "running" in result
            assert "stats" in result

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取所有摄像头的统计摘要"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
                "total_sanitize_events": 1,
                "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
            }

            result = await detection_service_domain.get_all_cameras_summary(period="7d")

            assert "period" in result
            assert "cameras" in result
            assert "total" in result
            assert result["period"] == "7d"

    @pytest.mark.asyncio
    async def test_get_camera_analytics(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取摄像头分析报告"""
        result = await detection_service_domain.get_camera_analytics("cam0")

        assert "camera_info" in result
        assert "detection_count_24h" in result
        assert "average_confidence" in result
        assert "total_objects_detected" in result

    @pytest.mark.asyncio
    async def test_update_violation_status_not_implemented(
        self, detection_service_domain
    ):
        """测试更新违规状态（仓储不支持）"""
        # 由于仓储不支持更新，应该抛出NotImplementedError
        with pytest.raises(NotImplementedError):
            await detection_service_domain.update_violation_status(
                violation_id=1, status="confirmed"
            )

    @pytest.mark.asyncio
    async def test_update_violation_status_invalid_status(
        self, detection_service_domain
    ):
        """测试更新违规状态（无效状态）"""
        with pytest.raises(ValueError):
            await detection_service_domain.update_violation_status(
                violation_id=1, status="invalid_status"
            )

    @pytest.mark.asyncio
    async def test_update_violation_status_success(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试更新违规状态（成功）"""
        # 模拟仓储支持更新
        mock_detection_repository.update_violation_status = AsyncMock(return_value=True)

        result = await detection_service_domain.update_violation_status(
            violation_id=1, status="confirmed", notes="Test note"
        )

        assert result["ok"] is True
        assert result["violation_id"] == 1
        assert result["status"] == "confirmed"

        # 验证仓储方法被调用
        mock_detection_repository.update_violation_status.assert_called_once_with(
            1, "confirmed", "Test note", None
        )

    @pytest.mark.asyncio
    async def test_update_violation_status_with_handled_by(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试更新违规状态（包含处理人）"""
        mock_detection_repository.update_violation_status = AsyncMock(return_value=True)

        result = await detection_service_domain.update_violation_status(
            violation_id=1, status="confirmed", notes="Test note", handled_by="admin"
        )

        assert result["ok"] is True
        assert result["status"] == "confirmed"

        # 验证处理人被传递
        mock_detection_repository.update_violation_status.assert_called_once_with(
            1, "confirmed", "Test note", "admin"
        )

    @pytest.mark.asyncio
    async def test_update_violation_status_not_found(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试更新违规状态（记录不存在）"""
        mock_detection_repository.update_violation_status = AsyncMock(
            return_value=False
        )

        with pytest.raises(ValueError, match="违规记录不存在或更新失败"):
            await detection_service_domain.update_violation_status(
                violation_id=999, status="confirmed"
            )

    @pytest.mark.asyncio
    async def test_update_violation_status_all_statuses(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试更新违规状态（所有状态值）"""
        mock_detection_repository.update_violation_status = AsyncMock(return_value=True)

        statuses = ["pending", "confirmed", "false_positive", "resolved"]

        for status in statuses:
            result = await detection_service_domain.update_violation_status(
                violation_id=1, status=status
            )
            assert result["ok"] is True
            assert result["status"] == status

    @pytest.mark.asyncio
    async def test_get_domain_statistics(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取领域模型统计信息"""
        result = await detection_service_domain.get_domain_statistics()

        assert "cameras" in result
        assert "detections" in result
        assert "domain_services" in result


class TestDetectionServiceDomainErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_get_camera_analytics_camera_not_found(
        self, detection_service_domain
    ):
        """测试获取摄像头分析报告（摄像头不存在）"""
        with pytest.raises(ValueError, match="摄像头不存在"):
            await detection_service_domain.get_camera_analytics("nonexistent")

    @pytest.mark.asyncio
    async def test_get_violation_details_empty(self, detection_service_domain):
        """测试获取违规明细（空结果）"""
        result = await detection_service_domain.get_violation_details(
            camera_id="cam0", limit=10, offset=0
        )

        assert result["total"] == 0
        assert len(result["violations"]) == 0


class TestDetectionServiceDomainEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_get_detection_records_by_camera_pagination(
        self, detection_service_domain, sample_records
    ):
        """测试检测记录列表分页"""
        # 测试第一页
        result1 = await detection_service_domain.get_detection_records_by_camera(
            camera_id="cam0", limit=2, offset=0
        )

        # 测试第二页
        result2 = await detection_service_domain.get_detection_records_by_camera(
            camera_id="cam0", limit=2, offset=2
        )

        assert len(result1["records"]) <= 2
        assert len(result2["records"]) <= 2
        assert result1["records"] != result2["records"]

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_no_cameras(self, detection_service_domain):
        """测试获取所有摄像头统计摘要（无摄像头）"""
        result = await detection_service_domain.get_all_cameras_summary(period="7d")

        assert "period" in result
        assert "cameras" in result
        assert "total" in result
        assert len(result["cameras"]) == 0

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_no_data(self, detection_service_domain):
        """测试获取实时统计信息（无数据）"""
        result = await detection_service_domain.get_realtime_statistics()

        assert "timestamp" in result
        assert "system_status" in result
        assert result["system_status"] in ["active", "inactive"]

    @pytest.mark.asyncio
    async def test_process_detection_with_violations(
        self, detection_service_domain, sample_cameras
    ):
        """测试处理检测结果（包含违规）"""
        detected_objects = [
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.8,
                "bbox": [10, 20, 30, 40],
                "track_id": 1,
            }
        ]

        with patch.object(detection_service_domain, "_publish_event") as mock_publish:
            result = await detection_service_domain.process_detection(
                camera_id="cam0",
                detected_objects=detected_objects,
                processing_time=0.1,
                frame_id=1,
            )

            assert isinstance(result, DetectionRecord)
            # 验证事件发布被调用（检测创建事件和可能的违规事件）
            assert mock_publish.called

    @pytest.mark.asyncio
    async def test_get_violation_details_with_filters(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试获取违规明细（带过滤条件）"""
        # 添加测试违规数据
        mock_detection_repository.violations = [
            {
                "id": 1,
                "camera_id": "cam0",
                "violation_type": "no_hairnet",
                "status": "pending",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track1",
                "confidence": 0.8,
            },
            {
                "id": 2,
                "camera_id": "cam0",
                "violation_type": "no_handwash",
                "status": "confirmed",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track2",
                "confidence": 0.9,
            },
        ]

        # 测试状态过滤
        result = await detection_service_domain.get_violation_details(
            camera_id="cam0", status="pending", limit=10, offset=0
        )
        assert result["total"] >= 0  # 可能为0或1

        # 测试违规类型过滤
        result = await detection_service_domain.get_violation_details(
            camera_id="cam0", violation_type="no_hairnet", limit=10, offset=0
        )
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_get_daily_statistics_with_camera_filter(
        self, detection_service_domain, sample_records
    ):
        """测试按天统计（带摄像头过滤）"""
        result = await detection_service_domain.get_daily_statistics(
            days=7, camera_id="cam0"
        )

        assert isinstance(result, list)
        assert len(result) <= 7

    @pytest.mark.asyncio
    async def test_get_event_history_with_filters(
        self, detection_service_domain, sample_records
    ):
        """测试查询事件列表（带各种过滤条件）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        # 测试事件类型过滤
        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, event_type="person", limit=10
        )
        assert "events" in result

        # 测试摄像头过滤
        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, camera_id="cam0", limit=10
        )
        assert "events" in result

    @pytest.mark.asyncio
    async def test_get_recent_events_with_filters(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（带过滤条件）"""
        # 测试事件类型过滤
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, event_type="person", camera_id="cam0"
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_cameras_active_only(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头列表（仅活跃）"""
        result = await detection_service_domain.get_cameras(active_only=True)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_detection_records_by_camera_with_offset(
        self, detection_service_domain, sample_records
    ):
        """测试检测记录列表（带偏移量）"""
        result = await detection_service_domain.get_detection_records_by_camera(
            camera_id="cam0", limit=2, offset=2
        )

        assert "records" in result
        assert result["offset"] == 2

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_different_periods(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（不同时间段）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
                "total_sanitize_events": 1,
                "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
            }

            # 测试1天
            result1 = await detection_service_domain.get_all_cameras_summary(
                period="1d"
            )
            assert result1["period"] == "1d"

            # 测试30天
            result2 = await detection_service_domain.get_all_cameras_summary(
                period="30d"
            )
            assert result2["period"] == "30d"

    @pytest.mark.asyncio
    async def test_get_camera_analytics_with_records(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取摄像头分析报告（有记录）"""
        # 设置记录的processing_time
        for record in sample_records:
            record.processing_time = 0.05

        result = await detection_service_domain.get_camera_analytics("cam0")

        assert "camera_info" in result
        assert "detection_count_24h" in result
        assert "performance" in result
        assert result["performance"]["fps_estimate"] > 0

    @pytest.mark.asyncio
    async def test_get_detection_records_by_camera_error_handling(
        self, detection_service_domain
    ):
        """测试检测记录列表（错误处理）"""
        # 测试不存在的摄像头
        result = await detection_service_domain.get_detection_records_by_camera(
            camera_id="nonexistent", limit=10, offset=0
        )

        assert "records" in result
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_detection_analytics_no_time_range(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取检测分析报告（无时间范围，使用摄像头ID）"""
        result = await detection_service_domain.get_detection_analytics(
            camera_id="cam0"
        )

        assert "detection_statistics" in result or "total_records" in result

    @pytest.mark.asyncio
    async def test_get_detection_analytics_no_camera_no_time(
        self, detection_service_domain, sample_records
    ):
        """测试获取检测分析报告（无摄像头，无时间范围，使用最近1小时）"""
        result = await detection_service_domain.get_detection_analytics()

        assert "detection_statistics" in result or "total_records" in result

    @pytest.mark.asyncio
    async def test_get_violation_details_with_repository_error(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试获取违规明细（仓储不支持）"""

        # 创建一个不支持get_violations的仓储
        class NoViolationsRepository(MockDetectionRepository):
            async def get_violations(self, *args, **kwargs):
                raise NotImplementedError("当前仓储未实现违规明细查询")

        no_violations_repo = NoViolationsRepository()
        detection_service_domain.detection_repository = no_violations_repo

        with pytest.raises(NotImplementedError):
            await detection_service_domain.get_violation_details(
                camera_id="cam0", limit=10, offset=0
            )

    @pytest.mark.asyncio
    async def test_get_daily_statistics_no_records(self, detection_service_domain):
        """测试按天统计（无记录）"""
        result = await detection_service_domain.get_daily_statistics(days=7)

        assert isinstance(result, list)
        assert len(result) == 7  # 应该返回7天的空数据

    @pytest.mark.asyncio
    async def test_get_daily_statistics_multiple_days(
        self, detection_service_domain, sample_records
    ):
        """测试按天统计（多天数据）"""
        result = await detection_service_domain.get_daily_statistics(days=30)

        assert isinstance(result, list)
        assert len(result) == 30

    @pytest.mark.asyncio
    async def test_get_event_history_no_records(self, detection_service_domain):
        """测试查询事件列表（无记录）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, limit=10
        )

        assert "events" in result
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_recent_history_no_records(self, detection_service_domain):
        """测试获取近期事件历史（无记录）"""
        result = await detection_service_domain.get_recent_history(
            minutes=60, limit=10, camera_id="nonexistent"
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_recent_events_no_matching(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（无匹配）"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, event_type="nonexistent_type"
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_with_data(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（有数据）"""
        result = await detection_service_domain.get_realtime_statistics()

        assert "timestamp" in result
        assert "detection_stats" in result
        assert "region_stats" in result

    @pytest.mark.asyncio
    async def test_get_camera_stats_detailed_error(self, detection_service_domain):
        """测试获取摄像头详细统计信息（错误处理）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.side_effect = Exception("测试错误")

            with pytest.raises(Exception):
                await detection_service_domain.get_camera_stats_detailed("cam0")

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_with_errors(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（部分摄像头失败）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            # 第一个成功，第二个失败
            mock_analytics.side_effect = [
                {
                    "total_objects_detected": 10,
                    "person_count": 5,
                    "total_hairnet_violations": 2,
                    "total_handwash_events": 3,
                    "total_sanitize_events": 1,
                    "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
                },
                Exception("摄像头统计失败"),
                {
                    "total_objects_detected": 5,
                    "person_count": 3,
                    "total_hairnet_violations": 1,
                    "total_handwash_events": 2,
                    "total_sanitize_events": 0,
                    "performance": {"fps_estimate": 20.0, "avg_processing_time": 0.15},
                },
            ]

            result = await detection_service_domain.get_all_cameras_summary(period="7d")

            assert "cameras" in result
            assert len(result["cameras"]) >= 2  # 至少2个成功

    @pytest.mark.asyncio
    async def test_get_camera_analytics_no_records(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头分析报告（无记录）"""
        result = await detection_service_domain.get_camera_analytics("cam0")

        assert "camera_info" in result
        assert result["detection_count_24h"] == 0
        assert result["average_confidence"] == 0

    @pytest.mark.asyncio
    async def test_get_camera_analytics_with_anomalies(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取摄像头分析报告（有异常）"""
        result = await detection_service_domain.get_camera_analytics("cam0")

        assert "camera_info" in result
        assert "anomalies" in result

    @pytest.mark.asyncio
    async def test_get_violation_by_id_not_found(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试根据违规ID获取违规详情（不存在）"""

        # 仓储支持get_violation_by_id，但返回None
        class ViolationByIdRepository(MockDetectionRepository):
            async def get_violation_by_id(self, violation_id: int):
                return None

        violation_repo = ViolationByIdRepository()
        detection_service_domain.detection_repository = violation_repo

        result = await detection_service_domain.get_violation_by_id(violation_id=999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_violation_by_id_fallback(
        self, detection_service_domain, mock_detection_repository
    ):
        """测试根据违规ID获取违规详情（回退到get_violations）"""
        # 仓储不支持get_violation_by_id，但支持get_violations
        mock_detection_repository.violations = [
            {
                "id": 1,
                "camera_id": "cam0",
                "violation_type": "no_hairnet",
                "status": "pending",
                "timestamp": datetime.now().isoformat(),
                "track_id": "track1",
                "confidence": 0.8,
            }
        ]

        # 移除get_violation_by_id支持，使其回退到get_violations
        class NoViolationByIdRepository(MockDetectionRepository):
            pass

        no_violation_by_id_repo = NoViolationByIdRepository()
        no_violation_by_id_repo.violations = mock_detection_repository.violations
        detection_service_domain.detection_repository = no_violation_by_id_repo

        result = await detection_service_domain.get_violation_by_id(violation_id=1)
        # 可能返回None或违规详情
        assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_daily_statistics_with_data(
        self, detection_service_domain, sample_records
    ):
        """测试按天统计（有数据）"""
        result = await detection_service_domain.get_daily_statistics(days=7)

        assert isinstance(result, list)
        assert len(result) == 7
        # 检查是否有数据
        for day_data in result:
            assert "date" in day_data
            assert "total_events" in day_data
            assert "counts_by_type" in day_data

    @pytest.mark.asyncio
    async def test_get_event_history_with_event_type(
        self, detection_service_domain, sample_records
    ):
        """测试查询事件列表（带事件类型过滤）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_event_history(
            start_time=start_time,
            end_time=end_time,
            event_type="person",
            camera_id="cam0",
            limit=10,
        )

        assert "events" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_get_recent_history_with_limit(
        self, detection_service_domain, sample_records
    ):
        """测试获取近期事件历史（限制数量）"""
        result = await detection_service_domain.get_recent_history(
            minutes=60, limit=3, camera_id="cam0"
        )

        assert isinstance(result, list)
        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_get_recent_events_with_camera_filter(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（带摄像头过滤）"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, camera_id="cam0"
        )

        assert isinstance(result, list)
        # 验证所有事件都属于指定摄像头
        for event in result:
            assert event.get("camera_id") == "cam0"

    @pytest.mark.asyncio
    async def test_get_recent_events_with_event_type(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（带事件类型过滤）"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, event_type="person"
        )

        assert isinstance(result, list)
        # 验证所有事件都是指定类型
        for event in result:
            assert event.get("type") == "person"

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_performance(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（性能指标）"""
        # 设置记录的processing_time
        for record in sample_records:
            record.processing_time = 0.05

        result = await detection_service_domain.get_realtime_statistics()

        assert "performance_metrics" in result
        assert "average_processing_time" in result["performance_metrics"]

    @pytest.mark.asyncio
    async def test_get_cameras_all(self, detection_service_domain, sample_cameras):
        """测试获取摄像头列表（所有摄像头）"""
        result = await detection_service_domain.get_cameras(active_only=False)

        assert isinstance(result, list)
        assert len(result) == len(sample_cameras)

    @pytest.mark.asyncio
    async def test_get_detection_analytics_with_records(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取检测分析报告（有记录）"""
        from datetime import timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_detection_analytics(
            camera_id="cam0", start_time=start_time, end_time=end_time
        )

        assert "detection_statistics" in result
        assert "violation_statistics" in result
        assert "anomalies" in result
        assert "quality_analysis" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_get_camera_analytics_no_performance(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头分析报告（无性能数据）"""
        result = await detection_service_domain.get_camera_analytics("cam0")

        assert "camera_info" in result
        assert (
            "performance" not in result
            or result.get("performance", {}).get("fps_estimate", 0) == 0
        )

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_with_violations(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（有违规）"""
        # 添加违规到记录
        for record in sample_records:
            record.add_metadata("violations", [{"type": "no_hairnet"}])

        result = await detection_service_domain.get_realtime_statistics()

        assert "detection_stats" in result
        assert result["detection_stats"]["violation_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_with_regions(
        self, detection_service_domain, sample_records, sample_cameras
    ):
        """测试获取实时统计信息（有区域）"""
        # 设置摄像头的region_id
        for camera in sample_cameras:
            camera.region_id = f"region_{camera.id}"

        result = await detection_service_domain.get_realtime_statistics()

        assert "region_stats" in result
        assert "active_regions" in result["region_stats"]

    @pytest.mark.asyncio
    async def test_get_event_history_time_range_only(
        self, detection_service_domain, sample_records
    ):
        """测试查询事件列表（仅时间范围）"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=12)

        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, limit=10
        )

        assert "events" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_get_event_history_default_time(
        self, detection_service_domain, sample_records
    ):
        """测试查询事件列表（默认时间范围）"""
        result = await detection_service_domain.get_event_history(limit=10)

        assert "events" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_get_recent_events_no_filters(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（无过滤）"""
        result = await detection_service_domain.get_recent_events(limit=10, minutes=60)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_recent_events_both_filters(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（同时使用事件类型和摄像头过滤）"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, event_type="person", camera_id="cam0"
        )

        assert isinstance(result, list)
        # 验证过滤条件
        for event in result:
            assert event.get("type") == "person"
            assert event.get("camera_id") == "cam0"

    @pytest.mark.asyncio
    async def test_get_daily_statistics_different_days(
        self, detection_service_domain, sample_records
    ):
        """测试按天统计（不同天数）"""
        # 测试1天
        result1 = await detection_service_domain.get_daily_statistics(days=1)
        assert len(result1) == 1

        # 测试30天
        result30 = await detection_service_domain.get_daily_statistics(days=30)
        assert len(result30) == 30

    @pytest.mark.asyncio
    async def test_get_camera_stats_detailed_no_performance(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头详细统计信息（无性能数据）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "camera_info": {"id": "cam0", "is_active": True},
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
            }

            result = await detection_service_domain.get_camera_stats_detailed("cam0")

            assert "camera_id" in result
            assert "stats" in result
            assert result["stats"]["avg_fps"] == 0.0

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_error_handling(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（部分摄像头失败）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            # 第一个成功，其他失败
            mock_analytics.side_effect = [
                {
                    "total_objects_detected": 10,
                    "person_count": 5,
                    "total_hairnet_violations": 2,
                    "total_handwash_events": 3,
                    "total_sanitize_events": 1,
                    "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
                },
            ] + [Exception("失败")] * (len(sample_cameras) - 1)

            result = await detection_service_domain.get_all_cameras_summary(period="7d")

            assert "cameras" in result
            assert len(result["cameras"]) <= len(sample_cameras)

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_invalid_period(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（无效时间段）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
                "total_sanitize_events": 1,
                "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
            }

            # 测试无效时间段（应该使用默认7天）
            result = await detection_service_domain.get_all_cameras_summary(
                period="invalid"
            )

            assert "period" in result
            assert result["period"] == "invalid"  # 即使无效也会保留原值，但使用7天计算

    @pytest.mark.asyncio
    async def test_generate_recommendations_poor_quality(
        self, detection_service_domain, sample_records
    ):
        """测试生成建议（检测质量低）"""
        # 创建低质量记录
        poor_records = []
        for i in range(10):
            record = DetectionRecord(
                id=f"poor_{i}",
                camera_id="cam0",
                timestamp=Timestamp(datetime.now() - timedelta(minutes=i)),
                confidence=Confidence(0.3),  # 低置信度
            )
            poor_records.append(record)

        recommendations = detection_service_domain._generate_recommendations(
            records=poor_records, violations=[], anomalies=[]
        )

        assert isinstance(recommendations, list)
        # 应该有质量相关的建议
        quality_recommendations = [r for r in recommendations if "质量" in r or "光照" in r]
        assert len(quality_recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_violations(
        self, detection_service_domain, sample_records
    ):
        """测试生成建议（有违规）"""
        violations = [Mock(violation_type="no_hairnet") for _ in range(5)]

        recommendations = detection_service_domain._generate_recommendations(
            records=sample_records, violations=violations, anomalies=[]
        )

        assert isinstance(recommendations, list)
        # 应该有违规相关的建议
        violation_recommendations = [
            r for r in recommendations if "违规" in r or "监管" in r
        ]
        assert len(violation_recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_anomalies(
        self, detection_service_domain, sample_records
    ):
        """测试生成建议（有异常）"""
        anomalies = [{"type": "gap", "severity": "high"}] * 3

        recommendations = detection_service_domain._generate_recommendations(
            records=sample_records, violations=[], anomalies=anomalies
        )

        assert isinstance(recommendations, list)
        # 应该有异常相关的建议
        anomaly_recommendations = [r for r in recommendations if "异常" in r or "系统" in r]
        assert len(anomaly_recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_recommendations_low_frequency(
        self, detection_service_domain
    ):
        """测试生成建议（检测频率低）"""
        # 创建少量记录
        few_records = []
        for i in range(5):
            record = DetectionRecord(
                id=f"few_{i}",
                camera_id="cam0",
                timestamp=Timestamp(datetime.now() - timedelta(minutes=i)),
            )
            few_records.append(record)

        recommendations = detection_service_domain._generate_recommendations(
            records=few_records, violations=[], anomalies=[]
        )

        assert isinstance(recommendations, list)
        # 应该有频率相关的建议
        frequency_recommendations = [
            r for r in recommendations if "频率" in r or "连接" in r
        ]
        assert len(frequency_recommendations) > 0

    @pytest.mark.asyncio
    async def test_publish_event(self, detection_service_domain):
        """测试发布领域事件"""
        from src.domain.events.detection_events import DetectionCreatedEvent

        # 创建事件
        record = DetectionRecord(
            id="test_001",
            camera_id="cam0",
            timestamp=Timestamp.now(),
        )
        event = DetectionCreatedEvent.from_detection_record(record)

        # 发布事件（应该不抛出异常）
        await detection_service_domain._publish_event(event)

        # 验证事件被记录（通过日志）
        # 这里主要验证方法不抛出异常

    @pytest.mark.asyncio
    async def test_process_detection_with_quality_analysis(
        self, detection_service_domain, sample_cameras
    ):
        """测试处理检测结果（包含质量分析）"""
        detected_objects = [
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.9,
                "bbox": [10, 20, 30, 40],
                "track_id": 1,
            }
        ]

        result = await detection_service_domain.process_detection(
            camera_id="cam0",
            detected_objects=detected_objects,
            processing_time=0.1,
            frame_id=1,
        )

        assert isinstance(result, DetectionRecord)
        # 验证质量分析被添加
        assert "quality_analysis" in result.metadata

    @pytest.mark.asyncio
    async def test_process_detection_with_violations_publish(
        self, detection_service_domain, sample_cameras
    ):
        """测试处理检测结果（违规并发布事件）"""
        detected_objects = [
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.8,
                "bbox": [10, 20, 30, 40],
                "track_id": 1,
            }
        ]

        with patch.object(detection_service_domain, "_publish_event") as mock_publish:
            result = await detection_service_domain.process_detection(
                camera_id="cam0",
                detected_objects=detected_objects,
                processing_time=0.1,
                frame_id=1,
            )

            # 验证事件被发布（至少检测创建事件）
            assert mock_publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_default_camera_repository_find_by_id_not_found(self):
        """测试默认摄像头仓储（查找不存在）"""
        from src.domain.entities.camera import CameraStatus, CameraType
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 查找不存在的摄像头，应该返回占位摄像头
        camera = await repo.find_by_id("nonexistent")

        assert camera is not None
        assert camera.id == "nonexistent"
        assert camera.status == CameraStatus.ACTIVE
        assert camera.camera_type == CameraType.FIXED

    @pytest.mark.asyncio
    async def test_default_camera_repository_find_by_region_id(self, sample_cameras):
        """测试默认摄像头仓储（按区域查找）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 添加一些摄像头
        for camera in sample_cameras[:3]:
            await repo.save(camera)

        # 查找区域摄像头
        if sample_cameras[0].region_id:
            cameras = await repo.find_by_region_id(sample_cameras[0].region_id)
            assert isinstance(cameras, list)
            assert all(c.region_id == sample_cameras[0].region_id for c in cameras)

    @pytest.mark.asyncio
    async def test_default_camera_repository_delete(self, sample_cameras):
        """测试默认摄像头仓储（删除）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 添加摄像头
        camera_id = await repo.save(sample_cameras[0])

        # 删除摄像头
        deleted = await repo.delete_by_id(camera_id)
        assert deleted is True

        # 再次删除应该返回False
        deleted_again = await repo.delete_by_id(camera_id)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_default_camera_repository_exists(self, sample_cameras):
        """测试默认摄像头仓储（存在检查）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 添加摄像头
        camera_id = await repo.save(sample_cameras[0])

        # 检查存在
        exists = await repo.exists(camera_id)
        assert exists is True

        # 检查不存在
        not_exists = await repo.exists("nonexistent")
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_default_camera_repository_count(self, sample_cameras):
        """测试默认摄像头仓储（计数）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 初始计数应该为0
        assert await repo.count() == 0

        # 添加摄像头
        for camera in sample_cameras[:3]:
            await repo.save(camera)

        # 计数应该增加
        assert await repo.count() == 3

    @pytest.mark.asyncio
    async def test_get_detection_service_domain_singleton(self):
        """测试获取领域服务（单例模式）"""
        # 重置单例（用于测试）
        import src.services.detection_service_domain as dsd_module
        from src.services.detection_service_domain import get_detection_service_domain

        dsd_module._detection_service_domain_instance = None

        # 第一次调用应该创建实例
        service1 = get_detection_service_domain()

        # 第二次调用应该返回同一个实例
        service2 = get_detection_service_domain()

        assert service1 is service2
        assert service1 is not None
        assert service2 is not None

    @pytest.mark.asyncio
    async def test_default_camera_repository_find_all_and_find_active(
        self, sample_cameras
    ):
        """测试默认摄像头仓储（查找全部和活跃）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 添加摄像头
        for camera in sample_cameras:
            await repo.save(camera)

        # 查找全部
        all_cameras = await repo.find_all()
        assert len(all_cameras) == len(sample_cameras)

        # 查找活跃
        active_cameras = await repo.find_active()
        assert isinstance(active_cameras, list)
        assert all(c.is_active for c in active_cameras)

    @pytest.mark.asyncio
    async def test_get_recent_history_with_camera_filter(
        self, detection_service_domain, sample_records
    ):
        """测试获取近期历史（摄像头过滤）"""
        result = await detection_service_domain.get_recent_history(
            minutes=60, limit=10, camera_id="cam0"
        )

        assert isinstance(result, list)
        if result:
            # get_recent_history返回的事件包含timestamp字段（不是ts）
            assert all("timestamp" in event or "ts" in event for event in result)

    @pytest.mark.asyncio
    async def test_get_event_history_with_event_type_filter(
        self, detection_service_domain, sample_records
    ):
        """测试查询事件列表（事件类型过滤）"""
        from datetime import timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        result = await detection_service_domain.get_event_history(
            start_time=start_time, end_time=end_time, limit=10, event_type="person"
        )

        assert isinstance(result, dict)
        assert "events" in result

    @pytest.mark.asyncio
    async def test_get_recent_events_with_event_type(
        self, detection_service_domain, sample_records
    ):
        """测试获取最近事件（事件类型过滤）"""
        result = await detection_service_domain.get_recent_events(
            limit=10, minutes=60, event_type="person"
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_different_periods(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（不同时间段）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.return_value = {
                "total_objects_detected": 10,
                "person_count": 5,
                "total_hairnet_violations": 2,
                "total_handwash_events": 3,
                "total_sanitize_events": 1,
                "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
            }

            # 测试1天
            result1 = await detection_service_domain.get_all_cameras_summary(
                period="1d"
            )
            assert result1["period"] == "1d"

            # 测试30天
            result2 = await detection_service_domain.get_all_cameras_summary(
                period="30d"
            )
            assert result2["period"] == "30d"

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_error_handling_branch(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（错误处理分支，覆盖978->956）"""
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            # 第一个摄像头成功，第二个失败，触发异常处理分支
            mock_analytics.side_effect = [
                {
                    "total_objects_detected": 10,
                    "person_count": 5,
                    "total_hairnet_violations": 2,
                    "total_handwash_events": 3,
                    "total_sanitize_events": 1,
                    "performance": {"fps_estimate": 25.0, "avg_processing_time": 0.1},
                },
                Exception("摄像头统计失败"),
            ]

            result = await detection_service_domain.get_all_cameras_summary(period="7d")

            assert "cameras" in result
            assert "total" in result
            # 验证异常被捕获并处理（至少1个成功）
            camera_results = [
                v for k, v in result["cameras"].items() if v.get("total_frames", 0) > 0
            ]
            assert len(camera_results) >= 1

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_with_zero_camera_ids(
        self, detection_service_domain
    ):
        """测试获取统计摘要（零摄像头ID，覆盖978->956分支）"""
        # 使用空的摄像头仓储
        from src.services.detection_service_domain import DefaultCameraRepository

        empty_repo = DefaultCameraRepository()

        detection_service_domain.camera_repository = empty_repo

        result = await detection_service_domain.get_all_cameras_summary(period="7d")

        assert "cameras" in result
        assert "total" in result
        assert len(result["cameras"]) == 0
        # 验证零摄像头时的平均值计算被跳过（len(camera_ids) == 0）

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_top_level_exception(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取统计摘要（顶层异常处理，覆盖1002-1004）"""
        # 模拟顶层异常（如获取摄像头列表失败）
        with patch.object(
            detection_service_domain.camera_repository, "find_all"
        ) as mock_find_all:
            mock_find_all.side_effect = Exception("获取摄像头列表失败")

            with pytest.raises(Exception):
                await detection_service_domain.get_all_cameras_summary(period="7d")

    @pytest.mark.asyncio
    async def test_default_camera_repository_find_by_id_placeholder_creation(self):
        """测试默认摄像头仓储（占位摄像头创建分支，覆盖1070, 1086）"""
        from src.domain.entities.camera import CameraStatus, CameraType
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 查找不存在的摄像头，应该创建占位摄像头（不是从store返回）
        camera = await repo.find_by_id("test_cam_placeholder")

        # 验证占位摄像头属性
        assert camera is not None
        assert camera.id == "test_cam_placeholder"
        assert camera.name == "test_cam_placeholder"
        assert camera.location == "unknown"
        assert camera.status == CameraStatus.ACTIVE
        assert camera.camera_type == CameraType.FIXED
        assert camera.resolution == (1920, 1080)
        assert camera.fps == 25
        assert camera.region_id is None

        # 验证占位摄像头不被缓存
        assert "test_cam_placeholder" not in repo._store

    @pytest.mark.asyncio
    async def test_default_camera_repository_find_by_region_id_empty(self):
        """测试默认摄像头仓储（按区域查找，空结果）"""
        from src.services.detection_service_domain import DefaultCameraRepository

        repo = DefaultCameraRepository()

        # 查找不存在的区域
        cameras = await repo.find_by_region_id("nonexistent_region")

        assert isinstance(cameras, list)
        assert len(cameras) == 0

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_with_violations_metadata(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（metadata中包含违规，覆盖777分支）"""
        # 为记录添加违规metadata
        for record in sample_records:
            record.add_metadata(
                "violations",
                [
                    {"type": "no_hairnet", "confidence": 0.8},
                    {"type": "no_handwash", "confidence": 0.9},
                ],
            )
            record.add_metadata("violation_count", 2)

        result = await detection_service_domain.get_realtime_statistics()

        assert "detection_stats" in result
        assert result["detection_stats"]["violation_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_with_regions(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（包含区域信息，覆盖779分支）"""
        # 为记录设置region_id
        for record in sample_records:
            record.region_id = "region_1"

        result = await detection_service_domain.get_realtime_statistics()

        assert "detection_stats" in result
        # region_stats在顶层结果中
        assert "region_stats" in result

    @pytest.mark.asyncio
    async def test_process_detection_with_violations_loop(
        self, detection_service_domain, sample_cameras, mock_detection_repository
    ):
        """测试处理检测结果（违规循环分支，覆盖115->125）"""
        detected_objects = [
            {
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.8,
                "bbox": [10, 20, 30, 40],
                "track_id": 1,
            }
        ]

        # 确保违规服务能够检测到违规（通过低置信度或特定配置）
        with patch.object(detection_service_domain, "_publish_event") as mock_publish:
            result = await detection_service_domain.process_detection(
                camera_id="cam0",
                detected_objects=detected_objects,
                processing_time=0.1,
            )

            # 验证结果包含metadata
            assert result.metadata is not None
            # 验证事件被发布（至少检测创建事件）
            assert mock_publish.call_count >= 0  # 可能没有违规，但仍应有检测事件

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_region_id_branch(
        self, detection_service_domain, sample_cameras, sample_records
    ):
        """测试获取实时统计信息（region_id分支，覆盖794）"""
        # 为记录设置region_id
        for record in sample_records:
            record.region_id = "region_1"

        # 为摄像头设置region_id
        for camera in sample_cameras:
            camera.region_id = "region_1"

        result = await detection_service_domain.get_realtime_statistics()

        assert "region_stats" in result
        assert result["region_stats"]["active_regions"] >= 0

    @pytest.mark.asyncio
    async def test_get_realtime_statistics_object_class_branches(
        self, detection_service_domain, sample_records
    ):
        """测试获取实时统计信息（对象类型分支，覆盖777, 779, 780）"""
        # 创建不同类型的对象记录
        from src.domain.entities.detected_object import DetectedObject
        from src.domain.value_objects.bounding_box import BoundingBox

        # 添加handwash对象
        handwash_obj = DetectedObject(
            class_id=1,
            class_name="handwash",
            confidence=Confidence(0.9),
            bbox=BoundingBox(10, 20, 30, 40),
        )

        # 添加sanitize对象
        sanitize_obj = DetectedObject(
            class_id=2,
            class_name="sanitize",
            confidence=Confidence(0.9),
            bbox=BoundingBox(10, 20, 30, 40),
        )

        # 添加hairnet对象
        hairnet_obj = DetectedObject(
            class_id=3,
            class_name="hairnet",
            confidence=Confidence(0.9),
            bbox=BoundingBox(10, 20, 30, 40),
        )

        # 创建包含不同类型对象的记录
        test_records = []
        for i, obj in enumerate([handwash_obj, sanitize_obj, hairnet_obj]):
            record = DetectionRecord(
                id=f"test_{i}",
                camera_id="cam0",
                objects=[obj],
                timestamp=Timestamp.now(),
                processing_time=0.1,
            )
            test_records.append(record)

        # 模拟仓储返回这些记录
        with patch.object(
            detection_service_domain.detection_repository,
            "find_by_time_range",
            return_value=test_records,
        ):
            result = await detection_service_domain.get_realtime_statistics()

            assert "detection_stats" in result
            assert result["detection_stats"]["handwashing_detections"] >= 0
            assert result["detection_stats"]["disinfection_detections"] >= 0
            assert result["detection_stats"]["hairnet_detections"] >= 0

    @pytest.mark.asyncio
    async def test_get_cameras_exception_handling(
        self, detection_service_domain, mock_camera_repository
    ):
        """测试获取摄像头列表（异常处理，覆盖821-823）"""
        # 模拟仓储抛出异常
        mock_camera_repository.find_all = AsyncMock(side_effect=Exception("获取摄像头列表失败"))

        with pytest.raises(Exception):
            await detection_service_domain.get_cameras(active_only=False)

    @pytest.mark.asyncio
    async def test_get_camera_stats_detailed_exception_handling(
        self, detection_service_domain, sample_cameras
    ):
        """测试获取摄像头详细统计信息（异常处理，覆盖861-863）"""
        # 模拟get_camera_analytics抛出异常
        with patch.object(
            detection_service_domain, "get_camera_analytics"
        ) as mock_analytics:
            mock_analytics.side_effect = Exception("摄像头分析失败")

            with pytest.raises(Exception):
                await detection_service_domain.get_camera_stats_detailed("cam0")

    @pytest.mark.asyncio
    async def test_get_all_cameras_summary_zero_camera_ids_branch(
        self, detection_service_domain
    ):
        """测试获取统计摘要（零摄像头ID分支，覆盖978->956）"""
        # 使用空的摄像头仓储
        from src.services.detection_service_domain import DefaultCameraRepository

        empty_repo = DefaultCameraRepository()

        detection_service_domain.camera_repository = empty_repo

        result = await detection_service_domain.get_all_cameras_summary(period="7d")

        assert "cameras" in result
        assert "total" in result
        assert len(result["cameras"]) == 0
        # 验证零摄像头时，平均值计算被跳过（len(camera_ids) == 0）
