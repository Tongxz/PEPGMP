# 检测性能优化：ROI区域检测

## 🔍 问题分析

### 当前实现问题

经过代码审查，发现**发网检测**和**姿态检测**都在**全帧图像**上运行，存在明显的性能浪费：

#### 1. 发网检测 (`YOLOHairnetDetector`)

**当前实现**：
```python
# src/detection/yolo_hairnet_detector.py:151
results = self.model(image, conf=conf, iou=iou, verbose=False)
```

- 传入的是**完整的全帧图像**
- 即使已经有人体检测结果，仍然在全帧上运行YOLO模型
- 计算量：`W × H × 3` 像素（全帧）

**问题影响**：
- 处理大量无关背景区域
- 计算资源浪费
- 推理速度慢

#### 2. 姿态检测 (`YOLOv8PoseDetector`)

**当前实现**：
```python
# src/detection/pose_detector.py:205
results = self.model(image, conf=..., iou=..., verbose=False)
```

- 传入的是**完整的全帧图像**
- 即使已经有人体检测结果，仍然在全帧上运行姿态检测模型
- 计算量：`W × H × 3` 像素（全帧）

**问题影响**：
- 处理大量无关背景区域
- 计算资源浪费
- 推理速度慢

### 性能浪费估算

假设：
- 图像尺寸：1920×1080 (Full HD)
- 检测到3个人，平均人体框大小：400×600
- 头部区域大小：400×180 (人体高度的30%)

**当前方式**：
- 发网检测：1920×1080 = **2,073,600 像素**
- 姿态检测：1920×1080 = **2,073,600 像素**
- **总计：4,147,200 像素**

**优化后（ROI检测）**：
- 发网检测：3 × (400×180) = **216,000 像素** (减少 **89.6%**)
- 姿态检测：3 × (400×600) = **720,000 像素** (减少 **65.3%**)
- **总计：936,000 像素** (减少 **77.4%**)

**性能提升预期**：
- 发网检测速度：提升 **5-10倍**
- 姿态检测速度：提升 **2-3倍**
- 总体检测速度：提升 **3-5倍**

---

## 🎯 优化方案

### 方案1：发网检测ROI优化

#### 1.1 实现头部区域裁剪检测

**改进点**：
- 只对每个人员的头部区域进行发网检测
- 裁剪头部ROI后，resize到模型输入尺寸
- 将检测结果坐标映射回原图坐标系

**实现位置**：
- `src/detection/yolo_hairnet_detector.py` - `detect_hairnet_compliance` 方法
- 新增 `_detect_hairnet_in_roi` 方法

**代码改进**：

