"""历史记录和统计数据查询API."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.services.database_service import DatabaseService, get_db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/records", tags=["records"])


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
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """获取违规记录列表.

    Args:
        camera_id: 摄像头ID筛选
        status: 违规状态筛选
        violation_type: 违规类型筛选
        limit: 返回记录数量
        offset: 分页偏移量
        db: 数据库服务实例

    Returns:
        包含违规记录列表和总数的字典
    """
    try:
        # 查询违规记录（简化版，后续可增加更多筛选）
        violations = await db.get_recent_violations(
            camera_id=camera_id, limit=limit, status=status
        )

        # 如果指定了违规类型，进行过滤
        if violation_type:
            violations = [v for v in violations if v["violation_type"] == violation_type]

        # 应用偏移量
        if offset > 0:
            violations = violations[offset:]

        # 格式化返回数据
        formatted_violations = []
        for v in violations:
            formatted_violations.append(
                {
                    "id": v["id"],
                    "camera_id": v["camera_id"],
                    "timestamp": v["timestamp"].isoformat(),
                    "violation_type": v["violation_type"],
                    "track_id": v["track_id"],
                    "confidence": v["confidence"],
                    "status": v["status"],
                    "snapshot_path": v["snapshot_path"],
                    "bbox": v["bbox"],
                    "handled_at": (
                        v["handled_at"].isoformat() if v["handled_at"] else None
                    ),
                    "handled_by": v["handled_by"],
                    "notes": v["notes"],
                }
            )

        return {
            "violations": formatted_violations,
            "total": len(formatted_violations),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get violations: {e}")
        raise HTTPException(status_code=500, detail=f"查询违规记录失败: {str(e)}")


@router.get("/violations/{violation_id}")
async def get_violation_detail(
    violation_id: int, db: DatabaseService = Depends(get_db_service)
) -> Dict[str, Any]:
    """获取单个违规事件详情.

    Args:
        violation_id: 违规事件ID
        db: 数据库服务实例

    Returns:
        违规事件详情
    """
    try:
        violations = await db.get_recent_violations(limit=1000)
        violation = next((v for v in violations if v["id"] == violation_id), None)

        if not violation:
            raise HTTPException(status_code=404, detail="违规记录不存在")

        return {
            "id": violation["id"],
            "camera_id": violation["camera_id"],
            "timestamp": violation["timestamp"].isoformat(),
            "violation_type": violation["violation_type"],
            "track_id": violation["track_id"],
            "confidence": violation["confidence"],
            "status": violation["status"],
            "snapshot_path": violation["snapshot_path"],
            "bbox": violation["bbox"],
            "handled_at": (
                violation["handled_at"].isoformat() if violation["handled_at"] else None
            ),
            "handled_by": violation["handled_by"],
            "notes": violation["notes"],
            "created_at": violation["created_at"].isoformat(),
            "updated_at": violation["updated_at"].isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get violation detail: {e}")
        raise HTTPException(status_code=500, detail=f"查询违规详情失败: {str(e)}")


@router.put("/violations/{violation_id}/status")
async def update_violation_status(
    violation_id: int,
    status: str = Query(..., description="新状态"),
    notes: Optional[str] = Query(None, description="备注信息"),
    handled_by: Optional[str] = Query(None, description="处理人"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """更新违规事件状态.

    Args:
        violation_id: 违规事件ID
        status: 新状态
        notes: 备注信息
        handled_by: 处理人
        db: 数据库服务实例

    Returns:
        操作结果
    """
    valid_statuses = ["pending", "confirmed", "false_positive", "resolved"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"无效的状态值，必须是: {', '.join(valid_statuses)}",
        )

    try:
        await db.update_violation_status(violation_id, status, notes)
        return {"ok": True, "violation_id": violation_id, "status": status}

    except Exception as e:
        logger.error(f"Failed to update violation status: {e}")
        raise HTTPException(status_code=500, detail=f"更新违规状态失败: {str(e)}")


@router.get("/statistics/{camera_id}")
async def get_camera_statistics(
    camera_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    period: str = Query("7d", description="时间段: 1d, 7d, 30d, 自定义请用start_time/end_time"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """获取摄像头统计数据.

    Args:
        camera_id: 摄像头ID
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        period: 预设时间段
        db: 数据库服务实例

    Returns:
        统计数据
    """
    try:
        # 如果没有指定具体时间，使用period
        if not start_time or not end_time:
            end_time = datetime.now()
            if period == "1d":
                start_time = end_time - timedelta(days=1)
            elif period == "7d":
                start_time = end_time - timedelta(days=7)
            elif period == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(days=7)  # 默认7天

        stats = await db.get_statistics(camera_id, start_time, end_time)

        return {
            "camera_id": camera_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "period": period,
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"查询统计数据失败: {str(e)}")


@router.get("/statistics/summary")
async def get_all_cameras_summary(
    period: str = Query("7d", description="时间段: 1d, 7d, 30d"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """获取所有摄像头的统计摘要.

    Args:
        period: 时间段
        db: 数据库服务实例

    Returns:
        所有摄像头的统计摘要
    """
    try:
        # 计算时间范围
        end_time = datetime.now()
        if period == "1d":
            start_time = end_time - timedelta(days=1)
        elif period == "7d":
            start_time = end_time - timedelta(days=7)
        elif period == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=7)

        # 获取所有摄像头列表（从cameras.yaml）
        import yaml
        from pathlib import Path

        config_path = Path("config/cameras.yaml")
        if config_path.exists():
            with open(config_path) as f:
                cameras_config = yaml.safe_load(f)
                camera_ids = [c["id"] for c in cameras_config.get("cameras", [])]
        else:
            # 如果配置文件不存在，从数据库查询
            camera_ids = ["cam0", "vid1"]  # 默认值

        # 查询每个摄像头的统计
        summary = {}
        total_stats = {
            "total_frames": 0,
            "total_persons": 0,
            "total_hairnet_violations": 0,
            "total_handwash_events": 0,
            "total_sanitize_events": 0,
        }

        for camera_id in camera_ids:
            try:
                stats = await db.get_statistics(camera_id, start_time, end_time)
                summary[camera_id] = stats

                # 累加到总计
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            except Exception as e:
                logger.warning(f"Failed to get stats for {camera_id}: {e}")
                summary[camera_id] = {
                    "total_frames": 0,
                    "total_persons": 0,
                    "total_hairnet_violations": 0,
                    "total_handwash_events": 0,
                    "total_sanitize_events": 0,
                    "avg_fps": 0.0,
                    "avg_processing_time": 0.0,
                }

        return {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "cameras": summary,
            "total": total_stats,
        }

    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=f"查询统计摘要失败: {str(e)}")


@router.get("/detection-records/{camera_id}")
async def get_detection_records(
    camera_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """获取检测记录列表（简化版，直接查询数据库）.

    Args:
        camera_id: 摄像头ID
        limit: 返回记录数量
        offset: 偏移量
        db: 数据库服务实例

    Returns:
        检测记录列表
    """
    try:
        # 直接查询数据库
        async with db.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT id, camera_id, timestamp, frame_number,
                       person_count, hairnet_violations,
                       handwash_events, sanitize_events,
                       fps, processing_time
                FROM detection_records
                WHERE camera_id = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
                """,
                camera_id,
                limit,
                offset,
            )

            formatted_records = []
            for r in records:
                formatted_records.append(
                    {
                        "id": r["id"],
                        "camera_id": r["camera_id"],
                        "timestamp": r["timestamp"].isoformat(),
                        "frame_number": r["frame_number"],
                        "person_count": r["person_count"],
                        "hairnet_violations": r["hairnet_violations"],
                        "handwash_events": r["handwash_events"],
                        "sanitize_events": r["sanitize_events"],
                        "fps": r["fps"],
                        "processing_time": r["processing_time"],
                    }
                )

            return {
                "records": formatted_records,
                "total": len(formatted_records),
                "camera_id": camera_id,
                "limit": limit,
                "offset": offset,
            }

    except Exception as e:
        logger.error(f"Failed to get detection records: {e}")
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

