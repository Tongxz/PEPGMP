# 数据库时区问题全面检查报告

## 📅 检查日期: 2025-11-04

**目的**: 确保所有数据库时间相关的操作都已正确处理时区
**状态**: ✅ 检查完成

---

## 📊 检查结果总结

| 模块 | 操作 | 状态 | 说明 |
|------|------|------|------|
| **PostgreSQLDetectionRepository** | `save()` | ✅ 已修复 | 保存时移除时区信息 |
| **PostgreSQLDetectionRepository** | `find_by_time_range()` | ✅ 已修复 | 查询前转换为naive datetime |
| **PostgreSQLDetectionRepository** | `get_statistics()` | ✅ 已修复 | 查询前转换为naive datetime |
| **PostgreSQLAlertRepository** | `save()` | ✅ 已修复 | 保存时移除时区信息 |
| **PostgreSQLCameraRepository** | `save()` | ✅ 正常 | 使用TIMESTAMP WITH TIME ZONE |
| **PostgreSQLRegionRepository** | `save()` | ✅ 正常 | 使用TIMESTAMP WITH TIME ZONE |

---

## ✅ 已修复的模块

### 1. PostgreSQLDetectionRepository

#### `save()` 方法 ✅
- **修复位置**: `src/infrastructure/repositories/postgresql_detection_repository.py`
- **修复内容**: 保存时移除时区信息
- **修复代码**:
```python
# 移除时区信息以匹配数据库 TIMESTAMP WITHOUT TIME ZONE
if timestamp_value.tzinfo is not None:
    timestamp_value = timestamp_value.replace(tzinfo=None)
```

#### `find_by_time_range()` 方法 ✅
- **修复位置**: `src/infrastructure/repositories/postgresql_detection_repository.py`
- **修复内容**: 查询前转换为naive datetime
- **修复代码**:
```python
# 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
if start_time.tzinfo is not None:
    start_time = start_time.astimezone(tz.utc).replace(tzinfo=None)
```

#### `get_statistics()` 方法 ✅
- **修复位置**: `src/infrastructure/repositories/postgresql_detection_repository.py`
- **修复内容**: 查询前转换为naive datetime
- **修复代码**:
```python
# 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
if start_time.tzinfo is not None:
    start_time = start_time.astimezone(tz.utc).replace(tzinfo=None)
```

---

## ⚠️ 需要确认的模块

### PostgreSQLAlertRepository

#### `save()` 方法 ✅

**代码位置**: `src/infrastructure/repositories/postgresql_alert_repository.py:93-131`

**修复内容**: 保存时移除时区信息

**表结构**:
```sql
CREATE TABLE IF NOT EXISTS alert_history (
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),  -- TIMESTAMP WITHOUT TIME ZONE
    ...
);
```

**修复代码**:
```python
# 数据库列是 TIMESTAMP WITHOUT TIME ZONE，需要naive datetime
# 如果传入的是aware datetime，先转换为UTC，然后去掉时区信息
from datetime import timezone as tz

timestamp_value = alert.timestamp
if timestamp_value.tzinfo is not None:
    # 转换为UTC并去掉时区信息
    timestamp_value = timestamp_value.astimezone(tz.utc).replace(tzinfo=None)

alert_id = await conn.fetchval(
    """
    INSERT INTO alert_history (
        rule_id, camera_id, alert_type, message, details,
        notification_sent, notification_channels_used, timestamp
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING id
    """,
    # ...
    timestamp_value,  # 使用转换后的naive datetime
)
```

---

## ✅ 正常的模块

### PostgreSQLCameraRepository

#### `save()` 方法 ✅

**代码位置**: `src/infrastructure/repositories/postgresql_camera_repository.py:112-166`

**当前实现**:
```python
await conn.execute(
    """
    INSERT INTO cameras
    (id, name, location, status, camera_type, resolution, fps, region_id, metadata, created_at, updated_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """,
    # ...
    camera.created_at.value,  # Timestamp对象
    camera.updated_at.value,  # Timestamp对象
)
```