```python
def detect_hairnet_compliance(
    self,
    image: Union[str, np.ndarray],
    human_detections: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    优化的发网检测：只检测头部ROI区域
    """
    # ... 现有的人体检测逻辑 ...
    
    if not human_detections:
        return self._create_error_result("未检测到人体")
    
    # 确保图像是numpy数组
    if isinstance(image, str):
        image_array = cv2.imread(image)
    else:
        image_array = image
    
    compliance_detections = []
    persons_with_hairnet = 0
    persons_without_hairnet = 0
    
    # 对每个人进行头部ROI检测
    for i, human_det in enumerate(human_detections):
        human_bbox = human_det.get("bbox", [0, 0, 0, 0])
        human_confidence = human_det.get("confidence", 0.0)
        
        # 提取头部区域
        head_bbox = self._get_head_bbox(human_bbox)
        x1, y1, x2, y2 = map(int, head_bbox)
        
        # 裁剪头部ROI
        head_roi = image_array[y1:y2, x1:x2]
        if head_roi.size == 0:
            # 头部区域无效，跳过
            compliance_detections.append({
                "bbox": human_bbox,
                "has_hairnet": None,
                "confidence": human_confidence,
                "hairnet_confidence": 0.0,
            })
            continue
        
        # 在头部ROI上运行发网检测
        hairnet_result = self._detect_hairnet_in_roi(head_roi, head_bbox)
        
        has_hairnet = hairnet_result.get("has_hairnet")
        hairnet_confidence = hairnet_result.get("confidence", 0.0)
        hairnet_bbox = hairnet_result.get("bbox", head_bbox)
        
        if has_hairnet is True:
            persons_with_hairnet += 1
        elif has_hairnet is False:
            persons_without_hairnet += 1
        
        compliance_detections.append({
            "bbox": human_bbox,
            "has_hairnet": has_hairnet,
            "confidence": human_confidence,
            "hairnet_confidence": hairnet_confidence,
            "hairnet_bbox": hairnet_bbox,
        })
    
    # ... 返回结果 ...
    
def _detect_hairnet_in_roi(
    self,
    head_roi: np.ndarray,
    head_bbox: List[float]
) -> Dict[str, Any]:
    """
    在头部ROI区域进行发网检测
    
    Args:
        head_roi: 头部区域图像
        head_bbox: 头部区域在原图中的坐标 [x1, y1, x2, y2]
    
    Returns:
        检测结果字典
    """
    # 运行YOLO检测（在裁剪后的ROI上）
    results = self.model(head_roi, conf=self.conf_thres, iou=self.iou_thres, verbose=False)
    
    has_hairnet = None
    hairnet_confidence = 0.0
    best_bbox = None
    
    for r in results:
        if r.boxes is None:
            continue
        
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # 检查是否是发网类别
            if cls_id == 0:  # 假设0是hairnet类别，需要根据实际模型调整
                if conf > hairnet_confidence:
                    hairnet_confidence = conf
                    # 获取边界框（ROI坐标系）
                    bbox_roi = box.xyxy[0].cpu().numpy().astype(int)
                    # 映射回原图坐标系
                    x1_orig, y1_orig = int(head_bbox[0]), int(head_bbox[1])
                    best_bbox = [
                        bbox_roi[0] + x1_orig,
                        bbox_roi[1] + y1_orig,
                        bbox_roi[2] + x1_orig,
                        bbox_roi[3] + y1_orig,
                    ]
    
    # 判定逻辑
    if hairnet_confidence > self.conf_thres:
        has_hairnet = True
    elif hairnet_confidence > 0.3:  # 低置信度阈值
        has_hairnet = False
    else:
        has_hairnet = None  # 不明确
    
    return {
        "has_hairnet": has_hairnet,
        "confidence": hairnet_confidence,
        "bbox": best_bbox if best_bbox else head_bbox,
    }

def _get_head_bbox(self, person_bbox: List[float]) -> List[float]:
    """
    根据人体框计算头部区域
    
    Args:
        person_bbox: 人体边界框 [x1, y1, x2, y2]
    
    Returns:
        头部边界框 [x1, y1, x2, y2]
    """
    x1, y1, x2, y2 = person_bbox
    person_height = y2 - y1
    head_height = int(person_height * 0.3)  # 头部占人体高度的30%
    
    return [x1, y1, x2, y1 + head_height]
```

#### 1.2 批量ROI检测优化

**改进点**：
- 将多个头部ROI合并为一张图像进行批量推理
- 利用GPU并行计算
- 进一步减少模型加载和推理开销

**代码改进**：

```python
def _batch_detect_hairnets_in_rois(
    self,
    head_rois: List[np.ndarray],
    head_bboxes: List[List[float]],
    target_size: Tuple[int, int] = (224, 224)
) -> List[Dict[str, Any]]:
    """
    批量检测多个头部ROI
    
    Args:
        head_rois: 头部区域图像列表
        head_bboxes: 头部区域在原图中的坐标列表
        target_size: 目标尺寸（模型输入尺寸）
    
    Returns:
        检测结果列表
    """
    if not head_rois:
        return []
    
    # 将ROI resize到统一尺寸
    resized_rois = []
    for roi in head_rois:
        resized = cv2.resize(roi, target_size)
        resized_rois.append(resized)
    
    # 合并为批量图像（如果模型支持批量推理）
    # 注意：YOLO模型通常支持批量推理
    batch_images = np.stack(resized_rois) if len(resized_rois) > 1 else resized_rois[0]
    
    # 批量推理
    results = self.model(batch_images, conf=self.conf_thres, iou=self.iou_thres, verbose=False)
    
    # 处理结果并映射回原图坐标
    detection_results = []
    for i, (result, head_bbox) in enumerate(zip(results, head_bboxes)):
        # ... 处理单个结果 ...
        detection_results.append(self._process_single_result(result, head_bbox, target_size))
    
    return detection_results
```

---

### 方案2：姿态检测ROI优化

#### 2.1 实现人体区域裁剪检测

