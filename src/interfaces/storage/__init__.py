"""
存储接口定义。

该包定义与数据样本存储相关的抽象接口，供应用层依赖。
"""

from .snapshot_storage_protocol import SnapshotInfo, SnapshotStorageProtocol

__all__ = ["SnapshotInfo", "SnapshotStorageProtocol"]
