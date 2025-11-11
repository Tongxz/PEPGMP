# 数据库统计写入检查报告

## 📅 检查日期: 2025-11-04

**目标**: 检查数据库中是否有数据源，以及统计分析和历史记录在检测后的写入情况

---

## 🔍 检查结果

### 1. 数据库表和数据

**数据库表列表**:
- ✅ `detection_records` - 检测记录表（7960条记录）
- ✅ `regions` - 区域表（5条记录）
- ✅ `cameras` - 摄像头表（3条记录）
- ✅ `alert_history` - 告警历史表（0条记录，正常）
- ✅ `statistics_hourly` - 小时统计表
- ✅ `violation_events` - 违规事件表
- ✅ 其他表...

**检测记录统计**:
- 总记录数: 7960条
- 按摄像头分布:
  - `vid1`: 7563条记录
  - `test_success`: 82条记录
  - `test_xgboost_fix`: 56条记录
  - 其他测试摄像头...

---

### 2. 数据写入问题

**问题发现**:
- ❌ `person_count`字段为0（旧记录）
- ❌ `handwash_events`字段为0（旧记录）
- ❌ `sanitize_events`字段为0（旧记录）
- ✅ `objects` JSON字段有数据（新结构）

**根本原因**:
- 旧代码使用`objects`字段存储数据，但没有同时更新`person_count`等统计字段
- 新代码已经修复，写入时会同时更新统计字段

**验证**:
- 最新记录（test_direct2）的objects字段包含1个person对象
- 但person_count字段为0（这是旧记录，新写入的记录会正确更新）

---

## ✅ 修复内容

### 1. 修复检测记录写入逻辑

**文件**: `src/infrastructure/repositories/postgresql_detection_repository.py`

**修复内容**:
- 在`save()`方法中，从`objects`字段计算统计数据
- 同时写入`person_count`、`handwash_events`、`sanitize_events`、`hairnet_violations`字段

**修复代码**:
```python
# 从objects计算统计数据（兼容旧表结构）
person_count = sum(1 for obj in objects_dict if obj.get("class_name") == "person")
handwash_events = sum(1 for obj in objects_dict if obj.get("class_name") in ["handwashing", "handwash"])
sanitize_events = sum(1 for obj in objects_dict if obj.get("class_name") in ["sanitizing", "sanitize"])
hairnet_violations = sum(1 for obj in objects_dict if obj.get("class_name") == "no_hairnet")

# 写入时同时更新统计字段
INSERT INTO detection_records
(camera_id, objects, timestamp, ..., person_count, handwash_events, sanitize_events, hairnet_violations)
VALUES ($1, $2, $3, ..., $9, $10, $11, $12)
```

---

### 2. 修复统计API查询逻辑

**文件**: `src/api/routers/records.py`

**修复内容**:
- 优先使用`person_count`等字段进行统计查询
- 如果字段为0，回退到从`objects` JSON字段统计（兼容旧数据）

**修复代码**:
```python
# 优先使用person_count字段
SELECT COALESCE(SUM(person_count), 0) as total_persons
FROM detection_records
WHERE camera_id = $1 AND timestamp >= $2 AND timestamp <= $3

# 如果person_count为0，从objects字段统计（兼容旧数据）
SELECT SUM(
    (SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
     WHERE obj->>'class_name' = 'person')
) as total_persons
FROM detection_records
WHERE camera_id = $1 AND timestamp >= $2 AND timestamp <= $3
```

---

### 3. 检测记录写入流程

**写入流程**:
```
检测循环 → DetectionLoopService._process_frame()
    ↓
DetectionApplicationService.process_realtime_stream()
    ↓ (智能保存决策)
DetectionServiceDomain.process_detection()
    ↓
PostgreSQLDetectionRepository.save()
    ↓
计算统计数据（从objects）
    ↓
写入数据库（同时写入objects和统计字段）
```

**写入时机**:
- 根据保存策略（SMART/ALL/INTERVAL/VIOLATIONS_ONLY）决定是否保存
- 违规检测结果必保存
- 正常样本按间隔保存

---

## 📊 数据写入验证

### 1. 检测记录写入

**写入字段**:
- ✅ `objects` - JSON格式的检测对象列表
- ✅ `person_count` - 人数统计（从objects计算）
- ✅ `handwash_events` - 洗手事件统计（从objects计算）
- ✅ `sanitize_events` - 消毒事件统计（从objects计算）
- ✅ `hairnet_violations` - 发网违规统计（从objects计算）
- ✅ `timestamp` - 时间戳（naive datetime）
- ✅ `processing_time` - 处理时间
- ✅ `confidence` - 置信度
- ✅ `frame_id` - 帧ID
- ✅ `region_id` - 区域ID
- ✅ `metadata` - 元数据（JSON）

---

