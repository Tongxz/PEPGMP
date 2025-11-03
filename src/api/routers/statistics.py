#!/usr/bin/env python3
"""统计信息路由模块.

提供统计数据和违规记录的API端点.
"""
import json
import logging
import os
from datetime import datetime, timedelta
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from src.api.utils.rollout import should_use_domain

from src.services.region_service import RegionService, get_region_service
try:
    from src.services.detection_service_domain import (
        get_detection_service_domain,
    )
except Exception:
    get_detection_service_domain = None  # type: ignore

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/statistics/realtime", summary="实时统计接口")
async def get_realtime_statistics(
    region_service: RegionService = Depends(get_region_service),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """获取实时统计信息.

    Args:
        region_service: 区域服务依赖项.
        force_domain: 测试用途，强制走领域分支

    Returns:
        实时统计数据，包括当前检测状态、违规统计等.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_realtime_statistics()
            # 如果区域服务可用，尝试补充区域信息
            if region_service:
                try:
                    # 可以尝试从区域服务获取额外信息（保持兼容）
                    pass
                except Exception as e:
                    logger.warning(f"获取区域统计失败: {e}")
            return result
    except Exception as e:
        logger.warning(f"领域服务获取实时统计失败，回退到默认实现: {e}")

    # 旧实现（回退）
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
                realtime_stats["region_stats"]["active_regions"] = 1  # type: ignore
                realtime_stats["region_stats"]["monitored_areas"] = ["默认区域"]  # type: ignore
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


def _read_recent_events(max_lines: int = 5000) -> List[Dict[str, Any]]:  # noqa: C901
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
async def get_statistics_summary(
    minutes: int = Query(60, ge=1, le=24 * 60),
    limit: int = Query(1000, ge=1, le=10000),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
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
    # 若开启领域服务，则优先使用领域服务统计
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=minutes)
            analytics = await domain_service.get_detection_analytics(
                camera_id=camera_id, start_time=start_time, end_time=end_time
            )
            stats = analytics.get("detection_statistics", {})
            # 适配原响应结构
            return {
                "window_minutes": minutes,
                "total_events": int(stats.get("total_records", 0)),
                "counts_by_type": stats.get("object_distribution", {}),
                "samples": [],
            }
    except Exception as e:
        logger.warning(f"领域服务统计失败，回退到日志统计: {e}")

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
async def get_statistics_daily(
    days: int = Query(7, ge=1, le=90),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> List[Dict[str, Any]]:
    """返回最近 N 天内的每日事件统计.

    输出：[{date: 'YYYY-MM-DD', total_events: int, counts_by_type: {etype: count}}]

    Args:
        days: 要查询的最近天数.
        camera_id: (可选) 要筛选的摄像头ID.
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个包含每日统计信息的列表.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_daily_statistics(
                days=days, camera_id=camera_id
            )
            return result
    except Exception as e:
        logger.warning(f"领域服务按天统计失败，回退到日志统计: {e}")

    # 旧实现（回退）
    rows = _read_recent_events(max_lines=200000)

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


@router.get("/statistics/events", summary="事件列表查询")
async def get_statistics_events(
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)"),
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    camera_id: Optional[str] = Query(None, description="摄像头ID过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> Dict[str, Any]:
    """查询事件列表，支持时间范围和多种过滤条件.

    Args:
        start_time: 开始时间 (ISO格式字符串)
        end_time: 结束时间 (ISO格式字符串)
        event_type: 事件类型
        camera_id: 摄像头ID
        limit: 返回数量限制
        force_domain: 测试用途，强制走领域分支

    Returns:
        包含事件列表的字典
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            
            # 解析时间范围
            from datetime import datetime as dt
            start_dt = None
            end_dt = None
            
            if start_time:
                try:
                    start_dt = dt.fromisoformat(start_time.replace('Z', '+00:00'))
                except Exception:
                    pass
            
            if end_time:
                try:
                    end_dt = dt.fromisoformat(end_time.replace('Z', '+00:00'))
                except Exception:
                    pass
            
            result = await domain_service.get_event_history(
                start_time=start_dt,
                end_time=end_dt,
                event_type=event_type,
                camera_id=camera_id,
                limit=limit,
            )
            return result
    except Exception as e:
        logger.warning(f"领域服务事件列表查询失败，回退到日志查询: {e}")

    # 旧实现（回退）
    from datetime import datetime as dt

    # 解析时间范围
    if start_time:
        try:
            start_dt = dt.fromisoformat(start_time.replace('Z', '+00:00'))
            since_ts = start_dt.timestamp()
        except Exception:
            since_ts = (datetime.utcnow() - timedelta(hours=24)).timestamp()
    else:
        since_ts = (datetime.utcnow() - timedelta(hours=24)).timestamp()

    if end_time:
        try:
            end_dt = dt.fromisoformat(end_time.replace('Z', '+00:00'))
            until_ts = end_dt.timestamp()
        except Exception:
            until_ts = datetime.utcnow().timestamp()
    else:
        until_ts = datetime.utcnow().timestamp()

    rows = _read_recent_events(max_lines=max(limit * 5, 2000))
    out: List[Dict[str, Any]] = []

    for r in reversed(rows):
        try:
            event_ts = float(r.get("ts", 0.0))
            
            # 时间范围过滤
            if event_ts < since_ts or event_ts > until_ts:
                continue
            
            # 摄像头过滤
            if camera_id is not None and str(r.get("camera_id", "")) != str(camera_id):
                continue
            
            # 事件类型过滤
            if event_type is not None and str(r.get("type", "")) != str(event_type):
                continue
            
            out.append({
                "id": str(r.get("ts", "")) + "_" + str(r.get("track_id", "")),
                "timestamp": dt.utcfromtimestamp(event_ts).isoformat() + 'Z',
                "type": r.get("type"),
                "camera_id": r.get("camera_id"),
                "confidence": r.get("evidence", {}).get("confidence", 0.0),
                "track_id": r.get("track_id"),
                "region": (r.get("evidence", {}) or {}).get("region"),
                "metadata": r.get("evidence", {}),
            })
            
            if len(out) >= limit:
                break
        except Exception:
            continue

    return {"events": out, "total": len(out)}


@router.get("/statistics/history", summary="近期事件历史")
async def get_statistics_history(
    minutes: int = Query(60, ge=1, le=24 * 60),
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[str] = Query(None, description="按摄像头过滤（可选）"),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> List[Dict[str, Any]]:
    """返回近期事件列表，按时间倒序.

    Args:
        minutes: 要查询的最近分钟数.
        limit: 返回事件的最大数量.
        camera_id: (可选) 要筛选的摄像头ID.
        force_domain: 测试用途，强制走领域分支

    Returns:
        一个包含事件详细信息的列表.
    """
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_recent_history(
                minutes=minutes, limit=limit, camera_id=camera_id
            )
            # 转换为旧格式
            formatted_result = []
            for event in result:
                formatted_result.append({
                    "ts": event.get("timestamp"),
                    "camera_id": event.get("camera_id"),
                    "type": event.get("type"),
                    "track_id": event.get("track_id"),
                    "region": event.get("region"),
                    "detail": event.get("metadata", {}),
                })
            return formatted_result
    except Exception as e:
        logger.warning(f"领域服务近期历史查询失败，回退到日志查询: {e}")

    # 旧实现（回退）
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
