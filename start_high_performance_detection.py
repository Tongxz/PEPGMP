#!/usr/bin/env python3
"""
高性能检测启动脚本
针对RTX 4090等高端GPU优化
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动高性能检测"""
    
    # 设置环境变量优化GPU性能
    env = os.environ.copy()
    env.update({
        'CUDA_VISIBLE_DEVICES': '0',  # 使用第一个GPU
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:512',  # 优化内存分配
        'OMP_NUM_THREADS': '8',  # 设置OpenMP线程数
        'MKL_NUM_THREADS': '8',  # 设置MKL线程数
    })
    
    # 构建高性能启动命令
    cmd = [
        sys.executable, 'main.py',
        '--mode', 'detection',
        '--source', 'tests/fixtures/videos/20250724072708.mp4',
        '--profile', 'accurate',  # 使用accurate模式
        '--device', 'cuda',  # 强制使用CUDA
        '--imgsz', '640',  # 设置输入尺寸
        '--log-interval', '30',  # 减少日志频率
        '--osd-regions',  # 启用区域显示
    ]
    
    print("🚀 启动高性能检测模式...")
    print(f"📊 GPU: RTX 4090")
    print(f"🎯 模式: accurate (高精度)")
    print(f"📐 输入尺寸: 640x640")
    print(f"🔄 批处理大小: 8")
    print(f"⚡ 帧跳过: 0 (处理所有帧)")
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
