# 违规检测问题修复总结

## 修复时间
2025-11-14

## 修复的问题

### 问题1: `has_hairnet=None` 时未判定为违规 ✅

**问题描述**：
- 日志显示："❌ 人员 2 (track_id=1) 未检测到发网"（`has_hairnet=None`）
- 但系统不判定为违规，导致没有违规记录保存

**修复内容**：

1. **修改 `ViolationService._check_no_hairnet`**：
   - 修改前：只有当 `has_hairnet is False` 时才判定为违规
   - 修改后：`has_hairnet is False` 或 `None` 都判定为违规
   - 如果 `has_hairnet is None`，降低置信度要求（使用人体检测置信度）

2. **修改 `DetectionApplicationService._analyze_violations`**：
   - 同样修改逻辑，支持 `has_hairnet=None` 时判定为违规

3. **修改 `DetectionApplicationService._extract_violations_summary`**：
   - 同样修改逻辑，保持一致

### 问题2: 确保所有人员都有 `has_hairnet` 字段 ✅

**问题描述**：
- 如果某个人员没有匹配到发网检测结果（bbox匹配失败），`has_hairnet` 不会被添加到 metadata
- 导致违规检测逻辑无法判断

**修复内容**：

**修改 `DetectionApplicationService._convert_to_domain_format`**：
- 如果没有匹配到发网检测结果，默认 `has_hairnet=False`
- 确保所有人员都有明确的发网状态
- 添加调试日志，记录未匹配的情况

### 问题3: 提升保存日志级别 ✅

**问题描述**：
- 保存成功的日志是DEBUG级别，默认不可见
- 难以监控保存操作是否成功

**修复内容**：

**修改 `DetectionLoopService._process_frame`**：
- 将保存成功的日志从 `logger.debug` 提升到 `logger.info`
- 添加 `detection_id` 信息，便于追踪

## 修复的文件

1. `src/domain/services/violation_service.py`
   - 修改 `_check_no_hairnet` 方法，支持 `has_hairnet=None` 时判定为违规

2. `src/application/detection_application_service.py`
   - 修改 `_analyze_violations` 方法，支持 `has_hairnet=None` 时判定为违规
   - 修改 `_extract_violations_summary` 方法，保持一致
   - 修改 `_convert_to_domain_format` 方法，确保所有人员都有 `has_hairnet` 字段

3. `src/application/detection_loop_service.py`
   - 提升保存成功的日志级别到INFO

## 预期效果

修复后，系统应该能够：

1. ✅ **正确检测违规**：
   - 当 `has_hairnet is False` 时，判定为违规（原有逻辑）
   - 当 `has_hairnet is None`（未检测到发网）时，也会判定为违规（新逻辑）

2. ✅ **确保数据完整性**：
   - 所有人员都有明确的 `has_hairnet` 状态
   - 即使没有匹配到发网检测结果，也会默认为 `False`

3. ✅ **可监控性**：
   - 保存操作会在INFO级别日志中可见
   - 违规检测会在INFO级别日志中记录

## 验证步骤

修复后，需要验证：

1. **检查日志**：
   ```bash
   tail -f logs/detect_vid1.log | grep -E "检测到发网违规|✓.*帧.*已保存|违规事件已保存"
   ```

2. **检查API**：
   ```bash
   curl "http://localhost:8000/api/v1/records/violations?camera_id=vid1&limit=10" | jq
   ```

3. **验证违规类型**：
   - 确认新生成的违规记录类型是 `no_hairnet`
   - 确认 `snapshot_path` 不为 `null`

## 注意事项

1. **置信度要求**：
   - `has_hairnet is False`：需要满足 `hairnet_confidence >= 0.5`
   - `has_hairnet is None`：需要满足 `detection_confidence >= 0.5`（人体检测置信度）

2. **日志级别**：
   - 违规检测成功的日志是INFO级别
   - 违规检测失败的日志是DEBUG级别（仅在调试时可见）

3. **默认行为**：
   - 如果未匹配到发网检测结果，默认 `has_hairnet=False`
   - 这样会触发违规检测，但会根据置信度要求决定是否保存违规记录

