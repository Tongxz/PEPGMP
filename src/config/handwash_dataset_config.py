"""
洗手数据集生成配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HandwashDatasetConfig:
    output_dir: Path
    session_base_dir: Path
    default_frame_interval: float = 0.5
    min_session_duration: float = 3.0
    max_sessions: int = 200


def get_handwash_dataset_config() -> HandwashDatasetConfig:
    output_dir = Path(
        os.getenv("HANDWASH_DATASET_OUTPUT_DIR", "datasets/handwash")
    ).expanduser()
    session_dir = Path(
        os.getenv("HANDWASH_SESSION_DIR", "data/handwash/sessions")
    ).expanduser()
    frame_interval = float(os.getenv("HANDWASH_FRAME_INTERVAL", "0.5"))
    min_duration = float(os.getenv("HANDWASH_MIN_SESSION_DURATION", "3.0"))
    max_sessions = int(os.getenv("HANDWASH_MAX_SESSIONS", "200"))

    output_dir.mkdir(parents=True, exist_ok=True)

    return HandwashDatasetConfig(
        output_dir=output_dir,
        session_base_dir=session_dir,
        default_frame_interval=frame_interval,
        min_session_duration=min_duration,
        max_sessions=max_sessions,
    )
