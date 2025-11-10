"""历史记录和统计数据查询API."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

try:
    from src.services.detection_service_domain import get_detection_service_domain
except ImportError:
    get_detection_service_domain = None

from src.services.database_service import DatabaseService, get_db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/records", tags=["records"])


def _ensure_domain_service():
    """确保领域服务可用，如果不可用则抛出HTTP异常."""
    if get_detection_service_domain is None:
        raise HTTPException(status_code=503, detail="检测领域服务不可用，请联系系统管理员")
    service = get_detection_service_domain()
    if service is None:
        raise HTTPException(status_code=503, detail="检测领域服务未初始化，请联系系统管理员")
    return service


@router.get("/violations")
async def get_violations(
    camera_id: Optional[str] = Query(None, description="摄像头ID，不提供则查询所有"),
    status: Optional[str] = Query(
        None, description="违规状态: pending, confirmed, false_positive, resolved"
    ),
    violation_type: Optional[str] = Query(
        None, description="违规类型: no_hairnet, no_handwash, no_sanitize"
    ),
    limit: int = Query(50, ge=1, le=1000, description="返回记录数量限制"),
    offset: int = Query(0, ge=0, description="偏移量，用于分页"),
) -> Dict[str, Any]:
    """获取违规记录列表.

    Args:
        camera_id: 摄像头ID筛选
        status: 违规状态筛选
        violation_type: 违规类型筛选
        limit: 返回记录数量
        offset: 分页偏移量

    Returns:
        包含违规记录列表和总数的字典
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_violation_details(
            camera_id=camera_id,
            status=status,
            violation_type=violation_type,
            limit=limit,
            offset=offset,
        )
        # 对齐旧响应结构（domain 已返回 ISO 时间字符串）
        return {
            "violations": result.get("violations", []),
            "total": int(result.get("total", 0)),
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询违规记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询违规记录失败: {str(e)}")


@router.get("/violations/{violation_id}")
async def get_violation_detail(
    violation_id: int,
) -> Dict[str, Any]:
    """获取单个违规事件详情.

    Args:
        violation_id: 违规事件ID

    Returns:
        违规事件详情
    """
    try:
        domain_service = _ensure_domain_service()
        violation = await domain_service.get_violation_by_id(violation_id)
        if violation:
            # 确保时间字段格式正确
            if "timestamp" in violation and not isinstance(violation["timestamp"], str):
                if hasattr(violation["timestamp"], "isoformat"):
                    violation["timestamp"] = violation["timestamp"].isoformat()
            if (
                "handled_at" in violation
                and violation["handled_at"]
                and not isinstance(violation["handled_at"], str)
            ):
                if hasattr(violation["handled_at"], "isoformat"):
                    violation["handled_at"] = violation["handled_at"].isoformat()
            if (
                "created_at" in violation
                and violation["created_at"]
                and not isinstance(violation["created_at"], str)
            ):
                if hasattr(violation["created_at"], "isoformat"):
                    violation["created_at"] = violation["created_at"].isoformat()
            if (
                "updated_at" in violation
                and violation["updated_at"]
                and not isinstance(violation["updated_at"], str)
            ):
                if hasattr(violation["updated_at"], "isoformat"):
                    violation["updated_at"] = violation["updated_at"].isoformat()
            return violation
        else:
            raise HTTPException(status_code=404, detail="违规记录不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询违规详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询违规详情失败: {str(e)}")


@router.put("/violations/{violation_id}/status")
async def update_violation_status(
    violation_id: int,
    status: str = Query(..., description="新状态"),
    notes: Optional[str] = Query(None, description="备注信息"),
    handled_by: Optional[str] = Query(None, description="处理人"),
) -> Dict[str, Any]:
    """更新违规事件状态.

    Args:
        violation_id: 违规事件ID
        status: 新状态
        notes: 备注信息
        handled_by: 处理人

    Returns:
        操作结果
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.update_violation_status(
            violation_id=violation_id,
            status=status,
            notes=notes,
            handled_by=handled_by,
        )
        return result
    except ValueError as e:
        # 业务逻辑错误（如状态值无效），直接抛出HTTP异常
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        # 领域服务不支持该操作
        logger.error(f"领域服务不支持更新违规状态: {e}", exc_info=True)
        raise HTTPException(status_code=501, detail="更新违规状态功能暂未实现")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新违规状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新违规状态失败: {str(e)}")


@router.get("/statistics/summary")
async def get_all_cameras_summary(
    period: str = Query("7d", description="时间段: 1d, 7d, 30d"),
) -> Dict[str, Any]:
    """获取所有摄像头的统计摘要.

    Args:
        period: 时间段

    Returns:
        所有摄像头的统计摘要
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_all_cameras_summary(period=period)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询统计摘要失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询统计摘要失败: {str(e)}")


@router.get("/statistics/{camera_id}")
async def get_camera_statistics(
    camera_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    period: str = Query("7d", description="时间段: 1d, 7d, 30d, 自定义请用start_time/end_time"),
) -> Dict[str, Any]:
    """获取摄像头统计数据.

    Args:
        camera_id: 摄像头ID
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        period: 预设时间段

    Returns:
        统计数据
    """
    try:
        domain_service = _ensure_domain_service()

        # 组装时间范围（如果没有指定具体时间，使用period）
        if not start_time or not end_time:
            end_time = datetime.now()
            if period == "1d":
                start_time = end_time - timedelta(days=1)
            elif period == "7d":
                start_time = end_time - timedelta(days=7)
            elif period == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)

        analytics = await domain_service.get_camera_analytics(camera_id)
        # 适配旧响应结构：直接返回 analytics（统计在其中），并保持字段
        return {
            "camera_id": camera_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "period": period,
            "statistics": analytics,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询统计数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询统计数据失败: {str(e)}")


@router.get("/detection-records/{camera_id}")
async def get_detection_records(
    camera_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)"),
) -> Dict[str, Any]:
    """获取检测记录列表.

    Args:
        camera_id: 摄像头ID
        limit: 返回记录数量
        offset: 偏移量
        start_time: 开始时间（可选，用于优化查询性能）
        end_time: 结束时间（可选，用于优化查询性能）

    Returns:
        检测记录列表
    """
    try:
        domain_service = _ensure_domain_service()

        # 解析时间参数
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"无效的开始时间格式: {start_time}")
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"无效的结束时间格式: {end_time}")

        result = await domain_service.get_detection_records_by_camera(
            camera_id=camera_id,
            limit=limit,
            offset=offset,
            start_time=start_dt,
            end_time=end_dt,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询检测记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询检测记录失败: {str(e)}")


@router.get("/health")
async def health_check(db: DatabaseService = Depends(get_db_service)) -> Dict[str, Any]:
    """健康检查 - 验证数据库连接.

    Returns:
        健康状态
    """
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
