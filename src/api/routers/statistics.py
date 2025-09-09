"""统计信息路由模块.

提供统计数据和违规记录的API端点.
"""
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

from fastapi import APIRouter, Depends, Query

from src.services.region_service import RegionService, get_region_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/statistics")
def get_statistics(region_service: RegionService = Depends(get_region_service)):
    """获取统计信息.

    Args:
        region_service: 区域服务依赖项

    Returns:
        统计信息数据
    """
    # This is a placeholder for statistics logic
    # In a real application, this would query a database or a metrics service
    return {"message": "Statistics endpoint"}


@router.get("/violations")
def get_violations(region_service: RegionService = Depends(get_region_service)):
    """获取违规记录.

    Args:
        region_service: 区域服务依赖项

    Returns:
        违规记录数据
    """
    # This is a placeholder for violation retrieval logic
    return {"message": "Violations endpoint"}


@router.get("/statistics/realtime", summary="实时统计接口")
def get_realtime_statistics(
    region_service: RegionService = Depends(get_region_service)
) -> Dict[str, Any]:
    """获取实时统计信息.

    Args:
        region_service: 区域服务依赖项

    Returns:
        实时统计数据，包括当前检测状态、违规统计等
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
                "violation_count": 0
            },
            "region_stats": {
                "active_regions": 0,
                "monitored_areas": []
            },
            "performance_metrics": {
                "average_processing_time": 0.0,
                "detection_accuracy": 0.0,
                "system_uptime": "00:00:00"
            },
            "alerts": {
                "active_alerts": 0,
                "recent_violations": []
            }
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
            "alerts": {}
        }


def _read_recent_events(max_lines: int = 5000) -> List[Dict[str, Any]]:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
) -> Dict[str, Any]:
    """返回最近 N 分钟内的事件统计与分布。"""
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