**改进点**：
- 只对每个人员的人体区域进行姿态检测
- 裁剪人体ROI后，resize到模型输入尺寸
- 将关键点坐标映射回原图坐标系

**实现位置**：
- `src/detection/pose_detector.py` - `YOLOv8PoseDetector.detect` 方法
- 新增 `detect_in_rois` 方法

**代码改进**：

```python
def detect_in_rois(
    self,
    image: np.ndarray,
    person_bboxes: List[List[float]]
) -> List[Dict[str, Any]]:
    """
    在指定的人体ROI区域进行姿态检测
    
    Args:
        image: 完整图像
        person_bboxes: 人体边界框列表 [x1, y1, x2, y2]
    
    Returns:
        检测结果列表，每个结果包含关键点信息
    """
    if self.model is None:
        raise RuntimeError("YOLOv8姿态模型未正确加载")
    
    all_detections = []
    
    # 对每个人体ROI进行检测
    for person_bbox in person_bboxes:
        x1, y1, x2, y2 = map(int, person_bbox)
        
        # 外扩20%边距（确保关键点不被裁剪）
        w = x2 - x1
        h = y2 - y1
        pad_x = int(0.2 * w)
        pad_y = int(0.2 * h)
        
        x1_pad = max(0, x1 - pad_x)
        y1_pad = max(0, y1 - pad_y)
        x2_pad = min(image.shape[1], x2 + pad_x)
        y2_pad = min(image.shape[0], y2 + pad_y)
        
        # 裁剪ROI
        person_roi = image[y1_pad:y2_pad, x1_pad:x2_pad]
        if person_roi.size == 0:
            continue
        
        # 在ROI上运行姿态检测
        results = self.model(
            person_roi,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False
        )
        
        # 处理结果并映射回原图坐标
        for result in results:
            if result.boxes is None or result.keypoints is None:
                continue
            
            for box, keypoints in zip(result.boxes, result.keypoints):
                if int(box.cls[0]) != 0:  # 只处理person类别
                    continue
                
                # 获取ROI坐标系下的边界框和关键点
                bbox_roi = box.xyxy[0].cpu().numpy().astype(int)
                kpts_xy_roi = keypoints.xy[0].cpu().numpy()
                kpts_conf = (
                    keypoints.conf[0].cpu().numpy()
                    if keypoints.conf is not None
                    else np.ones(len(kpts_xy_roi))
                )
                
                # 映射回原图坐标
                bbox_orig = [
                    bbox_roi[0] + x1_pad,
                    bbox_roi[1] + y1_pad,
                    bbox_roi[2] + x1_pad,
                    bbox_roi[3] + y1_pad,
                ]
                
                kpts_xy_orig = kpts_xy_roi.copy()
                kpts_xy_orig[:, 0] += x1_pad  # x坐标
                kpts_xy_orig[:, 1] += y1_pad  # y坐标
                
                detection = {
                    "bbox": bbox_orig,
                    "confidence": float(box.conf[0]),
                    "keypoints": {
                        "xy": kpts_xy_orig,
                        "conf": kpts_conf,
                    },
                    "class_id": 0,
                    "class_name": "person",
                }
                all_detections.append(detection)
    
    return all_detections
```

#### 2.2 在检测管道中集成ROI检测

**实现位置**：
- `src/core/optimized_detection_pipeline.py` - `_execute_detection_pipeline` 方法

**代码改进**：

```python
def _execute_detection_pipeline(
    self,
    image: np.ndarray,
    enable_hairnet: bool,
    enable_handwash: bool,
    enable_sanitize: bool,
) -> DetectionResult:
    # ... 人体检测 ...
    person_detections = self._detect_persons(image)
    
    # 提取人体边界框列表
    person_bboxes = [det.get("bbox", [0, 0, 0, 0]) for det in person_detections]
    
    # 阶段2: 发网检测（ROI优化）
    hairnet_results = []
    if enable_hairnet and len(person_detections) > 0:
        hairnet_start = time.time()
        # 使用ROI检测
        if hasattr(self.hairnet_detector, "detect_hairnet_compliance"):
            # 优化：只检测头部ROI
            compliance_result = self.hairnet_detector.detect_hairnet_compliance(
                image, person_detections
            )
            # ... 处理结果 ...
        processing_times["hairnet_detection"] = time.time() - hairnet_start
    
    # 阶段3: 姿态检测（ROI优化）
    pose_detections = []
    if self.pose_detector is not None and len(person_bboxes) > 0:
        pose_start = time.time()
        # 使用ROI检测
        if hasattr(self.pose_detector, "detect_in_rois"):
            pose_detections = self.pose_detector.detect_in_rois(image, person_bboxes)
        else:
            # 回退到全帧检测
            pose_detections = self.pose_detector.detect(image)
        processing_times["pose_detection"] = time.time() - pose_start
    
    # 阶段4: 行为检测（使用姿态检测结果）
    # ... 后续逻辑 ...
```

