from typing import Any, Dict, List, Optional

import pytest

from src.services.detection_service_domain import DetectionServiceDomain


class _FakeRepo:
    def __init__(self, data: List[Dict[str, Any]]):
        self._data = data

    async def get_violations(
        self,
        camera_id: Optional[str] = None,
        status: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        items = self._data
        if camera_id is not None:
            items = [x for x in items if x.get("camera_id") == camera_id]
        if status is not None:
            items = [x for x in items if x.get("status") == status]
        if violation_type is not None:
            items = [x for x in items if x.get("violation_type") == violation_type]
        sliced = items[offset : offset + limit]
        return {
            "violations": sliced,
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }


class _FakeCameraRepo:
    async def find_all(self):
        return []

    async def find_active(self):
        return []


@pytest.mark.asyncio
async def test_get_violation_details_basic():
    fake_rows = [
        {
            "id": 1,
            "camera_id": "cam0",
            "timestamp": "2025-01-01T00:00:00",
            "violation_type": "no_hairnet",
            "track_id": 10,
            "confidence": 0.9,
            "status": "pending",
            "snapshot_path": None,
            "bbox": {"x": 1, "y": 2, "w": 3, "h": 4},
            "handled_at": None,
            "handled_by": None,
            "notes": None,
        },
        {
            "id": 2,
            "camera_id": "cam1",
            "timestamp": "2025-01-02T00:00:00",
            "violation_type": "no_handwash",
            "track_id": 20,
            "confidence": 0.8,
            "status": "confirmed",
            "snapshot_path": "path.jpg",
            "bbox": None,
            "handled_at": None,
            "handled_by": None,
            "notes": "ok",
        },
    ]

    domain = DetectionServiceDomain(
        detection_repository=_FakeRepo(fake_rows),
        camera_repository=_FakeCameraRepo(),
    )

    result = await domain.get_violation_details(camera_id="cam0", limit=10, offset=0)
    assert isinstance(result, dict)
    assert "violations" in result and "total" in result
    assert result["total"] == 1
    assert len(result["violations"]) == 1
    v0 = result["violations"][0]
    assert v0["camera_id"] == "cam0"
    assert v0["violation_type"] == "no_hairnet"


@pytest.mark.asyncio
async def test_get_violation_details_filters_and_pagination():
    rows = []
    for i in range(30):
        rows.append(
            {
                "id": i + 1,
                "camera_id": "cam0" if i % 2 == 0 else "cam1",
                "timestamp": "2025-01-01T00:00:00",
                "violation_type": "no_hairnet" if i % 3 == 0 else "no_handwash",
                "track_id": i,
                "confidence": 0.5 + (i % 5) * 0.1,
                "status": "pending" if i % 4 == 0 else "confirmed",
                "snapshot_path": None,
                "bbox": None,
                "handled_at": None,
                "handled_by": None,
                "notes": None,
            }
        )

    domain = DetectionServiceDomain(
        detection_repository=_FakeRepo(rows),
        camera_repository=_FakeCameraRepo(),
    )

    # 过滤 + 分页
    result = await domain.get_violation_details(
        camera_id="cam0", violation_type="no_hairnet", limit=5, offset=0
    )
    assert result["total"] > 0
    assert len(result["violations"]) <= 5
    for item in result["violations"]:
        assert item["camera_id"] == "cam0"
        assert item["violation_type"] == "no_hairnet"
