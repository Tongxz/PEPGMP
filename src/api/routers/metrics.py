from __future__ import annotations

import json
import os
from typing import Dict

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


def _read_event_counts(max_lines: int = 5000) -> Dict[str, int]:
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    # 事件日志现在位于 logs/events/ 目录下
    events_file = os.path.join(project_root, "logs", "events", "events_record.jsonl")
    counts: Dict[str, int] = {}
    if not os.path.exists(events_file):
        return counts
    try:
        with open(events_file, "rb") as f:
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
                obj = json.loads(line)
                et = str(obj.get("type", "UNKNOWN"))
                cam = str(obj.get("camera_id", "unknown"))
                key = f"{cam}||{et}"
                counts[key] = counts.get(key, 0) + 1
            except Exception:
                continue
    except Exception:
        return counts
    return counts


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus 文本格式指标。"""
    counts = _read_event_counts()
    total = sum(counts.values())
    lines = []
    lines.append("# HELP hbd_events_total Total number of events recorded")
    lines.append("# TYPE hbd_events_total counter")
    # 输出按 camera+type 的计数，并派生按 type 的聚合
    by_type: Dict[str, int] = {}
    for key, c in counts.items():
        try:
            cam, et = key.split("||", 1)
        except ValueError:
            cam, et = "unknown", key
        lines.append(f'hbd_events_total{{camera="{cam}",type="{et}"}} {c}')
        by_type[et] = by_type.get(et, 0) + c
    for et, c in by_type.items():
        lines.append(f'hbd_events_total{{type="{et}"}} {c}')
    lines.append(f"hbd_events_total {total}")
    return "\n".join(lines) + "\n"
