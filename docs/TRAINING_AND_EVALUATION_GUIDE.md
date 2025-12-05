# 模型训练与评估指南

## 📋 目录

1. [发网检测模型训练](#发网检测模型训练)
2. [手部检测模型训练](#手部检测模型训练)
3. [评估训练程度](#评估训练程度)
4. [加强训练的方法](#加强训练的方法)
5. [评估指标详解](#评估指标详解)

---

## 🎯 发网检测模型训练

### 1. 训练脚本使用

**脚本位置**: `scripts/training/train_hairnet_model.py`

**基本用法**:
```bash
python scripts/training/train_hairnet_model.py \
    --data datasets/hairnet/data.yaml \
    --epochs 150 \
    --batch-size 16 \
    --img-size 640 \
    --pretrained \
    --device cuda:0
```

**参数说明**:
- `--data`: 数据集配置文件路径（YAML格式，包含train/val路径和类别信息）
- `--epochs`: 训练轮数（建议100-200）
- `--batch-size`: 批次大小（根据GPU内存调整，建议8-32）
- `--img-size`: 图像尺寸（建议640，与检测时保持一致）
- `--weights`: 预训练权重路径（默认使用yolov8n.pt）
- `--pretrained`: 使用预训练权重（推荐）
- `--resume`: 恢复训练（从checkpoint继续）
- `--device`: 训练设备（cuda:0, cuda:1, cpu）

### 2. 数据集准备

**数据集结构**:
```
datasets/hairnet/
├── data.yaml          # 数据集配置文件
├── train/
│   ├── images/        # 训练图像
│   └── labels/        # YOLO格式标注文件
└── val/
    ├── images/        # 验证图像
    └── labels/        # YOLO格式标注文件
```

**data.yaml 格式**:
```yaml
path: datasets/hairnet
train: train/images
val: val/images
nc: 3  # 类别数
names:
  0: hairnet    # 发网
  1: head       # 头部
  2: person     # 人体
```

### 3. 训练建议

#### 3.1 数据增强（在data.yaml中配置）
```yaml
# 在训练脚本中，YOLOv8会自动应用数据增强
# 可以通过修改训练参数调整：
hsv_h: 0.015    # 色调增强
hsv_s: 0.7      # 饱和度增强
hsv_v: 0.4      # 亮度增强
degrees: 10.0   # 旋转角度
translate: 0.1  # 平移
scale: 0.5      # 缩放
fliplr: 0.5     # 水平翻转
mosaic: 1.0     # Mosaic增强
mixup: 0.1      # Mixup增强
```

#### 3.2 超参数优化

**学习率调整**:
- 初始学习率: `lr0: 0.01`
- 最终学习率: `lrf: 0.01`
- 预热轮数: `warmup_epochs: 3.0`

**损失函数权重**:
- 边界框损失: `box: 7.5`
- 分类损失: `cls: 0.5`
- DFL损失: `dfl: 1.5`

**早停机制**:
- `patience: 50`  # 验证损失50轮不下降则停止

---

## 🤲 手部检测模型训练

### 1. 训练服务使用

**服务位置**: `src/application/handwash_training_service.py`

**API调用**:
```python
from src.application.handwash_training_service import HandwashTrainingService
from pathlib import Path

service = HandwashTrainingService()

result = await service.train(
    dataset_dir=Path("datasets/handwash"),
    annotations_file=Path("datasets/handwash/annotations.json"),
    training_params={
        "epochs": 100,
        "batch_size": 32,
        "learning_rate": 0.001,
        "validation_split": 0.2,
        "device": "cuda:0"
    }
)
```

### 2. 数据集准备

**数据集结构**:
```
datasets/handwash/
├── annotations.json   # 标注文件（姿态序列）
├── sequences/         # 姿态序列数据
│   ├── session_001.npy
│   ├── session_002.npy
│   └── ...
└── metadata.json      # 元数据
```

**annotations.json 格式**:
```json
{
  "sessions": [
    {
      "session_id": "session_001",
      "sequence_file": "sequences/session_001.npy",
      "label": 1,  # 1=洗手, 0=未洗手
      "steps": ["wet", "soap", "scrub", "rinse", "dry"],
      "compliance": true
    }
  ]
}
```

### 3. 训练建议

#### 3.1 模型架构
- **输入**: 姿态序列（30帧 × 21关键点 × 2坐标 = 1260维）
- **模型**: Temporal CNN (TCN)
- **输出**: 二分类（洗手/未洗手）

#### 3.2 超参数优化
```python
training_params = {
    "epochs": 100,              # 训练轮数
    "batch_size": 32,           # 批次大小
    "learning_rate": 0.001,     # 学习率
    "validation_split": 0.2,    # 验证集比例
    "sequence_length": 30,      # 序列长度（帧数）
    "seed": 42                  # 随机种子
}
```

---

## 📊 评估训练程度

### 1. 发网检测评估指标

#### 1.1 YOLOv8自动评估

训练过程中，YOLOv8会自动计算以下指标：

**主要指标**:
- **mAP@0.5**: 平均精度（IoU=0.5）
- **mAP@0.5:0.95**: 平均精度（IoU=0.5-0.95）
- **Precision**: 精确率（检测为发网的样本中，真正是发网的比例）
- **Recall**: 召回率（真正的发网样本中，被正确检测的比例）
- **F1-Score**: F1分数（精确率和召回率的调和平均）

**训练日志位置**:
```
models/hairnet_model/
├── results.csv        # 训练指标CSV
├── results.png        # 训练曲线图
├── confusion_matrix.png  # 混淆矩阵
└── weights/
    ├── best.pt        # 最佳模型
    └── last.pt        # 最后一轮模型
```

#### 1.2 手动评估脚本

**创建评估脚本**: `scripts/evaluation/evaluate_hairnet_model.py`

```python
from ultralytics import YOLO
import json
from pathlib import Path

def evaluate_model(model_path, test_data_yaml):
    """评估发网检测模型"""
    model = YOLO(model_path)

    # 在测试集上评估
    results = model.val(
        data=test_data_yaml,
        imgsz=640,
        conf=0.25,
        iou=0.45,
        save_json=True,
        plots=True
    )

    # 提取指标
    metrics = {
        "mAP50": results.box.map50,
        "mAP50-95": results.box.map,
        "precision": results.box.mp,
        "recall": results.box.mr,
        "f1": 2 * (results.box.mp * results.box.mr) / (results.box.mp + results.box.mr)
    }

    return metrics

# 使用示例
if __name__ == "__main__":
    metrics = evaluate_model(
        "models/hairnet_detection/hairnet_detection.pt",
        "datasets/hairnet/data.yaml"
    )
    print(json.dumps(metrics, indent=2))
```

#### 1.3 评估标准

**优秀模型标准**:
- mAP@0.5 ≥ 0.90
- Precision ≥ 0.85
- Recall ≥ 0.85
- F1-Score ≥ 0.85

**良好模型标准**:
- mAP@0.5 ≥ 0.80
- Precision ≥ 0.75
- Recall ≥ 0.75
- F1-Score ≥ 0.75

**需要改进**:
- mAP@0.5 < 0.75
- Precision < 0.70
- Recall < 0.70

### 2. 手部检测评估指标

#### 2.1 训练过程评估

**评估指标**:
- **Loss**: 损失值（越小越好）
- **Accuracy**: 准确率（正确预测的比例）
- **Validation Loss**: 验证损失（越小越好）
- **Validation Accuracy**: 验证准确率（越高越好）

**训练日志**:
```python
# 训练过程中会输出：
# Epoch 1/100: Loss=0.523, Accuracy=0.75, Val_Loss=0.456, Val_Accuracy=0.82
# Epoch 2/100: Loss=0.412, Accuracy=0.83, Val_Loss=0.389, Val_Accuracy=0.85
# ...
```

#### 2.2 详细评估脚本

**创建评估脚本**: `scripts/evaluation/evaluate_handwash_model.py`

```python
import torch
from torch.utils.data import DataLoader
from src.application.handwash_training_service import HandwashTrainingService
import json

def evaluate_handwash_model(model_path, test_loader, device="cuda:0"):
    """评估手部检测模型"""
    model = torch.load(model_path)
    model.eval()

    total_correct = 0
    total_samples = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    with torch.no_grad():
        for sequences, labels in test_loader:
            sequences = sequences.to(device)
            labels = labels.to(device)

            logits = model(sequences)
            predictions = torch.sigmoid(logits) > 0.5

            # 计算准确率
            correct = (predictions.float() == labels).sum().item()
            total_correct += correct
            total_samples += labels.numel()

            # 计算混淆矩阵
            true_positives += ((predictions == 1) & (labels == 1)).sum().item()
            false_positives += ((predictions == 1) & (labels == 0)).sum().item()
            false_negatives += ((predictions == 0) & (labels == 1)).sum().item()

    # 计算指标
    accuracy = total_correct / total_samples if total_samples > 0 else 0.0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives
    }

    return metrics
```

#### 2.3 评估标准

**优秀模型标准**:
- Accuracy ≥ 0.90
- Precision ≥ 0.85
- Recall ≥ 0.85
- F1-Score ≥ 0.85

**良好模型标准**:
- Accuracy ≥ 0.80
- Precision ≥ 0.75
- Recall ≥ 0.75
- F1-Score ≥ 0.75

**需要改进**:
- Accuracy < 0.75
- Precision < 0.70
- Recall < 0.70

---

## 🚀 加强训练的方法

### 1. 数据增强

#### 1.1 发网检测数据增强

**图像增强**:
- 亮度调整（±20%）
- 对比度调整（±15%）
- 色调调整（±10%）
- 旋转（±15度）
- 缩放（0.8-1.2倍）
- 水平翻转（50%概率）
- Mosaic增强（4张图像拼接）
- Mixup增强（图像混合）

**实现方式**:
```python
# 在训练脚本中，YOLOv8会自动应用这些增强
# 可以通过修改训练参数调整强度
train_args = {
    "hsv_h": 0.02,      # 增加色调变化
    "hsv_s": 0.8,       # 增加饱和度变化
    "hsv_v": 0.5,       # 增加亮度变化
    "degrees": 15.0,    # 增加旋转角度
    "translate": 0.15,  # 增加平移
    "scale": 0.6,       # 增加缩放范围
    "mosaic": 1.0,      # 启用Mosaic
    "mixup": 0.15       # 启用Mixup
}
```

#### 1.2 手部检测数据增强

**序列增强**:
- 时间扭曲（加速/减速）
- 噪声添加（高斯噪声）
- 关键点抖动（±2像素）
- 序列裁剪（随机起始点）
- 序列翻转（左右手互换）

**实现方式**:
```python
def augment_sequence(sequence, label):
    """增强姿态序列"""
    # 时间扭曲
    if random.random() < 0.3:
        sequence = time_warp(sequence, sigma=0.2)

    # 噪声添加
    if random.random() < 0.3:
        noise = np.random.normal(0, 0.01, sequence.shape)
        sequence = sequence + noise

    # 关键点抖动
    if random.random() < 0.3:
        jitter = np.random.normal(0, 2, sequence.shape)
        sequence = sequence + jitter

    return sequence, label
```

### 2. 增加训练数据

#### 2.1 数据收集策略

**发网检测**:
- 收集不同光照条件下的图像
- 收集不同角度的图像（正面、侧面、背面）
- 收集不同发网类型的图像（颜色、材质）
- 收集遮挡情况下的图像（部分遮挡、完全遮挡）
- 收集不同背景的图像

**手部检测**:
- 收集不同洗手动作的序列
- 收集不同速度的洗手序列（快速、慢速）
- 收集不同环境下的序列（不同水池、不同位置）
- 收集异常情况的序列（非洗手动作）

#### 2.2 数据标注

**发网检测标注**:
- 使用标注工具（LabelImg、CVAT等）
- 标注格式：YOLO格式（类别ID + 归一化坐标）
- 标注类别：hairnet, head, person

**手部检测标注**:
- 标注洗手步骤（wet, soap, scrub, rinse, dry）
- 标注合规状态（compliant, non-compliant）
- 标注时间戳和持续时间

### 3. 超参数优化

#### 3.1 发网检测超参数

**学习率调整**:
```python
# 使用学习率调度器
from torch.optim.lr_scheduler import CosineAnnealingLR

scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
```

**批次大小调整**:
- GPU内存充足：batch_size=32-64
- GPU内存一般：batch_size=16-32
- GPU内存不足：batch_size=8-16

**图像尺寸调整**:
- 高精度：imgsz=640（推荐）
- 平衡：imgsz=512
- 快速：imgsz=416

#### 3.2 手部检测超参数

**学习率调整**:
```python
# 使用学习率调度器
from torch.optim.lr_scheduler import ReduceLROnPlateau

scheduler = ReduceLROnPlateau(
    optimizer,
    mode='min',
    factor=0.5,
    patience=10,
    verbose=True
)
```

**序列长度调整**:
- 长序列：sequence_length=60（捕获完整动作）
- 标准：sequence_length=30（推荐）
- 短序列：sequence_length=15（快速检测）

### 4. 模型架构优化

#### 4.1 发网检测模型

**模型选择**:
- YOLOv8n: 快速，适合实时检测
- YOLOv8s: 平衡，推荐使用
- YOLOv8m: 高精度，适合离线检测

**迁移学习**:
```python
# 使用预训练权重
model = YOLO("yolov8s.pt")  # 使用COCO预训练权重
model.train(data="datasets/hairnet/data.yaml", epochs=150)
```

#### 4.2 手部检测模型

**模型架构**:
- Temporal CNN (TCN): 当前使用
- Transformer: 更强大的时序建模（可升级）
- LSTM/GRU: 传统时序模型（备选）

**升级到Transformer**:
```python
from transformers import TransformerEncoder

class HandwashTransformer(nn.Module):
    def __init__(self, input_dim, d_model=256, nhead=8, num_layers=4):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        self.transformer = TransformerEncoder(
            TransformerEncoderLayer(d_model, nhead),
            num_layers
        )
        self.classifier = nn.Linear(d_model, 1)
```

### 5. 训练策略优化

#### 5.1 渐进式训练

**阶段1: 基础训练**
- 使用预训练权重
- 冻结backbone，只训练检测头
- 训练10-20轮

**阶段2: 微调训练**
- 解冻backbone
- 降低学习率（×0.1）
- 训练50-100轮

**阶段3: 精细训练**
- 进一步降低学习率（×0.01）
- 训练30-50轮

#### 5.2 集成学习

**模型集成**:
```python
# 训练多个模型，然后集成
models = [
    load_model("model_1.pt"),
    load_model("model_2.pt"),
    load_model("model_3.pt")
]

def ensemble_predict(models, input_data):
    predictions = [model(input_data) for model in models]
    return torch.mean(torch.stack(predictions), dim=0)
```

---

## 📈 评估指标详解

### 1. 发网检测指标

#### 1.1 mAP (Mean Average Precision)

**定义**: 所有类别的平均精度（AP）的平均值

**计算方式**:
```
AP = ∫₀¹ P(R) dR
mAP = (1/N) × Σ AP_i
```

**解读**:
- mAP@0.5: IoU阈值为0.5时的平均精度
- mAP@0.5:0.95: IoU阈值从0.5到0.95（步长0.05）的平均精度
- 值越高越好，范围0-1

#### 1.2 Precision (精确率)

**定义**: 检测为发网的样本中，真正是发网的比例

**公式**:
```
Precision = TP / (TP + FP)
```

**解读**:
- 值越高，误报越少
- 范围0-1，目标≥0.85

#### 1.3 Recall (召回率)

**定义**: 真正的发网样本中，被正确检测的比例

**公式**:
```
Recall = TP / (TP + FN)
```

**解读**:
- 值越高，漏报越少
- 范围0-1，目标≥0.85

#### 1.4 F1-Score

**定义**: 精确率和召回率的调和平均

**公式**:
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**解读**:
- 平衡精确率和召回率
- 范围0-1，目标≥0.85

### 2. 手部检测指标

#### 2.1 Accuracy (准确率)

**定义**: 正确预测的样本占总样本的比例

**公式**:
```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

**解读**:
- 整体性能指标
- 范围0-1，目标≥0.90

#### 2.2 Precision (精确率)

**定义**: 预测为洗手的样本中，真正是洗手的比例

**公式**:
```
Precision = TP / (TP + FP)
```

**解读**:
- 减少误报（将非洗手动作识别为洗手）
- 范围0-1，目标≥0.85

#### 2.3 Recall (召回率)

**定义**: 真正的洗手行为中，被正确识别的比例

**公式**:
```
Recall = TP / (TP + FN)
```

**解读**:
- 减少漏报（遗漏真正的洗手行为）
- 范围0-1，目标≥0.85

#### 2.4 F1-Score

**定义**: 精确率和召回率的调和平均

**公式**:
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**解读**:
- 平衡精确率和召回率
- 范围0-1，目标≥0.85

### 3. 混淆矩阵

**2×2混淆矩阵**:
```
               预测
           正类    负类
实际 正类  TP    FN
     负类  FP    TN
```

**解读**:
- TP (True Positive): 真正例（正确识别为洗手）
- FP (False Positive): 假正例（误报，非洗手识别为洗手）
- FN (False Negative): 假负例（漏报，洗手未识别）
- TN (True Negative): 真负例（正确识别为非洗手）

---

## 🎯 训练检查清单

### 发网检测训练检查清单

- [ ] 数据集准备完成（train/val/test）
- [ ] 数据标注质量检查（标注准确、完整）
- [ ] 数据集平衡性检查（各类别样本数量）
- [ ] 训练参数设置（epochs, batch_size, learning_rate）
- [ ] 数据增强配置（强度适中）
- [ ] 预训练权重加载（使用预训练模型）
- [ ] 训练过程监控（loss下降、指标提升）
- [ ] 验证集评估（mAP, Precision, Recall）
- [ ] 测试集评估（最终性能）
- [ ] 模型保存（best.pt, last.pt）
- [ ] 训练报告生成（metrics, curves）

### 手部检测训练检查清单

- [ ] 数据集准备完成（序列数据、标注）
- [ ] 数据质量检查（序列完整、标注准确）
- [ ] 数据集平衡性检查（正负样本比例）
- [ ] 训练参数设置（epochs, batch_size, learning_rate）
- [ ] 序列增强配置（时间扭曲、噪声）
- [ ] 模型架构选择（TCN/Transformer）
- [ ] 训练过程监控（loss下降、accuracy提升）
- [ ] 验证集评估（Accuracy, Precision, Recall）
- [ ] 测试集评估（最终性能）
- [ ] 模型保存（checkpoint）
- [ ] 训练报告生成（metrics, confusion matrix）

---

## 📝 总结

### 发网检测训练要点

1. **数据质量**: 确保标注准确、数据多样
2. **数据增强**: 适度增强，避免过度
3. **超参数**: 根据GPU和数据集调整
4. **评估指标**: 关注mAP、Precision、Recall
5. **持续改进**: 根据评估结果迭代优化

### 手部检测训练要点

1. **序列质量**: 确保序列完整、标注准确
2. **时序建模**: 选择合适的时序模型
3. **特征工程**: 提取有效的时序特征
4. **评估指标**: 关注Accuracy、Precision、Recall
5. **持续改进**: 根据评估结果迭代优化

---

## 🔗 相关文档

- [模型训练服务文档](../src/application/model_training_service.py)
- [洗手训练服务文档](../src/application/handwash_training_service.py)
- [训练脚本文档](../scripts/training/train_hairnet_model.py)
- [ML融合准确率分析](./ML_FUSION_ACCURACY_ANALYSIS.md)
- [发网检测优化总结](./HAIRNET_DETECTION_OPTIMIZATION_SUMMARY.md)
