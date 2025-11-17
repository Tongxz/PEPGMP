#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CUDA 诊断脚本
检查 CUDA 不可用的原因
"""

import sys
import os

def check_pytorch():
    """检查 PyTorch 安装"""
    print("=" * 60)
    print("1. 检查 PyTorch 安装")
    print("=" * 60)
    try:
        import torch
        print(f"[OK] PyTorch 已安装")
        print(f"   版本: {torch.__version__}")
        return torch
    except ImportError:
        print("[ERROR] PyTorch 未安装")
        print("   请运行: pip install torch torchvision")
        return None

def check_cuda_availability(torch):
    """检查 CUDA 可用性"""
    print("\n" + "=" * 60)
    print("2. 检查 CUDA 可用性")
    print("=" * 60)
    if torch is None:
        print("❌ 无法检查（PyTorch 未安装）")
        return False
    
    try:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print("[OK] CUDA 可用")
            print(f"   CUDA 版本: {torch.version.cuda}")
            print(f"   cuDNN 版本: {torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else 'N/A'}")
            print(f"   GPU 数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
                props = torch.cuda.get_device_properties(i)
                print(f"      显存: {props.total_memory / 1024**3:.2f} GB")
            return True
        else:
            print("[ERROR] CUDA 不可用")
            return False
    except Exception as e:
        print(f"[ERROR] 检查 CUDA 时出错: {e}")
        return False

def check_nvidia_driver():
    """检查 NVIDIA 驱动"""
    print("\n" + "=" * 60)
    print("3. 检查 NVIDIA 驱动")
    print("=" * 60)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("[OK] NVIDIA 驱动已安装")
            # 提取驱动版本
            lines = result.stdout.split('\n')
            for line in lines:
                if "Driver Version" in line:
                    print(f"   {line.strip()}")
                if "CUDA Version" in line:
                    print(f"   {line.strip()}")
            return True
        else:
            print("[ERROR] nvidia-smi 命令执行失败")
            return False
    except FileNotFoundError:
        print("[ERROR] nvidia-smi 未找到")
        print("   可能原因:")
        print("   1. NVIDIA 驱动未安装")
        print("   2. NVIDIA 驱动未正确安装")
        print("   3. 系统没有 NVIDIA GPU")
        return False
    except subprocess.TimeoutExpired:
        print("[ERROR] nvidia-smi 命令超时")
        return False
    except Exception as e:
        print(f"[ERROR] 检查驱动时出错: {e}")
        return False

def check_pytorch_cuda_build(torch):
    """检查 PyTorch CUDA 构建"""
    print("\n" + "=" * 60)
    print("4. 检查 PyTorch CUDA 构建")
    print("=" * 60)
    if torch is None:
        print("❌ 无法检查（PyTorch 未安装）")
        return False
    
    try:
        # 检查 PyTorch 是否支持 CUDA
        has_cuda = hasattr(torch.version, 'cuda') and torch.version.cuda is not None
        if has_cuda:
            print(f"[OK] PyTorch 支持 CUDA")
            print(f"   编译时 CUDA 版本: {torch.version.cuda}")
        else:
            print("[ERROR] PyTorch 不支持 CUDA（可能是 CPU 版本）")
            print("   解决方案:")
            print("   1. 卸载当前 PyTorch: pip uninstall torch torchvision")
            print("   2. 安装 CUDA 版本 PyTorch:")
            print("      pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
            return False
        
        # 检查 cuDNN
        if torch.backends.cudnn.is_available():
            print(f"[OK] cuDNN 可用")
            print(f"   版本: {torch.backends.cudnn.version()}")
        else:
            print("[WARNING] cuDNN 不可用（可能影响性能）")
        
        return has_cuda
    except Exception as e:
        print(f"[ERROR] 检查构建信息时出错: {e}")
        return False

def check_environment_variables():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("5. 检查环境变量")
    print("=" * 60)
    cuda_path = os.environ.get("CUDA_PATH")
    cuda_home = os.environ.get("CUDA_HOME")
    path = os.environ.get("PATH", "")
    
    if cuda_path:
        print(f"[OK] CUDA_PATH: {cuda_path}")
    else:
        print("[WARNING] CUDA_PATH 未设置")
    
    if cuda_home:
        print(f"[OK] CUDA_HOME: {cuda_home}")
    else:
        print("[WARNING] CUDA_HOME 未设置")
    
    if "cuda" in path.lower() or "nvidia" in path.lower():
        print("[OK] PATH 中包含 CUDA/NVIDIA 路径")
    else:
        print("[WARNING] PATH 中未找到 CUDA/NVIDIA 路径")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("CUDA 诊断工具")
    print("=" * 60 + "\n")
    
    # 检查 PyTorch
    torch = check_pytorch()
    
    # 检查 NVIDIA 驱动
    driver_ok = check_nvidia_driver()
    
    # 检查 PyTorch CUDA 构建
    pytorch_cuda_ok = check_pytorch_cuda_build(torch)
    
    # 检查 CUDA 可用性
    cuda_available = check_cuda_availability(torch)
    
    # 检查环境变量
    check_environment_variables()
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    if cuda_available:
        print("[OK] CUDA 可用，无需修复")
    else:
        print("[ERROR] CUDA 不可用")
        print("\n可能的原因和解决方案:")
        print("\n1. NVIDIA 驱动未安装或版本过旧")
        if not driver_ok:
            print("   → 请安装或更新 NVIDIA 驱动")
            print("   → 下载地址: https://www.nvidia.com/Download/index.aspx")
        
        print("\n2. PyTorch 是 CPU 版本")
        if not pytorch_cuda_ok:
            print("   → 请安装 CUDA 版本的 PyTorch")
            print("   → 运行: pip uninstall torch torchvision")
            print("   → 然后: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        
        print("\n3. CUDA 工具包未安装")
        print("   → 请安装 CUDA Toolkit")
        print("   → 下载地址: https://developer.nvidia.com/cuda-downloads")
        
        print("\n4. 系统没有 NVIDIA GPU")
        print("   → 如果确实没有 NVIDIA GPU，这是正常的")
        print("   → 系统将使用 CPU 进行训练（速度较慢）")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

