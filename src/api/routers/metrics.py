from __future__ import annotations

import os
import json
from typing import Dict

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


router = APIRouter()


def _read_event_counts(max_lines: int = 5000) -> Dict[str, int]:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    events_file = os.path.join(project_root, "logs", "events_record.jsonl")
    counts: Dict[str, int] = {}
    total = 0
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
                counts[et] = counts.get(et, 0) + 1
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
    for et, c in counts.items():
        lines.append(f'hbd_events_total{{type="{et}"}} {c}')
    lines.append(f"hbd_events_total {total}")
    return "\n".join(lines) + "\n"



