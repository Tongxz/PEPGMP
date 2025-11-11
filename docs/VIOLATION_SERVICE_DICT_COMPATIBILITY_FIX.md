# ViolationService 字典兼容性修复

## 问题描述

后端日志中出现了大量错误：

```
ERROR:src.domain.services.violation_service:检查违规规则 no_safety_helmet 时出错: 'dict' object has no attribute 'is_person'
ERROR:src.domain.services.violation_service:检查违规规则 no_safety_vest 时出错: 'dict' object has no attribute 'is_person'
ERROR:src.domain.services.violation_service:检查违规规则 crowding 时出错: 'dict' object has no attribute 'is_person'
ERROR:src.domain.services.violation_service:检查违规规则 speeding 时出错: 'dict' object has no attribute 'track_id'
```

## 根本原因

`ViolationService` 在检查违规规则时，假设 `DetectionRecord.objects` 中的每个对象都是 `DetectedObject` 实例。但实际上，当从数据库读取数据时，`objects` 字段（JSONB）中的对象是字典格式，而不是 `DetectedObject` 实例。

这是因为：
1. 数据从 PostgreSQL 的 JSONB 字段读取时，会被反序列化为字典
2. `ViolationService` 直接访问了对象的属性（如 `obj.is_person`、`obj.track_id`），但字典没有这些属性

## 解决方案

### 1. 添加兼容性辅助方法

在 `ViolationService` 类中添加了以下辅助方法，用于兼容字典格式和对象格式：

- `_is_person(obj)`: 检查对象是否是人体
- `_get_confidence_value(obj)`: 获取置信度值
- `_get_track_id(obj)`: 获取跟踪ID
- `_get_bbox(obj)`: 获取边界框
- `_get_center(obj)`: 获取边界框中心点
- `_get_area(obj)`: 获取边界框面积
- `_get_class_name(obj)`: 获取类别名称
- `_to_detected_object(obj)`: 将对象转换为 `DetectedObject` 实例
- `_get_metadata(obj, key, default)`: 获取元数据

### 2. 修改违规检查方法

所有违规检查方法都已更新，使用新的辅助方法：

- `_check_no_safety_helmet`: 检查未戴安全帽违规
- `_check_no_safety_vest`: 检查未穿安全背心违规
- `_check_unauthorized_access`: 检查未授权进入违规
- `_check_crowding`: 检查人员聚集违规
- `_check_speeding`: 检查超速违规

### 3. 修改辅助方法

- `_has_object_nearby`: 更新为兼容字典格式和对象格式
- `_is_in_restricted_area`: 更新为兼容字典格式和对象格式

## 代码变更

### 文件

`src/domain/services/violation_service.py`

### 主要变更

1. **添加类型导入**：
   ```python
   from typing import Any, Dict, List, Optional, Tuple
   ```

2. **添加兼容性辅助方法**（在 `__init__` 之后）：
   ```python
   def _is_person(self, obj: Any) -> bool:
       """检查对象是否是人体（兼容字典格式和对象格式）"""
       if isinstance(obj, dict):
           class_name = obj.get("class_name", "").lower()
           return class_name in ["person", "人", "human"]
       return obj.is_person

   # ... 其他辅助方法
   ```

3. **更新违规检查方法**：
   ```python
   def _check_no_safety_helmet(self, record: DetectionRecord, rule_config: Dict[str, Any]) -> List[Violation]:
       violations = []
       for obj in record.objects:
           if not self._is_person(obj):  # 使用辅助方法
               continue
           conf_value = self._get_confidence_value(obj)  # 使用辅助方法
           # ... 其他逻辑
   ```

4. **更新辅助方法签名**：
   ```python
   def _has_object_nearby(
       self,
       objects: List[Any],  # 从 List[DetectedObject] 改为 List[Any]
       target_obj: Any,     # 从 DetectedObject 改为 Any
       object_classes: List[str],
       max_distance: float,
   ) -> bool:
   ```

## 兼容性处理逻辑

### 字典格式对象

当对象是字典时：
- `class_name`: 从 `obj.get("class_name")` 获取
- `confidence`: 从 `obj.get("confidence")` 获取，可能是 `{"value": 0.8}` 或 `0.8`
- `track_id`: 从 `obj.get("track_id")` 获取
- `bbox`: 从 `obj.get("bbox")` 获取，可能是字典或列表格式
- `metadata`: 从 `obj.get("metadata", {})` 获取

### 对象格式对象

当对象是 `DetectedObject` 实例时：
- 直接使用对象的属性（如 `obj.is_person`、`obj.confidence.value` 等）

### 转换逻辑

在需要创建 `Violation` 对象时，使用 `_to_detected_object()` 方法将字典转换为 `DetectedObject` 实例，确保：
- `confidence` 字段正确解析（字典 `{"value": 0.8}` 或数值 `0.8`）
- `bbox` 字段正确解析（字典、列表或 `BoundingBox` 实例）
- 必需的字段存在（`class_id`、`class_name`）

## 测试验证

修复后，以下违规检查规则应该能够正常工作：

1. ✅ `no_safety_helmet`: 检查未戴安全帽
2. ✅ `no_safety_vest`: 检查未穿安全背心
3. ✅ `unauthorized_access`: 检查未授权进入
4. ✅ `crowding`: 检查人员聚集
5. ✅ `speeding`: 检查超速

## 相关修复

此修复与以下之前的修复类似：
- `DetectionRecord` 实体的字典兼容性（`person_count`、`vehicle_count` 等属性）
- `DetectionServiceDomain` 的字典兼容性（`get_event_history`、`get_daily_statistics` 等方法）

所有这些修复都是为了解决同一个根本问题：**从数据库读取的 JSONB 数据是字典格式，而不是领域对象实例**。

## 注意事项

1. **性能影响**: 每次检查违规时都需要进行类型判断和格式转换，但对性能影响很小。

2. **数据完整性**: 确保数据库中的 JSONB 数据格式正确，包含必需的字段（`class_name`、`confidence`、`bbox` 等）。

3. **向后兼容**: 此修复保持了向后兼容性，既支持字典格式，也支持对象格式。

## 后续优化建议

1. **数据标准化**: 考虑在数据读取时统一转换为领域对象，而不是在使用时转换。

2. **缓存转换**: 对于频繁访问的对象，可以考虑缓存转换结果。

3. **类型提示**: 虽然使用了 `Any` 类型，但可以考虑使用 `Union[DetectedObject, Dict[str, Any]]` 来提供更明确的类型提示。

---

**修复日期**: 2024-11-05
**修复文件**: `src/domain/services/violation_service.py`
**影响范围**: 所有违规检测规则
