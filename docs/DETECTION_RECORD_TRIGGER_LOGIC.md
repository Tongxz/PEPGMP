# 检测记录触发逻辑说明

## 概述

本文档详细说明检测记录何时触发保存，以及触发后的完整处理流程。

## 触发时机

### 1. 实时流处理 (`process_realtime_stream`)

在 `DetectionApplicationService.process_realtime_stream()` 中，每帧处理时都会判断是否保存：

```python
# 1. 执行检测
detection_result = self.detection_pipeline.detect_comprehensive(frame)

# 2. 分析违规
has_violations, violation_severity = self._analyze_violations(detection_result)

# 3. 智能保存决策
should_save = self._should_save_detection(
    frame_count=frame_count,
    has_violations=has_violations,
    violation_severity=violation_severity,
)

# 4. 如果需要保存，执行保存流程
if should_save:
    # ... 保存逻辑
```

## 保存策略

系统支持4种保存策略，通过 `SavePolicy.strategy` 配置：

### 策略1: `ALL` - 保存所有（按间隔）

**触发条件**：
```python
frame_count % self.save_policy.save_interval == 0
```

**说明**：
- 每 `save_interval` 帧保存一次（默认30帧）
- 不管是否有违规，都按间隔保存
- 适合需要完整记录的场景

**保存原因**：
```python
"interval_save (interval=30)"
```

### 策略2: `VIOLATIONS_ONLY` - 仅保存违规

**触发条件**：
```python
has_violations and violation_severity >= violation_severity_threshold
```

**说明**：
- 只保存有违规的帧
- 违规严重程度必须 >= `violation_severity_threshold`（默认0.5）
- 适合只关注违规行为的场景

**保存原因**：
```python
"violation_detected (severity=0.80)"
```

### 策略3: `INTERVAL` - 按固定间隔保存

**触发条件**：
```python
frame_count % self.save_policy.save_interval == 0
```

**说明**：
- 每 `save_interval` 帧保存一次（默认30帧）
- 与 `ALL` 策略相同，但语义更清晰
- 适合需要定期记录的场景

**保存原因**：
```python
"interval_save (interval=30)"
```

### 策略4: `SMART` - 智能保存（推荐，默认）

**触发条件**：
```python
# 条件1: 违规必保存
if has_violations and violation_severity >= violation_severity_threshold:
    return True

# 条件2: 定期保存正常样本
if frame_count % self.save_policy.normal_sample_interval == 0:
    return True
```

**说明**：
- **违规帧**：必须保存（违规严重程度 >= 0.5）
- **正常帧**：每 `normal_sample_interval` 帧保存一次（默认300帧，约10秒）
- 既保证违规不遗漏，又定期保存正常样本用于对比和训练

**保存原因**：
```python
# 违规帧
"violation_detected (severity=0.80)"

# 正常帧
"normal_sample (interval=300)"
```

## 违规判断逻辑

### 1. 违规分析 (`_analyze_violations`)

```python
def _analyze_violations(self, detection_result: DetectionResult) -> Tuple[bool, float]:
    violations = []
    
    # 检查发网违规
    for hairnet in detection_result.hairnet_results:
        has_hairnet = hairnet.get("has_hairnet", None)
        hairnet_confidence = hairnet.get("hairnet_confidence", 0.0)
        
        # 只有在明确检测到未佩戴发网（has_hairnet = False）且置信度足够高时，才判定为违规
        if has_hairnet is False and hairnet_confidence > 0.5:
            violations.append({
                "type": "no_hairnet",
                "confidence": hairnet.get("confidence", 0.0),
                "severity": 0.8,  # 发网违规严重程度高
            })
    
    if not violations:
        return False, 0.0
    
    # 计算综合严重程度（取最高严重程度）
    max_severity = max(v["severity"] for v in violations)
    return True, max_severity
```

**关键判断条件**：
- `has_hairnet is False`：明确检测到未佩戴发网
- `hairnet_confidence > 0.5`：发网检测置信度足够高
- 如果 `has_hairnet is None`，不判定为违规（可能是检测模型未检测到）

**违规严重程度**：
- 发网违规：`severity = 0.8`（高）
- 其他违规：可扩展

## 触发后的完整流程

### 步骤1: 转换检测结果为领域格式

```python
detected_objects = self._convert_to_domain_format(detection_result)
```

**转换逻辑**：
1. 将人体检测结果转换为 `DetectedObject` 实体
2. 关联发网检测结果到对应的人员对象（通过 bbox 或索引匹配）
3. 将发网信息添加到人员的 `metadata` 中：
   - `has_hairnet`: 是否佩戴发网
   - `hairnet_confidence`: 发网检测置信度
   - `hairnet_bbox`: 发网边界框
   - `head_bbox`: 头部边界框
4. 转换行为检测结果（洗手、消毒）

### 步骤2: 保存快照图片

```python
snapshot_info = await self._save_snapshot_if_possible(
    frame,
    camera_id,
    violation_type=primary_violation_type,
    metadata={
        "mode": DetectionMode.REALTIME_STREAM.value,
        "frame_count": frame_count,
        "has_violations": has_violations,
    },
)
```

