from typing import Any, Dict, List
from typing import List as _List

from fastapi import APIRouter, Depends, HTTPException

# This would be in a service file
from src.services.region_service import RegionService, get_region_service

router = APIRouter()
# 兼容旧前端的路由（/api/regions）
compat_router = APIRouter()


@router.get("/regions", summary="获取所有区域信息")
def get_all_regions(
    region_service: RegionService = Depends(get_region_service),
) -> List[Dict[str, Any]]:
    return region_service.get_all_regions()


@router.post("/regions", summary="创建新区域")
def create_region(
    region_data: Dict[str, Any],
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    try:
        region_id = region_service.create_region(region_data)
        # 持久化
        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success", "region_id": region_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/regions/{region_id}", summary="更新区域信息")
def update_region(
    region_id: str,
    region_data: Dict[str, Any],
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    try:
        region_service.update_region(region_id, region_data)
        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/regions/{region_id}", summary="删除区域")
def delete_region(
    region_id: str, region_service: RegionService = Depends(get_region_service)
) -> Dict[str, Any]:
    try:
        region_service.delete_region(region_id)
        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------
# 兼容旧版前端的API (/api/regions)
# ----------------------------

def _region_to_ui(r: Dict[str, Any]) -> Dict[str, Any]:
    """将内部Region字典转换为旧前端期望的字段命名。"""
    return {
        "id": r.get("region_id") or r.get("id"),
        "name": r.get("name", ""),
        "type": r.get("region_type") or r.get("type", "custom"),
        "description": "",
        "points": r.get("polygon") or r.get("points", []),
        "rules": r.get("rules", {}),
        "isActive": r.get("is_active", True),
        "color": "#007bff",
    }


@compat_router.get("/api/regions", summary="[兼容] 获取区域（旧版前端）")
def compat_get_regions(
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    try:
        data = region_service.get_all_regions()
        ui_regions = [_region_to_ui(d) for d in data]
        return {"regions": ui_regions, "canvas_size": {"width": 800, "height": 600}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@compat_router.post("/api/regions", summary="[兼容] 保存区域（旧版前端）")
def compat_save_regions(
    payload: Dict[str, Any],
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    try:
        regions = payload.get("regions", [])
        created = 0
        updated = 0
        upsert_ids: _List[str] = []
        for item in regions:
            rid = item.get("id")
            rtype = item.get("type", "custom")
            points = item.get("points", [])
            name = item.get("name", "")
            is_active = item.get("isActive", True)
            rules = item.get("rules", {})

            # 自动将2点线段膨胀为窄矩形
            if isinstance(points, list) and len(points) == 2:
                (x1, y1) = (points[0].get("x", 0), points[0].get("y", 0))
                (x2, y2) = (points[1].get("x", 0), points[1].get("y", 0))
                thickness = 6
                if abs(x2 - x1) >= abs(y2 - y1):
                    points = [
                        {"x": x1, "y": y1 - thickness},
                        {"x": x2, "y": y2 - thickness},
                        {"x": x2, "y": y2 + thickness},
                        {"x": x1, "y": y1 + thickness},
                    ]
                else:
                    points = [
                        {"x": x1 - thickness, "y": y1},
                        {"x": x1 + thickness, "y": y1},
                        {"x": x2 + thickness, "y": y2},
                        {"x": x2 - thickness, "y": y2},
                    ]

            data = {
                "region_id": rid,
                "region_type": rtype,
                "polygon": points,
                "name": name,
                "is_active": is_active,
                "rules": rules,
            }

            try:
                region_service.update_region(rid, data)
                updated += 1
            except Exception:
                region_service.create_region(data)
                created += 1
            upsert_ids.append(rid)

        # 删除前端未提交的旧区域
        removed = region_service.remove_regions_not_in(upsert_ids)
        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success", "created": created, "updated": updated, "removed": removed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
