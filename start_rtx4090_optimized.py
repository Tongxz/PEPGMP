#!/usr/bin/env python3
"""
RTX 4090 极致性能优化启动脚本
针对顶级GPU的专门优化配置
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动RTX 4090优化检测"""

    # RTX 4090专用环境变量优化
    env = os.environ.copy()
    env.update({
        'CUDA_VISIBLE_DEVICES': '0',
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:1024,garbage_collection_threshold:0.8',
        'OMP_NUM_THREADS': '16',
        'MKL_NUM_THREADS': '16',
        'CUDA_LAUNCH_BLOCKING': '0',
        'TORCH_USE_CUDA_DSA': '1',  # 启用CUDA设备端断言
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:1024,garbage_collection_threshold:0.8',
    })

    print("🚀 RTX 4090 极致性能优化模式...")
    print("=" * 60)
    print("📊 GPU: NVIDIA RTX 4090")
    print("🎯 模式: fast (极速)")
    print("📐 输入尺寸: 512x512")
    print("🔄 批处理大小: 16")
    print("⚡ 置信度阈值: 0.4")
    print("🎯 IoU阈值: 0.6")
    print("🔍 最小检测面积: 1000")
    print("🚫 级联检测: 禁用")
    print("⚡ 跳帧: 0")
    print("=" * 60)

    # 构建极致性能启动命令
    cmd = [
        sys.executable, 'main.py',
        '--mode', 'detection',
        '--source', 'tests/fixtures/videos/20250724072708.mp4',
        '--profile', 'fast',
        '--device', 'cuda',
        '--imgsz', '512',
        '--human-weights', 'models/yolo/yolov8s.pt',
        '--log-interval', '60',
        '--osd-regions',
    ]

    try:
        # 启动检测
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n⏹️ 检测已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 检测失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