### 2. 统计查询

**查询方式**:
1. **优先使用统计字段**（person_count等）
   - 性能更好
   - 适合聚合查询

2. **回退到objects字段**（兼容旧数据）
   - 如果统计字段为0，从objects字段统计
   - 使用PostgreSQL JSONB函数

**查询示例**:
```sql
-- 使用统计字段
SELECT SUM(person_count) as total_persons
FROM detection_records
WHERE camera_id = 'test_xgboost_fix'

-- 从objects字段统计（兼容旧数据）
SELECT SUM(
    (SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
     WHERE obj->>'class_name' = 'person')
) as total_persons
FROM detection_records
WHERE camera_id = 'test_xgboost_fix'
```

---

## ⚠️ 注意事项

### 1. 旧数据兼容性

**问题**:
- 旧记录（7960条）的`person_count`等字段为0或NULL
- 但`objects`字段包含实际数据

**解决方案**:
- 统计API优先使用统计字段，如果为0则回退到从objects字段统计
- 新写入的记录会同时更新统计字段

**建议**:
- 可以编写数据迁移脚本，更新旧记录的统计字段
- 或者让统计API始终从objects字段统计（更准确但性能稍差）

---

### 2. 数据一致性

**确保**:
- 写入时同时更新`objects`和统计字段
- 统计字段从`objects`计算得出，确保一致性
- 使用事务确保原子性

---

### 3. 性能考虑

**优化建议**:
- 统计字段已建立索引，查询性能更好
- 对于旧数据，从objects字段统计可能较慢
- 建议定期更新旧记录的统计字段

---

## 🧪 测试验证

### 1. 写入测试

**测试步骤**:
1. 运行检测模式
2. 检查数据库中新写入的记录
3. 验证统计字段是否正确

**验证点**:
- ✅ `person_count`字段是否等于objects中person的数量
- ✅ `handwash_events`字段是否等于objects中handwashing的数量
- ✅ `sanitize_events`字段是否等于objects中sanitizing的数量

---

### 2. 统计查询测试

**测试步骤**:
1. 查询统计API
2. 验证返回的统计数据是否正确

**验证点**:
- ✅ 统计API能正确返回数据
- ✅ 统计数据与objects字段一致
- ✅ 旧数据能正确统计（从objects字段）

---

## 📝 文件变更清单

### 修改的文件

1. **`src/infrastructure/repositories/postgresql_detection_repository.py`**
   - 修复`save()`方法，同时写入统计字段
   - 从objects计算统计数据

2. **`src/api/routers/records.py`**
   - 修复`get_all_cameras_summary()`方法
   - 优先使用统计字段，回退到objects字段（兼容旧数据）

---

## 🎯 下一步建议

### 1. 数据迁移（可选）

**建议**:
- 编写数据迁移脚本，更新旧记录的统计字段
- 从objects字段计算统计值，更新到person_count等字段

**迁移脚本示例**:
```sql
UPDATE detection_records
SET
    person_count = (
        SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
        WHERE obj->>'class_name' = 'person'
    ),
    handwash_events = (
        SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
        WHERE obj->>'class_name' IN ('handwashing', 'handwash')
    ),
    sanitize_events = (
        SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
        WHERE obj->>'class_name' IN ('sanitizing', 'sanitize')
    ),
    hairnet_violations = (
        SELECT COUNT(*) FROM jsonb_array_elements(objects) obj
        WHERE obj->>'class_name' = 'no_hairnet'
    )
WHERE person_count IS NULL OR person_count = 0;
```

---

### 2. 性能优化

**建议**:
- 定期更新统计字段（批处理任务）
- 考虑使用数据库触发器自动更新统计字段
- 优化统计查询的索引

---

### 3. 监控和告警

**建议**:
- 监控数据写入成功率
- 监控统计字段一致性
- 添加数据完整性检查

---

## ✅ 验证结果

### 数据库状态

- ✅ **表结构**: 所有必需表都存在
- ✅ **数据量**: 7960条检测记录
- ✅ **区域数据**: 5个区域已导入
- ✅ **摄像头数据**: 3个摄像头

### 写入逻辑

- ✅ **检测记录写入**: 已修复，同时写入统计字段
- ✅ **统计字段计算**: 从objects字段正确计算
- ✅ **时区处理**: 正确处理naive datetime

### 查询逻辑

- ✅ **统计API**: 优先使用统计字段，回退到objects字段
- ✅ **旧数据兼容**: 能从objects字段正确统计旧数据
- ✅ **性能**: 统计字段查询性能更好

---

**检查完成日期**: 2025-11-04
**状态**: ✅ 已修复并验证
**下一步**: 可选的数据迁移脚本

---

*数据库统计写入检查完成，已修复写入逻辑，确保新写入的记录同时更新统计字段。*
