"""
检测服务初始化器

负责初始化检测相关的所有组件：
- 检测管线
- 应用服务
- 配置参数
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DetectionInitializer:
    """
    检测服务初始化器

    职责：
    1. 初始化检测管线（人体检测、姿态检测、行为识别等）
    2. 初始化应用服务（检测应用服务、视频流服务）
    3. 创建检测循环配置

    这个类将 main.py 中复杂的初始化逻辑集中管理。
    """

    @staticmethod
    def initialize_pipeline(args, logger, effective_config: Dict[str, Any]):
        """
        初始化检测管线

        Args:
            args: 命令行参数
            logger: 日志记录器
            effective_config: 有效配置（合并后的）

        Returns:
            OptimizedDetectionPipeline实例
        """
        from config.unified_params import get_unified_params, update_global_param
        from src.core.behavior import BehaviorRecognizer
        from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
        from src.detection.detector import HumanDetector
        from src.detection.pose_detector import PoseDetectorFactory
        from src.detection.yolo_hairnet_detector import YOLOHairnetDetector

        # 1. 提取配置
        hd = effective_config.get("human_detection", {})
        weights = hd.get("model_path", "models/yolo/yolov8n.pt")
        device = args.device or "cpu"
        cascade_cfg = effective_config.get("cascade", {})

        # 2. 回填全局配置
        for k in [
            "model_path",
            "confidence_threshold",
            "iou_threshold",
            "min_box_area",
            "max_box_ratio",
            "min_width",
            "min_height",
            "nms_threshold",
            "max_detections",
            "device",
        ]:
            if k in hd:
                update_global_param("human_detection", k, hd[k])

        # 3. 权重文件存在性检查
        wpath = Path(weights) if weights else None
        if not (wpath and wpath.exists()):
            alt = Path("models/yolo/yolov8n.pt")
            logger.warning(f"指定权重不存在: {weights}，回退到 {alt}")
            weights = str(alt)
            update_global_param("human_detection", "model_path", weights)

        # 4. 初始化人体检测器
        human_detector = HumanDetector(model_path=weights, device=device)

        # 5. 初始化姿态检测器
        params = get_unified_params()
        pose_backend = params.pose_detection.backend
        if pose_backend == "auto":
            pose_backend = "yolov8" if str(device).lower() == "cuda" else "mediapipe"

        pose_detector = PoseDetectorFactory.create(
            backend=pose_backend,
            device=params.pose_detection.device
            if params.pose_detection.device != "auto"
            else device,
        )
        logger.info(f"姿态检测器后端: {pose_backend}, 设备: {device}")

        # 6. 初始化其他组件
        behavior_recognizer = BehaviorRecognizer()
        # 从环境变量读取是否保存调试ROI
        save_debug_roi = os.getenv("SAVE_DEBUG_ROI", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        debug_roi_dir = os.getenv("DEBUG_ROI_DIR", None)
        hairnet_detector = YOLOHairnetDetector(
            device=device, save_debug_roi=save_debug_roi, debug_roi_dir=debug_roi_dir
        )

        # 7. 创建管线
        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            hairnet_detector=hairnet_detector,
            behavior_recognizer=behavior_recognizer,
            pose_detector=pose_detector,
            enable_cache=True,
            cache_size=50,
            cache_ttl=20.0,
            cascade_config=cascade_cfg,
        )

        logger.info("✓ 检测管线初始化完成")
        return pipeline

    @staticmethod
    def initialize_services(
        args, logger, pipeline
    ) -> Tuple[Optional[Any], Optional[Any]]:
        """
        初始化应用服务

        Args:
            args: 命令行参数
            logger: 日志记录器
            pipeline: 检测管线

        Returns:
            (DetectionApplicationService, VideoStreamApplicationService) 元组
        """
        from src.application.detection_application_service import (
            DetectionApplicationService,
            SavePolicy,
            SaveStrategy,
        )
        from src.application.video_stream_application_service import (
            get_video_stream_service,
        )
        from src.config.storage_config import build_snapshot_storage
        from src.services.detection_service_domain import get_detection_service_domain

        # 1. 创建检测应用服务
        try:
            save_strategy = SaveStrategy[args.save_strategy.upper()]
            save_policy = SavePolicy(
                strategy=save_strategy,
                save_interval=args.save_interval,
                normal_sample_interval=args.normal_sample_interval,
                save_normal_summary=True,
                violation_severity_threshold=args.violation_threshold,
            )

            domain_service = get_detection_service_domain()
            snapshot_storage = build_snapshot_storage()
            detection_app_service = DetectionApplicationService(
                detection_pipeline=pipeline,
                detection_domain_service=domain_service,
                snapshot_storage=snapshot_storage,
                save_policy=save_policy,
            )

            logger.info(
                f"✓ 智能保存策略已启用: {save_strategy.value}, "
                f"违规阈值={args.violation_threshold}, "
                f"采样间隔={args.normal_sample_interval}"
            )
        except Exception as e:
            logger.error(f"初始化检测应用服务失败: {e}")
            detection_app_service = None

        # 2. 创建视频流服务
        try:
            video_stream_service = get_video_stream_service()
            logger.info("✓ 视频流服务已启用")
        except Exception as e:
            logger.warning(f"视频流服务初始化失败: {e}，将禁用视频流推送")
            video_stream_service = None

        return detection_app_service, video_stream_service

    @staticmethod
    def create_loop_config(args):
        """
        创建检测循环配置

        Args:
            args: 命令行参数

        Returns:
            DetectionLoopConfig对象
        """
        from src.application.detection_loop_service import DetectionLoopConfig

        return DetectionLoopConfig(
            camera_id=getattr(args, "camera_id", "unknown"),
            source=args.source,
            log_interval=args.log_interval if args.log_interval is not None else 1,
            stream_interval=int(os.getenv("VIDEO_STREAM_INTERVAL", "3")),
            video_quality=int(os.getenv("VIDEO_STREAM_QUALITY", "60")),
            stream_width=int(os.getenv("VIDEO_STREAM_WIDTH", "800")),
            stream_height=int(os.getenv("VIDEO_STREAM_HEIGHT", "450")),
        )
