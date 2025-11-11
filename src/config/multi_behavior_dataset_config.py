"""
多行为数据集生成配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class MultiBehaviorDatasetConfig:
    output_dir: Path
    snapshot_base_dir: Path
    classes: List[str]
    include_normal: bool = False
    max_records: int = 3000


def get_multi_behavior_dataset_config() -> MultiBehaviorDatasetConfig:
    output_dir = Path(
        os.getenv("MULTI_BEHAVIOR_DATASET_DIR", "datasets/multi_behavior")
    ).expanduser()
    snapshot_dir = Path(os.getenv("SNAPSHOT_BASE_DIR", "datasets/raw")).expanduser()
    classes_env = os.getenv(
        "MULTI_BEHAVIOR_CLASSES", "no_hairnet,handwashing,mask_violation"
    )
    classes = [cls.strip() for cls in classes_env.split(",") if cls.strip()]
    include_normal = (
        os.getenv("MULTI_BEHAVIOR_INCLUDE_NORMAL", "false").lower() == "true"
    )
    max_records = int(os.getenv("MULTI_BEHAVIOR_MAX_RECORDS", "3000"))

    output_dir.mkdir(parents=True, exist_ok=True)

    return MultiBehaviorDatasetConfig(
        output_dir=output_dir,
        snapshot_base_dir=snapshot_dir,
        classes=classes,
        include_normal=include_normal,
        max_records=max_records,
    )
