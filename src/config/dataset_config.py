"""
数据集生成配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetGenerationConfig:
    """数据集生成配置。"""

    output_dir: Path
    snapshot_base_dir: Path
    annotation_format: str = "csv"
    annotation_filename: str = "annotations.csv"


def get_dataset_generation_config() -> DatasetGenerationConfig:
    """
    构建数据集生成配置。
    """

    output_dir = Path(os.getenv("DATASET_OUTPUT_DIR", "datasets/exports")).expanduser()
    snapshot_base_dir = Path(
        os.getenv("SNAPSHOT_BASE_DIR", "datasets/raw")
    ).expanduser()
    annotation_format = os.getenv("DATASET_ANNOTATION_FORMAT", "csv").lower()
    annotation_filename = os.getenv("DATASET_ANNOTATION_FILENAME", "annotations.csv")

    output_dir.mkdir(parents=True, exist_ok=True)

    return DatasetGenerationConfig(
        output_dir=output_dir,
        snapshot_base_dir=snapshot_base_dir,
        annotation_format=annotation_format,
        annotation_filename=annotation_filename,
    )
