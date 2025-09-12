#!/usr/bin/env python3
"""
测试修复后的硬件自适应性能
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """测试修复后的性能"""

    # 设置环境变量
    env = os.environ.copy()
    env.update({
        'CUDA_VISIBLE_DEVICES': '0',
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:1024',
        'OMP_NUM_THREADS': '16',
        'MKL_NUM_THREADS': '16',
        'CUDA_LAUNCH_BLOCKING': '0',
    })

    print("🔧 测试修复后的硬件自适应性能")
    print("=" * 60)
    print("📊 预期配置:")
    print("  • GPU: NVIDIA RTX 4090 (24GB)")
    print("  • 模型: yolov8m.pt (中等大小)")
    print("  • 输入尺寸: 640x640")
    print("  • 设备: CUDA")
    print("=" * 60)

    # 测试命令 - 让系统自动选择配置
    cmd = [
        sys.executable, 'main.py',
        '--mode', 'detection',
        '--source', 'tests/fixtures/videos/20250724072708.mp4',
        '--log-interval', '30',
        # 不指定device/imgsz，让系统自动选择
    ]

    try:
        print("\n🚀 启动自动配置检测...")
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n⏹️ 测试已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
