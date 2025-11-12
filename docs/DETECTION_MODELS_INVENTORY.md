# 检测流程模型清单

## 📋 概述

本文档详细列出整个检测流程中使用的所有模型，包括模型类型、用途、路径和配置信息。

## 🔍 核心检测模型

### 1. 人体检测模型 (Human Detection)

**模型类型**: YOLOv8  
**模型文件**: 
- 默认: `models/yolo/yolov8s.pt` (YOLOv8 Small)
- 可选: `models/yolo/yolov8n.pt` (YOLOv8 Nano - 轻量级)
- 可选: `models/yolo/yolov8m.pt` (YOLOv8 Medium - 平衡模式)
- 可选: `models/yolo/yolov8l.pt` (YOLOv8 Large - 级联检测重模型)

**实现位置**: 
- `src/detection/detector.py` - `HumanDetector` 类
- `src/strategies/detection/yolo_strategy.py` - `YOLOStrategy` 类

**用途**: 
- 检测图像/视频中的人体目标
- 为后续检测（发网、姿态、行为）提供基础边界框

**配置参数** (`config/unified_params.yaml`):
```yaml
human_detection:
  model_path: models/yolo/yolov8s.pt
  confidence_threshold: 0.4
  iou_threshold: 0.6
  nms_threshold: 0.4
  imgsz: 416
  max_detections: 15
  min_box_area: 1000
  min_height: 60
  min_width: 40
```

**设备支持**: CPU, CUDA, MPS (Apple Silicon)

---

### 2. 发网检测模型 (Hairnet Detection)

**模型类型**: YOLOv8 (自定义训练)  
**模型文件**: `models/hairnet_detection/hairnet_detection.pt`

**实现位置**: 
- `src/detection/yolo_hairnet_detector.py` - `YOLOHairnetDetector` 类

**用途**: 
- 检测人员是否佩戴发网
- 输出发网边界框和置信度
- 与人体检测结果匹配，判断每个人是否佩戴发网

**配置参数** (`config/unified_params.yaml`):
```yaml
hairnet_detection:
  model_path: null  # 如果为null，使用默认路径
  confidence_threshold: 0.6
  device: auto
  input_size: [224, 224]
```

**设备支持**: CPU, CUDA, MPS (Apple Silicon)

**注意**: 
- 如果模型文件不存在，检测器会抛出异常
- 模型需要通过MLOps工作流训练生成

---

### 3. 姿态检测模型 (Pose Detection)

**模型类型**: YOLOv8 Pose 或 MediaPipe Pose  
**模型文件**: 
- YOLOv8 Pose: `models/yolo/yolov8n-pose.pt` (YOLOv8 Nano Pose)
- MediaPipe: 内置模型（无需文件）

**实现位置**: 
- `src/detection/pose_detector.py` - `YOLOv8PoseDetector` 和 `MediaPipePoseDetector` 类
- `src/detection/pose_detector.py` - `PoseDetectorFactory` 工厂类

**用途**: 
- 检测人体关键点（17个关键点：鼻子、眼睛、耳朵、肩膀、肘部、手腕、臀部、膝盖、脚踝等）
- 用于行为识别（洗手、消毒等）
- 优化头部区域定位（用于发网检测）

**配置参数** (`config/unified_params.yaml`):
```yaml
pose_detection:
  backend: yolov8  # 'yolov8' or 'mediapipe' or 'auto'
  device: auto
  model_path: models/yolo/yolov8n-pose.pt
  confidence_threshold: 0.5
  iou_threshold: 0.7
```

**设备支持**: 
- YOLOv8 Pose: CPU, CUDA, MPS
- MediaPipe: CPU, GPU (如果支持)

**后端选择逻辑**:
- `backend: "auto"` 时：
  - 如果设备是 CUDA → 使用 YOLOv8 Pose
  - 否则 → 使用 MediaPipe

---

### 4. 行为识别模型 (Behavior Recognition)

#### 4.1 XGBoost 洗手分类器

**模型类型**: XGBoost (梯度提升树)  
**模型文件**: `models/handwash_xgb.joblib.real`

**实现位置**: 
- `src/core/behavior.py` - `BehaviorRecognizer` 类

**用途**: 
- 基于手部关键点时序数据分类洗手行为
- 输入：手部关键点坐标序列（时间窗口）
- 输出：洗手行为置信度

