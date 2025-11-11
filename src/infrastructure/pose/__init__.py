"""
姿态提取基础设施实现。
"""

from .mediapipe_pose_extractor import (
    MediapipePoseExtractor,
    MediapipePoseExtractorConfig,
)

__all__ = ["MediapipePoseExtractor", "MediapipePoseExtractorConfig"]
