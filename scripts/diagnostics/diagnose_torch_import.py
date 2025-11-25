#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断 PyTorch 导入问题
检查代码中导入的 PyTorch 版本和系统环境中的版本
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

print("=" * 60)
print("PyTorch 导入诊断")
print("=" * 60)

# 1. 直接导入 torch
print("\n1. 直接导入 torch:")
try:
    import torch
    print(f"  PyTorch版本: {torch.__version__}")
    print(f"  torch模块路径: {torch.__file__}")
    print(f"  CUDA可用: {torch.cuda.is_available()}")
    if hasattr(torch.version, 'cuda') and torch.version.cuda:
        print(f"  CUDA编译版本: {torch.version.cuda}")
    else:
        print(f"  CUDA编译版本: N/A (CPU版本)")
    direct_torch = torch
except Exception as e:
    print(f"  错误: {e}")
    direct_torch = None

# 2. 通过 ModelConfig 导入
print("\n2. 通过 ModelConfig 导入:")
try:
    from src.config.model_config import ModelConfig
    mc = ModelConfig()
    
    # 在 select_device 中导入的 torch
    import torch as config_torch
    print(f"  ModelConfig中导入的PyTorch版本: {config_torch.__version__}")
    print(f"  torch模块路径: {config_torch.__file__}")
    print(f"  CUDA可用: {config_torch.cuda.is_available()}")
    if hasattr(config_torch.version, 'cuda') and config_torch.version.cuda:
        print(f"  CUDA编译版本: {config_torch.version.cuda}")
    else:
        print(f"  CUDA编译版本: N/A (CPU版本)")
    
    # 检查是否是同一个模块
    if direct_torch is not None:
        if direct_torch is config_torch:
            print("  ✓ 是同一个 torch 模块")
        else:
            print("  ✗ 是不同的 torch 模块！")
            print(f"    直接导入: {direct_torch.__file__}")
            print(f"    ModelConfig导入: {config_torch.__file__}")
    
    # 测试设备选择
    print("\n3. 测试设备选择:")
    device = mc.select_device('auto')
    print(f"  选择的设备: {device}")
    
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 3. 检查 ultralytics 使用的 torch
print("\n4. 检查 ultralytics 使用的 torch:")
try:
    from ultralytics import YOLO
    import torch as ultralytics_torch
    print(f"  Ultralytics使用的PyTorch版本: {ultralytics_torch.__version__}")
    print(f"  torch模块路径: {ultralytics_torch.__file__}")
    print(f"  CUDA可用: {ultralytics_torch.cuda.is_available()}")
    if hasattr(ultralytics_torch.version, 'cuda') and ultralytics_torch.version.cuda:
        print(f"  CUDA编译版本: {ultralytics_torch.version.cuda}")
    else:
        print(f"  CUDA编译版本: N/A (CPU版本)")
    
    # 检查是否是同一个模块
    if direct_torch is not None:
        if direct_torch is ultralytics_torch:
            print("  ✓ 是同一个 torch 模块")
        else:
            print("  ✗ 是不同的 torch 模块！")
            print(f"    直接导入: {direct_torch.__file__}")
            print(f"    Ultralytics导入: {ultralytics_torch.__file__}")
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查所有已安装的 torch
print("\n5. 检查所有已安装的 torch:")
try:
    import subprocess
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                          capture_output=True, text=True, encoding='utf-8')
    torch_lines = [line for line in result.stdout.split('\n') if 'torch' in line.lower()]
    print("  已安装的 torch 相关包:")
    for line in torch_lines:
        print(f"    {line}")
except Exception as e:
    print(f"  错误: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