**配置参数** (`config/unified_params.yaml`):
```yaml
behavior_recognition:
  use_ml_classifier: true
  ml_model_path: models/handwash_xgb.joblib.real
  ml_window: 30  # 时间窗口大小（帧数）
  ml_fusion_alpha: 0.5  # ML结果与规则结果的融合权重
```

**数据格式**: 
- 输入特征：手部关键点坐标的时间序列
- 特征维度：取决于时间窗口大小和关键点数量

**注意**: 
- 如果模型文件不存在，ML分类器会被禁用，但不会影响其他功能
- 支持 `.json`, `.ubj`, `.joblib` 格式

#### 4.2 MediaPipe Hands

**模型类型**: MediaPipe (Google)  
**模型文件**: 内置（无需文件）

**实现位置**: 
- `src/core/behavior.py` - `BehaviorRecognizer` 类
- `src/detection/enhanced_hand_detector.py` - `EnhancedHandDetector` 类

**用途**: 
- 检测手部关键点（21个关键点）
- 用于洗手行为识别和手部消毒识别

**配置参数** (`config/unified_params.yaml`):
```yaml
behavior_recognition:
  use_mediapipe: true
  max_num_hands: 2
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5
```

**设备支持**: CPU, GPU (如果MediaPipe支持)

---

## 🔄 级联检测模型 (可选)

### 5. 级联重检测模型 (Cascade Heavy Model)

**模型类型**: YOLOv8 Large  
**模型文件**: `models/yolo/yolov8l.pt` (YOLOv8 Large)

**实现位置**: 
- `src/core/optimized_detection_pipeline.py` - `_cascade_refine_persons` 方法

**用途**: 
- 对低置信度或边界区域的检测结果进行二次检测
- 提高检测准确率

**配置参数** (`config/unified_params.yaml`):
```yaml
cascade:
  enable: false  # 默认关闭
  heavy_weights: models/yolo/yolov8l.pt
  trigger_confidence_range: [0.4, 0.6]  # 触发级联检测的置信度范围
  trigger_roi: null  # 触发级联检测的ROI区域
```

**工作流程**:
1. 主模型（yolov8s）进行初步检测
2. 如果检测结果置信度在 `trigger_confidence_range` 内，或位于 `trigger_roi` 区域
3. 使用重模型（yolov8l）对该区域进行二次检测
4. 合并结果

**注意**: 
- 级联检测会增加计算开销，默认关闭
- 仅在 `accurate` 配置档位下启用

---

## 📊 模型使用流程图

```
视频帧输入
    ↓
[1] 人体检测 (YOLOv8s/n/m)
    ├─ 输出: person_detections (边界框列表)
    ↓
[2] 发网检测 (YOLOv8 自定义)
    ├─ 输入: 整张图像
    ├─ 匹配: person_detections
    └─ 输出: hairnet_results (has_hairnet, confidence)
    ↓
[3] 姿态检测 (YOLOv8 Pose 或 MediaPipe)
    ├─ 输入: person_detections
    └─ 输出: pose_keypoints (17个关键点)
    ↓
[4] 行为识别
    ├─ [4.1] MediaPipe Hands
    │   └─ 输出: hand_keypoints (21个关键点/手)
    │
    ├─ [4.2] XGBoost 分类器 (可选)
    │   ├─ 输入: hand_keypoints 时序数据
    │   └─ 输出: handwash_confidence
    │
    └─ [4.3] 规则引擎
        ├─ 基于关键点的规则判断
        └─ 输出: handwash_results, sanitize_results
    ↓
[5] 级联检测 (可选)
    ├─ 触发条件: 低置信度或边界区域
    └─ 使用: YOLOv8l 重模型
    ↓
最终检测结果
```

---

## 🎯 模型依赖关系

### 直接依赖
- **发网检测** → 依赖 **人体检测** (需要人体边界框)
- **姿态检测** → 依赖 **人体检测** (在人体区域内检测关键点)
- **行为识别** → 依赖 **姿态检测** (需要手部关键点)
- **级联检测** → 依赖 **人体检测** (对低置信度结果重检)

### 并行检测
- **人体检测** 和 **发网检测** 可以并行（发网检测使用整张图像）
- **姿态检测** 和 **发网检测** 可以并行（不相互依赖）

---

## 💾 模型文件位置

```
项目根目录/
├── models/
│   ├── yolo/
│   │   ├── yolov8s.pt          # 人体检测 (默认)
│   │   ├── yolov8n.pt           # 人体检测 (轻量级)
│   │   ├── yolov8m.pt           # 人体检测 (平衡模式)
│   │   ├── yolov8l.pt           # 人体检测 (级联重模型)
│   │   └── yolov8n-pose.pt      # 姿态检测
│   │
│   ├── hairnet_detection/
│   │   └── hairnet_detection.pt # 发网检测 (需训练)
│   │
│   └── handwash_xgb.joblib.real # 洗手行为分类器 (需训练)
```

