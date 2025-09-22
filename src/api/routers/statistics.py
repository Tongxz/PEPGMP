#!/usr/bin/env python3
"""统计信息路由模块.

提供统计数据和违规记录的API端点.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from src.services.region_service import RegionService, get_region_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/statistics/summary")
def get_statistics_summary(
    camera_id: Optional[str] = Query(None, description="摄像头ID"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """获取统计摘要信息.

    Args:
        camera_id: 可选的摄像头ID筛选.
        region_service: 区域服务依赖项.

    Returns:
        统计摘要数据.
    """
    # 模拟统计数据
    return {
        "window_minutes": 60,
        "total_events": 125,
        "counts_by_type": {
            "handwashing": 45,
            "mask_detection": 38,
            "region_violation": 22,
            "occupancy_alert": 20,
        },
        "samples": [],
    }


@router.get("/statistics/daily")
def get_daily_statistics(
    days: int = Query(7, description="天数"),
    camera_id: Optional[str] = Query(None, description="摄像头ID"),
    region_service: RegionService = Depends(get_region_service),
) -> List[Dict[str, Any]]:
    """获取每日统计数据.

    Args:
        days: 查询天数.
        camera_id: 可选的摄像头ID筛选.
        region_service: 区域服务依赖项.

    Returns:
        每日统计数据列表.
    """
    # 模拟每日统计数据
    from datetime import datetime, timedelta

    daily_stats = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats.append(
            {
                "date": date,
                "total_events": 50 + i * 5,
                "counts_by_type": {
                    "handwashing": 20 + i * 2,
                    "mask_detection": 15 + i,
                    "region_violation": 10 + i,
                    "occupancy_alert": 5 + i,
                },
            }
        )

    return daily_stats


@router.get("/statistics/events")
def get_statistics_events(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    camera_id: Optional[str] = Query(None, description="摄像头ID"),
    region_service: RegionService = Depends(get_region_service),
) -> List[Dict[str, Any]]:
    """获取统计事件列表.

    Args:
        start_date: 开始日期.
        end_date: 结束日期.
        event_type: 事件类型筛选.
        camera_id: 摄像头ID筛选.
        region_service: 区域服务依赖项.

    Returns:
        事件列表数据.
    """
    # 模拟事件数据
    import random
    from datetime import datetime, timedelta

    events = []
    event_types = [
        "handwashing",
        "mask_detection",
        "region_violation",
        "occupancy_alert",
    ]

    # 生成模拟事件数据
    for i in range(20):
        event_time = datetime.now() - timedelta(hours=random.randint(1, 72))
        event = {
            "id": f"event_{i+1}",
            "timestamp": event_time.isoformat(),
            "type": random.choice(event_types),
            "camera_id": camera_id or f"camera_{random.randint(1, 3)}",
            "confidence": round(random.uniform(0.7, 0.99), 2),
            "details": {
                "duration": random.randint(5, 30),
                "location": f"区域_{random.randint(1, 5)}",
            },
        }

        # 根据事件类型筛选
        if event_type and event["type"] != event_type:
            continue

        events.append(event)

    return events


@router.get("/statistics")
def get_statistics(region_service: RegionService = Depends(get_region_service)):
    """获取统计信息.

    Args:
        region_service: 区域服务依赖项.

    Returns:
        统计信息数据.
    """
    # This is a placeholder for statistics logic
    # In a real application, this would query a database or a metrics service
    return {"message": "Statistics endpoint"}


@router.get("/violations")
def get_violations(region_service: RegionService = Depends(get_region_service)):
    """获取违规记录.

    Args:
        region_service: 区域服务依赖项.

    Returns:
        违规记录数据.
    """
    # This is a placeholder for violation retrieval logic
    return {"message": "Violations endpoint"}


@router.get("/statistics/realtime", summary="实时统计接口")
def get_realtime_statistics(
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """获取实时统计信息.

    Args:
        region_service: 区域服务依赖项.

    Returns:
        实时统计数据，包括当前检测状态、违规统计等.
    """
    try:
        # 获取当前时间
        current_time = datetime.now()

        # 实时统计数据结构
        realtime_stats = {
            "timestamp": current_time.isoformat(),
            "system_status": "active",
            "detection_stats": {
                "total_detections_today": 0,
                "handwashing_detections": 0,
                "disinfection_detections": 0,
                "hairnet_detections": 0,
                "violation_count": 0,
            },
            "region_stats": {"active_regions": 0, "monitored_areas": []},
            "performance_metrics": {
                "average_processing_time": 0.0,
                "detection_accuracy": 0.0,
                "system_uptime": "00:00:00",
            },
            "alerts": {"active_alerts": 0, "recent_violations": []},
        }

        # 如果区域服务可用，获取区域相关统计
        if region_service:
            try:
                # 这里可以添加从区域服务获取实际数据的逻辑
                realtime_stats["region_stats"]["active_regions"] = 1
                realtime_stats["region_stats"]["monitored_areas"] = ["默认区域"]
            except Exception as e:
                logger.warning(f"获取区域统计失败: {e}")

        logger.info("成功获取实时统计数据")
        return realtime_stats

    except Exception as e:
        logger.exception(f"获取实时统计失败: {e}")
        # 返回错误状态但不抛出异常，保证接口可用性
        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": "error",
            "error": str(e),
            "detection_stats": {},
            "region_stats": {},
            "performance_metrics": {},
            "alerts": {},
        }


def _read_recent_events(max_lines: int = 5000) -> List[Dict[str, Any]]:
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    events_file = os.path.join(project_root, "logs", "events_record.jsonl")
    out: List[Dict[str, Any]] = []
    if not os.path.exists(events_file):
        return out
    try:
        with open(events_file, "rb") as f:
            # 尾读，提高大文件效率
            try:
                f.seek(0, os.SEEK_END)
                end = f.tell()
                step = 8192
                data = b""
                while end > 0 and data.count(b"\n") <= max_lines:
                    offset = max(0, end - step)
                    f.seek(offset)
                    chunk = f.read(end - offset)
                    data = chunk + data
                    end = offset
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = open(events_file, "r", encoding="utf-8").read()
        for line in text.strip().splitlines()[-max_lines:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return out


@router.get("/statistics/summary", summary="事件统计汇总")
def get_statistics_summary(
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
    """
    rows = _read_recent_events(max_lines=max(limit * 2, 2000))
    since_ts = (datetime.utcnow() - timedelta(minutes=minutes)).timestamp()
    total = 0
    by_type: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []

    for r in reversed(rows):
        try:
            ts = float(r.get("ts", 0.0))
            if ts < since_ts:
                continue
            if camera_id is not None:
                if str(r.get("camera_id", "")) != str(camera_id):
                    continue
            et = str(r.get("type", "UNKNOWN"))
            by_type[et] = by_type.get(et, 0) + 1
            total += 1
            if len(samples) < limit:
                samples.append(r)
        except Exception:
            continue

    return {
        "window_minutes": minutes,
        "total_events": total,
        "counts_by_type": by_type,
        "samples": list(reversed(samples)),  # 按时间正序返回样本
    }


