# 发网检测详细分析

## 1. 使用的模型

### 1.1 模型类型
- **检测器**: `YOLOHairnetDetector`
- **模型架构**: YOLOv8（基于Ultralytics）
- **模型文件**: `models/hairnet_detection/hairnet_detection.pt`
- **模型类别**: 目标检测模型（检测"hairnet"类别）

### 1.2 模型加载
- **默认路径**: `models/hairnet_detection/hairnet_detection.pt`
- **配置路径**: `config/unified_params.yaml` 中 `hairnet_detection.model_path`（当前为 `null`）
- **初始化**: 在 `DetectionInitializer` 中创建 `YOLOHairnetDetector` 实例

## 2. 检测逻辑流程

### 2.1 整体流程
```
1. 人体检测 → 2. 提取头部ROI → 3. 发网检测 → 4. 结果匹配 → 5. 可视化
```

### 2.2 详细步骤

#### 步骤1: 人体检测
- 使用 `HumanDetector` 检测图像中的人体
- 获取人体边界框 `[x1, y1, x2, y2]`

#### 步骤2: 提取头部ROI
- **头部区域计算**: 人体高度的30%（`head_height = person_height * 0.3`）
- **ROI坐标**:
  ```python
  head_y1 = y1  # 人体框顶部
  head_y2 = y1 + head_height  # 头部区域底部
  head_x1 = x1  # 人体框左边界
  head_x2 = x2  # 人体框右边界
  ```
- **Padding**: 添加10%的padding以提高检测准确度

#### 步骤3: 发网检测
- **检测方法**: 在头部ROI区域运行YOLOv8模型
- **检测参数**:
  - `conf_thres`: 0.25（YOLO检测置信度阈值）
  - `iou_thres`: 0.45（IoU阈值）
- **检测类别**: 查找类别名称为 "hairnet" 的检测结果

#### 步骤4: 结果匹配
- **匹配逻辑**: 检查发网检测框是否与人体框重叠
- **重叠判断**: 使用 `_boxes_overlap` 方法
- **结果状态**:
  - `has_hairnet = True`: 检测到发网且与人体框重叠
  - `has_hairnet = False`: 检测到发网但未与人体框重叠，或明确未检测到发网
  - `has_hairnet = None`: 没有发网检测结果，结果不明确（不判定为违规）

#### 步骤5: 可视化
- **头部框**: 绿色（有发网）或红色（无发网）
- **标签**: 显示"有发网"或"无发网"及置信度

## 3. 配置参数

### 3.1 关键参数（`config/unified_params.yaml`）
```yaml
hairnet_detection:
  model_path: null  # ⚠️ 当前为null，使用默认路径
  confidence_threshold: 0.65  # ⚠️ 可能太高，导致检测不到
  total_score_threshold: 0.85  # 总分数阈值
  device: auto  # 自动选择设备
```

### 3.2 YOLO检测参数（代码中设置）
```python
conf_thres: 0.25  # YOLO检测置信度阈值
iou_thres: 0.45   # IoU阈值
```

## 4. 可能的问题分析

### 4.1 模型未正确加载
**问题**: 配置中 `model_path: null`，可能没有正确指定模型路径

**检查方法**:
```bash
# 检查模型文件是否存在
ls -lh models/hairnet_detection/hairnet_detection.pt

# 检查日志中是否有模型加载错误
grep -i "hairnet\|model" logs/*.log
```

**解决方案**:
1. 确认模型文件存在
2. 在配置文件中指定正确的模型路径
3. 检查模型文件权限

### 4.2 置信度阈值过高
**问题**: `confidence_threshold: 0.65` 可能太高，导致检测不到发网

**分析**:
- YOLO检测使用 `conf_thres: 0.25`，会检测到置信度 >= 0.25 的发网
- 但后续处理可能使用了 `confidence_threshold: 0.65` 进行过滤
- 如果模型输出的置信度在 0.25-0.65 之间，会被检测到但被过滤掉

**解决方案**:
1. 降低 `confidence_threshold` 到 0.3-0.4
2. 或者调整YOLO检测的 `conf_thres` 到 0.5-0.6

