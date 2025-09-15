#!/usr/bin/env python3
"""
测试不同硬件环境下的自适应优化效果
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.adaptive_optimizer import AdaptiveOptimizer


def simulate_hardware_environments():
    """模拟不同硬件环境下的优化配置"""

    # 模拟不同硬件环境
    test_environments = [
        {
            "name": "RTX 4090 (旗舰)",
            "env": {
                "has_cuda": True,
                "gpu_name": "NVIDIA GeForce RTX 4090",
                "vram_gb": 24.0,
                "cpu_cores": 32,
            },
        },
        {
            "name": "RTX 3070 (高端)",
            "env": {
                "has_cuda": True,
                "gpu_name": "NVIDIA GeForce RTX 3070",
                "vram_gb": 8.0,
                "cpu_cores": 16,
            },
        },
        {
            "name": "GTX 1660 (中端)",
            "env": {
                "has_cuda": True,
                "gpu_name": "NVIDIA GeForce GTX 1660",
                "vram_gb": 6.0,
                "cpu_cores": 8,
            },
        },
        {
            "name": "GTX 1050 (入门)",
            "env": {
                "has_cuda": True,
                "gpu_name": "NVIDIA GeForce GTX 1050",
                "vram_gb": 2.0,
                "cpu_cores": 4,
            },
        },
        {
            "name": "CPU Only (无GPU)",
            "env": {"has_cuda": False, "gpu_name": "", "vram_gb": 0, "cpu_cores": 8},
        },
    ]

    print("=== 硬件自适应优化测试 ===\n")

    for test_env in test_environments:
        print(f"🖥️  {test_env['name']}")
        print("-" * 50)

        # 创建优化器并模拟环境
        optimizer = AdaptiveOptimizer()
        optimizer.env = test_env["env"]  # 模拟硬件环境

        # 获取优化配置
        tier = optimizer.detect_hardware_tier()
        config = optimizer.get_optimization_config()

        print(f"硬件档位: {tier}")
        print(f"批大小: {config['batch_size']}")
        print(f"输入尺寸: {config['imgsz']}")
        print(f"混合精度: {config['enable_amp']}")
        print(f"TensorRT: {config['enable_tensorrt']}")
        print(f"推荐人体模型: {config['model_recommendations']['human_model']}")
        print(f"推荐姿态模型: {config['model_recommendations']['pose_model']}")
        print(f"原因: {config['model_recommendations']['reason']}")

        # 计算预期性能提升
        performance_prediction = predict_performance(config, test_env["env"])
        print(f"预期FPS: {performance_prediction['expected_fps']}")
        print(f"内存使用: {performance_prediction['memory_usage']}MB")
        print(f"适用场景: {performance_prediction['use_case']}")

        print()


def predict_performance(config, env):
    """预测性能表现"""
    base_fps = 25  # 基准FPS

    # 根据硬件档位调整FPS
    tier_multipliers = {
        "flagship_gpu": 6.0,  # RTX 4090 等
        "high_end_gpu": 3.5,  # RTX 3070 等
        "mid_range_gpu": 2.0,  # GTX 1660 等
        "entry_gpu": 1.2,  # GTX 1050 等
        "cpu_optimized": 0.3,  # CPU only
    }

    tier = config["hardware_tier"]
    expected_fps = base_fps * tier_multipliers.get(tier, 1.0)

    # 根据批大小调整（批处理效率）
    batch_efficiency = 1.0 + (config["batch_size"] - 1) * 0.15
    expected_fps *= batch_efficiency

    # 内存使用估算
    base_memory = 200  # 基础内存使用
    batch_memory = config["batch_size"] * 100
    model_memory = {
        "yolov8n.pt": 50,
        "yolov8s.pt": 100,
        "yolov8m.pt": 200,
        "yolov8l.pt": 400,
    }

    human_model = config["model_recommendations"]["human_model"]
    memory_usage = base_memory + batch_memory + model_memory.get(human_model, 100)

    # 使用场景推荐
    if expected_fps >= 60:
        use_case = "实时高精度检测、4K视频处理"
    elif expected_fps >= 30:
        use_case = "实时检测、1080p视频处理"
    elif expected_fps >= 15:
        use_case = "准实时检测、视频文件处理"
    else:
        use_case = "离线批处理、单张图片检测"

    return {
        "expected_fps": round(expected_fps, 1),
        "memory_usage": memory_usage,
        "use_case": use_case,
    }


def test_performance_scaling():
    """测试性能扩展性"""
    print("=== 性能扩展性测试 ===\n")

    # 模拟不同批大小的影响
    batch_sizes = [1, 2, 4, 8, 16, 32]

    print("RTX 4090 - 不同批大小性能预测:")
    print("批大小\t预期FPS\t加速比\t内存使用")
    print("-" * 40)

    for batch_size in batch_sizes:
        # 模拟配置
        config = {
            "hardware_tier": "flagship_gpu",
            "batch_size": batch_size,
            "model_recommendations": {"human_model": "yolov8s.pt"},
        }

        env = {"has_cuda": True, "vram_gb": 24.0}
        perf = predict_performance(config, env)

        speedup = perf["expected_fps"] / 25  # 相对基准的加速比

        print(
            f"{batch_size}\t{perf['expected_fps']}\t{speedup:.1f}x\t{perf['memory_usage']}MB"
        )

        # 检查内存限制
        if perf["memory_usage"] > 20000:  # 超过20GB显存
            print(f"  ⚠️  显存不足风险")


if __name__ == "__main__":
    simulate_hardware_environments()
    print("\n" + "=" * 60 + "\n")
    test_performance_scaling()
