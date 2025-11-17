# 检测记录和快照保存问题修复总结

## 问题诊断结果

### ✅ 已发现的问题

1. **检测记录保存失败 - 时区问题**（已修复）
   - **问题**：`Timestamp.now()` 返回带时区的datetime（UTC），但代码中只使用 `replace(tzinfo=None)` 移除时区，未先转换
   - **影响**：可能导致时间值不正确（虽然时区信息已移除，但时间值可能仍是UTC+8而不是UTC）
   - **修复**：修改为 `astimezone(tz.utc).replace(tzinfo=None)`，确保先转换为UTC再移除时区信息

2. **检测记录保存失败 - 事件循环关闭**（需进一步排查）
   - **问题**：日志显示 `Event loop is closed` 错误
   - **可能原因**：程序退出时事件循环已关闭，但保存操作仍在执行
   - **影响**：保存操作失败

3. **违规记录的snapshot_path为空**
   - **根本原因**：由于问题1和2，检测记录保存失败，导致快照路径无法关联
   - **影响**：前端无法显示快照图片

4. **违规类型不正确**
   - **问题**：数据库中违规类型是 `no_safety_helmet`、`no_safety_vest`，而不是 `no_hairnet`
   - **可能原因**：违规检测逻辑使用了默认规则，而不是实际的发网检测结果

## 已实施的修复

### 修复1: 时区处理（已完成）

**文件**：`src/infrastructure/repositories/postgresql_detection_repository.py`

**修改位置**：
- 第362行（bigint ID分支）
- 第443行（VARCHAR ID分支）

**修改内容**：
```python
# 修改前
if timestamp_value.tzinfo is not None:
    timestamp_value = timestamp_value.replace(tzinfo=None)

# 修改后
if timestamp_value.tzinfo is not None:
    from datetime import timezone as tz
    timestamp_value = timestamp_value.astimezone(tz.utc).replace(tzinfo=None)
```

**说明**：
- `replace(tzinfo=None)` 只移除时区信息，不转换时间值
- `astimezone(tz.utc)` 先转换为UTC时间，确保时间值正确
- 然后 `replace(tzinfo=None)` 移除时区信息，匹配数据库的 `TIMESTAMP WITHOUT TIME ZONE`

## 待解决的问题

### 问题1: 事件循环关闭

**需要检查**：
1. 保存操作是否在正确的事件循环上下文中执行
2. 是否有异常导致事件循环提前关闭
3. 是否需要在保存操作中添加错误处理和重试机制

**建议**：
- 检查 `DetectionServiceDomain.process_detection()` 的调用上下文
- 添加异常处理和日志记录
- 确保异步操作在正确的事件循环中执行

### 问题2: 违规类型不正确

**需要检查**：
1. `ViolationService.detect_violations()` 如何读取发网检测结果
2. `DetectionRecord.objects` 中的 `metadata["has_hairnet"]` 是否正确设置
3. 违规类型映射是否正确

**建议**：
- 检查 `_convert_to_domain_format()` 方法，确保发网信息正确传递
- 检查 `ViolationService._check_no_hairnet()` 方法的逻辑
- 验证违规检测是否正确使用发网检测结果

## 验证步骤

修复后，需要验证以下内容：

1. **检查日志**：
   ```bash
   # 查看保存是否成功
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

3. **检查API**：
   ```bash
   curl "http://localhost:8000/api/v1/records/violations?camera_id=vid1&limit=5" | jq
   ```

4. **检查文件系统**：
   ```bash
   find datasets/raw -name "*.jpg" -type f -mtime -1
   ```

## 下一步行动

1. ✅ 修复时区处理问题（已完成）
2. ⏳ 排查事件循环关闭问题
3. ⏳ 验证违规检测逻辑
4. ⏳ 测试完整流程：检测 → 保存记录 → 保存快照 → 保存违规事件