### 4.3 头部ROI提取不准确
**问题**: 头部区域可能提取不准确，导致发网检测失败

**分析**:
- 当前使用人体高度的30%作为头部区域
- 如果人体检测框不准确，头部区域也会不准确
- 如果人员姿态特殊（低头、侧身等），头部区域可能不包含发网

**解决方案**:
1. 使用姿态检测的关键点来精确定位头部
2. 增加头部区域的padding
3. 调整头部区域的比例（从30%调整到35-40%）

### 4.4 模型质量问题
**问题**: 模型可能没有针对当前场景进行训练或微调

**分析**:
- 模型可能是在其他数据集上训练的
- 当前场景的发网颜色、形状、光照条件可能与训练数据不同
- 模型可能对某些类型的发网（颜色、材质）检测效果不好

**解决方案**:
1. 检查模型训练数据是否包含当前场景
2. 使用当前场景的数据对模型进行微调
3. 收集当前场景的样本，重新训练模型

## 5. 调试建议

### 5.1 检查模型加载
```python
# 在代码中添加日志
logger.info(f"发网检测器模型路径: {self.model_path}")
logger.info(f"模型文件存在: {os.path.exists(self.model_path)}")
logger.info(f"模型加载成功: {self.model is not None}")
```

### 5.2 检查检测结果
```python
# 在 detect_hairnet_compliance 中添加详细日志
logger.info(f"YOLO检测结果数量: {len(hairnet_detections)}")
for det in hairnet_detections:
    logger.info(f"检测结果: {det}")
```

### 5.3 检查ROI提取
```python
# 保存头部ROI图像用于调试
cv2.imwrite(f"debug_head_roi_{i}.jpg", head_roi)
```

### 5.4 调整参数测试
1. **降低置信度阈值**:
   ```yaml
   hairnet_detection:
     confidence_threshold: 0.3  # 从0.65降低到0.3
   ```

2. **调整YOLO检测阈值**:
   ```python
   # 在 YOLOHairnetDetector.__init__ 中
   conf_thres: float = 0.15  # 从0.25降低到0.15
   ```

3. **增加头部区域**:
   ```python
   # 在 _detect_hairnet_in_rois 中
   head_height = int(person_height * 0.35)  # 从0.3增加到0.35
   ```

## 6. 推荐的修复步骤

### 步骤1: 检查模型文件
```bash
# 确认模型文件存在且可读
ls -lh models/hairnet_detection/hairnet_detection.pt
file models/hairnet_detection/hairnet_detection.pt
```

### 步骤2: 降低置信度阈值
修改 `config/unified_params.yaml`:
```yaml
hairnet_detection:
  confidence_threshold: 0.3  # 从0.65降低到0.3
```

### 步骤3: 检查日志
查看检测过程中的详细日志，确认：
- 模型是否成功加载
- 是否检测到发网（即使置信度较低）
- 头部ROI是否提取正确

### 步骤4: 测试调整
逐步调整参数，观察检测效果：
1. 先降低置信度阈值到0.3
2. 如果还是检测不到，降低到0.2
3. 同时检查头部ROI提取是否准确

### 步骤5: 模型微调（如果需要）
如果参数调整后仍然检测不到，可能需要：
1. 收集当前场景的样本数据
2. 使用这些数据对模型进行微调
3. 或者重新训练模型

## 7. 代码位置

- **检测器实现**: `src/detection/yolo_hairnet_detector.py`
- **检测逻辑**: `src/core/optimized_detection_pipeline.py::_detect_hairnet_for_persons`
- **配置参数**: `config/unified_params.yaml`
- **初始化**: `src/application/detection_initializer.py`

## 8. 总结

当前发网检测未识别到发网的可能原因：
1. **置信度阈值过高**（最可能）：`confidence_threshold: 0.65` 可能太高
2. **模型未正确加载**：配置中 `model_path: null`，需要确认模型文件路径
3. **头部ROI提取不准确**：头部区域可能不包含发网
4. **模型质量问题**：模型可能不适合当前场景

**建议优先尝试**：
1. 降低 `confidence_threshold` 到 0.3
2. 检查模型文件是否存在
3. 查看详细日志，确认检测过程

