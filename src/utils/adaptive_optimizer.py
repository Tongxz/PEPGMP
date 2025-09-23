#!/usr/bin/env python3
"""
自适应优化器 - 根据硬件环境自动调整性能优化参数
支持从高端RTX 4090到低端CPU的自适应优化
"""

import logging
import os
import platform
from dataclasses import dataclass
from typing import Any, Dict, Optional

import torch

from src.utils.hardware_probe import detect_environment

logger = logging.getLogger(__name__)


@dataclass
class OptimizationProfile:
    """优化配置档案"""

    batch_size: int
    imgsz: int
    enable_amp: bool  # 混合精度
    enable_tensorrt: bool  # TensorRT优化
    num_workers: int  # 数据加载工作线程
    prefetch_factor: int  # 预取因子
    pin_memory: bool  # 锁页内存
    compile_model: bool  # 模型编译
    inference_threads: int  # 推理线程数
    description: str


class AdaptiveOptimizer:
    """自适应性能优化器"""

    def __init__(self):
        self.env = detect_environment()
        self.platform = platform.system()
        self.optimization_profiles = self._init_profiles()

    def _init_profiles(self) -> Dict[str, OptimizationProfile]:
        """初始化不同硬件档位的优化配置"""
        return {
            # 高端GPU: RTX 4090, RTX 4080, RTX 3090等
            "flagship_gpu": OptimizationProfile(
                batch_size=16,
                imgsz=640,
                enable_amp=True,
                enable_tensorrt=True,
                num_workers=8,
                prefetch_factor=4,
                pin_memory=True,
                compile_model=True,
                inference_threads=4,
                description="旗舰级GPU优化 (RTX 4090/4080/3090等)",
            ),
            # 中高端GPU: RTX 3070, RTX 4060Ti等
            "high_end_gpu": OptimizationProfile(
                batch_size=8,
                imgsz=512,
                enable_amp=True,
                enable_tensorrt=True,
                num_workers=6,
                prefetch_factor=3,
                pin_memory=True,
                compile_model=True,
                inference_threads=2,
                description="高端GPU优化 (RTX 3070/4060Ti等)",
            ),
            # 中端GPU: GTX 1660, RTX 2060等
            "mid_range_gpu": OptimizationProfile(
                batch_size=4,
                imgsz=416,
                enable_amp=True,
                enable_tensorrt=False,  # 老架构可能不支持
                num_workers=4,
                prefetch_factor=2,
                pin_memory=True,
                compile_model=False,
                inference_threads=1,
                description="中端GPU优化 (GTX 1660/RTX 2060等)",
            ),
            # 低端GPU: GTX 1050, 集成显卡等
            "entry_gpu": OptimizationProfile(
                batch_size=2,
                imgsz=320,
                enable_amp=False,  # 可能不支持
                enable_tensorrt=False,
                num_workers=2,
                prefetch_factor=1,
                pin_memory=False,
                compile_model=False,
                inference_threads=1,
                description="入门级GPU优化 (GTX 1050/集成显卡等)",
            ),
            # CPU模式
            "cpu_optimized": OptimizationProfile(
                batch_size=1,
                imgsz=320,
                enable_amp=False,
                enable_tensorrt=False,
                num_workers=min(4, os.cpu_count()),
                prefetch_factor=1,
                pin_memory=False,
                compile_model=False,
                inference_threads=min(4, os.cpu_count()),
                description="CPU优化模式",
            ),
        }

    def detect_hardware_tier(self) -> str:
        """检测硬件档位"""
        if not self.env.get("has_cuda", False):
            return "cpu_optimized"

        gpu_name = self.env.get("gpu_name", "").lower()
        vram_gb = self.env.get("vram_gb", 0)

        # RTX 40系列和高端30系列
        if (
            any(
                x in gpu_name
                for x in ["rtx 4090", "rtx 4080", "rtx 3090", "rtx 3080 ti"]
            )
            or vram_gb >= 20
        ):
            return "flagship_gpu"

        # 中高端GPU
        elif (
            any(
                x in gpu_name
                for x in ["rtx 4070", "rtx 4060 ti", "rtx 3070", "rtx 3060 ti"]
            )
            or vram_gb >= 8
        ):
            return "high_end_gpu"

        # 中端GPU
        elif (
            any(x in gpu_name for x in ["rtx 3060", "rtx 2060", "gtx 1660"])
            or vram_gb >= 4
        ):
            return "mid_range_gpu"

        # 低端GPU
        else:
            return "entry_gpu"

    def get_optimization_config(
        self, user_profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取优化配置"""
        # 用户可以手动指定配置档位
        if user_profile and user_profile in self.optimization_profiles:
            tier = user_profile
        else:
            tier = self.detect_hardware_tier()

        profile = self.optimization_profiles[tier]

        # 构建配置字典
        config = {
            "hardware_tier": tier,
            "batch_size": profile.batch_size,
            "imgsz": profile.imgsz,
            "enable_amp": profile.enable_amp,
            "enable_tensorrt": profile.enable_tensorrt,
            "num_workers": profile.num_workers,
            "prefetch_factor": profile.prefetch_factor,
            "pin_memory": profile.pin_memory,
            "compile_model": profile.compile_model,
            "inference_threads": profile.inference_threads,
            "description": profile.description,
            # 环境变量设置
            "env_vars": self._get_env_vars(profile),
            # 模型选择建议
            "model_recommendations": self._get_model_recommendations(tier),
        }

        logger.info(f"自适应优化配置: {profile.description}")
        logger.info(f"批大小: {profile.batch_size}, 输入尺寸: {profile.imgsz}")

        return config

    def _get_env_vars(self, profile: OptimizationProfile) -> Dict[str, str]:
        """获取推荐的环境变量设置"""
        env_vars = {}

        if profile.enable_amp:
            env_vars["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"

        # CPU线程数设置
        cpu_threads = min(profile.inference_threads * 2, os.cpu_count())
        env_vars["OMP_NUM_THREADS"] = str(cpu_threads)
        env_vars["MKL_NUM_THREADS"] = str(cpu_threads)

        # CUDA优化设置
        if self.env.get("has_cuda", False):
            env_vars["CUDNN_BENCHMARK"] = "1"
            env_vars["CUDA_LAUNCH_BLOCKING"] = "0"

        return env_vars

    def _get_model_recommendations(self, tier: str) -> Dict[str, str]:
        """获取模型选择建议"""
        recommendations = {
            "flagship_gpu": {
                "human_model": "yolov8l.pt",  # 大模型
                "pose_model": "yolov8m-pose.pt",
                "reason": "高端硬件可以使用大模型获得最佳精度",
            },
            "high_end_gpu": {
                "human_model": "yolov8m.pt",
                "pose_model": "yolov8s-pose.pt",
                "reason": "平衡精度与性能",
            },
            "mid_range_gpu": {
                "human_model": "yolov8s.pt",
                "pose_model": "yolov8n-pose.pt",
                "reason": "优先保证流畅性",
            },
            "entry_gpu": {
                "human_model": "yolov8n.pt",
                "pose_model": "yolov8n-pose.pt",
                "reason": "最轻量级模型",
            },
            "cpu_optimized": {
                "human_model": "yolov8n.pt",
                "pose_model": "mediapipe",  # CPU模式使用MediaPipe
                "reason": "CPU优化配置",
            },
        }

        return recommendations.get(tier, recommendations["cpu_optimized"])

    def apply_optimizations(self, config: Dict[str, Any]) -> None:
        """应用优化设置"""
        # 设置环境变量
        for key, value in config["env_vars"].items():
            os.environ[key] = value
            logger.debug(f"设置环境变量: {key}={value}")

        # PyTorch优化设置
        if config["enable_amp"] and torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True

        # CPU线程设置
        torch.set_num_threads(config["inference_threads"])

        # 内存优化
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("优化设置已应用")

    def benchmark_profile(self, profile_name: str) -> Dict[str, float]:
        """对指定配置档位进行基准测试"""
        # 这里可以实现具体的基准测试逻辑
        logger.info(f"开始基准测试档位: {profile_name}")
        # 返回测试结果
        return {"fps": 0.0, "latency": 0.0, "gpu_usage": 0.0}


# 便捷函数
def get_adaptive_config(user_profile: Optional[str] = None) -> Dict[str, Any]:
    """获取自适应优化配置的便捷函数"""
    optimizer = AdaptiveOptimizer()
    return optimizer.get_optimization_config(user_profile)


def apply_adaptive_optimizations(user_profile: Optional[str] = None) -> Dict[str, Any]:
    """应用自适应优化的便捷函数"""
    optimizer = AdaptiveOptimizer()
    config = optimizer.get_optimization_config(user_profile)
    optimizer.apply_optimizations(config)
    return config


if __name__ == "__main__":
    # 测试自适应优化器
    optimizer = AdaptiveOptimizer()

    print("=== 硬件环境检测 ===")
    for key, value in optimizer.env.items():
        print(f"{key}: {value}")

    print(f"\n=== 检测到的硬件档位 ===")
    tier = optimizer.detect_hardware_tier()
    print(f"硬件档位: {tier}")

    print(f"\n=== 优化配置 ===")
    config = optimizer.get_optimization_config()
    for key, value in config.items():
        if key != "env_vars":
            print(f"{key}: {value}")
