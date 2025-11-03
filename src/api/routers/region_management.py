import logging
from typing import Any, Dict
from typing import List
from typing import List as _List
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.utils.rollout import should_use_domain

# This would be in a service file
from src.services.region_service import RegionService, get_region_service

logger = logging.getLogger(__name__)

try:
    from src.domain.services.region_service import RegionDomainService
    from src.infrastructure.repositories.postgresql_region_repository import (
        PostgreSQLRegionRepository,
    )
    from src.services.database_service import get_db_service

    async def get_region_domain_service() -> Optional[RegionDomainService]:
        """获取区域领域服务实例."""
        try:
            # 使用PostgreSQL仓储
            db_service = await get_db_service()
            if not db_service.pool:
                logger.warning("数据库连接池未初始化，无法创建RegionDomainService")
                return None
            region_repo = PostgreSQLRegionRepository(db_service.pool)
            return RegionDomainService(region_repo)
        except Exception as e:
            logger.warning(f"创建RegionDomainService失败: {e}")
            return None

except Exception:
    get_region_domain_service = None  # type: ignore
    RegionDomainService = None  # type: ignore

router = APIRouter()
# 兼容旧前端的路由（/api/regions）
compat_router = APIRouter()


@router.get("/regions", summary="获取所有区域信息")
async def get_all_regions(
    active_only: bool = Query(False, description="是否只返回活跃区域"),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
    region_service: RegionService = Depends(get_region_service),
) -> List[Dict[str, Any]]:
    """获取所有区域信息."""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_region_domain_service is not None:
            region_domain_service = await get_region_domain_service()
            if region_domain_service:
                regions = await region_domain_service.get_all_regions(
                    active_only=active_only
                )
                return regions
    except Exception as e:
        logger.warning(f"领域服务获取区域列表失败，回退到旧实现: {e}")

    # 旧实现（回退到JSON文件）
    return region_service.get_all_regions()


@router.post("/regions", summary="创建新区域")
async def create_region(
    region_data: Dict[str, Any],
    camera_id: Optional[str] = Query(None, description="关联的相机ID（可选）"),
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """创建新区域."""
    # 灰度：写操作需要更谨慎，使用should_use_domain进行灰度控制
    try:
        if should_use_domain(force_domain) and get_region_domain_service is not None:
            region_domain_service = await get_region_domain_service()
            if region_domain_service:
                result = await region_domain_service.create_region(
                    region_data, camera_id
                )
                return result
    except ValueError as e:
        # 业务逻辑错误（如ID已存在），直接抛出HTTP异常
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务创建区域失败，回退到旧实现: {e}")

    # 旧实现（回退到JSON文件）
    try:
        region_id = region_service.create_region(region_data)
        # 持久化到JSON文件（向后兼容）
        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success", "region_id": region_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/regions/meta", summary="更新区域元信息（画布/背景/铺放/参考）")
async def update_regions_meta(
    payload: Dict[str, Any],
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """更新区域元信息."""
    try:
        meta = payload or {}
        cs = meta.get("canvas_size") or {}
        bs = meta.get("background_size") or {}
        fit = meta.get("fit_mode") or None
        ref = meta.get("ref_size") or None

        normalized = {
            "canvas_size": {
                "width": int(cs.get("width") or 0),
                "height": int(cs.get("height") or 0),
            }
            if cs
            else None,
            "background_size": {
                "width": int(bs.get("width") or 0),
                "height": int(bs.get("height") or 0),
            }
            if bs
            else None,
            "fit_mode": str(fit) if fit else None,
            "ref_size": str(ref) if ref else None,
        }

        # 灰度：尝试使用数据库存储meta
        try:
            if (
                should_use_domain(force_domain)
                and get_region_domain_service is not None
            ):
                region_domain_service = await get_region_domain_service()
                if region_domain_service:
                    await region_domain_service.save_meta(normalized)
                    return {"status": "success", "meta": normalized}
        except Exception as e:
            logger.warning(f"领域服务保存meta失败，回退到旧实现: {e}")

        # 旧实现（回退到JSON文件和内存）
        try:
            region_service.region_manager.meta = normalized
        except Exception:
            # 兼容早期注入
            from src.services import region_service as _rs

            if getattr(_rs, "region_manager", None) is not None:
                _rs.region_manager.meta = normalized

        try:
            region_service.save_to_file()
        except Exception:
            pass
        return {"status": "success", "meta": normalized}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/regions/{region_id}", summary="更新区域信息")
async def update_region(
    region_id: str,
    region_data: Dict[str, Any],
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """更新区域信息."""
    # 灰度：写操作需要更谨慎
    try:
        if should_use_domain(force_domain) and get_region_domain_service is not None:
            region_domain_service = await get_region_domain_service()
            if region_domain_service:
                result = await region_domain_service.update_region(
                    region_id, region_data
                )
                return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务更新区域失败，回退到旧实现: {e}")

    # 旧实现（回退到JSON文件）
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
async def delete_region(
    region_id: str,
    force_domain: bool | None = Query(None, description="测试用途，强制走领域分支"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """删除区域."""
    # 灰度：写操作需要更谨慎
    try:
        if should_use_domain(force_domain) and get_region_domain_service is not None:
            region_domain_service = await get_region_domain_service()
            if region_domain_service:
                result = await region_domain_service.delete_region(region_id)
                return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.warning(f"领域服务删除区域失败，回退到旧实现: {e}")

    # 旧实现（回退到JSON文件）
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
        # 可选：保存 meta（画布/背景/铺放方式），用于后端还原映射
        meta = payload.get("meta")
        try:
            if isinstance(meta, dict):
                cs = meta.get("canvas_size") or {}
                bs = meta.get("background_size") or {}
                fit = meta.get("fit_mode") or None
                ref = meta.get("ref_size") or None
                # 仅写入合法的数值
                _meta = {
                    "canvas_size": {
                        "width": int(cs.get("width") or 0),
                        "height": int(cs.get("height") or 0),
                    }
                    if (
                        cs
                        and str(cs.get("width", "0")).isdigit()
                        and str(cs.get("height", "0")).isdigit()
                    )
                    else None,
                    "background_size": {
                        "width": int(bs.get("width") or 0),
                        "height": int(bs.get("height") or 0),
                    }
                    if (
                        bs
                        and str(bs.get("width", "0")).isdigit()
                        and str(bs.get("height", "0")).isdigit()
                    )
                    else None,
                    "fit_mode": str(fit) if fit else None,
                    "ref_size": str(ref) if ref else None,
                }
                region_service.region_manager.meta = _meta
        except Exception:
            pass
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
        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "removed": removed,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
