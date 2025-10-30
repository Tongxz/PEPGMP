"""
检测器工厂
使用工厂模式创建不同的检测器策略
"""

import logging
from typing import Any, Dict, List, Type

from src.interfaces.detection.detector_interface import IDetector

from .mediapipe_strategy import MediaPipeStrategy
from .yolo_strategy import YOLOStrategy

logger = logging.getLogger(__name__)


class DetectorFactory:
    """检测器工厂"""

    # 注册的检测器策略
    _strategies: Dict[str, Type[IDetector]] = {
        "yolo": YOLOStrategy,
        "mediapipe": MediaPipeStrategy,
    }

    @classmethod
    def create_detector(self, detector_type: str, **kwargs) -> IDetector:
        """
        创建检测器实例

        Args:
            detector_type: 检测器类型
            **kwargs: 检测器参数

        Returns:
            IDetector: 检测器实例

        Raises:
            ValueError: 不支持的检测器类型
            DetectionError: 检测器创建失败
        """
        if detector_type not in self._strategies:
            available_types = list(self._strategies.keys())
            raise ValueError(f"不支持的检测器类型: {detector_type}. 可用类型: {available_types}")

        try:
            strategy_class = self._strategies[detector_type]
            detector = strategy_class(**kwargs)

            logger.info(f"创建检测器成功: {detector_type}")
            return detector

        except Exception as e:
            logger.error(f"创建检测器失败: {detector_type}, 错误: {e}")
            raise

    @classmethod
    def get_available_detectors(cls) -> List[str]:
        """
        获取可用的检测器列表

        Returns:
            List[str]: 可用的检测器类型列表
        """
        available = []

        for detector_type, strategy_class in cls._strategies.items():
            try:
                # 尝试创建检测器实例来检查可用性
                if detector_type == "yolo":
                    # YOLO需要模型路径
                    detector = strategy_class(model_path="dummy.pt")
                else:
                    detector = strategy_class()

                if detector.is_available():
                    available.append(detector_type)

            except Exception as e:
                logger.debug(f"检测器 {detector_type} 不可用: {e}")
                continue

        return available

    @classmethod
    def get_detector_info(cls, detector_type: str) -> Dict[str, Any]:
        """
        获取检测器信息

        Args:
            detector_type: 检测器类型

        Returns:
            Dict[str, Any]: 检测器信息
        """
        if detector_type not in cls._strategies:
            raise ValueError(f"不支持的检测器类型: {detector_type}")

        strategy_class = cls._strategies[detector_type]

        # 获取策略类的文档字符串
        doc = strategy_class.__doc__ or "无文档"

        return {
            "type": detector_type,
            "class": strategy_class.__name__,
            "module": strategy_class.__module__,
            "description": doc.strip(),
            "available": detector_type in cls.get_available_detectors(),
        }

    @classmethod
    def register_strategy(
        cls, detector_type: str, strategy_class: Type[IDetector]
    ) -> None:
        """
        注册新的检测器策略

        Args:
            detector_type: 检测器类型名称
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, IDetector):
            raise ValueError(f"策略类必须实现 IDetector 接口: {strategy_class}")

        cls._strategies[detector_type] = strategy_class
        logger.info(f"注册检测器策略: {detector_type} -> {strategy_class.__name__}")

    @classmethod
    def unregister_strategy(cls, detector_type: str) -> None:
        """
        注销检测器策略

        Args:
            detector_type: 检测器类型名称
        """
        if detector_type in cls._strategies:
            del cls._strategies[detector_type]
            logger.info(f"注销检测器策略: {detector_type}")
        else:
            logger.warning(f"尝试注销不存在的检测器策略: {detector_type}")

    @classmethod
    def get_supported_strategies(cls) -> List[str]:
        """
        获取所有支持的策略类型

        Returns:
            List[str]: 策略类型列表
        """
        return list(cls._strategies.keys())

    @classmethod
    def validate_detector_config(
        cls, detector_type: str, config: Dict[str, Any]
    ) -> bool:
        """
        验证检测器配置

        Args:
            detector_type: 检测器类型
            config: 配置字典

        Returns:
            bool: 配置是否有效
        """
        if detector_type not in cls._strategies:
            return False

        try:
            # 尝试创建检测器实例来验证配置
            detector = cls.create_detector(detector_type, **config)
            return detector.is_available()
        except Exception as e:
            logger.debug(f"检测器配置验证失败: {detector_type}, 错误: {e}")
            return False


def create_detector_from_config(config: Dict[str, Any]) -> IDetector:
    """
    从配置创建检测器

    Args:
        config: 配置字典，必须包含 'type' 字段

    Returns:
        IDetector: 检测器实例
    """
    detector_type = config.get("type")
    if not detector_type:
        raise ValueError("配置中必须包含 'type' 字段")

    # 移除 type 字段，其余作为参数
    detector_config = {k: v for k, v in config.items() if k != "type"}

    return DetectorFactory.create_detector(detector_type, **detector_config)


def get_detector_recommendations() -> Dict[str, Any]:
    """
    获取检测器推荐信息

    Returns:
        Dict[str, Any]: 推荐信息
    """
    available = DetectorFactory.get_available_detectors()

    recommendations = {
        "yolo": {
            "description": "YOLO - 高精度目标检测，支持多种类别",
            "best_for": ["目标检测", "多类别识别", "高精度要求"],
            "performance": "高",
            "resource_usage": "中等",
            "available": "yolo" in available,
        },
        "mediapipe": {
            "description": "MediaPipe - 轻量级人体姿态检测",
            "best_for": ["人体姿态", "实时检测", "低资源环境"],
            "performance": "中等",
            "resource_usage": "低",
            "available": "mediapipe" in available,
        },
    }

    return recommendations