**快照保存位置**：
```
output/processed_images/{camera_id}/{year}/{month}/{day}/{timestamp}_{violation_type}_{hash}.jpg
```

**快照信息包含**：
- `relative_path`: 相对路径
- `absolute_path`: 绝对路径
- `captured_at`: 捕获时间
- `violation_type`: 违规类型（如果有）
- `metadata`: 其他元数据

### 步骤3: 创建检测记录实体

```python
record = await self.detection_domain_service.process_detection(
    camera_id=camera_id,
    detected_objects=detected_objects,
    processing_time=processing_time,
    frame_id=frame_count,
    snapshots=[snapshot_info] if snapshot_info else None,
)
```

**内部流程**：

#### 3.1 创建检测对象实体

```python
domain_objects = []
for obj_data in detected_objects:
    domain_obj = DetectedObject(
        class_id=obj_data["class_id"],
        class_name=obj_data["class_name"],
        confidence=Confidence(obj_data.get("confidence", 0.0)),
        bbox=BoundingBox(x1, y1, x2, y2),
        track_id=obj_data.get("track_id"),
        metadata=obj_data.get("metadata", {}),
    )
    domain_objects.append(domain_obj)
```

#### 3.2 创建检测记录实体

```python
record = DetectionRecord(
    id=f"{camera_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
    camera_id=camera_id,
    objects=domain_objects,
    timestamp=Timestamp.now(),
    processing_time=processing_time,
    frame_id=frame_id,
    region_id=camera.region_id,
)
```

#### 3.3 添加快照信息到metadata

```python
if snapshots:
    record.add_metadata("snapshots", [
        {
            "relative_path": info.relative_path,
            "absolute_path": info.absolute_path,
            "captured_at": info.captured_at.isoformat(),
            "violation_type": info.violation_type,
            "metadata": dict(info.metadata) if info.metadata else None,
        }
        for info in snapshots
    ])
```

### 步骤4: 分析检测质量

```python
quality_analysis = self.detection_service.analyze_detection_quality(record)
record.add_metadata("quality_analysis", quality_analysis)
```

**质量分析包含**：
- 检测置信度统计
- 对象数量和质量评估
- 其他质量指标

### 步骤5: 检测违规行为

```python
violations = self.violation_service.detect_violations(record)
if violations:
    record.add_metadata("violations", [v.__dict__ for v in violations])
    record.add_metadata("violation_count", len(violations))
```

**违规检测**：
- 检查每个检测对象的 `metadata` 中的违规信息
- 创建 `Violation` 实体列表
- 添加到记录的 `metadata` 中

### 步骤6: 保存检测记录到数据库

```python
saved_record_id = await self.detection_repository.save(record)
```

**保存到 `detection_records` 表**：
- `id`: 自增ID或字符串ID
- `camera_id`: 摄像头ID
- `timestamp`: 检测时间
- `frame_id`: 帧编号
- `objects`: 检测对象列表（JSONB格式）
- `person_count`: 检测到的人数
- `hairnet_violations`: 未佩戴发网的人数
- `handwash_events`: 洗手事件数
- `sanitize_events`: 消毒事件数
- `confidence`: 整体置信度
- `processing_time`: 处理耗时
- `region_id`: 区域ID
- `metadata`: 元数据（包含快照路径、违规信息等）

### 步骤7: 保存违规事件到数据库

```python
if violations and self.violation_repository:
    for violation in violations:
        # 查找对应的快照路径
        snapshot_path = None
        if snapshots:
            # 优先查找匹配违规类型的快照
            for snapshot in snapshots:
                if snapshot.get("violation_type") == violation.violation_type.value:
                    snapshot_path = snapshot.get("relative_path")
                    break
            
            # 如果没有匹配的，使用第一个快照
            if not snapshot_path and snapshots:
                snapshot_path = snapshots[0].get("relative_path")
        
        # 添加detection_id和snapshot_path到violation.metadata
        violation.metadata["detection_id"] = saved_record_id
        if snapshot_path:
            violation.metadata["snapshot_path"] = snapshot_path
        
        # 保存违规事件
        await self.violation_repository.save(violation, detection_id=saved_record_id)
```

**保存到 `violation_events` 表**：
- `id`: 自增ID
- `detection_id`: 关联的检测记录ID
- `camera_id`: 摄像头ID
- `timestamp`: 违规时间
- `violation_type`: 违规类型（如`no_hairnet`、`no_handwash`）
- `track_id`: 跟踪ID
- `confidence`: 置信度
- `snapshot_path`: 快照路径（从metadata中提取）
- `bbox`: 边界框坐标（JSONB格式）
- `status`: 状态（默认`pending`）

## 完整流程图