---

## 📊 性能优化效果预期

### 计算量减少

| 检测类型 | 当前方式 | 优化后 | 减少比例 |
|---------|---------|--------|---------|
| 发网检测 | 全帧 (1920×1080) | 头部ROI (3×400×180) | **89.6%** |
| 姿态检测 | 全帧 (1920×1080) | 人体ROI (3×400×600) | **65.3%** |
| **总计** | **4,147,200 像素** | **936,000 像素** | **77.4%** |

### 速度提升

| 检测类型 | 当前速度 (FPS) | 优化后 (FPS) | 提升倍数 |
|---------|---------------|-------------|---------|
| 发网检测 | ~10 | ~50-100 | **5-10倍** |
| 姿态检测 | ~15 | ~30-45 | **2-3倍** |
| **总体** | **~8** | **~25-40** | **3-5倍** |

### 内存使用减少

- 模型推理内存：减少 **60-80%**
- 图像缓存内存：减少 **70-90%**

---

## ⚠️ 注意事项

### 1. 坐标映射准确性

- **关键点坐标映射**：必须准确映射回原图坐标系
- **边界框映射**：需要考虑padding的影响
- **测试验证**：确保映射后的坐标与原图坐标一致

### 2. ROI裁剪边界处理

- **边界检查**：确保ROI坐标在图像范围内
- **Padding处理**：姿态检测需要外扩边距，避免关键点被裁剪
- **空ROI处理**：检查ROI是否有效（size > 0）

### 3. 模型输入尺寸

- **Resize策略**：ROI裁剪后需要resize到模型输入尺寸
- **长宽比保持**：考虑是否保持长宽比（可能影响检测准确率）
- **批量推理**：如果使用批量推理，需要统一ROI尺寸

### 4. 兼容性处理

- **向后兼容**：保留全帧检测作为回退方案
- **配置开关**：添加配置项控制是否启用ROI检测
- **渐进式部署**：可以先在测试环境验证，再逐步推广

---

## 🚀 实施步骤

### 阶段1：发网检测ROI优化（1-2天）

1. 修改 `YOLOHairnetDetector.detect_hairnet_compliance`
2. 实现 `_detect_hairnet_in_roi` 方法
3. 实现 `_get_head_bbox` 方法
4. 单元测试和集成测试
5. 性能基准测试

### 阶段2：姿态检测ROI优化（1-2天）

1. 修改 `YOLOv8PoseDetector.detect`
2. 实现 `detect_in_rois` 方法
3. 在 `OptimizedDetectionPipeline` 中集成
4. 单元测试和集成测试
5. 性能基准测试

### 阶段3：批量优化（可选，1天）

1. 实现批量ROI检测
2. 优化内存使用
3. 性能调优

### 阶段4：配置和文档（0.5天）

1. 添加配置项
2. 更新文档
3. 性能报告

---

## 📝 配置参数

### 新增配置项

```yaml
performance:
  # ROI检测优化
  use_roi_detection: true  # 是否启用ROI检测
  hairnet_roi_detection: true  # 发网检测是否使用ROI
  pose_roi_detection: true  # 姿态检测是否使用ROI
  
  # ROI参数
  head_region_ratio: 0.3  # 头部区域占人体高度的比例
  pose_padding_ratio: 0.2  # 姿态检测ROI外扩比例
  
  # 批量检测
  batch_roi_detection: false  # 是否启用批量ROI检测
  max_batch_size: 8  # 最大批量大小
```

---

## 📚 相关文档

- `docs/DETECTION_LOGIC_OPTIMIZATION_PLAN.md` - 检测逻辑优化计划
- `docs/DETECTION_MODELS_INVENTORY.md` - 检测模型清单
- `src/detection/yolo_hairnet_detector.py` - 发网检测器实现
- `src/detection/pose_detector.py` - 姿态检测器实现

