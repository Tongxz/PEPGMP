# Windows GPU优化配置
# 在main.py开头添加以下代码

import os

import torch


def setup_windows_gpu_optimization():
    """设置Windows GPU优化"""
    print("🚀 启用Windows GPU优化...")

    # 环境变量设置
    os.environ.update(
        {
            "CUDA_LAUNCH_BLOCKING": "0",
            "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512,roundup_power2_divisions:16",
            "CUBLAS_WORKSPACE_CONFIG": ":16:8",
            "CUDA_MODULE_LOADING": "LAZY",
            "TORCH_CUDNN_V8_API_ENABLED": "1",
        }
    )

    if torch.cuda.is_available():
        print(f"✅ CUDA可用: {torch.cuda.device_count()}个GPU")

        # PyTorch优化设置
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        # 显存优化
        torch.cuda.empty_cache()

        # 混合精度设置
        if hasattr(torch.backends.cudnn, "benchmark"):
            torch.backends.cudnn.benchmark = True

        print("✅ GPU优化设置完成")

        # 显示GPU信息
        for i in range(torch.cuda.device_count()):
            gpu_name = torch.cuda.get_device_name(i)
            memory_gb = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"  GPU {i}: {gpu_name} ({memory_gb:.1f}GB)")

    else:
        print("⚠️ CUDA不可用，请检查驱动和CUDA安装")


# 在程序开始时调用
setup_windows_gpu_optimization()
