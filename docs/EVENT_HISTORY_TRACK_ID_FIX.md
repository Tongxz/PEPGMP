# 事件列表查询track_id错误修复报告

## 📅 修复日期: 2025-11-04

**问题**: `'dict' object has no attribute 'track_id'`

---

## 🔴 问题描述

```
ERROR:src.services.detection_service_domain:获取事件列表失败: 'dict' object has no attribute 'track_id'
WARNING:src.api.routers.statistics:领域服务事件列表查询失败，回退到数据库查询: 'dict' object has no attribute 'track_id'
```

### 根本原因

在`DetectionServiceDomain.get_event_history()`方法中，代码假设`record.objects`中的每个`obj`都是`DetectedObject`对象，可以直接访问`obj.track_id`、`obj.class_name`等属性。

但实际上，从数据库读取的`objects`字段是JSON格式，`_row_to_record()`方法将其解析为字典列表，而不是`DetectedObject`对象列表。

**问题代码**:
```python
for obj in record.objects:
    events.append({
        "track_id": obj.track_id,  # ❌ 错误：obj是dict，没有track_id属性
        "type": obj.class_name,    # ❌ 错误：obj是dict，没有class_name属性
    })
```

---

## ✅ 修复方案

### 修复内容

在`DetectionServiceDomain`的以下方法中添加了字典格式兼容性检查：

1. **`get_event_history()`** - 获取事件列表
2. **`get_recent_history()`** - 获取近期历史
3. **`get_recent_events()`** - 获取最近事件
4. **`get_daily_statistics()`** - 获取每日统计
5. **`get_realtime_statistics()`** - 获取实时统计

### 修复逻辑

**兼容字典格式和对象格式**:
```python
for obj in record.objects:
    # 兼容字典格式和对象格式
    if isinstance(obj, dict):
        obj_class_name = obj.get("class_name", "unknown")
        obj_confidence = obj.get("confidence", 0.0)
        obj_track_id = obj.get("track_id")
        obj_metadata = obj.get("metadata", {})
        obj_bbox = obj.get("bbox", [])
    else:
        # DetectedObject对象格式
        obj_class_name = obj.class_name
        obj_confidence = obj.confidence.value if hasattr(obj.confidence, 'value') else obj.confidence
        obj_track_id = obj.track_id
        obj_metadata = obj.metadata or {}
        obj_bbox = obj.bbox

    # 使用兼容后的变量
    events.append({
        "track_id": obj_track_id,
        "type": obj_class_name,
        "confidence": float(obj_confidence) if obj_confidence is not None else 0.0,
        "metadata": obj_metadata,
    })
```

---

## 📝 修复的文件

### 修改的文件

1. **`src/services/detection_service_domain.py`**
   - 修复`get_event_history()`方法
   - 修复`get_recent_history()`方法
   - 修复`get_recent_events()`方法
   - 修复`get_daily_statistics()`方法
   - 修复`get_realtime_statistics()`方法

---

## 🔍 修复详情

### 1. `get_event_history()`方法

**修复前**:
```python
for obj in record.objects:
    events.append({
        "id": f"{record.id}_{obj.track_id or ''}",
        "track_id": obj.track_id,
        "type": obj.class_name,
        "confidence": obj.confidence.value,
    })
```

**修复后**:
```python
for obj in record.objects:
    # 兼容字典格式和对象格式
    if isinstance(obj, dict):
        obj_class_name = obj.get("class_name", "unknown")
        obj_confidence = obj.get("confidence", 0.0)
        obj_track_id = obj.get("track_id")
        obj_metadata = obj.get("metadata", {})
    else:
        # DetectedObject对象格式
        obj_class_name = obj.class_name
        obj_confidence = obj.confidence.value if hasattr(obj.confidence, 'value') else obj.confidence
        obj_track_id = obj.track_id
        obj_metadata = obj.metadata or {}

    # 获取时间戳（兼容Timestamp对象和datetime）
    timestamp_str = record.timestamp.iso_string if hasattr(record.timestamp, 'iso_string') else record.timestamp.isoformat()

    events.append({
        "id": f"{record.id}_{obj_track_id or ''}",
        "timestamp": timestamp_str,
        "type": obj_class_name,
        "camera_id": record.camera_id,
        "confidence": float(obj_confidence) if obj_confidence is not None else 0.0,
        "track_id": obj_track_id,
        "region": record.region_id,
        "metadata": obj_metadata,
    })
```

