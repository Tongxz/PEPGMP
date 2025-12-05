# 违规检测日志修复总结

## 问题
用户反馈：检测日志中没有看到：
1. "检测到发网违规" 的 INFO 级别日志
2. "✓ 帧 X: 已保存" 的 INFO 级别日志

## 分析结果

### ✅ 日志语句存在且级别正确

1. **"检测到发网违规" 日志**：
   - 位置1：`src/application/detection_application_service.py` 第198行（INFO级别）
   - 位置2：`src/domain/services/violation_service.py` 第326行（INFO级别）

2. **"✓ 帧 X: 已保存" 日志**：
   - 位置：`src/application/detection_loop_service.py` 第349行（INFO级别）
   - 条件：`saved_to_db=True`

### ⚠️ 发现的问题

**问题1：违规检测错误**
- 日志中显示：`检查违规规则 no_hairnet 时出错: unhashable type: 'dict'`
- 原因：`_get_metadata(obj, {})` 调用错误，传递了 `{}` 作为 `key` 参数，而不是 `None`
- 位置：`src/domain/services/violation_service.py` 第286行

**问题2：保存策略**
- "✓ 帧 X: 已保存" 日志只有在 `saved_to_db=True` 时才会输出
- `saved_to_db` 取决于 `_should_save_detection` 方法的返回值
- 保存策略：`SMART`（默认）
  - 违规且严重程度 >= 0.5：保存
  - 每300帧保存一次正常样本（用于基线对比和模型训练）

## 修复内容

### 修复1: `_get_metadata` 方法 ✅

**文件**：`src/domain/services/violation_service.py`

**修改位置**：第173行

**修改内容**：
```python
# 修改前
def _get_metadata(self, obj: Any, key: str, default: Any = None) -> Any:
    """获取元数据（兼容字典格式和对象格式）"""
    if isinstance(obj, dict):
        metadata = obj.get("metadata", {})
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default
    return obj.get_metadata(key, default)

# 修改后
def _get_metadata(self, obj: Any, key: Optional[str] = None, default: Any = None) -> Any:
    """获取元数据（兼容字典格式和对象格式）

    Args:
        obj: 对象（字典或对象）
        key: 元数据键（如果为None，返回整个metadata字典）
        default: 默认值

    Returns:
        元数据值或整个metadata字典
    """
    if isinstance(obj, dict):
        metadata = obj.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        if key is None:
            return metadata
        return metadata.get(key, default)
    if key is None:
        return obj.metadata if hasattr(obj, "metadata") else {}
    return obj.get_metadata(key, default) if hasattr(obj, "get_metadata") else default
```

### 修复2: `_check_no_hairnet` 方法调用 ✅

**文件**：`src/domain/services/violation_service.py`

**修改位置**：第286行

**修改内容**：
```python
# 修改前
metadata = self._get_metadata(obj, {})

# 修改后
metadata = self._get_metadata(obj)  # 获取整个metadata字典
if not isinstance(metadata, dict):
    metadata = {}
```

## 修复后的预期效果

### 1. 违规检测日志

修复后，如果检测到违规，应该能看到：

**来自 `detection_application_service.py`**：
```
检测到发网违规: has_hairnet=False, hairnet_confidence=0.65, person_confidence=0.78
```

**来自 `violation_service.py`**（如果使用了领域服务）：
```
检测到发网违规: camera_id=vid1, track_id=1, has_hairnet=False, hairnet_confidence=0.65, detection_confidence=0.78
```

### 2. 保存日志

修复后，如果满足保存条件，应该能看到：
```
✓ 帧 123: 已保存 (violation_detected), 违规=True, 严重程度=0.80, detection_id=xxx
```

或：
```
✓ 帧 300: 已保存 (normal_sample), 违规=False, 严重程度=0.00, detection_id=xxx
```

## 验证步骤

1. **重启检测进程**（必须，因为修复了代码错误）

2. **检查违规检测日志**：
   ```bash
   tail -f logs/detect_vid1.log | grep -E "检测到发网违规|检查违规规则.*出错"
   ```

3. **检查保存日志**：
   ```bash
   tail -f logs/detect_vid1.log | grep -E "✓.*帧.*已保存|保存检测记录"
   ```

4. **检查保存策略**：
   ```bash
   tail -f logs/detect_vid1.log | grep -E "智能保存策略|should_save|保存策略"
   ```

## 可能的原因（如果修复后仍没有日志）

### 1. 没有触发违规检测

**原因**：
- 所有人都有发网（`has_hairnet=True`）
- 或者发网检测结果不明确且置信度不足

**检查方法**：
```bash
tail -f logs/detect_vid1.log | grep -E "has_hairnet|发网检测结果"
```

### 2. 保存策略没有触发

**原因**：
- 没有违规且帧数不是300的倍数
- 或者违规严重程度 < 0.5

**检查方法**：
```bash
tail -f logs/detect_vid1.log | grep -E "智能保存策略|保存策略|should_save"
```

**当前保存策略**：
- 策略：`SMART`
- 违规阈值：0.5
- 正常样本间隔：300帧

### 3. 日志级别问题

**检查**：确认日志级别配置为 INFO 或更低

## 相关文件

- `src/domain/services/violation_service.py` - 违规检测领域服务（已修复）
- `src/application/detection_application_service.py` - 应用层违规检测（日志正常）
- `src/application/detection_loop_service.py` - 检测循环服务（日志正常）

## 总结

修复了违规检测中的 `unhashable type: 'dict'` 错误，这个错误阻止了违规检测的正常执行。修复后，违规检测应该能正常工作，日志也会正常输出。

**重要**：必须重启检测进程才能应用修复！
