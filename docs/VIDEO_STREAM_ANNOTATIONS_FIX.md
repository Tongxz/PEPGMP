# 实时视频流检测框显示修复

## 🔍 问题描述

用户在查看检测的实时视频中没有看到识别框，希望在视频上看到检测框。

## 📊 问题分析

### 问题根源

1. **异步检测时缺少可视化图片**:
   - `OptimizedDetectionPipeline._execute_detection_pipeline_async()` 使用异步检测
   - `_frame_meta_to_detection_result()` 方法将 `annotated_image` 设置为 `None`
   - 导致视频流推送时没有检测框

2. **属性名不匹配**:
   - `DetectionResult` 的属性是 `annotated_image`
   - `DetectionLoopService` 中使用的是 `result.annotated_frame`
   - 导致无法正确获取可视化图片

3. **可视化图片创建不完整**:
   - `_create_annotated_image()` 方法绘制了检测框，但没有绘制文本标签
   - 检测框信息不够完整

## ✅ 修复方案

### 1. 修复异步检测时的可视化图片创建

**文件**: `src/core/optimized_detection_pipeline.py`

**修改内容**:
```python
def _frame_meta_to_detection_result(
    self,
    frame_meta: FrameMetadata,
    image: Optional[np.ndarray] = None,  # 新增参数：原始图像
) -> DetectionResult:
    """
    将FrameMetadata转换为DetectionResult（向后兼容）
    
    Args:
        frame_meta: 帧元数据
        image: 原始图像（用于创建可视化图片，如果frame_meta.frame为None）
    
    Returns:
        DetectionResult: 检测结果
    """
    # 计算处理时间
    processing_times = frame_meta.processing_times.copy()
    if "total" not in processing_times:
        processing_times["total"] = sum(processing_times.values())
    
    # 创建可视化图片（如果原始图像可用）
    annotated_image = None
    source_image = frame_meta.frame if frame_meta.frame is not None else image
    if source_image is not None:
        try:
            annotated_image = self._create_annotated_image(
                source_image,
                frame_meta.person_detections,
                frame_meta.hairnet_results,
                frame_meta.handwash_results,
                frame_meta.sanitize_results,
            )
        except Exception as e:
            logger.warning(f"创建可视化图片失败: {e}", exc_info=True)
    
    return DetectionResult(
        person_detections=frame_meta.person_detections,
        hairnet_results=frame_meta.hairnet_results,
        handwash_results=frame_meta.handwash_results,
        sanitize_results=frame_meta.sanitize_results,
        processing_times=processing_times,
        annotated_image=annotated_image,  # ✅ 现在包含可视化图片
        frame_cache_key=frame_meta.frame_hash,
    )
```

**调用处修改**:
```python
# 转换为DetectionResult（向后兼容）
# 传递原始图像用于创建可视化图片
return self._frame_meta_to_detection_result(frame_meta, image)
```

### 2. 修复属性名不匹配

**文件**: `src/application/detection_loop_service.py`

**修改内容**:
```python
# 判断是否有标注（使用annotated_image属性）
annotated_frame = (
    result.annotated_image  # ✅ 使用正确的属性名
    if hasattr(result, "annotated_image") and result.annotated_image is not None
    else None
)
has_annotations = annotated_frame is not None

# 使用标注后的帧（如果有）或原始帧
frame_to_push = annotated_frame if has_annotations else frame
```

### 3. 增强可视化图片的标签显示

**文件**: `src/core/optimized_detection_pipeline.py`

**修改内容**:
```python
def _create_annotated_image(
    self,
    image: np.ndarray,
    person_detections: List[Dict],
    hairnet_results: List[Dict],
    handwash_results: List[Dict],
    sanitize_results: List[Dict],
) -> np.ndarray:
    """创建带注释的结果图像"""
    annotated = image.copy()

    try:
        # 绘制人体检测框
        for detection in person_detections:
            bbox = detection.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = map(int, bbox)
            confidence = detection.get("confidence", 0.0)
            track_id = detection.get("track_id")
            
            # 绘制人体边界框（绿色）
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"Person {confidence:.2f}"
            if track_id is not None:
                label += f" ID:{track_id}"
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        # 绘制发网检测结果
        for result in hairnet_results:
            head_bbox = result.get("head_bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = map(int, head_bbox)
            has_hairnet = result.get("has_hairnet", False)
            confidence = result.get("hairnet_confidence", 0.0)
            
            # 绿色=有发网，红色=无发网
            color = (0, 255, 0) if has_hairnet else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签
            label = f"{'有发网' if has_hairnet else '无发网'} {confidence:.2f}"
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        # 绘制洗手检测结果
        for result in handwash_results:
            if result.get("is_handwashing", False):
                person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, person_bbox)
                confidence = result.get("confidence", 0.0)
                
                # 在人体框上方绘制洗手标签（黄色）
                label = f"洗手中 {confidence:.2f}"
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

        # 绘制消毒检测结果
        for result in sanitize_results:
            if result.get("is_sanitizing", False):
                person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, person_bbox)
                confidence = result.get("confidence", 0.0)
                
                # 在人体框上方绘制消毒标签（青色）
                label = f"消毒中 {confidence:.2f}"
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
        
        # ... 手部可视化代码 ...
    except Exception as e:
        logger.error(f"绘制检测框失败: {e}", exc_info=True)
    
    return annotated
```

## 🎯 修复效果

### 修复前

- ❌ 异步检测时 `annotated_image` 为 `None`
- ❌ 视频流中看不到检测框
- ❌ 检测框信息不完整（缺少标签）

### 修复后

- ✅ 异步检测时创建 `annotated_image`
- ✅ 视频流中正确显示检测框
- ✅ 检测框包含完整的标签信息（人体、发网、洗手、消毒）

## 📝 检测框颜色说明

- **绿色**: 人体检测框、有发网
- **红色**: 无发网
- **黄色**: 洗手中
- **青色**: 消毒中
- **黄色**: 手部检测框

## 🔍 验证方法

### 1. 检查检测结果

```python
# 检查DetectionResult是否包含annotated_image
result = pipeline.detect_comprehensive(image)
print('annotated_image 是否为 None:', result.annotated_image is None)
print('annotated_image 形状:', result.annotated_image.shape if result.annotated_image is not None else 'None')
```

### 2. 查看视频流

1. 启动检测服务
2. 打开前端视频流页面
3. 检查视频中是否显示检测框
4. 验证检测框标签是否正确显示

### 3. 检查日志

```bash
# 查看日志，确认是否有可视化图片
grep "has_annotations" logs/*.log
```

## ✅ 修复完成

- ✅ `_frame_meta_to_detection_result()` 方法现在创建可视化图片
- ✅ `DetectionLoopService` 使用正确的属性名 `annotated_image`
- ✅ `_create_annotated_image()` 方法增强，包含完整的标签信息
- ✅ 视频流中正确显示检测框和标签

## 📚 相关文档

- [视频流架构](./VIDEO_STREAM_ARCHITECTURE.md)
- [检测管道优化](./OPTIMIZATION_CHANGELOG.md)
- [系统架构](./SYSTEM_ARCHITECTURE.md)

