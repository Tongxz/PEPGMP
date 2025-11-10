"""
检测帧快照存储接口定义。

应用层只依赖此协议，实现由基础设施层提供。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional, Protocol

import numpy as np


@dataclass(frozen=True)
class SnapshotInfo:
    """快照存储结果信息。"""

    relative_path: str
    absolute_path: str
    camera_id: str
    captured_at: datetime
    violation_type: Optional[str] = None
    metadata: Optional[Mapping[str, str]] = None


class SnapshotStorageProtocol(Protocol):
    """检测帧快照存储协议。"""

    async def save_frame(
        self,
        frame: np.ndarray,
        camera_id: str,
        *,
        captured_at: Optional[datetime] = None,
        violation_type: Optional[str] = None,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> SnapshotInfo:
        """
        保存原始检测帧或违规截图。

        Args:
            frame: BGR 格式图像数据。
            camera_id: 摄像头 ID。
            captured_at: 捕获时间，不提供则使用当前时间。
            violation_type: 违规类型（如存在）。
            metadata: 额外元数据。

        Returns:
            SnapshotInfo: 保存结果描述。
        """
