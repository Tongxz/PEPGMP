from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from src.api.utils.rollout import should_use_domain

try:
    from src.services.detection_service_domain import get_detection_service_domain
except Exception:
    get_detection_service_domain = None  # type: ignore

router = APIRouter()
logger = logging.getLogger(__name__)


def _read_events(lines: int = 2000) -> List[Dict[str, Any]]:
    # 事件日志现在位于 logs/events/ 目录下
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    events_file = os.path.join(project_root, "logs", "events", "events_record.jsonl")
    out: List[Dict[str, Any]] = []
    if not os.path.exists(events_file):
        return out
    try:
        # 只读尾部以提高效率
        with open(events_file, "rb") as f:
            try:
                f.seek(0, os.SEEK_END)
                end = f.tell()
                step = 4096
                data = b""
                while end > 0 and data.count(b"\n") <= lines:
                    offset = max(0, end - step)
                    f.seek(offset)
                    chunk = f.read(end - offset)
                    data = chunk + data
                    end = offset
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = open(events_file, "r", encoding="utf-8").read()
        for line in text.strip().splitlines()[-lines:]:
            line = line.strip()
            if not line:
                continue
            try:
                import json

                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return out


@router.get("/api/v1/events/recent")
async def recent_events(
    limit: int = Query(100, ge=1, le=1000),
    minutes: int = Query(60, ge=1, le=24 * 60),
    etype: Optional[str] = Query(None, description="过滤事件类型，如 NO_HAIRNET_AT_SINK"),
    camera_id: Optional[str] = Query(None, description="过滤摄像头 ID，如 cam0"),
    force_domain: Optional[bool] = Query(None, description="测试用途，强制走领域分支"),
) -> List[Dict[str, Any]]:
    """返回最近的事件列表（从 logs/events_record.jsonl 读取或从领域服务）"""
    # 灰度：按配置或强制参数决定是否走领域分支
    try:
        if should_use_domain(force_domain) and get_detection_service_domain is not None:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_recent_events(
                limit=limit,
                minutes=minutes,
                event_type=etype,
                camera_id=camera_id,
            )
            return result
    except Exception as e:
        logger.warning(f"领域服务获取最近事件失败，回退到日志读取: {e}")

    # 旧实现（回退）
    rows = _read_events(lines=2000)
    since_ts = (datetime.utcnow() - timedelta(minutes=minutes)).timestamp()
    out: List[Dict[str, Any]] = []
    for r in reversed(rows):  # 优先最近
        try:
            if float(r.get("ts", 0.0)) < since_ts:
                continue
            if etype and str(r.get("type")) != etype:
                continue
            if camera_id is not None and str(r.get("camera_id", "")) != str(camera_id):
                continue
            out.append(r)
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out
