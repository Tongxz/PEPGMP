# 工作流继续训练指南

## 概述

工作流支持基于之前训练的结果继续训练，这对于增量训练、微调模型或提高模型性能非常有用。

## 方法一：自动继续训练（推荐）

如果工作流中有多个训练步骤，后续的训练步骤会自动使用上一次训练的模型作为起点。

**示例工作流配置：**

```json
{
  "name": "增量训练工作流",
  "steps": [
    {
      "name": "数据预处理",
      "type": "multi_behavior_training",
      "config": {
        "dataset_dir": "data/datasets/hairnet.v15i.yolov8",
        "data_config": "data/datasets/hairnet.v15i.yolov8/data.yaml",
        "training_params": {
          "model": "yolov8m.pt",
          "epochs": 50,
          "batch_size": 16
        }
      }
    },
    {
      "name": "继续训练",
      "type": "multi_behavior_training",
      "config": {
        "dataset_dir": "data/datasets/hairnet.v15i.yolov8",
        "data_config": "data/datasets/hairnet.v15i.yolov8/data.yaml",
        "training_params": {
          "epochs": 30,  // 继续训练30轮
          "batch_size": 16,
          "lr0": 0.001   // 继续训练时使用较小的学习率（可选）
        }
        // 注意：不需要指定 resume_from，系统会自动使用上一步的模型
      }
    }
  ]
}
```

## 方法二：手动指定模型路径

如果需要在不同的工作流运行之间继续训练，可以手动指定之前训练的模型路径。

**在训练参数中指定 `resume_from`：**

```json
{
  "name": "继续训练",
  "type": "multi_behavior_training",
  "config": {
    "dataset_dir": "data/datasets/hairnet.v15i.yolov8",
    "data_config": "data/datasets/hairnet.v15i.yolov8/data.yaml",
    "training_params": {
      "resume_from": "models/multi_behavior_20250113_120000.pt",
      "epochs": 30,
      "batch_size": 16,
      "lr0": 0.001
    }
  }
}
```

**或者使用 `from_model` 参数（与 `resume_from` 等效）：**

```json
{
  "training_params": {
    "from_model": "models/multi_behavior_20250113_120000.pt",
    "epochs": 30
  }
}
```

## 方法三：从工作流运行结果中获取模型路径

1. 查看上一次工作流运行的详情
2. 在运行详情中找到训练步骤的输出
3. 复制 `model_path` 字段的值
4. 在下次训练时使用该路径作为 `resume_from`

## 继续训练的最佳实践

### 1. 调整学习率

继续训练时，建议使用较小的学习率，避免破坏已学习的特征：

```json
{
  "training_params": {
    "resume_from": "models/previous_model.pt",
    "lr0": 0.001,  // 初始学习率（默认继续训练时为 0.001）
    "lrf": 0.01    // 最终学习率（默认继续训练时为 0.01）
  }
}
```

### 2. 调整训练轮数

继续训练时，通常不需要训练太多轮：

```json
{
  "training_params": {
    "resume_from": "models/previous_model.pt",
    "epochs": 20  // 继续训练20-30轮通常足够
  }
}
```

### 3. 使用相同的数据集配置

继续训练时，建议使用相同的数据集和配置，以确保模型的一致性。

### 4. 监控训练指标

继续训练时，注意观察以下指标：
- **mAP50**: 平均精度（IoU=0.5）
- **mAP50-95**: 平均精度（IoU=0.5-0.95）
- **训练损失**: 应该继续下降
- **验证损失**: 应该继续下降或保持稳定

如果指标没有改善，可能需要：
- 进一步降低学习率
- 增加训练轮数
- 检查数据集质量
- 考虑使用不同的数据增强策略

## 常见问题

### Q: 如何找到之前训练的模型文件？

A: 模型文件通常保存在以下位置：
- `models/multi_behavior_*.pt` - 最终保存的模型
- `models/runs/multi_behavior_*/weights/best.pt` - 训练过程中的最佳模型
- `models/runs/multi_behavior_*/weights/last.pt` - 最后一轮的模型

### Q: 继续训练和从头训练有什么区别？

A:
- **从头训练**: 使用预训练模型（如 `yolov8m.pt`）作为起点
- **继续训练**: 使用之前训练的模型作为起点，保留已学习的特征

继续训练通常：
- 收敛更快
- 需要更少的数据
- 适合微调和增量学习

### Q: 可以继续训练多少次？

A: 理论上可以无限次继续训练，但需要注意：
- 每次继续训练都会在原有基础上学习
- 如果学习率设置不当，可能会破坏已学习的特征
- 建议每次继续训练后评估模型性能

### Q: 继续训练时可以使用不同的数据集吗？

A: 可以，但需要注意：
- 数据集格式应该相同（相同的类别和标注格式）
- 如果类别不同，需要重新训练
- 如果只是增加了数据，继续训练是很好的选择

## 示例：完整的工作流配置

```json
{
  "name": "发网检测增量训练",
  "type": "training",
  "status": "active",
  "trigger": "manual",
  "description": "基于之前训练结果继续训练，提高模型性能",
  "steps": [
    {
      "name": "初始训练",
      "type": "multi_behavior_training",
      "description": "使用预训练模型进行初始训练",
      "config": {
        "dataset_dir": "data/datasets/hairnet.v15i.yolov8",
        "data_config": "data/datasets/hairnet.v15i.yolov8/data.yaml",
        "training_params": {
          "model": "yolov8m.pt",
          "epochs": 50,
          "batch_size": 16,
          "image_size": 640,
          "device": "auto"
        }
      }
    },
    {
      "name": "继续训练（微调）",
      "type": "multi_behavior_training",
      "description": "基于初始训练结果继续训练，使用更小的学习率",
      "config": {
        "dataset_dir": "data/datasets/hairnet.v15i.yolov8",
        "data_config": "data/datasets/hairnet.v15i.yolov8/data.yaml",
        "training_params": {
          "epochs": 30,
          "batch_size": 16,
          "image_size": 640,
          "device": "auto",
          "lr0": 0.001,
          "lrf": 0.01
        }
      }
    }
  ]
}
```

## 参考

- [Ultralytics YOLO 文档](https://docs.ultralytics.com/)
- [迁移学习最佳实践](https://pytorch.org/tutorials/beginner/transfer_learning_tutorial.html)

