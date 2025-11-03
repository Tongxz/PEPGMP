"""
跟踪器策略实现
使用策略模式实现不同的跟踪算法
"""

try:
    from .byte_tracker_strategy import ByteTrackerStrategy
except ImportError:
    # ByteTrackerStrategy 已被归档，提供占位符
    ByteTrackerStrategy = None

from .simple_tracker_strategy import SimpleTrackerStrategy
from .tracker_factory import TrackerFactory

__all__ = ["ByteTrackerStrategy", "SimpleTrackerStrategy", "TrackerFactory"]
