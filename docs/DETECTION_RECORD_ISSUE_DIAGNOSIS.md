# 检测记录和快照保存问题诊断指南

## 问题描述

从逻辑上看，系统应该能够触发记录和保留快照，但实际在详情页没有看到准确的记录和快照图片。本文档帮助排查可能的问题。

## 可能的问题点

### 问题1: 违规检测未触发

**检查点**：
1. **违规判断条件是否满足**：
   - `has_hairnet` 必须是 `False`（不是 `None`）
   - `hairnet_confidence` 必须 > 0.5
   - 如果 `has_hairnet is None`，不会判定为违规

**诊断方法**：
- 查看日志中的 "发网检测结果示例"（每100帧记录一次）
- 检查 `has_hairnet` 的值是 `False` 还是 `None`
- 检查 `hairnet_confidence` 的值是否 > 0.5

**日志示例**：
```python
logger.info(
    f"发网检测结果示例 (前3个): {[{'has_hairnet': h.get('has_hairnet'), 'confidence': h.get('hairnet_confidence')} for h in result.hairnet_results[:3]]}"
)
```

**修复建议**：
- 如果 `has_hairnet` 经常是 `None`，可能是发网检测模型未正常工作
- 检查发网检测模型的置信度阈值设置
- 检查全图检测回退是否正常工作

### 问题2: 保存未触发

**检查点**：
1. **保存策略设置**：
   - 默认是 `SMART` 策略
   - 违规帧：必须保存（`has_violations=True` 且 `violation_severity >= 0.5`）
   - 正常帧：每300帧保存一次

2. **违规严重程度**：
   - 发网违规的 `severity` 是 `0.8`
   - `violation_severity_threshold` 默认是 `0.5`
   - 应该满足条件

**诊断方法**：
- 查看日志中的 "保存检测记录" 日志
- 检查 `saved_to_db` 是否为 `True`
- 检查 `save_reason` 的内容

**日志示例**：
```python
logger.info(
    f"保存检测记录: camera={camera_id}, frame={frame_count}, "
    f"violations={has_violations}, severity={violation_severity:.2f}, "
    f"violation_type={primary_violation_type}, "
    f"has_snapshot={snapshot_info is not None}, "
    f"snapshot_path={snapshot_info.relative_path if snapshot_info else None}"
)
```

**修复建议**：
- 如果 `saved_to_db=False`，检查是否满足保存条件
- 如果满足条件但仍未保存，检查是否有异常

### 问题3: 快照未保存

**检查点**：
1. **快照存储是否配置**：
   - `snapshot_storage` 是否为 `None`
   - 如果为 `None`，不会保存快照

2. **快照保存是否成功**：
   - 查看日志中的 "快照已保存" 或 "快照保存失败" 日志
   - 检查 `snapshot_info` 是否为 `None`

**诊断方法**：
- 查看日志中的快照保存日志
- 检查文件系统中是否存在快照文件
- 检查快照路径是否正确

**日志示例**：
```python
logger.info(
    f"快照已保存: camera={camera_id}, frame={frame_count}, "
    f"relative_path={snapshot_info.relative_path}, "
    f"violation_type={primary_violation_type}"
)
```

或

```python
logger.warning(
    f"快照保存失败: camera={camera_id}, frame={frame_count}, "
    f"violation_type={primary_violation_type}, "
    f"snapshot_storage={'已配置' if self.snapshot_storage else '未配置'}"
)
```

**修复建议**：
- 如果 `snapshot_storage is None`，需要配置快照存储
- 如果保存失败，检查文件系统权限
- 检查快照目录是否存在

### 问题4: 违规事件未保存到数据库

**检查点**：
1. **违规事件是否被检测到**：
   - `violations` 列表是否为空
   - `violation_repository` 是否已初始化

2. **快照路径是否传递**：
   - `snapshot_path` 是否正确从 `record.metadata["snapshots"]` 提取
   - 是否传递给 `violation.metadata["snapshot_path"]`