```
检测循环
    ↓
每帧处理 (_process_frame)
    ↓
执行检测 (detect_comprehensive)
    ↓
分析违规 (_analyze_violations)
    ├─→ 检查发网违规
    ├─→ has_hairnet is False?
    ├─→ hairnet_confidence > 0.5?
    └─→ 计算违规严重程度
    ↓
智能保存决策 (_should_save_detection)
    ├─→ 违规帧? → 是 → 保存
    └─→ 正常帧? → 间隔到了? → 是 → 保存
    ↓
如果需要保存 (should_save = True)
    ↓
┌─────────────────────────────────────────┐
│ 步骤1: 转换检测结果为领域格式            │
│ - 人体检测 → DetectedObject             │
│ - 关联发网检测结果                       │
│ - 转换行为检测结果                       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤2: 保存快照图片                      │
│ - 保存到文件系统                         │
│ - 生成快照路径                           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤3: 创建检测记录实体                  │
│ - DetectedObject 列表                    │
│ - DetectionRecord 实体                   │
│ - 添加快照信息到metadata                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤4: 分析检测质量                      │
│ - 检测置信度统计                         │
│ - 对象数量和质量评估                     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤5: 检测违规行为                      │
│ - 检查每个对象的违规信息                 │
│ - 创建 Violation 实体列表                │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤6: 保存检测记录到数据库              │
│ - 保存到 detection_records 表            │
│ - 获取保存的记录ID                       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 步骤7: 保存违规事件到数据库              │
│ - 关联检测记录ID                         │
│ - 关联快照路径                           │
│ - 保存到 violation_events 表             │
└─────────────────────────────────────────┘
    ↓
完成
```

## 配置参数

### 环境变量配置

```bash
# 保存策略（all, violations_only, interval, smart）
DETECTION_SAVE_STRATEGY=smart

# 保存间隔（帧数）
DETECTION_SAVE_INTERVAL=30

# 正常样本采样间隔（帧数，SMART策略使用）
DETECTION_NORMAL_SAMPLE_INTERVAL=300

# 是否保存统计摘要
DETECTION_SAVE_SUMMARY=true

# 违规严重程度阈值（0.0-1.0）
VIOLATION_SEVERITY_THRESHOLD=0.5
```

### 默认配置

```python
SavePolicy(
    strategy=SaveStrategy.SMART,           # 智能保存
    save_interval=30,                       # 间隔保存30帧
    normal_sample_interval=300,             # 正常样本每300帧保存一次
    save_normal_summary=True,               # 保存统计摘要
    violation_severity_threshold=0.5,       # 违规严重程度阈值0.5
)
```

## 关键要点

### 1. 违规判断的严格性

- **必须明确检测到未佩戴**：`has_hairnet is False`
- **置信度必须足够高**：`hairnet_confidence > 0.5`
- **避免误判**：如果 `has_hairnet is None`，不判定为违规

### 2. 保存策略的选择

- **生产环境推荐**：`SMART` 策略（默认）
  - 违规不遗漏
  - 定期保存正常样本用于对比
  - 平衡存储空间和记录完整性

- **调试场景**：`ALL` 策略
  - 保存所有帧，方便分析
  - 注意存储空间消耗

- **仅关注违规**：`VIOLATIONS_ONLY` 策略
  - 只保存违规帧，节省空间
  - 无法查看正常样本

### 3. 保存后的数据关联

- **检测记录** ↔ **违规事件**：通过 `detection_id` 关联
- **违规事件** ↔ **快照图片**：通过 `snapshot_path` 关联
- **检测记录** ↔ **快照图片**：通过 `metadata["snapshots"]` 关联

### 4. 性能考虑

- **保存是异步操作**：不阻塞检测循环
- **快照保存可能失败**：如果失败，记录仍会保存，但 `snapshot_path` 为空
- **批量操作**：违规事件按批次保存，提高性能

## 示例场景

### 场景1: 检测到违规

```
帧数: 123
检测结果: 2人，其中1人未佩戴发网
违规分析: has_violations=True, severity=0.8
保存决策: should_save=True (违规必保存)
保存原因: "violation_detected (severity=0.80)"

→ 保存检测记录
→ 保存快照图片 (violation_type=no_hairnet)
→ 保存违规事件 (violation_type=no_hairnet)
```

### 场景2: 正常帧（SMART策略）

```
帧数: 300
检测结果: 2人，都佩戴发网
违规分析: has_violations=False, severity=0.0
保存决策: should_save=True (normal_sample_interval=300)
保存原因: "normal_sample (interval=300)"

→ 保存检测记录
→ 保存快照图片 (violation_type=None)
→ 不保存违规事件
```

### 场景3: 正常帧（间隔未到）

```
帧数: 150
检测结果: 2人，都佩戴发网
违规分析: has_violations=False, severity=0.0
保存决策: should_save=False (间隔未到)

→ 不保存
```

## 总结

检测记录的触发和保存逻辑：

1. **触发时机**：每帧都会判断，根据保存策略决定是否保存
2. **违规判断**：严格的判断条件，避免误判
3. **保存策略**：4种策略可选，推荐SMART策略
4. **完整流程**：从检测结果转换到数据库保存，包括快照和违规事件的关联
5. **性能优化**：异步保存，批量操作，失败容错

这套机制既保证了违规不遗漏，又控制了存储空间，同时保留了足够的灵活性。

