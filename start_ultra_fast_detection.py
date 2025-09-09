#!/usr/bin/env python3
"""
极致性能检测启动脚本
针对RTX 4090等高端GPU的极致优化
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动极致性能检测"""
    
    # 设置环境变量优化GPU性能
    env = os.environ.copy()
    env.update({
        'CUDA_VISIBLE_DEVICES': '0',
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:1024',
        'OMP_NUM_THREADS': '16',
        'MKL_NUM_THREADS': '16',
        'CUDA_LAUNCH_BLOCKING': '0',  # 异步执行
    })
    
    # 构建极致性能启动命令
    cmd = [
        sys.executable, 'main.py',
        '--mode', 'detection',
        '--source', 'tests/fixtures/videos/20250724072708.mp4',
        '--profile', 'fast',  # 使用fast模式
        '--device', 'cuda',
        '--imgsz', '512',  # 降低输入尺寸
        '--log-interval', '60',  # 减少日志频率
        '--human-weights', 'models/yolo/yolov8s.pt',  # 使用small版本
    ]
    
    print("⚡ 启动极致性能检测模式...")
    print(f"📊 GPU: RTX 4090")
    print(f"🎯 模式: fast (极速)")
    print(f"📐 输入尺寸: 512x512")
    print(f"🔄 批处理大小: 8")
    print(f"⚡ 帧跳过: 1 (跳帧处理)")
    print(f"🚫 级联检测: 禁用")
    print("=" * 50)
    
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