**诊断方法**：
- 查看日志中的 "准备保存违规事件" 日志
- 查看日志中的 "违规事件已保存" 日志
- 检查数据库中是否有违规记录

**日志示例**：
```python
logger.info(
    f"准备保存违规事件: violations_count={len(violations)}, "
    f"snapshots_count={len(snapshots)}"
)

logger.info(
    f"找到匹配的快照: violation_type={violation.violation_type.value}, "
    f"snapshot_path={snapshot_path}"
)

logger.info(
    f"违规事件已保存: type={violation.violation_type.value}, "
    f"camera={violation.camera_id}, detection_id={saved_record_id}, "
    f"snapshot_path={snapshot_path}"
)
```

**修复建议**：
- 如果 `violations` 为空，检查违规检测逻辑
- 如果 `snapshot_path` 为 `None`，检查快照保存逻辑
- 如果保存失败，查看异常日志

### 问题5: 数据库查询问题

**检查点**：
1. **API是否正确返回数据**：
   - `/api/v1/records/violations` 是否正确返回违规记录
   - `snapshot_path` 字段是否存在

2. **前端是否正确显示**：
   - 前端是否正确获取 `snapshot_path`
   - 图片URL是否正确生成

**诊断方法**：
- 直接查询API：`GET /api/v1/records/violations?camera_id=vid1&limit=12`
- 检查返回的JSON中是否有 `snapshot_path` 字段
- 检查前端控制台的日志

**修复建议**：
- 如果API返回的数据中没有 `snapshot_path`，检查数据库查询逻辑
- 如果前端无法显示图片，检查图片URL生成逻辑

### 问题6: 图片下载问题

**检查点**：
1. **图片路径是否正确**：
   - `snapshot_path` 是否是相对路径
   - 文件是否存在于文件系统中

2. **图片下载接口是否正常**：
   - `/api/v1/download/image/{filename}` 是否能正常访问
   - 文件是否存在

**诊断方法**：
- 直接访问图片URL：`/api/v1/download/image/{snapshot_path}`
- 检查文件系统中是否存在文件
- 检查图片下载接口的日志

**修复建议**：
- 如果文件不存在，检查快照保存逻辑
- 如果下载接口404，检查文件路径匹配逻辑

## 完整诊断流程

### 步骤1: 检查违规检测

查看日志中的发网检测结果：
```bash
grep "发网检测结果示例" logs/detect_*.log | tail -20
```

检查是否有 `has_hairnet=False` 的记录，以及 `hairnet_confidence` 是否 > 0.5。

### 步骤2: 检查保存触发

查看保存相关的日志：
```bash
grep "保存检测记录\|保存违规事件\|快照已保存\|快照保存失败" logs/detect_*.log | tail -20
```

检查：
- 是否有 "保存检测记录" 日志
- `has_snapshot` 是否为 `True`
- `snapshot_path` 是否不为空
- 是否有 "违规事件已保存" 日志

### 步骤3: 检查数据库

直接查询数据库：
```sql
-- 检查最近的违规记录
SELECT id, camera_id, violation_type, snapshot_path, timestamp, confidence
FROM violation_events
WHERE camera_id = 'vid1'
ORDER BY timestamp DESC
LIMIT 10;

-- 检查最近的检测记录
SELECT id, camera_id, timestamp, person_count, hairnet_violations, metadata
FROM detection_records
WHERE camera_id = 'vid1'
ORDER BY timestamp DESC
LIMIT 10;
```

检查：
- `violation_events` 表中是否有记录
- `snapshot_path` 字段是否不为空
- `detection_records` 表中是否有记录

### 步骤4: 检查文件系统

检查快照文件是否存在：
```bash
# 检查快照目录
ls -la output/processed_images/vid1/

# 或者
ls -la datasets/raw/vid1/

# 检查最近的快照文件
find output/processed_images -name "*.jpg" -type f -mtime -1 | head -10
```

### 步骤5: 检查API

