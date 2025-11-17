# 发网检测逻辑详细分析

## 1. 检测流程概览

### 1.1 主入口：`detect_hairnet_compliance`

```
detect_hairnet_compliance(image, human_detections)
  ├─ 如果提供了人体检测结果
  │   ├─ 策略1: 先尝试全图检测 (conf_thres=0.1)
  │   │   ├─ 如果全图检测成功 (has_hairnet=True && confidence >= 0.1)
  │   │   │   └─ 直接使用全图检测结果，映射到每个人
  │   │   └─ 如果全图检测失败
  │   │       └─ 策略2: 回退到ROI检测
  │   │           └─ _detect_hairnet_in_rois()
  │   └─ 如果没有提供人体检测结果
  │       └─ 回退到全帧检测: detect()
  └─ 返回结果
```

### 1.2 全图检测：`detect` 方法

**参数**:
- `conf_thres`: 如果传入则使用传入值，否则使用 `self.conf_thres` (从统一配置读取，默认0.25)
- `iou_thres`: 如果传入则使用传入值，否则使用 `self.iou_thres` (默认0.45)
- `imgsz`: 固定为 640

**流程**:
1. 检查输入图像有效性
2. 调用 `self.model(image, conf=conf, iou=iou, imgsz=640, verbose=False)`
3. 遍历所有检测结果，查找类别为 "hairnet" 的目标
4. 返回 `wearing_hairnet`, `confidence`, `detections` 等

**关键点**:
- ✅ 全图检测能检测到发网，说明模型本身没有问题
- ✅ 使用 `imgsz=640` 与训练时保持一致

### 1.3 ROI检测：`_detect_hairnet_in_rois` 方法

**ROI提取参数**:
- `head_height = person_height * 0.30` (30%的人体高度)
- `padding_height = head_height * 0.15` (15%的头部高度)
- `padding_width = person_width * 0.10` (10%的人体宽度)

**ROI坐标计算**:
```python
roi_x1 = max(0, x1 - padding_width)
roi_y1 = max(0, y1 - padding_height)  # 向上扩展
roi_x2 = min(image.shape[1], x2 + padding_width)
roi_y2 = min(image.shape[0], y1 + head_height + padding_height)  # 向下扩展
```

**检测参数**:
- `detection_conf = 0.1` (固定值，不是配置值)
- `iou = self.iou_thres` (默认0.45)
- `imgsz = 640` (固定值)

**后处理阈值**:
- `post_process_threshold = min(self.conf_thres, 0.2)` (不超过0.2)

**流程**:
1. 提取头部ROI区域
2. 保存ROI用于调试（如果启用）
3. 调用 `self.model(head_roi, conf=0.1, iou=iou, imgsz=640, verbose=False)`
4. 处理检测结果：
   - 如果检测到 "hairnet" 类别：
     - 如果 `hairnet_confidence >= post_process_threshold`: 标记为 `has_hairnet=True`
     - 如果 `hairnet_confidence >= 0.1` (但 < post_process_threshold): 标记为 `has_hairnet=True` (可能佩戴)
     - 否则: 标记为 `has_hairnet=False`
   - 如果没有检测到任何目标：
     - 尝试扩展ROI检测（扩展50像素，阈值降低到 `max(0.1, detection_conf * 0.8)`）
     - 如果扩展ROI检测也失败，标记为 `has_hairnet=None` (不确定)

## 2. 关键差异分析

### 2.1 检测阈值差异

| 检测方式 | 检测阈值 | 后处理阈值 | 说明 |
|---------|---------|-----------|------|
| 全图检测 | `conf_thres` (传入0.1或使用self.conf_thres) | 无 | 直接使用检测结果 |
| ROI检测 | `0.1` (固定值) | `min(self.conf_thres, 0.2)` | 检测时使用0.1，后处理时使用更严格的阈值 |

**问题**: ROI检测虽然使用了0.1的检测阈值，但后处理时使用了更严格的阈值（`min(self.conf_thres, 0.2)`），这可能导致即使检测到了发网，也会被过滤掉。

### 2.2 图像尺寸差异

| 检测方式 | 输入图像 | 模型输入尺寸 |
|---------|---------|------------|
| 全图检测 | 完整图像 (例如 1920x1080) | 640x640 (模型自动resize) |
| ROI检测 | 头部ROI (例如 200x300) | 640x640 (模型自动resize) |

**问题**: 
- 全图检测时，模型看到的是完整的上下文信息
- ROI检测时，模型只看到头部区域，可能缺少上下文信息
- 虽然都resize到640x640，但ROI区域可能被过度放大，导致细节丢失

### 2.3 ROI位置准确性

**ROI提取逻辑**:
- 头部高度: 人体高度的30%
- Padding: 高度方向15%，宽度方向10%

**潜在问题**:
1. **ROI位置可能不准确**: 如果人体检测框不准确，ROI位置也会不准确
2. **发网位置可能超出ROI**: 如果发网位置超出了预期的头部区域（30%），ROI检测会失败
3. **ROI太小**: 如果人体检测框很小，ROI也会很小，可能导致模型无法识别

### 2.4 模型在ROI上的表现

**可能的原因**:
1. **上下文信息缺失**: 全图检测时，模型可以看到完整的场景信息；ROI检测时，模型只能看到头部区域
2. **图像质量**: ROI区域可能被过度放大，导致细节丢失或模糊
3. **训练数据**: 如果模型主要在全图上训练，在ROI上的表现可能不如全图

## 3. 问题诊断

