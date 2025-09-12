#!/usr/bin/env python3
"""
超极致性能优化启动脚本
牺牲少量精度换取最大速度
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动超极致性能检测"""

    # 超极致GPU优化配置
    env = os.environ.copy()
    env.update({
        'CUDA_VISIBLE_DEVICES': '0',
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512,garbage_collection_threshold:0.6',
        'OMP_NUM_THREADS': '8',  # 减少线程数避免竞争
        'MKL_NUM_THREADS': '8',
        'CUDA_LAUNCH_BLOCKING': '0',
        'TORCH_USE_CUDA_DSA': '1',
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512,garbage_collection_threshold:0.6',
        'CUDA_CACHE_DISABLE': '0',  # 启用CUDA缓存
    })

    print("⚡ 超极致性能优化模式 (最大速度)...")
    print("=" * 60)
    print("📊 GPU: NVIDIA RTX 4090")
    print("🎯 模式: ultra_fast (超极速)")
    print("📐 输入尺寸: 416x416")
    print("🔄 批处理大小: 32")
    print("⚡ 置信度阈值: 0.5")
    print("🎯 IoU阈值: 0.7")
    print("🔍 最小检测面积: 1500")
    print("🚫 可视化: 最小化")
    print("⚡ 跳帧: 1 (每2帧处理1帧)")
    print("=" * 60)

    # 构建超极致性能启动命令
    cmd = [
        sys.executable, 'main.py',
        '--mode', 'detection',
        '--source', 'tests/fixtures/videos/20250724072708.mp4',
        '--profile', 'fast',
        '--device', 'cuda',
        '--imgsz', '416',
        '--human-weights', 'models/yolo/yolov8n.pt',  # 使用最小的nano模型
        '--log-interval', '120',  # 减少日志频率
        '--frame-skip', '1',  # 跳帧处理
        # '--osd-minimal',  # 最小化可视化 (如果支持)
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
