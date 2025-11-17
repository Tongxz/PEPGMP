# 检测记录和快照保存问题诊断报告

## 诊断时间
2025-11-14

## 发现的问题

### 问题1: 检测记录保存失败（严重）⚠️

**症状**：
- 日志中显示：`保存检测记录失败: invalid input for query argument $3: datetime.datetime... (can't subtract offset-naive and offset-aware datetimes)`
- 日志中显示：`Failed to save detection record: Event loop is closed`

**影响**：
- 检测记录无法保存到数据库
- 由于检测记录未保存，违规事件也无法正确关联
- 导致详情页看不到检测记录和快照

**根本原因**：
1. **时区问题**：`Timestamp` 值对象返回的datetime可能带时区信息，但数据库需要naive datetime
2. **事件循环关闭**：异步保存操作时，事件循环可能已经关闭

**已修复的代码**：
- `src/infrastructure/repositories/postgresql_detection_repository.py` 已经有处理时区的逻辑（第360-362行），但可能在某些情况下仍失败

### 问题2: 违规记录的snapshot_path为空（严重）⚠️

**症状**：
- API返回的违规记录中，`snapshot_path` 字段都是 `null`
- 前端无法显示快照图片

**可能原因**：
1. **检测记录保存失败**：由于问题1，检测记录未保存，导致快照路径无法关联
2. **快照未保存**：快照保存逻辑可能未执行或失败
3. **快照路径未传递**：保存违规事件时，快照路径未正确传递

**当前状态**：
- 从API查询结果看，违规记录存在（如 `no_safety_helmet`、`no_safety_vest`），但 `snapshot_path` 为 `null`

### 问题3: 违规检测结果不正确（中等问题）⚠️

**症状**：
- 日志显示违规类型是 `no_safety_helmet`、`no_safety_vest`，而不是 `no_hairnet`
- 但检测内容应该是发网检测

**可能原因**：
- 违规检测逻辑使用了默认的违规规则，而不是实际的发网检测结果
- `ViolationService.detect_violations()` 可能没有正确读取发网检测结果

### 问题4: 发网检测结果显示正常（信息）

**症状**：
- 日志显示：`✅ 人员 1 (track_id=0) 检测到发网: 置信度=0.899`
- 日志显示：`✅ 人员 2 (track_id=1) 检测到发网: 置信度=0.885`
- 所有检测到的人员都有发网（`has_hairnet=True`）

**说明**：
- 这可能是正常的（实际检测场景中人员都佩戴了发网）
- 也可能是因为全图检测成功，但违规检测逻辑未正确使用这些结果

### 问题5: 快照目录存在但无文件（信息）

**症状**：
- `output/processed_images` 目录存在
- `datasets/raw` 目录存在
- 但最近7天内没有找到快照文件

**可能原因**：
1. **快照未保存**：由于检测记录保存失败，快照可能也未保存
2. **保存路径不同**：快照可能保存在其他位置

## 排查建议

### 立即行动项

1. **修复时区问题**：
   - 检查 `Timestamp` 值对象的实现
   - 确保所有 datetime 在保存到数据库前都转换为 naive UTC datetime
   - 测试时区转换逻辑

2. **修复事件循环问题**：
   - 检查异步保存操作的执行上下文
   - 确保在正确的事件循环中执行
   - 可能需要使用 `asyncio.create_task()` 或 `asyncio.run_coroutine_threadsafe()`

3. **检查违规检测逻辑**：
   - 验证 `ViolationService.detect_violations()` 是否正确读取发网检测结果
   - 检查违规类型映射是否正确

### 验证步骤

1. **检查日志**：
   ```bash
   # 查看最近的保存操作
   tail -200 logs/detect_vid1.log | grep -E "保存|save|snapshot"
   
   # 查看违规检测
   tail -200 logs/detect_vid1.log | grep -E "违规|violation|has_hairnet"
   ```

2. **直接查询数据库**：
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
   find datasets/raw -name "*.jpg" -type f -mtime -7
   find output/processed_images -name "*.jpg" -type f -mtime -7
   ```

## 修复优先级

1. **高优先级**：修复检测记录保存失败问题（时区和事件循环）
2. **高优先级**：修复快照路径传递问题
3. **中优先级**：修复违规检测逻辑（确保使用正确的违规类型）
4. **低优先级**：优化日志输出，便于未来排查

## 下一步行动

1. 修复时区和事件循环问题
2. 验证修复后的保存流程
3. 检查违规检测逻辑是否正确
4. 测试完整流程：检测 → 保存记录 → 保存快照 → 保存违规事件