@router.get("/statistics/daily", summary="按天统计事件趋势")
def get_statistics_daily(
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
    """
    rows = _read_recent_events(max_lines=200000)
    from datetime import timezone

    # 构建最近 N 天日期集合（UTC）
    today = datetime.utcnow().date()
    days_set = {str((today - timedelta(days=i))) for i in range(days)}
    per_day: Dict[str, Dict[str, int]] = {}
    total_day: Dict[str, int] = {}
    for r in rows:
        try:
            if camera_id is not None and str(r.get("camera_id", "")) != str(camera_id):
                continue
            ts = float(r.get("ts", 0.0))
            d = datetime.utcfromtimestamp(ts).date()
            dstr = str(d)
            if dstr not in days_set:
                continue
            et = str(r.get("type", "UNKNOWN"))
            if dstr not in per_day:
                per_day[dstr] = {}
                total_day[dstr] = 0
            per_day[dstr][et] = per_day[dstr].get(et, 0) + 1
            total_day[dstr] = total_day.get(dstr, 0) + 1
        except Exception:
            continue
    # 组装输出（按日期升序）
    out: List[Dict[str, Any]] = []
    for i in range(days - 1, -1, -1):
        dstr = str(today - timedelta(days=i))
        out.append(
            {
                "date": dstr,
                "total_events": int(total_day.get(dstr, 0)),
                "counts_by_type": per_day.get(dstr, {}),
            }
        )
    return out


@router.get("/statistics/history", summary="近期事件历史")
def get_statistics_history(
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
    """
    rows = _read_recent_events(max_lines=max(limit * 5, 2000))
    since_ts = (datetime.utcnow() - timedelta(minutes=minutes)).timestamp()
    out: List[Dict[str, Any]] = []
    for r in reversed(rows):
        try:
            if float(r.get("ts", 0.0)) < since_ts:
                continue
            if camera_id is not None and str(r.get("camera_id", "")) != str(camera_id):
                continue
            out.append(
                {
                    "ts": r.get("ts"),
                    "camera_id": r.get("camera_id"),
                    "type": r.get("type"),
                    "track_id": r.get("track_id"),
                    "region": (r.get("evidence", {}) or {}).get("region"),
                    "detail": r.get("evidence", {}),
                }
            )
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out
