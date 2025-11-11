"""
配置加载器

负责加载和合并各种配置源：
- YAML配置文件
- 环境变量
- 命令行参数
- 自适应优化
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    统一配置加载器

    职责：
    1. 加载统一参数配置
    2. 应用CLI覆盖
    3. 应用自适应优化
    4. 应用硬件探测回退
    5. 选择计算设备
    """

    @staticmethod
    def load_and_merge(args, logger) -> Optional[Dict[str, Any]]:
        """
        加载并合并配置

        Args:
            args: 命令行参数
            logger: 日志记录器

        Returns:
            有效配置字典，失败返回None
        """
        try:
            from config.unified_params import get_unified_params

            params = get_unified_params()

            # CLI覆盖
            cli_overrides = {"runtime": {}, "human_detection": {}, "cascade": {}}
            if args.imgsz:
                cli_overrides["human_detection"]["imgsz"] = int(args.imgsz)
            if args.human_weights:
                cli_overrides["human_detection"]["model_path"] = str(args.human_weights)
            if args.cascade_enable:
                cli_overrides["cascade"]["enable"] = True
            if args.log_interval is not None:
                cli_overrides["runtime"]["log_interval"] = int(args.log_interval)

            effective = params.build_effective_config(
                profile=args.profile, cli_overrides=cli_overrides
            )

            logger.info("✓ 配置加载成功")
            return effective

        except Exception as e:
            logger.error(f"加载/合并配置失败: {e}")
            return None

    @staticmethod
    def apply_optimizations(args, logger) -> bool:
        """
        应用自适应优化和硬件探测

        Args:
            args: 命令行参数
            logger: 日志记录器

        Returns:
            是否成功应用优化
        """
        # 1. 尝试自适应优化
        if ConfigLoader._apply_adaptive_optimizations(args, logger):
            return True

        # 2. 回退到硬件探测
        ConfigLoader._apply_hardware_probe_fallback(args, logger)
        return True

    @staticmethod
    def _apply_adaptive_optimizations(args, logger) -> bool:
        """应用自适应性能优化"""
        try:
            from src.utils.adaptive_optimizer import apply_adaptive_optimizations

            adaptive_config = apply_adaptive_optimizations()

            # 应用自适应配置（如果用户未手动指定）
            auto_device = (args.device is None) or (str(args.device).lower() == "auto")
            auto_imgsz = (args.imgsz is None) or (str(args.imgsz).lower() == "auto")
            auto_weights = args.human_weights is None

            if auto_device:
                args.device = "cuda" if adaptive_config.get("enable_amp") else "cpu"
            if auto_imgsz:
                args.imgsz = adaptive_config.get("imgsz", 416)
            if auto_weights:
                recommended_model = adaptive_config.get(
                    "model_recommendations", {}
                ).get("human_model", "yolov8s.pt")
                args.human_weights = f"models/yolo/{recommended_model}"

            logger.info(f"✓ 自适应优化已启用: {adaptive_config['description']}")
            logger.info(
                f"推荐配置 - 设备: {args.device}, 图像尺寸: {args.imgsz}, 模型: {args.human_weights}"
            )
            return True

        except Exception as e:
            logger.debug(f"自适应优化跳过: {e}")
            return False

    @staticmethod
    def _apply_hardware_probe_fallback(args, logger):
        """应用硬件探测回退逻辑"""
        auto_device = (args.device is None) or (str(args.device).lower() == "auto")
        auto_imgsz = (args.imgsz is None) or (str(args.imgsz).lower() == "auto")
        auto_weights = args.human_weights is None

        if auto_device or auto_imgsz or auto_weights:
            try:
                from src.utils.hardware_probe import decide_policy

                pol = decide_policy(
                    preferred_profile=args.profile,
                    user_device=args.device,
                    user_imgsz=args.imgsz,
                )
                if auto_device:
                    args.device = pol.get("device")
                if auto_imgsz:
                    args.imgsz = pol.get("imgsz")
                if auto_weights and pol.get("human_weights"):
                    args.human_weights = pol.get("human_weights")

                # 环境变量注入（线程数等）
                for k, v in (pol.get("env") or {}).items():
                    os.environ[str(k)] = str(v)

                logger.info(f"✓ 硬件探测策略已应用: {pol}")
            except Exception as e:
                logger.debug(f"硬件探测跳过: {e}")

    @staticmethod
    def select_device(args, logger) -> str:
        """
        选择计算设备

        Args:
            args: 命令行参数
            logger: 日志记录器

        Returns:
            设备字符串 (cpu/cuda/mps)
        """
        try:
            from config.model_config import ModelConfig

            mc = ModelConfig()
            dev_req = args.device or None
            device = mc.select_device(requested=dev_req)
            logger.info(f"✓ Device selected: {device}")
            return device
        except Exception as e:
            logger.error(f"选择设备失败: {e}")
            return "cpu"
