# Detection module
# 检测模块

# 具体检测器实现
__all__ = [
    "HumanDetector",
    "YOLOHairnetDetector",
    "EnhancedHandDetector",
    "PoseDetectorFactory",
    "MotionAnalyzer",
    "HairnetDetector",
    "HairnetDetectionFactory",
]


# 延迟导入以避免循环依赖
def __getattr__(name):
    if name == "HumanDetector":
        from .detector import HumanDetector

        return HumanDetector
    elif name == "YOLOHairnetDetector":
        from .yolo_hairnet_detector import YOLOHairnetDetector

        return YOLOHairnetDetector
    elif name == "EnhancedHandDetector":
        from .enhanced_hand_detector import EnhancedHandDetector

        return EnhancedHandDetector
    elif name == "PoseDetectorFactory":
        from .pose_detector import PoseDetectorFactory

        return PoseDetectorFactory
    elif name == "MotionAnalyzer":
        from .motion_analyzer import MotionAnalyzer

        return MotionAnalyzer
    elif name == "HairnetDetector":
        from .hairnet_detector import HairnetDetector

        return HairnetDetector
    elif name == "HairnetDetectionFactory":
        from .hairnet_detection_factory import HairnetDetectionFactory

        return HairnetDetectionFactory
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
