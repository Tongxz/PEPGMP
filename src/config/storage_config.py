"""
快照存储相关配置。
"""

from __future__ import annotations

import os
from pathlib import Path

from src.infrastructure.storage.filesystem_snapshot_storage import (
    FileSystemSnapshotStorage,
    SnapshotStorageConfig,
)


def get_snapshot_storage_config() -> SnapshotStorageConfig:
    """
    构建快照存储配置。

    Returns:
        SnapshotStorageConfig: 配置实例。
    """

    base_dir = Path(
        os.getenv("SNAPSHOT_BASE_DIR", "datasets/raw"),
    ).expanduser()
    image_format = os.getenv("SNAPSHOT_IMAGE_FORMAT", "jpg").lower()
    image_quality = int(os.getenv("SNAPSHOT_IMAGE_QUALITY", "90"))

    return SnapshotStorageConfig(
        base_dir=base_dir,
        image_format=image_format,
        image_quality=image_quality,
    )


def build_snapshot_storage() -> FileSystemSnapshotStorage:
    """
    工厂方法，构建默认的快照存储实现。
    """

    return FileSystemSnapshotStorage(get_snapshot_storage_config())