直接调用API：
```bash
# 获取违规记录
curl "http://localhost:8000/api/v1/records/violations?camera_id=vid1&limit=12" | jq

# 检查返回的数据中是否有snapshot_path
```

### 步骤6: 检查前端

查看前端控制台日志：
- 打开浏览器开发者工具
- 查看控制台的日志
- 检查 `loadViolations()` 的返回值
- 检查图片URL是否正确生成

## 常见问题解决方案

### 问题：has_hairnet 总是 None

**原因**：
- 发网检测模型未正常工作
- ROI检测失败，全图检测也失败

**解决方案**：
1. 检查发网检测模型是否加载成功
2. 检查ROI检测是否正常工作
3. 检查全图检测回退是否触发
4. 降低发网检测置信度阈值（临时方案）

### 问题：违规事件保存了但snapshot_path为空

**原因**：
- 快照保存失败
- 快照路径未正确传递

**解决方案**：
1. 检查快照存储是否配置
2. 检查快照保存日志是否有错误
3. 检查 `record.metadata["snapshots"]` 是否正确设置
4. 检查 `violation.metadata["snapshot_path"]` 是否正确设置

### 问题：数据库中有记录但前端不显示

**原因**：
- API返回的数据格式不正确
- 前端字段映射错误

**解决方案**：
1. 检查API返回的JSON格式
2. 检查前端 `loadViolations()` 的字段映射
3. 检查前端 `getViolationImageUrl()` 的逻辑

### 问题：图片URL生成但无法显示

**原因**：
- 文件路径不正确
- 文件不存在
- 图片下载接口问题

**解决方案**：
1. 检查 `snapshot_path` 的实际值
2. 检查文件系统中是否存在文件
3. 检查图片下载接口是否能访问
4. 检查文件路径匹配逻辑

## 调试建议

### 1. 添加更多日志

在关键位置添加日志，帮助定位问题：

```python
# 在 _analyze_violations 中
logger.warning(f"违规分析: has_violations={has_violations}, severity={violation_severity}")

# 在 _should_save_detection 中
logger.warning(f"保存决策: should_save={should_save}, frame={frame_count}, has_violations={has_violations}")

# 在保存快照时
logger.warning(f"快照信息: snapshot_info={snapshot_info}")

# 在保存违规事件时
logger.warning(f"违规信息: violation={violation}, snapshot_path={snapshot_path}")
```

### 2. 检查配置

确认保存策略和阈值设置：

```python
# 检查 SavePolicy 配置
save_policy = SavePolicy(
    strategy=SaveStrategy.SMART,           # 智能保存
    save_interval=30,                       # 间隔保存30帧
    normal_sample_interval=300,             # 正常样本每300帧保存一次
    violation_severity_threshold=0.5,       # 违规严重程度阈值0.5
)
```

### 3. 数据库直接查询

直接查询数据库确认数据是否正确保存：

```sql
-- 检查违规记录
SELECT * FROM violation_events WHERE camera_id = 'vid1' ORDER BY timestamp DESC LIMIT 10;

-- 检查检测记录
SELECT id, camera_id, timestamp, person_count, hairnet_violations, metadata->'snapshots' as snapshots
FROM detection_records 
WHERE camera_id = 'vid1' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### 4. 文件系统检查

检查快照文件是否实际保存：

```bash
# 查找最近保存的快照
find output/processed_images -name "*.jpg" -type f -mtime -1 -ls

# 检查快照目录权限
ls -la output/processed_images/
```

## 总结

如果详情页没有看到准确的记录和快照图片，可能的原因有：

1. **违规检测未触发**：`has_hairnet` 不是 `False`，或置信度不够
2. **保存未触发**：未满足保存条件
3. **快照未保存**：快照存储未配置或保存失败
4. **违规事件未保存**：违规事件保存逻辑有问题
5. **数据库查询问题**：API未正确返回数据
6. **图片下载问题**：文件不存在或路径不正确

建议按照上述诊断流程逐步排查，重点检查日志中的关键信息。

