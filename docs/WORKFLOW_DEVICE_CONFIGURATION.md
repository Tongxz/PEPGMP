# 工作流设备配置指南

## 📋 概述

本文档说明如何在工作流中配置训练设备（CPU/CUDA/MPS），以及如何解决设备配置相关的问题。

## 🔧 配置方法

### 方法1: 前端界面配置（推荐）⭐

1. 打开工作流管理界面
2. 选择或创建训练工作流
3. 在训练步骤的"训练参数"中，配置设备：
   - **设备**: 下拉选择（自动选择/CPU/CUDA (GPU)/MPS (Apple Silicon)）
   - **学习率**: 输入学习率（如 0.001）
   - **批次大小**: 输入批次大小（如 32）

**设备选项说明**:
- **自动选择 (auto)**: 自动选择可用设备（优先级：MPS → CUDA → CPU）
- **CPU**: 强制使用CPU
- **CUDA (GPU)**: 使用CUDA GPU（如果可用）
- **MPS (Apple Silicon)**: 使用Apple Silicon的Metal Performance Shaders（如果可用）

### 方法2: 工作流配置（JSON）

在工作流的训练步骤中，可以通过 `training_params` 配置设备：

```json
{
  "steps": [
    {
      "name": "模型训练",
      "type": "model_training",
      "training_params": {
        "device": "cpu",
        "learning_rate": "0.001",
        "batch_size": "32"
      }
    }
  ]
}
```

### 方法3: 环境变量配置

#### 3.1 发网分类模型训练

设置环境变量 `YOLO_TRAIN_DEVICE`：

```bash
# 使用CPU
export YOLO_TRAIN_DEVICE=cpu

# 使用CUDA（如果可用）
export YOLO_TRAIN_DEVICE=cuda

# 使用MPS（Apple Silicon）
export YOLO_TRAIN_DEVICE=mps

# 使用自动选择（默认）
export YOLO_TRAIN_DEVICE=auto
```

#### 3.2 多行为检测模型训练

设置环境变量 `MULTI_BEHAVIOR_DEVICE`：

```bash
# 使用CPU
export MULTI_BEHAVIOR_DEVICE=cpu

# 使用CUDA（如果可用）
export MULTI_BEHAVIOR_DEVICE=cuda

# 使用MPS（Apple Silicon）
export MULTI_BEHAVIOR_DEVICE=mps

# 使用自动选择（默认）
export MULTI_BEHAVIOR_DEVICE=auto
```

## 🚀 默认配置

### 默认设备

- **发网分类模型训练**: `auto`（默认，自动选择设备）
- **多行为检测模型训练**: `auto`（默认，自动选择设备）

### 优先级

工作流配置的优先级：
1. **工作流training_params.device**（最高优先级）
2. **环境变量**（YOLO_TRAIN_DEVICE 或 MULTI_BEHAVIOR_DEVICE）
3. **默认值**（auto）

### 设备选择逻辑

1. **显式指定设备**（`cpu`/`cuda`/`mps`）:
   - 如果设备可用，直接使用
   - 如果设备不可用，自动回退到 CPU

2. **自动选择设备**（`auto`）:
   - 使用 `ModelConfig.select_device()` 方法
   - 优先级：MPS → CUDA → CPU
   - 如果所有设备都不可用，回退到 CPU

## 🐛 常见问题

### 问题1: CUDA设备不可用

**错误信息**:
```
Invalid CUDA 'device=auto' requested. Use 'device=cpu' or pass valid CUDA device(s) if available.
torch.cuda.is_available(): False
```

**解决方案**:
1. 设置环境变量 `YOLO_TRAIN_DEVICE=cpu`
2. 或在工作流中配置 `training_params.device=cpu`
3. 或检查 CUDA 是否正确安装

### 问题2: 设备选择失败

**错误信息**:
```
设备选择失败，使用 CPU
```

**解决方案**:
1. 检查 PyTorch 是否正确安装
2. 检查设备是否可用（`torch.cuda.is_available()`）
3. 显式指定设备（`cpu`/`cuda`/`mps`）

### 问题3: 训练速度慢

**症状**: 使用CPU训练速度很慢

**解决方案**:
1. 如果有GPU，设置 `device=cuda`
2. 如果是Apple Silicon，设置 `device=mps`
3. 减少批量大小（`batch_size`）
4. 减少训练轮数（`epochs`）

## 📝 配置示例

### 示例1: 使用CPU训练

```bash
# 设置环境变量
export YOLO_TRAIN_DEVICE=cpu

# 或在工作流配置中
{
  "training_params": {
    "device": "cpu",
    "epochs": 30,
    "batch_size": 32
  }
}
```

### 示例2: 使用CUDA训练

```bash
# 设置环境变量
export YOLO_TRAIN_DEVICE=cuda

# 或在工作流配置中
{
  "training_params": {
    "device": "cuda",
    "epochs": 50,
    "batch_size": 64
  }
}
```

### 示例3: 使用MPS训练（Apple Silicon）

```bash
# 设置环境变量
export YOLO_TRAIN_DEVICE=mps

# 或在工作流配置中
{
  "training_params": {
    "device": "mps",
    "epochs": 30,
    "batch_size": 32
  }
}
```

## 🔍 验证配置

### 检查设备可用性

```python
import torch

# 检查CUDA是否可用
print(f"CUDA available: {torch.cuda.is_available()}")

# 检查MPS是否可用（Apple Silicon）
if hasattr(torch.backends, "mps"):
    print(f"MPS available: {torch.backends.mps.is_available()}")
```

### 查看训练日志

训练日志会显示使用的设备：

```
设备选择: auto -> cpu
加载 YOLO 模型: yolov8n-cls.pt (epochs=30, imgsz=224, batch=32, device=cpu)
```

## 📚 相关文档

- [工作流引擎文档](./WORKFLOW_ENGINE.md)
- [模型训练配置文档](./MODEL_TRAINING_CONFIG.md)
- [系统架构文档](./SYSTEM_ARCHITECTURE.md)

## 🎯 最佳实践

1. **开发环境**: 使用 `cpu` 进行快速测试
2. **生产环境**: 使用 `cuda` 或 `mps` 进行高效训练
3. **自动选择**: 不推荐使用 `auto`，建议显式指定设备
4. **设备验证**: 在训练前验证设备是否可用
5. **错误处理**: 设备不可用时，自动回退到 CPU

