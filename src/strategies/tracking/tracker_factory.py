"""
跟踪器工厂
使用工厂模式创建不同的跟踪器策略
"""

import logging
from typing import Any, Dict, List, Optional, Type

from src.interfaces.tracking.tracker_interface import ITracker

try:
    from .byte_tracker_strategy import ByteTrackerStrategy
except ImportError:
    # ByteTrackerStrategy 已被归档，设置为 None
    ByteTrackerStrategy = None

from .simple_tracker_strategy import SimpleTrackerStrategy

logger = logging.getLogger(__name__)


class TrackerFactory:
    """跟踪器工厂"""

    # 注册的跟踪器策略
    _strategies: Dict[str, Optional[Type[ITracker]]] = {
        "simple_tracker": SimpleTrackerStrategy,
    }

    # 如果 ByteTrackerStrategy 可用，注册它
    if ByteTrackerStrategy is not None:
        _strategies["byte_tracker"] = ByteTrackerStrategy

    @classmethod
    def create_tracker(cls, tracker_type: str, **kwargs) -> ITracker:
        """
        创建跟踪器实例

        Args:
            tracker_type: 跟踪器类型
            **kwargs: 跟踪器参数

        Returns:
            ITracker: 跟踪器实例

        Raises:
            ValueError: 不支持的跟踪器类型
            TrackingError: 跟踪器创建失败
        """
        if tracker_type not in cls._strategies:
            available_types = list(cls._strategies.keys())
            raise ValueError(f"不支持的跟踪器类型: {tracker_type}. 可用类型: {available_types}")

        strategy_class = cls._strategies[tracker_type]
        if strategy_class is None:
            raise ValueError(f"跟踪器类型 {tracker_type} 不可用（已被归档）")

        try:
            tracker = strategy_class(**kwargs)

            logger.info(f"创建跟踪器成功: {tracker_type}")
            return tracker

        except Exception as e:
            logger.error(f"创建跟踪器失败: {tracker_type}, 错误: {e}")
            raise

    @classmethod
    def get_available_trackers(cls) -> List[str]:
        """
        获取可用的跟踪器列表

        Returns:
            List[str]: 可用的跟踪器类型列表
        """
        available = []

        for tracker_type, strategy_class in cls._strategies.items():
            try:
                # 尝试创建跟踪器实例来检查可用性
                tracker = strategy_class()

                # 简单跟踪器总是可用的
                if tracker_type == "simple_tracker":
                    available.append(tracker_type)
                else:
                    # 其他跟踪器需要检查依赖
                    if hasattr(tracker, "is_available") and tracker.is_available():
                        available.append(tracker_type)

            except Exception as e:
                logger.debug(f"跟踪器 {tracker_type} 不可用: {e}")
                continue

        return available

    @classmethod
    def get_tracker_info(cls, tracker_type: str) -> Dict[str, Any]:
        """
        获取跟踪器信息

        Args:
            tracker_type: 跟踪器类型

        Returns:
            Dict[str, Any]: 跟踪器信息
        """
        if tracker_type not in cls._strategies:
            raise ValueError(f"不支持的跟踪器类型: {tracker_type}")

        strategy_class = cls._strategies[tracker_type]

        # 获取策略类的文档字符串
        doc = strategy_class.__doc__ or "无文档"

        return {
            "type": tracker_type,
            "class": strategy_class.__name__,
            "module": strategy_class.__module__,
            "description": doc.strip(),
            "available": tracker_type in cls.get_available_trackers(),
        }

    @classmethod
    def register_strategy(
        cls, tracker_type: str, strategy_class: Type[ITracker]
    ) -> None:
        """
        注册新的跟踪器策略

        Args:
            tracker_type: 跟踪器类型名称
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, ITracker):
            raise ValueError(f"策略类必须实现 ITracker 接口: {strategy_class}")

        cls._strategies[tracker_type] = strategy_class
        logger.info(f"注册跟踪器策略: {tracker_type} -> {strategy_class.__name__}")

    @classmethod
    def unregister_strategy(cls, tracker_type: str) -> None:
        """
        注销跟踪器策略

        Args:
            tracker_type: 跟踪器类型名称
        """
        if tracker_type in cls._strategies:
            del cls._strategies[tracker_type]
            logger.info(f"注销跟踪器策略: {tracker_type}")
        else:
            logger.warning(f"尝试注销不存在的跟踪器策略: {tracker_type}")

    @classmethod
    def get_supported_strategies(cls) -> List[str]:
        """
        获取所有支持的策略类型

        Returns:
            List[str]: 策略类型列表
        """
        return list(cls._strategies.keys())

    @classmethod
    def validate_tracker_config(cls, tracker_type: str, config: Dict[str, Any]) -> bool:
        """
        验证跟踪器配置

        Args:
            tracker_type: 跟踪器类型
            config: 配置字典

        Returns:
            bool: 配置是否有效
        """
        if tracker_type not in cls._strategies:
            return False

        try:
            # 尝试创建跟踪器实例来验证配置
            cls.create_tracker(tracker_type, **config)
            return True
        except Exception as e:
            logger.debug(f"跟踪器配置验证失败: {tracker_type}, 错误: {e}")
            return False


def create_tracker_from_config(config: Dict[str, Any]) -> ITracker:
    """
    从配置创建跟踪器

    Args:
        config: 配置字典，必须包含 'type' 字段

    Returns:
        ITracker: 跟踪器实例
    """
    tracker_type = config.get("type")
    if not tracker_type:
        raise ValueError("配置中必须包含 'type' 字段")

    # 移除 type 字段，其余作为参数
    tracker_config = {k: v for k, v in config.items() if k != "type"}

    return TrackerFactory.create_tracker(tracker_type, **tracker_config)


def get_tracker_recommendations() -> Dict[str, Any]:
    """
    获取跟踪器推荐信息

    Returns:
        Dict[str, Any]: 推荐信息
    """
    available = TrackerFactory.get_available_trackers()

    recommendations = {
        "byte_tracker": {
            "description": "ByteTracker - 高性能多目标跟踪，基于ByteTrack算法",
            "best_for": ["多目标跟踪", "高精度要求", "复杂场景"],
            "performance": "高",
            "resource_usage": "中等",
            "available": "byte_tracker" in available,
        },
        "simple_tracker": {
            "description": "SimpleTracker - 轻量级IoU匹配跟踪",
            "best_for": ["简单场景", "低资源环境", "快速原型"],
            "performance": "中等",
            "resource_usage": "低",
            "available": "simple_tracker" in available,
        },
    }

    return recommendations
