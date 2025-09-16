#!/usr/bin/env python3
"""
自动生成的GPU性能优化脚本
Generated GPU Performance Optimization Script
"""

import os
import torch

def setup_gpu_optimization():
    """设置GPU性能优化"""
    print("🚀 启用GPU性能优化...")

    # PyTorch后端优化
    if torch.cuda.is_available():
        print("✅ CUDA可用，启用GPU优化")
        os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False

        # 清理GPU缓存
        torch.cuda.empty_cache()

        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f}GB")

    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("✅ MPS可用，启用macOS GPU优化")

    else:
        print("⚠️  GPU不可用，启用CPU优化")
        torch.set_num_threads(32)
        os.environ['OMP_NUM_THREADS'] = '32'
        os.environ['MKL_NUM_THREADS'] = '32'

def get_optimized_config():
    """获取优化配置"""
    return {
        "device_strategy": "auto",
        "mixed_precision": True,
        "compile_model": True,
        "batch_size": 16,
        "num_workers": 8,
        "pin_memory": True,
        "non_blocking": True,
        "optimization_level": "O2",
        "device": "cuda",
        "cudnn_benchmark": True
}

if __name__ == "__main__":
    setup_gpu_optimization()
    config = get_optimized_config()
    print("\n📊 优化配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
