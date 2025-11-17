# 检测准确度提升方案

## 🔍 问题分析

用户反馈视频流中识别准确度不高。经过分析，发现以下问题：

### 1. 人体检测置信度阈值过低

**当前配置**:
- 人体检测置信度阈值: `0.4`
- 这个阈值相对较低，可能检测到很多低置信度的人体
- 导致后续的发网、行为检测也不准确

### 2. 可视化时没有过滤低置信度检测

**问题**:
- `_create_annotated_image()` 方法显示所有检测结果
- 包括低置信度的检测（如 0.4-0.5）
- 用户看到的是所有检测，包括不准确的

### 3. 没有后处理置信度过滤

**问题**:
- 虽然检测器内部有过滤逻辑（面积、宽高比等）
- 但在可视化时没有进一步过滤低置信度的检测
- 所有检测结果都被绘制在视频流上

### 4. 发网和行为检测的阈值可能需要调整

**当前配置**:
- 发网检测置信度阈值: `0.6`
- 行为识别置信度阈值: `0.6`
- 这些阈值可能也需要根据实际情况调整

## ✅ 解决方案

### 方案1: 在可视化时添加置信度过滤（推荐）⭐

**修改文件**: `src/core/optimized_detection_pipeline.py`

**修改内容**:
```python
def _create_annotated_image(
    self,
    image: np.ndarray,
    person_detections: List[Dict],
    hairnet_results: List[Dict],
    handwash_results: List[Dict],
    sanitize_results: List[Dict],
    min_confidence: float = 0.5,  # 新增：最小置信度阈值
) -> np.ndarray:
    """创建带注释的结果图像"""
    annotated = image.copy()

    try:
        # 过滤低置信度的人体检测
        filtered_person_detections = [
            det for det in person_detections
            if det.get("confidence", 0.0) >= min_confidence
        ]
        
        # 绘制人体检测框
        for detection in filtered_person_detections:
            # ... 绘制逻辑 ...
        
        # 过滤低置信度的发网检测
        filtered_hairnet_results = [
            result for result in hairnet_results
            if result.get("hairnet_confidence", 0.0) >= min_confidence
        ]
        
        # 绘制发网检测结果
        for result in filtered_hairnet_results:
            # ... 绘制逻辑 ...
        
        # 过滤低置信度的行为检测
        filtered_handwash_results = [
            result for result in handwash_results
            if result.get("confidence", 0.0) >= min_confidence
        ]
        
        # 绘制洗手检测结果
        for result in filtered_handwash_results:
            # ... 绘制逻辑 ...
        
        # 过滤低置信度的消毒检测
        filtered_sanitize_results = [
            result for result in sanitize_results
            if result.get("confidence", 0.0) >= min_confidence
        ]
        
        # 绘制消毒检测结果
        for result in filtered_sanitize_results:
            # ... 绘制逻辑 ...
    except Exception as e:
        logger.error(f"绘制检测框失败: {e}", exc_info=True)
    
    return annotated
```

### 方案2: 提高人体检测置信度阈值

**修改文件**: `config/unified_params.yaml`

**修改内容**:
```yaml
human_detection:
  confidence_threshold: 0.5  # 从 0.4 提高到 0.5
  min_box_area: 1500  # 从 1000 提高到 1500（过滤小目标）
  min_height: 80  # 从 60 提高到 80（过滤过小的人体）
  min_width: 50  # 从 40 提高到 50（过滤过窄的人体）
```

### 方案3: 添加配置参数控制可视化过滤

**修改文件**: `src/config/unified_params.py`

**修改内容**:
```python
@dataclass
class SystemParams:
    """系统级参数配置"""
    
    # 可视化配置
    visualization_min_confidence: float = 0.5  # 可视化最小置信度阈值
    show_low_confidence_detections: bool = False  # 是否显示低置信度检测
```

### 方案4: 使用不同的置信度阈值

**建议配置**:
- **人体检测**: `0.5` (从 0.4 提高)
- **发网检测**: `0.65` (从 0.6 提高)
- **行为识别**: `0.65` (从 0.6 提高)
- **可视化过滤**: `0.5` (新增)

## 🎯 实施步骤

### 步骤1: 在可视化时添加置信度过滤

1. 修改 `_create_annotated_image()` 方法
2. 添加 `min_confidence` 参数
3. 过滤低置信度的检测结果

### 步骤2: 提高检测置信度阈值

1. 修改 `config/unified_params.yaml`
2. 提高人体检测置信度阈值
3. 提高最小框面积和尺寸要求

### 步骤3: 添加配置参数

1. 添加可视化配置参数
2. 允许用户自定义可视化过滤阈值
3. 提供配置接口

### 步骤4: 测试和验证

1. 测试不同置信度阈值的效果
2. 验证准确度提升
3. 调整阈值直到满意

## 📝 配置优化建议

### 推荐配置（平衡准确度和召回率）

```yaml
human_detection:
  confidence_threshold: 0.5  # 提高准确度
  min_box_area: 1500  # 过滤小目标
  min_height: 80  # 过滤过小的人体
  min_width: 50  # 过滤过窄的人体

hairnet_detection:
  confidence_threshold: 0.65  # 提高准确度
  total_score_threshold: 0.85  # 提高综合得分阈值

behavior_recognition:
  confidence_threshold: 0.65  # 提高准确度
  handwashing_stability_frames: 3  # 提高稳定性要求
  sanitizing_stability_frames: 3  # 提高稳定性要求
```

### 高准确度配置（优先准确度）

```yaml
human_detection:
  confidence_threshold: 0.6  # 更高准确度
  min_box_area: 2000  # 更大的最小框面积
  min_height: 100  # 更大的最小高度
  min_width: 60  # 更大的最小宽度

hairnet_detection:
  confidence_threshold: 0.7  # 更高准确度
  total_score_threshold: 0.9  # 更高的综合得分阈值

behavior_recognition:
  confidence_threshold: 0.7  # 更高准确度
  handwashing_stability_frames: 5  # 更高的稳定性要求
  sanitizing_stability_frames: 5  # 更高的稳定性要求
```

## 🔍 验证方法

### 1. 检查当前配置

```bash
python -c "
from src.config.unified_params import get_unified_params
params = get_unified_params()
print(f'人体检测置信度阈值: {params.human_detection.confidence_threshold}')
print(f'发网检测置信度阈值: {params.hairnet_detection.confidence_threshold}')
print(f'行为识别置信度阈值: {params.behavior_recognition.confidence_threshold}')
"
```

### 2. 测试不同阈值

1. 修改配置文件
2. 重启服务
3. 观察视频流中的检测结果
4. 调整阈值直到满意

### 3. 检查检测日志

```bash
# 查看检测日志
grep "YOLO检测完成" logs/*.log | tail -20

# 查看过滤的检测框数量
grep "检测框被过滤" logs/*.log | tail -20
```

## ✅ 预期效果

### 修复前

- ❌ 视频流中显示很多低置信度的检测（0.4-0.5）
- ❌ 检测准确度不高
- ❌ 误检较多

### 修复后

- ✅ 视频流中只显示高置信度的检测（≥0.5）
- ✅ 检测准确度提高
- ✅ 误检减少

## 📚 相关文档

- [检测配置说明](./DETECTION_CONFIG.md)
- [检测管道优化](./OPTIMIZATION_CHANGELOG.md)
- [系统架构](./SYSTEM_ARCHITECTURE.md)