---

## 🔧 模型配置档位

系统支持三种配置档位（`config/unified_params.yaml` 中的 `profiles`）：

### Fast (快速模式)
- 人体检测: `yolov8s.pt`
- 级联检测: 关闭
- 帧跳过: 0

### Balanced (平衡模式)
- 人体检测: `yolov8s.pt`
- 置信度阈值: 0.5
- 级联检测: 关闭

### Accurate (准确模式)
- 人体检测: `yolov8m.pt`
- 最大检测数: 20
- 级联检测: 启用 (`yolov8l.pt`)

---

## 📈 模型性能特征

| 模型 | 参数量 | 推理速度 (FPS) | 准确率 | 内存占用 |
|------|--------|----------------|--------|----------|
| YOLOv8n | ~3M | ~100+ (CPU) | 中等 | 低 |
| YOLOv8s | ~11M | ~50 (CPU) | 高 | 中 |
| YOLOv8m | ~26M | ~30 (CPU) | 很高 | 中高 |
| YOLOv8l | ~44M | ~20 (CPU) | 极高 | 高 |
| YOLOv8n-pose | ~3M | ~80 (CPU) | 高 | 低 |
| 发网检测 (自定义) | 取决于训练 | ~40 (CPU) | 取决于训练 | 中 |
| XGBoost | 取决于训练 | ~1000+ | 高 | 极低 |
| MediaPipe | 内置 | ~60 (CPU) | 高 | 低 |

*注：实际性能取决于硬件配置、图像分辨率、检测目标数量等因素*

---

## 🚀 模型加载时机

### 启动时加载（延迟加载）
- **人体检测模型**: 在 `HumanDetector` 初始化时加载
- **发网检测模型**: 在 `YOLOHairnetDetector` 初始化时加载
- **姿态检测模型**: 在 `PoseDetectorFactory.create()` 时加载
- **XGBoost模型**: 在 `BehaviorRecognizer` 初始化时加载（如果启用）
- **MediaPipe**: 在 `BehaviorRecognizer` 初始化时加载（如果启用）

### 运行时加载（惰性加载）
- **级联重模型**: 在首次触发级联检测时加载

---

## ⚠️ 注意事项

1. **模型文件缺失处理**:
   - 人体检测模型缺失 → 程序无法启动
   - 发网检测模型缺失 → 发网检测功能不可用（抛出异常）
   - XGBoost模型缺失 → ML分类器禁用，使用规则引擎
   - MediaPipe不可用 → 使用YOLOv8 Pose作为替代

2. **设备兼容性**:
   - CUDA: 需要NVIDIA GPU和CUDA支持
   - MPS: 需要Apple Silicon (M1/M2/M3) Mac
   - CPU: 所有平台支持，但速度较慢

3. **模型版本兼容性**:
   - YOLOv8模型需要 `ultralytics` 库支持
   - XGBoost模型需要与训练时相同的XGBoost版本
   - MediaPipe需要 `mediapipe` 库支持

4. **内存管理**:
   - 所有模型在初始化时加载到内存
   - 级联模型使用惰性加载，减少初始内存占用
   - 建议根据硬件配置选择合适的模型大小

---

## 📚 相关文档

- `docs/DETECTION_FLOW_ANALYSIS.md` - 检测流程分析
- `docs/CURRENT_DETECTION_LOGIC_ANALYSIS.md` - 当前检测逻辑分析
- `docs/DETECTION_LOGIC_OPTIMIZATION_PLAN.md` - 检测逻辑优化计划
- `config/unified_params.yaml` - 统一配置参数

---

## 🔄 模型更新和维护

### 模型训练
- 发网检测模型: 通过MLOps工作流训练 (`src/workflow/workflow_engine.py`)
- XGBoost分类器: 通过MLOps工作流训练 (`src/application/handwash_training_service.py`)

### 模型注册
- 所有训练完成的模型会注册到模型注册表 (`src/application/model_registry_service.py`)
- 模型信息存储在数据库 (`src/database/models.py` - `ModelRegistry` 表)

### 模型版本管理
- 每个模型都有版本号
- 模型路径包含时间戳或版本信息
- 支持模型回滚和A/B测试

