# 发网检测问题分析报告

## 🔍 问题描述

用户反馈：发网检测模型之前单独训练过，效果是可以的也是稳定的，但是现在识别不到发网。

## 📊 诊断结果

### 1. 模型状态
- ✅ **模型文件存在**: `models/hairnet_detection/hairnet_detection.pt` (49.71 MB)
- ✅ **模型加载正常**: 可以成功加载
- ✅ **模型类别正确**: `{0: 'hairnet', 1: 'head', 2: 'person'}`
- ✅ **全图检测正常**: 在全图上可以检测到发网，置信度很高（0.839, 0.913）

### 2. ROI检测问题
- ❌ **ROI检测失败**: 在ROI上检测不到任何目标
- ✅ **ROI位置正确**: 发网中心在ROI内
- ✅ **ROI大小合理**: ROI尺寸（270x305, 262x229）足够大

### 3. 关键发现

#### 模型训练配置
- **训练图像尺寸**: `imgsz: 640` (从 `models/hairnet_model/args.yaml` 确认)
- **批次大小**: `batch: 16`

#### 当前检测配置
- **检测阈值**: `0.15` (已优化降低)
- **后处理阈值**: `min(conf_thres, 0.2)` = `0.2`
- **最低接受阈值**: `0.15`

#### 问题分析
1. **全图检测成功**：说明模型本身是正常的
2. **ROI检测失败**：说明问题在ROI处理流程
3. **可能原因**：
   - YOLO模型在推理时没有指定 `imgsz`，可能使用了默认值或自动调整
   - ROI图像经过预处理（CLAHE、锐化）后，特征可能发生变化
   - 模型在ROI上的表现不如全图（可能是训练数据的问题）

## 🔧 解决方案

### 方案1: 指定推理时的图像尺寸（推荐）

在YOLO模型推理时明确指定 `imgsz=640`，与训练时保持一致：

```python
# 当前代码
results = self.model(head_roi, conf=detection_conf, iou=iou, verbose=False)

# 修改为
results = self.model(head_roi, conf=detection_conf, iou=iou, imgsz=640, verbose=False)
```

### 方案2: 调整ROI预处理策略

如果预处理改变了图像特征，可以：
1. 减少预处理强度（降低CLAHE的clipLimit）
2. 移除锐化处理
3. 或者尝试不进行预处理，直接使用原始ROI

### 方案3: 使用全图检测作为备用策略

如果ROI检测失败，回退到全图检测：

```python
# 如果ROI检测失败，使用全图检测
if len(roi_detections) == 0:
    full_results = self.model(image, conf=detection_conf, iou=iou, imgsz=640, verbose=False)
    # 然后匹配到对应的人体检测框
```

### 方案4: 调整ROI提取策略

如果ROI位置不准确，可以：
1. 增加头部ROI比例（从35%增加到40%或45%）
2. 增加padding（从20%增加到30%）
3. 使用姿态关键点来精确定位头部

## 📝 实施建议

### 优先级1: 指定推理图像尺寸
**原因**: 这是最可能的问题，模型训练时使用640，推理时如果不指定可能使用其他尺寸。

**修改位置**: `src/detection/yolo_hairnet_detector.py`
- `_detect_hairnet_in_rois` 方法中的 `self.model(head_roi, ...)`
- `_batch_detect_hairnet_in_rois` 方法中的 `self.model(head_rois, ...)`

### 优先级2: 优化预处理策略
**原因**: 预处理可能改变图像特征，影响模型识别。

**修改位置**: `src/detection/yolo_hairnet_detector.py`
- 可以添加一个开关来控制是否使用预处理
- 或者降低预处理强度

### 优先级3: 添加备用策略
**原因**: 如果ROI检测失败，可以使用全图检测作为备用。

**修改位置**: `src/detection/yolo_hairnet_detector.py`
- 在 `_detect_hairnet_in_rois` 中添加备用逻辑

## 🧪 验证步骤

1. **修改代码后测试**：
   ```bash
   python scripts/diagnose_hairnet_roi.py
   ```

2. **检查日志**：
   - 查看是否有 `✅ 检测到发网` 日志
   - 查看检测置信度是否合理

3. **可视化检查**：
   - 查看生成的 `temp_visualization.jpg`
   - 确认ROI是否包含发网区域
   - 确认检测框是否准确

4. **实际运行测试**：
   - 启动检测服务
   - 查看视频流中的发网检测结果
   - 检查日志中的检测信息

## 📚 相关文档

- `docs/HAIRNET_DETECTION_DEBUG_GUIDE.md`: 发网检测调试指南
- `docs/HAIRNET_DETECTION_ANALYSIS.md`: 发网检测逻辑分析
- `docs/HAIRNET_DETECTION_ACCURACY_OPTIMIZATION_V2.md`: 发网检测准确率优化