**表结构**:
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
```

**状态**: ✅ 正常
- 使用`TIMESTAMP WITH TIME ZONE`，可以接受aware datetime
- `Timestamp.value`返回的是aware datetime（UTC）

### PostgreSQLRegionRepository

#### `save()` 方法 ✅

**表结构**:
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
```

**状态**: ✅ 正常
- 使用`TIMESTAMP WITH TIME ZONE`，可以接受aware datetime

---

## 🔍 详细检查清单

### 检测记录（detection_records）

- ✅ **保存**: `save()` - 已修复，移除时区信息
- ✅ **查询**: `find_by_time_range()` - 已修复，转换为naive datetime
- ✅ **统计**: `get_statistics()` - 已修复，转换为naive datetime
- ✅ **查询**: `find_by_id()` - 正常，只查询不传入时间参数
- ✅ **查询**: `find_by_camera_id()` - 正常，只查询不传入时间参数
- ✅ **查询**: `find_by_confidence_range()` - 正常，只查询不传入时间参数

### 告警记录（alert_history）

- ✅ **保存**: `save()` - 已修复，移除时区信息
- ✅ **查询**: `find_by_id()` - 正常，只查询不传入时间参数
- ✅ **查询**: `find_all()` - 正常，只查询不传入时间参数

### 摄像头（cameras）

- ✅ **保存**: `save()` - 正常，使用TIMESTAMP WITH TIME ZONE
- ✅ **查询**: `find_by_id()` - 正常，只查询不传入时间参数

### 区域（regions）

- ✅ **保存**: `save()` - 正常，使用TIMESTAMP WITH TIME ZONE
- ✅ **查询**: 正常，只查询不传入时间参数

### 违规事件（violation_events）

- ✅ **查询**: `get_violations()` - 正常，只查询不传入时间参数

---

## ✅ 所有修复完成

### PostgreSQLAlertRepository.save() 已修复

**表结构确认**:
- `alert_history`表的`timestamp`列类型：`TIMESTAMP NOT NULL`（即`TIMESTAMP WITHOUT TIME ZONE`）

**修复内容**:
- 在保存前将aware datetime转换为naive datetime（UTC）
- 与`PostgreSQLDetectionRepository.save()`使用相同的处理逻辑

**修复代码**:
```python
# 数据库列是 TIMESTAMP WITHOUT TIME ZONE，需要naive datetime
from datetime import timezone as tz

timestamp_value = alert.timestamp
if timestamp_value.tzinfo is not None:
    timestamp_value = timestamp_value.astimezone(tz.utc).replace(tzinfo=None)
```

---

## 🎯 总结

### 已修复的模块 ✅

1. **PostgreSQLDetectionRepository.save()** - 保存时移除时区信息
2. **PostgreSQLDetectionRepository.find_by_time_range()** - 查询前转换为naive datetime
3. **PostgreSQLDetectionRepository.get_statistics()** - 查询前转换为naive datetime

### 已修复的模块 ✅

1. **PostgreSQLAlertRepository.save()** - 已修复，保存时移除时区信息

### 正常的模块 ✅

1. **PostgreSQLCameraRepository** - 使用`TIMESTAMP WITH TIME ZONE`
2. **PostgreSQLRegionRepository** - 使用`TIMESTAMP WITH TIME ZONE`

---

## 📚 相关文档

- [P0问题修复报告](./P0_ISSUES_FIX_COMPLETE.md) - 数据库时区保存问题修复
- [数据库时区查询问题修复](./DATABASE_TIMEZONE_QUERY_FIX.md) - 查询时区问题修复

---

**检查完成日期**: 2025-11-04
**修复状态**: ✅ 全部完成
**所有模块**: ✅ 已修复或正常

---

*所有数据库时区问题已完全修复，所有模块都已正确处理时区转换。*
