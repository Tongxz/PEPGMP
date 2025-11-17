# 检测记录和快照保存问题汇总

## 🔴 核心问题

从排查结果来看，**检测记录保存失败是根本原因**，导致后续的违规记录和快照都无法正确保存和关联。

## 发现的问题

### 1. 检测记录保存失败（严重）❌

**症状**：
- 日志显示：`Failed to save detection record: Event loop is closed`
- 日志显示：`保存检测记录失败: invalid input for query argument $3: datetime.datetime... (can't subtract offset-naive and offset-aware datetimes)`

**根本原因**：
1. **事件循环关闭**：异步保存操作在错误的事件循环上下文中执行，导致 `Event loop is closed` 错误
2. **时区问题**：虽然代码中有处理时区的逻辑（第360-362行），但在某些情况下仍失败

**影响**：
- ✅ 检测记录无法保存到数据库
- ✅ 由于检测记录未保存，违规事件无法正确关联 `detection_id`
- ✅ 快照路径无法传递到违规事件

### 2. 违规记录的snapshot_path为空（严重）❌

**症状**：
- API返回的违规记录中，`snapshot_path` 字段都是 `null`
- 前端无法显示快照图片

**根本原因**：
- 由于问题1，检测记录保存失败，导致：
  1. 快照信息无法保存到 `detection_records.metadata["snapshots"]`
  2. 违规事件保存时无法从检测记录获取快照路径
  3. 即使快照文件已保存，路径也无法关联到违规事件

### 3. 违规类型不正确（中等问题）⚠️

**症状**：
- 数据库中违规类型是 `no_safety_helmet`、`no_safety_vest`
- 但检测内容应该是发网检测（`no_hairnet`）

**可能原因**：
- `ViolationService.detect_violations()` 可能使用了默认的违规规则
- 或者从 `DetectionRecord` 的 `objects` 中提取违规信息时，发网信息未正确传递

## 代码分析

### 问题1: 时区处理逻辑

**当前代码**（`postgresql_detection_repository.py` 第360-362行）：
```python
if timestamp_value.tzinfo is not None:
    # 转换为UTC时间并移除时区信息
    timestamp_value = timestamp_value.replace(tzinfo=None)
```

**问题**：
- `replace(tzinfo=None)` 不会转换时区，只是移除时区信息
- 如果原始datetime是UTC+8，移除时区后仍保留UTC+8的时间值，但数据库期望UTC时间

**正确做法**：
```python
if timestamp_value.tzinfo is not None:
    # 先转换为UTC，再移除时区信息
    timestamp_value = timestamp_value.astimezone(timezone.utc).replace(tzinfo=None)
```

### 问题2: 事件循环关闭

**可能原因**：
- 检测循环在独立线程中运行
- 异步保存操作在错误的线程/事件循环中执行
- 需要使用 `asyncio.run_coroutine_threadsafe()` 或确保在同一事件循环中执行

## 修复建议

### 修复1: 修复时区处理

**文件**：`src/infrastructure/repositories/postgresql_detection_repository.py`

**修改位置**：第360-362行

**修改内容**：
```python
# 移除时区信息以匹配数据库 TIMESTAMP WITHOUT TIME ZONE
# 数据库表定义为 WITHOUT TIME ZONE，无法接受带时区的datetime
if timestamp_value.tzinfo is not None:
    # 先转换为UTC，再移除时区信息
    from datetime import timezone as tz
    timestamp_value = timestamp_value.astimezone(tz.utc).replace(tzinfo=None)
```

### 修复2: 修复事件循环问题

**需要检查**：
1. 检测循环是否在独立线程中运行
2. 异步保存操作是否在正确的事件循环中执行
3. 是否需要在保存操作中使用 `asyncio.run_coroutine_threadsafe()`

### 修复3: 验证违规检测逻辑

**需要检查**：
1. `ViolationService.detect_violations()` 是否正确读取发网检测结果
2. `DetectionRecord.objects` 中的 `metadata["has_hairnet"]` 是否正确设置
3. 违规类型映射是否正确

## 验证步骤

修复后，按以下步骤验证：

1. **查看日志**：
   ```bash
   # 检查保存是否成功
   tail -f logs/detect_vid1.log | grep -E "保存检测记录|违规事件已保存|快照已保存"
   ```

2. **查询数据库**：
   ```sql
   -- 检查最近的检测记录
   SELECT id, camera_id, timestamp, person_count, hairnet_violations
   FROM detection_records
   WHERE camera_id = 'vid1'
   ORDER BY timestamp DESC
   LIMIT 10;
   
   -- 检查违规记录的snapshot_path
   SELECT id, violation_type, snapshot_path, timestamp
   FROM violation_events
   WHERE camera_id = 'vid1'
   ORDER BY timestamp DESC
   LIMIT 10;
   ```

3. **检查文件系统**：
   ```bash
   # 检查快照文件
   find datasets/raw -name "*.jpg" -type f -mtime -1
   ```

4. **检查API**：
   ```bash
   # 验证API返回的数据
   curl "http://localhost:8000/api/v1/records/violations?camera_id=vid1&limit=5" | jq
   ```

## 优先级

1. **🔴 高优先级**：修复检测记录保存失败问题（时区和事件循环）
2. **🔴 高优先级**：验证快照保存是否成功
3. **🟡 中优先级**：修复违规类型映射问题
4. **🟢 低优先级**：优化错误处理和日志输出

