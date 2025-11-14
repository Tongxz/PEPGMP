"""配置重载辅助工具.

用于检测进程中重新加载配置并更新检测管道的参数。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def reload_detection_config(
    detection_pipeline: Any,
    config_type: str,
    config_key: str,
    config_value: Any,
) -> bool:
    """重新加载检测配置并更新检测管道

    Args:
        detection_pipeline: 检测管道实例（OptimizedDetectionPipeline）
        config_type: 配置类型（human_detection, hairnet_detection等）
        config_key: 配置项名称
        config_value: 配置值

    Returns:
        bool: 是否成功重新加载配置
    """
    try:
        # 重新加载统一参数配置
        from src.config.unified_params import get_unified_params

        params = get_unified_params()

        # 更新检测管道的参数
        if hasattr(detection_pipeline, "params"):
            detection_pipeline.params = params
            logger.info(
                f"检测管道参数已更新: config_type={config_type}, "
                f"config_key={config_key}, config_value={config_value}"
            )

        # 根据配置类型更新相应的检测器
        if config_type == "human_detection":
            # 更新人体检测器参数
            if (
                hasattr(detection_pipeline, "human_detector")
                and detection_pipeline.human_detector
            ):
                if config_key == "confidence_threshold":
                    detection_pipeline.human_detector.confidence_threshold = (
                        config_value
                    )
                    logger.info(f"人体检测器置信度阈值已更新: {config_value}")
                elif config_key == "iou_threshold":
                    detection_pipeline.human_detector.iou_threshold = config_value
                    logger.info(f"人体检测器IoU阈值已更新: {config_value}")
                elif config_key in [
                    "min_box_area",
                    "min_width",
                    "min_height",
                    "max_detections",
                ]:
                    setattr(detection_pipeline.human_detector, config_key, config_value)
                    logger.info(f"人体检测器{config_key}已更新: {config_value}")

        elif config_type == "hairnet_detection":
            # 更新发网检测器参数
            if (
                hasattr(detection_pipeline, "hairnet_detector")
                and detection_pipeline.hairnet_detector
            ):
                if config_key == "confidence_threshold":
                    detection_pipeline.hairnet_detector.conf_thres = config_value
                    logger.info(f"发网检测器置信度阈值已更新: {config_value}")
                elif config_key == "total_score_threshold":
                    detection_pipeline.hairnet_detector.total_score_threshold = (
                        config_value
                    )
                    logger.info(f"发网检测器总分数阈值已更新: {config_value}")
                elif hasattr(detection_pipeline.hairnet_detector, config_key):
                    setattr(
                        detection_pipeline.hairnet_detector, config_key, config_value
                    )
                    logger.info(f"发网检测器{config_key}已更新: {config_value}")

        elif config_type == "behavior_recognition":
            # 更新行为识别器参数
            if (
                hasattr(detection_pipeline, "behavior_recognizer")
                and detection_pipeline.behavior_recognizer
            ):
                if config_key == "confidence_threshold":
                    detection_pipeline.behavior_recognizer.confidence_threshold = (
                        config_value
                    )
                    logger.info(f"行为识别器置信度阈值已更新: {config_value}")
                elif config_key in [
                    "handwashing_stability_frames",
                    "sanitizing_stability_frames",
                    "hairnet_stability_frames",
                ]:
                    setattr(
                        detection_pipeline.behavior_recognizer, config_key, config_value
                    )
                    logger.info(f"行为识别器{config_key}已更新: {config_value}")

        elif config_type == "pose_detection":
            # 姿态检测器参数更新（可能需要重新初始化）
            logger.info(
                f"姿态检测器参数变更: {config_key}={config_value}。" "注意：部分参数可能需要重启检测进程才能完全生效。"
            )

        return True

    except Exception as e:
        logger.error(f"重新加载检测配置失败: {e}")
        return False