---

### 2. `get_recent_history()`方法

**修复内容**:
- 添加字典格式兼容性检查
- 兼容时间戳格式（Timestamp对象和datetime）
- 兼容bbox格式（BoundingBox对象和列表）

---

### 3. `get_recent_events()`方法

**修复内容**:
- 添加字典格式兼容性检查
- 兼容时间戳格式
- 兼容bbox格式（BoundingBox对象和列表）
- 修复排序逻辑中的时间戳访问

---

### 4. `get_daily_statistics()`方法

**修复内容**:
- 添加字典格式兼容性检查
- 兼容`class_name`访问

---

### 5. `get_realtime_statistics()`方法

**修复内容**:
- 添加字典格式兼容性检查
- 兼容`class_name`访问

---

## 🧪 测试验证

### 测试步骤

1. **测试事件列表查询**:
   ```bash
   curl 'http://localhost:8000/api/v1/statistics/events?limit=10'
   ```

2. **验证返回格式**:
   - 检查返回的事件列表是否包含正确的字段
   - 检查`track_id`字段是否存在
   - 检查`type`字段是否正确

3. **测试不同数据格式**:
   - 测试字典格式的数据（从数据库读取）
   - 测试对象格式的数据（新创建的对象）

---

## ✅ 验证结果

### 修复前

- ❌ 查询事件列表失败：`'dict' object has no attribute 'track_id'`
- ❌ 统计API回退到数据库查询

### 修复后

- ✅ 查询事件列表成功
- ✅ 兼容字典格式和对象格式
- ✅ 时间戳、bbox等字段正确处理
- ✅ 统计API正常工作

---

## 📊 影响范围

### 修复的方法

1. `get_event_history()` - 事件列表查询
2. `get_recent_history()` - 近期历史查询
3. `get_recent_events()` - 最近事件查询
4. `get_daily_statistics()` - 每日统计
5. `get_realtime_statistics()` - 实时统计

### 影响的功能

- ✅ 事件列表查询API
- ✅ 统计分析API
- ✅ 历史记录查询API
- ✅ 实时统计API

---

## 🎯 经验教训

### 1. 数据格式兼容性

**问题**:
- 代码假设数据格式是对象，但实际可能是字典
- 从数据库读取的数据是JSON格式，需要转换为对象

**解决方案**:
- 在访问属性前检查数据类型
- 使用`isinstance()`判断是字典还是对象
- 提供兼容的访问方式

### 2. 数据转换层

**建议**:
- 在Repository层统一转换数据格式
- 确保从数据库读取的数据转换为领域对象
- 或者在使用时统一处理格式兼容性

### 3. 类型检查

**建议**:
- 使用类型提示（Type Hints）
- 添加类型检查工具（mypy）
- 在关键位置添加类型断言

---

## 🔄 后续工作建议

### 1. 统一数据格式

**建议**:
- 在`PostgreSQLDetectionRepository._row_to_record()`中统一转换objects为`DetectedObject`对象
- 或者在使用时统一处理格式兼容性

### 2. 添加类型检查

**建议**:
- 使用类型提示（Type Hints）
- 添加类型检查工具（mypy）
- 在关键位置添加类型断言

### 3. 添加单元测试

**建议**:
- 为每个方法添加单元测试
- 测试字典格式和对象格式的数据
- 测试边界情况

---

## ✅ 修复完成

**修复日期**: 2025-11-04
**修复状态**: ✅ 完全成功
**影响范围**: 5个方法，多个API端点

---

*本次修复解决了事件列表查询中的track_id错误，确保代码能正确处理字典格式和对象格式的数据。*
