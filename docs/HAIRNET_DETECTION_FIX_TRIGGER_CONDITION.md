# 发网检测扩展ROI和全图检测触发条件修复

## 🔍 问题分析

用户反馈：没有看到"尝试扩展ROI检测"或"全图检测作为备用策略"的日志。

### 原因分析

1. **扩展ROI检测触发条件过于严格**：
   - 原逻辑：只在 `all_classes_found` 为空时触发（即完全没有检测到任何目标）
   - 问题：如果检测到了其他类别（如head或person），但没有检测到hairnet，就不会触发扩展ROI检测

2. **全图检测备用策略触发条件过于严格**：
   - 原逻辑：`persons_with_hairnet == 0` 且 `persons_without_hairnet == 0`
   - 问题：如果某些人被标记为未佩戴（`persons_without_hairnet > 0`），就不会触发全图检测

## ✅ 修复方案

### 1. 扩展ROI检测触发条件

**修改前**：
```python
if not all_classes_found:  # 只在完全没有检测到任何目标时触发
    # 扩展ROI检测
```

**修改后**：
```python
# 无论是否检测到其他类别，只要没有检测到发网，就尝试扩展ROI
if has_hairnet is None or has_hairnet is False:
    # 扩展ROI检测
```

### 2. 全图检测备用策略触发条件

**修改前**：
```python
if result.get("persons_with_hairnet", 0) == 0 and result.get("persons_without_hairnet", 0) == 0:
    # 全图检测
```

**修改后**：
```python
# 只要没有检测到任何人佩戴发网，就尝试全图检测
if result.get("persons_with_hairnet", 0) == 0:
    # 全图检测
```

## 📝 修改位置

### `src/detection/yolo_hairnet_detector.py`

1. **单个ROI检测**（第720-774行）：
   - 修改扩展ROI检测触发条件：从 `if not all_classes_found` 改为 `if has_hairnet is None or has_hairnet is False`

2. **批量ROI检测**（第1086-1140行）：
   - 修改扩展ROI检测触发条件：从 `if boxes is None or num_boxes == 0` 改为 `if has_hairnet is None or has_hairnet is False`
   - 将扩展ROI检测逻辑移到处理完所有检测结果之后

3. **全图检测备用策略**（第332行）：
   - 修改触发条件：从 `persons_with_hairnet == 0 and persons_without_hairnet == 0` 改为 `persons_with_hairnet == 0`

## 🎯 预期效果

修复后，应该能看到以下日志：

1. **扩展ROI检测日志**：
   ```
   尝试扩展ROI检测: track_id=1, 扩展ROI大小=(...), 原因=未检测到发网
   ```
   或
   ```
   尝试扩展ROI检测（批量）: track_id=1, 扩展ROI大小=(...), 原因=未检测到发网
   ```

2. **全图检测备用策略日志**：
   ```
   ROI检测未检测到发网，尝试全图检测作为备用策略: 人数=2, 未佩戴=0, 图像大小=(...)
   ```

## ⚠️ 重要提示

1. **需要重启服务**：修改代码后，必须重启检测服务才能生效
2. **检查日志级别**：确保日志级别设置为INFO或WARNING，才能看到这些日志
3. **如果仍然看不到日志**：
   - 检查是否有异常被捕获（查看ERROR日志）
   - 检查 `has_hairnet` 的值（可能是其他值，不是None或False）
   - 检查 `persons_with_hairnet` 的值（可能不为0）

## 🔄 验证步骤

1. **重启检测服务**
2. **运行视频检测**
3. **查看日志**，应该能看到：
   - `尝试扩展ROI检测` 或 `尝试扩展ROI检测（批量）`
   - `ROI检测未检测到发网，尝试全图检测作为备用策略`
   - `✅ 扩展ROI检测到发网`（如果扩展ROI检测成功）
   - `全图检测检测到发网，使用全图检测结果`（如果全图检测成功）

