"""
姿态关键点提取服务接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np


@dataclass
class PoseSequence:
    """姿态关键点序列。"""

    timestamps: np.ndarray  # shape: (T,)
    landmarks: np.ndarray  # shape: (T, K, D)

    @property
    def frame_count(self) -> int:
        return int(self.landmarks.shape[0])


class PoseExtractorProtocol(Protocol):
    """姿态提取服务协议。"""

    def extract_from_video(
        self,
        video_path: Path,
        *,
        frame_interval: float = 0.5,
        start_offset: float = 0.0,
        end_offset: float | None = None,
    ) -> PoseSequence:
        """
        从视频中提取关键点序列。

        Args:
            video_path: 视频文件路径
            frame_interval: 采样间隔秒数
            start_offset: 起始偏移（秒）
            end_offset: 结束偏移（秒），None 表示到视频末尾
        """
