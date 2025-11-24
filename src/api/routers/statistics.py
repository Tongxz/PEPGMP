#!/usr/bin/env python3
"""统计信息路由模块.

提供统计数据和违规记录的API端点.
所有接口统一使用领域服务，不提供回退逻辑.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)

# 领域服务依赖
try:
    from src.services.detection_service_domain import get_detection_service_domain
except ImportError:
    get_detection_service_domain = None


def _ensure_domain_service():
    """确保领域服务可用，如果不可用则抛出HTTP异常."""
    if get_detection_service_domain is None:
        raise HTTPException(status_code=503, detail="检测领域服务不可用，请联系系统管理员")
    service = get_detection_service_domain()
    if service is None:
        raise HTTPException(status_code=503, detail="检测领域服务未初始化，请联系系统管理员")
    return service


@router.get("/statistics/realtime", summary="实时统计接口")
async def get_realtime_statistics() -> Dict[str, Any]:
    """获取实时统计信息.

    Returns:
        实时统计数据，包括当前检测状态、违规统计等.

    Raises:
        HTTPException: 如果领域服务不可用
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_realtime_statistics()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取实时统计失败: {str(e)}")


@router.get("/statistics/detection-realtime", summary="智能检测实时统计接口")
async def get_detection_realtime_statistics() -> Dict[str, Any]:
    """获取智能检测实时统计数据（用于首页检测面板）.

    Returns:
        包含处理效率、FPS、帧数、场景分布、性能监控等数据的字典:
        - processing_efficiency: 处理效率 (0-100)
        - avg_fps: 平均FPS
        - processed_frames: 已处理帧数
        - skipped_frames: 已跳过帧数
        - scene_distribution: 场景分布 {static, dynamic, critical}
        - performance: 性能监控 {cpu_usage, memory_usage, gpu_usage}
        - connection_status: 连接状态 {connected, active_cameras}
        - timestamp: 时间戳

    Raises:
        HTTPException: 如果领域服务不可用
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_detection_realtime_stats()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取检测实时统计失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"获取检测实时统计失败: {str(e)}"
        )


@router.get("/statistics/summary", summary="事件统计汇总")
async def get_statistics_summary(
    minutes: int = Query(60, ge=1, le=24 * 60),
    limit: int = Query(1000, ge=1, le=10000),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
) -> Dict[str, Any]:
    """返回最近 N 分钟内的事件统计与分布.

    可选参数 camera_id 用于仅统计指定摄像头的事件.

    Args:
        minutes: 要查询的最近分钟数.
        limit: 返回样本的最大数量.
        camera_id: (可选) 要筛选的摄像头ID.

    Returns:
        一个包含统计信息的字典.

    Raises:
        HTTPException: 如果领域服务不可用或查询失败
    """
    try:
        domain_service = _ensure_domain_service()
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)

        analytics = await domain_service.get_detection_analytics(
            camera_id=camera_id, start_time=start_time, end_time=end_time
        )

        # 处理没有检测记录的情况
        if "detection_statistics" not in analytics:
            # 如果返回的是空记录消息，返回空统计
            return {
                "window_minutes": minutes,
                "total_events": analytics.get("total_records", 0),
                "counts_by_type": {},
                "samples": [],
            }

        stats = analytics.get("detection_statistics", {})

        # 适配原响应结构
        return {
            "window_minutes": minutes,
            "total_events": int(stats.get("total_records", 0)),
            "counts_by_type": stats.get("object_distribution", {}),
            "samples": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计摘要失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计摘要失败: {str(e)}")


@router.get("/statistics/daily", summary="按天统计事件趋势")
async def get_statistics_daily(
    days: int = Query(7, ge=1, le=90),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
) -> List[Dict[str, Any]]:
    """返回最近 N 天内的每日事件统计.

    输出：[{date: 'YYYY-MM-DD', total_events: int, counts_by_type: {etype: count}}]

    Args:
        days: 要查询的最近天数.
        camera_id: (可选) 要筛选的摄像头ID.

    Returns:
        一个包含每日统计信息的列表.

    Raises:
        HTTPException: 如果领域服务不可用或查询失败
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_daily_statistics(
            days=days, camera_id=camera_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取每日统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取每日统计失败: {str(e)}")


@router.get("/statistics/events", summary="事件列表查询")
async def get_statistics_events(
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)"),
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    camera_id: Optional[str] = Query(None, description="摄像头ID过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
) -> Dict[str, Any]:
    """查询事件列表，支持时间范围和多种过滤条件.

    Args:
        start_time: 开始时间 (ISO格式字符串)
        end_time: 结束时间 (ISO格式字符串)
        event_type: 事件类型
        camera_id: 摄像头ID
        limit: 返回数量限制

    Returns:
        包含事件列表的字典

    Raises:
        HTTPException: 如果领域服务不可用或查询失败
    """
    try:
        domain_service = _ensure_domain_service()

        # 解析时间范围
        from datetime import datetime as dt

        start_dt = None
        end_dt = None

        if start_time:
            try:
                start_dt = dt.fromisoformat(start_time.replace("Z", "+00:00"))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"开始时间格式错误: {str(e)}")

        if end_time:
            try:
                end_dt = dt.fromisoformat(end_time.replace("Z", "+00:00"))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"结束时间格式错误: {str(e)}")

        result = await domain_service.get_event_history(
            start_time=start_dt,
            end_time=end_dt,
            event_type=event_type,
            camera_id=camera_id,
            limit=limit,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取事件列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {str(e)}")


@router.get("/statistics/history", summary="近期事件历史")
async def get_statistics_history(
    minutes: int = Query(60, ge=1, le=24 * 60),
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
) -> List[Dict[str, Any]]:
    """返回近期事件列表，按时间倒序.

    Args:
        minutes: 要查询的最近分钟数.
        limit: 返回事件的最大数量.
        camera_id: (可选) 要筛选的摄像头ID.

    Returns:
        一个包含事件详细信息的列表.

    Raises:
        HTTPException: 如果领域服务不可用或查询失败
    """
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_recent_history(
            minutes=minutes, limit=limit, camera_id=camera_id
        )

        # 转换为API响应格式
        formatted_result = []
        for event in result:
            formatted_result.append(
                {
                    "ts": event.get("timestamp"),
                    "camera_id": event.get("camera_id"),
                    "type": event.get("type"),
                    "track_id": event.get("track_id"),
                    "region": event.get("region"),
                    "detail": event.get("metadata", {}),
                }
            )
        return formatted_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取近期历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取近期历史失败: {str(e)}")
