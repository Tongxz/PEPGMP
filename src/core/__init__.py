# Core modules for human behavior detection
# 人体行为检测核心模块

# 延迟导入以避免循环依赖
__all__ = [
    "HumanDetector",
    "MultiObjectTracker",
    "BehaviorRecognizer",
    "RegionManager",
    "FrameMetadata",
    "FrameSource",
    "FrameMetadataManager",
    "StateManager",
    "TemporalSmoother",
    "SynchronizedCache",
    "FrameSkipDetector",
]


def __getattr__(name):
    if name == "HumanDetector":
        from src.detection.detector import HumanDetector

        return HumanDetector
    elif name == "MultiObjectTracker":
        from .tracker import MultiObjectTracker

        return MultiObjectTracker
    elif name == "BehaviorRecognizer":
        from .behavior import BehaviorRecognizer

        return BehaviorRecognizer
    elif name == "RegionManager":
        from .region import RegionManager

        return RegionManager
    elif name == "FrameMetadata":
        from .frame_metadata import FrameMetadata

        return FrameMetadata
    elif name == "FrameSource":
        from .frame_metadata import FrameSource

        return FrameSource
    elif name == "FrameMetadataManager":
        from .frame_metadata_manager import FrameMetadataManager

        return FrameMetadataManager
    elif name == "StateManager":
        from .state_manager import StateManager

        return StateManager
    elif name == "TemporalSmoother":
        from .temporal_smoother import TemporalSmoother

        return TemporalSmoother
    elif name == "SynchronizedCache":
        from .synchronized_cache import SynchronizedCache

        return SynchronizedCache
    elif name == "FrameSkipDetector":
        from .frame_skip_detector import FrameSkipDetector

        return FrameSkipDetector
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