### 3.1 为什么全图检测能检测到发网，但ROI检测失败？

**可能的原因**:

1. **ROI位置不准确**
   - 全图检测到的发网位置不在ROI区域内
   - 需要对比全图检测到的发网bbox和ROI区域

2. **ROI太小或质量差**
   - ROI区域太小，模型无法识别
   - ROI图像质量差（模糊、过曝等）

3. **后处理阈值太严格**
   - 虽然检测时使用了0.1的阈值，但后处理时使用了更严格的阈值（`min(self.conf_thres, 0.2)`）
   - 如果 `self.conf_thres` 很高（例如0.65），后处理阈值会是0.2，可能过滤掉一些检测结果

4. **模型在ROI上的表现不如全图**
   - 模型在全图上训练，在ROI上的表现可能不如全图
   - 缺少上下文信息

### 3.2 诊断步骤

1. **对比全图检测和ROI检测的位置**
   - 检查全图检测到的发网bbox是否在ROI区域内
   - 如果不在，说明ROI位置不准确

2. **检查ROI图像质量**
   - 查看保存的ROI图像，检查是否包含发网
   - 检查ROI图像是否清晰、大小是否合适

3. **检查检测阈值**
   - 查看日志中的检测阈值和后处理阈值
   - 检查是否有检测结果被后处理过滤掉

4. **检查模型输出**
   - 查看ROI检测时模型是否输出了任何结果
   - 检查是否有其他类别（如"head"、"person"）被检测到，但没有"hairnet"

## 4. 建议的优化方向

### 4.1 不修改代码，先诊断问题

1. **启用诊断日志**
   - 已经添加了诊断日志，可以对比全图检测和ROI检测的位置
   - 查看保存的ROI图像，检查是否包含发网

2. **分析日志输出**
   - 查看ROI检测时的详细日志
   - 检查是否有检测结果被后处理过滤掉
   - 检查扩展ROI检测是否被触发

3. **对比全图和ROI的检测结果**
   - 如果全图检测能检测到发网，但ROI检测失败，说明问题在ROI提取或后处理

### 4.1.1 ROI 参数可配置化（已落实）
- `roi_head_ratio`：头部区域占人体高度比例（默认 0.30）
- `roi_padding_height_ratio` / `roi_padding_width_ratio`：上下、左右 padding 比例
- `roi_min_size`：ROI 最小尺寸阈值，用于判定 ROI 是否过小
- `roi_detection_confidence`：ROI 推理使用的置信度阈值
- `roi_postprocess_threshold_cap` / `roi_min_positive_confidence`：后处理阶段判定佩戴的阈值
- `roi_expansion_pixels` / `roi_expansion_attempts` / `roi_expansion_conf_scale`：扩展 ROI 的像素步进、次数与阈值缩放

通过 `config/unified_params.yaml` 中的 `hairnet_detection` 段可灵活调整上述参数，用于不同场景的召回率/精准率权衡。

### 4.2 可能的优化方向（待确认问题后）

1. **调整ROI提取参数**
   - 如果ROI位置不准确，可以调整头部高度比例或padding
   - 如果ROI太小，可以增加头部高度比例

2. **调整后处理阈值**
   - 如果后处理阈值太严格，可以降低后处理阈值
   - 或者使用与检测阈值相同的阈值

3. **改进ROI提取逻辑**
   - 如果ROI位置不准确，可以使用更智能的ROI提取方法
   - 例如，使用关键点检测来确定头部位置

4. **使用全图检测结果**
   - 如果ROI检测总是失败，可以考虑直接使用全图检测结果
   - 但需要注意资源消耗和性能问题

## 5. 当前代码的关键点

### 5.1 检测阈值设置

```python
# 全图检测
full_frame_result = self.detect(image_array, conf_thres=0.1)

# ROI检测
detection_conf = 0.1  # 固定值
results = self.model(head_roi, conf=detection_conf, iou=iou, imgsz=640, verbose=False)

# 后处理
post_process_threshold = min(self.conf_thres, 0.2)  # 可能比检测阈值更严格
if hairnet_confidence >= post_process_threshold:
    has_hairnet = True
```

### 5.2 ROI提取参数

```python
head_height = int(person_height * 0.30)  # 30%
padding_height = int(head_height * 0.15)  # 15%
padding_width = int(person_width * 0.10)  # 10%
```

### 5.3 扩展ROI检测

```python
# 如果初始ROI检测失败，尝试扩展ROI
expanded_roi_x1 = max(0, roi_x1 - 50)
expanded_roi_y1 = max(0, roi_y1 - 50)
expanded_roi_x2 = min(image.shape[1], roi_x2 + 50)
expanded_roi_y2 = min(image.shape[0], roi_y2 + 50)
expanded_conf = max(0.1, detection_conf * 0.8)  # 进一步降低阈值
```

## 6. 下一步行动

1. **查看诊断日志**
   - 运行检测，查看详细的诊断日志
   - 特别关注"🔍 诊断：对比全图检测和ROI检测的位置"部分

2. **检查ROI图像**
   - 查看保存的ROI图像，确认是否包含发网
   - 检查ROI图像的质量和大小

3. **分析检测结果**
   - 查看ROI检测时是否有任何检测结果
   - 检查是否有其他类别被检测到，但没有"hairnet"

4. **根据诊断结果决定优化方向**
   - 如果ROI位置不准确，调整ROI提取参数
   - 如果后处理阈值太严格，调整后处理阈值
   - 如果ROI太小，增加头部高度比例

