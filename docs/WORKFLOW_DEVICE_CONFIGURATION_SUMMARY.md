# 工作流设备配置问题修复总结

## 🔧 问题描述

工作流中模型训练时，当 `device=auto` 且 CUDA 不可用时，会出现以下错误：

```
Invalid CUDA 'device=auto' requested. Use 'device=cpu' or pass valid CUDA device(s) if available.
torch.cuda.is_available(): False
```

## ✅ 解决方案

### 1. 添加前端设备配置界面

- 在工作流管理界面的训练步骤中，添加了**设备选择下拉框**
- 支持选择：自动选择/CPU/CUDA (GPU)/MPS (Apple Silicon)
- 设备参数会保存到工作流的 `training_params.device` 中

### 2. 保持默认设备配置为auto

- **发网分类模型训练**: 默认设备保持为 `auto`（自动选择）
- **多行为检测模型训练**: 默认设备保持为 `auto`（自动选择）
- 用户可以通过前端界面或工作流配置覆盖默认值

### 3. 添加智能设备选择逻辑

在 `ModelTrainingService` 和 `MultiBehaviorTrainingService` 中添加了 `_select_device()` 方法：

- **显式指定设备**（`cpu`/`cuda`/`mps`）: 如果设备可用，直接使用；如果不可用，自动回退到 CPU
- **自动选择设备**（`auto`）: 使用 `ModelConfig.select_device()` 方法，优先级：MPS → CUDA → CPU

### 4. 修改的文件

1. `frontend/src/components/MLOps/WorkflowManager.vue`: 
   - 添加设备选择下拉框
   - 更新 `training_params` 接口，添加 `device` 字段
   - 更新 `normalizeStepsForSubmit` 函数，确保 `device` 参数被正确传递
   - 更新 `prepareStepForForm` 函数，确保 `device` 参数被正确读取

2. `src/application/model_training_service.py`: 添加 `_select_device()` 方法，支持智能设备选择

3. `src/application/multi_behavior_training_service.py`: 添加 `_select_device()` 方法，支持智能设备选择

4. `src/workflow/workflow_engine.py`: 正确传递 `training_params.device` 到训练服务

## 🚀 使用方法

### 方法1: 前端界面配置（推荐）⭐

1. 打开工作流管理界面
2. 选择或创建训练工作流
3. 在训练步骤的"训练参数"中，选择设备：
   - **设备**: 下拉选择（自动选择/CPU/CUDA (GPU)/MPS (Apple Silicon)）

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

## 🔍 验证

测试设备选择逻辑：

```python
from src.application.model_training_service import ModelTrainingService
from src.config.model_training_config import get_model_training_config

config = get_model_training_config()
service = ModelTrainingService(config)

# 测试设备选择
device1 = service._select_device('cpu')  # 返回: cpu
device2 = service._select_device('auto')  # 返回: mps/cuda/cpu（根据可用性）
device3 = service._select_device('cuda')  # 如果CUDA不可用，返回: cpu
```

## 📝 相关文档

- [工作流设备配置指南](./WORKFLOW_DEVICE_CONFIGURATION.md)
- [工作流引擎文档](./WORKFLOW_ENGINE.md)
- [模型训练配置文档](./MODEL_TRAINING_CONFIG.md)

## 🎯 最佳实践

1. **开发环境**: 使用 `cpu` 进行快速测试
2. **生产环境**: 使用 `cuda` 或 `mps` 进行高效训练
3. **自动选择**: 不推荐使用 `auto`，建议显式指定设备
4. **设备验证**: 在训练前验证设备是否可用
5. **错误处理**: 设备不可用时，自动回退到 CPU

## ✅ 修复结果

- ✅ 前端界面已添加设备选择下拉框
- ✅ 设备选择逻辑已添加（智能选择设备）
- ✅ 设备不可用时自动回退到 CPU
- ✅ 支持前端界面、工作流配置和环境变量三种方式
- ✅ 工作流配置的优先级最高
- ✅ 文档已更新

现在用户可以在工作流管理界面中直接选择训练设备，无需修改代码或环境变量。

