# 检测数据汇总、记录和保存逻辑

## 概述

本文档详细说明检测过程中数据的汇总、记录和保存逻辑，包括：
- **实时统计数据**：内存中累计的统计信息
- **检测记录**：保存到数据库的详细检测结果
- **违规事件**：保存到数据库的违规记录
- **快照图片**：保存到文件系统的图像快照

## 数据流程总览

```
检测循环 (DetectionLoopService)
    ↓
每帧处理 (_process_frame)
    ↓
┌─────────────────────────────────────────┐
│ 1. 检测 (OptimizedDetectionPipeline)   │
│    - person_detections                  │
│    - hairnet_results                    │
│    - handwash_results                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. 实时统计收集                         │
│    - detected_persons (累计)            │
│    - detected_hairnets (累计)           │
│    - detected_handwash (累计)           │
│    → 每5秒发布到Redis                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. 智能保存决策                         │
│    (DetectionApplicationService)        │
│    - 违规帧：必保存                     │
│    - 正常帧：按间隔保存                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. 保存检测记录                         │
│    (DetectionServiceDomain)             │
│    ↓                                    │
│    4.1 保存快照图片                     │
│    4.2 创建检测记录实体                 │
│    4.3 分析违规行为                     │
│    4.4 保存到detection_records表        │
│    4.5 保存违规到violation_events表     │
└─────────────────────────────────────────┘
```

## 详细逻辑

### 1. 实时统计数据收集 (`detection_loop_service.py`)

#### 1.1 每帧统计更新

在 `_process_frame` 方法中，每帧处理完成后更新内存中的统计数据：

```python
# 1. 更新处理帧数
self.detection_stats["processed_frames"] += 1

# 2. 统计人数（累计所有帧的人数总和）
person_count = len(result.person_detections) if result.person_detections else 0
if person_count > 0:
    self.detection_stats["detected_persons"] += person_count

# 3. 统计发网检测（只统计 has_hairnet=True 的人数）
if hasattr(result, 'hairnet_results') and result.hairnet_results:
    hairnet_detected_count = sum(
        1 for h in result.hairnet_results 
        if h.get("has_hairnet") is True
    )
    self.detection_stats["detected_hairnets"] += hairnet_detected_count

# 4. 统计洗手检测（只统计 is_handwashing=True 的人数）
if hasattr(result, 'handwash_results') and result.handwash_results:
    handwash_detected_count = sum(
        1 for h in result.handwash_results 
        if h.get("is_handwashing") is True
    )
    self.detection_stats["detected_handwash"] += handwash_detected_count
```

**注意**：
- **detected_persons**：累计所有帧中检测到的人数总和（例如：第1帧2人，第2帧3人，则累计为5）
- **detected_hairnets**：累计所有帧中 `has_hairnet=True` 的人数总和
- **detected_handwash**：累计所有帧中 `is_handwashing=True` 的人数总和

#### 1.2 统计数据发布到Redis

每5秒通过 `_publish_stats_to_redis()` 发布统计数据：

```python
stats_data = {
    "type": "stats",
    "camera_id": self.config.camera_id,
    "timestamp": now,
    "data": {
        "total_frames": self.frame_count,
        "processed_frames": self.detection_stats["processed_frames"],
        "detected_persons": self.detection_stats["detected_persons"],
        "detected_hairnets": self.detection_stats["detected_hairnets"],
        "detected_handwash": self.detection_stats["detected_handwash"],
        "avg_fps": avg_fps,
        "avg_detection_time": avg_detection_time,
        "last_detection_time": now,
    }
}

# 发布到Redis Pub/Sub
redis_client.publish("hbd:stats", json.dumps(stats_data).encode('utf-8'))
```

**特点**：
- 实时统计数据只存储在内存中，不持久化
- 通过Redis Pub/Sub实时推送，前端可以实时显示
- 服务重启后统计数据会重置

### 2. 检测记录保存 (`detection_application_service.py`)

#### 2.1 智能保存决策

`DetectionApplicationService.process_realtime_stream()` 决定是否保存检测记录：

```python
# 分析违规
has_violations, violation_severity = self._analyze_violations(detection_result)

# 智能保存决策
should_save = self._should_save_detection(
    frame_count=frame_count,
    has_violations=has_violations,
    violation_severity=violation_severity,
)
```

**保存策略**：
- **违规帧**：必须保存（`has_violations=True`）
- **正常帧**：按间隔保存（默认每300帧保存一次）
- **SMART策略**：违规必保存 + 定期保存正常样本

#### 2.2 保存流程

如果需要保存，执行以下步骤：

```python
# 1. 转换检测结果为领域实体格式
detected_objects = self._convert_to_domain_format(detection_result)

# 2. 保存快照图片
snapshot_info = await self._save_snapshot_if_possible(
    frame,
    camera_id,
    violation_type=primary_violation_type,
    metadata={...},
)

# 3. 保存检测记录
record = await self.detection_domain_service.process_detection(
    camera_id=camera_id,
    detected_objects=detected_objects,
    processing_time=processing_time,
    frame_id=frame_count,
    snapshots=[snapshot_info] if snapshot_info else None,
)
```

### 3. 检测记录持久化 (`detection_service_domain.py`)

#### 3.1 创建检测记录实体

`DetectionServiceDomain.process_detection()` 创建领域实体：

```python
# 1. 创建检测对象实体列表
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

# 2. 创建检测记录实体
record = DetectionRecord(
    id=f"{camera_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
    camera_id=camera_id,
    objects=domain_objects,
    timestamp=Timestamp.now(),
    processing_time=processing_time,
    frame_id=frame_id,
    region_id=camera.region_id,
)

# 3. 添加快照信息到metadata
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

#### 3.2 分析违规行为

```python
# 检测违规行为
violations = self.violation_service.detect_violations(record)
if violations:
    record.add_metadata("violations", [v.__dict__ for v in violations])
    record.add_metadata("violation_count", len(violations))
```

#### 3.3 保存到数据库

```python
# 保存检测记录到detection_records表
saved_record_id = await self.detection_repository.save(record)

# 如果有违规，保存到violation_events表
if violations and self.violation_repository:
    for violation in violations:
        # 查找对应的快照路径
        snapshot_path = None
        if snapshots:
            for snapshot in snapshots:
                if snapshot.get("violation_type") == violation.violation_type.value:
                    snapshot_path = snapshot.get("relative_path")
                    break
        
        # 添加detection_id和snapshot_path到violation.metadata
        violation.metadata["detection_id"] = saved_record_id
        if snapshot_path:
            violation.metadata["snapshot_path"] = snapshot_path
        
        # 保存违规事件
        await self.violation_repository.save(violation, detection_id=saved_record_id)
```

### 4. 数据库表结构

#### 4.1 `detection_records` 表

存储检测记录的详细结果：

```sql
CREATE TABLE detection_records (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    frame_id VARCHAR(255),
    
    -- 检测对象列表 (JSONB格式)
    objects JSONB NOT NULL,
    
    -- 统计字段
    person_count INTEGER DEFAULT 0,
    handwash_events INTEGER DEFAULT 0,
    sanitize_events INTEGER DEFAULT 0,
    hairnet_violations INTEGER DEFAULT 0,
    
    -- 性能指标
    confidence FLOAT,
    processing_time FLOAT,
    
    -- 元数据
    region_id VARCHAR(50),
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**字段说明**：
- `objects`: 存储所有检测到的对象列表（JSONB格式）
- `person_count`: 检测到的人数（从`objects`中统计）
- `hairnet_violations`: 未佩戴发网的人数（从`objects`中统计）
- `handwash_events`: 洗手事件数（从`objects`中统计）
- `metadata`: 存储快照路径、违规信息等元数据

#### 4.2 `violation_events` 表

存储违规事件的详细记录：

```sql
CREATE TABLE violation_events (
    id BIGSERIAL PRIMARY KEY,
    detection_id BIGINT REFERENCES detection_records(id),
    camera_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- 违规信息
    violation_type VARCHAR(50) NOT NULL,  -- no_hairnet, no_handwash, etc.
    track_id INTEGER,
    confidence FLOAT,
    
    -- 快照和边界框
    snapshot_path VARCHAR(500),
    bbox JSONB,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**字段说明**：
- `detection_id`: 关联的检测记录ID
- `violation_type`: 违规类型（如`no_hairnet`、`no_handwash`等）
- `snapshot_path`: 违规快照的路径（存储在文件系统中）
- `bbox`: 违规对象的边界框坐标

#### 4.3 索引优化

```sql
-- 检测记录表索引
CREATE INDEX idx_detection_camera_timestamp ON detection_records(camera_id, timestamp DESC);
CREATE INDEX idx_detection_timestamp ON detection_records(timestamp DESC);

-- 违规事件表索引
CREATE INDEX idx_violation_camera_timestamp ON violation_events(camera_id, timestamp DESC);
CREATE INDEX idx_violation_type ON violation_events(violation_type);
CREATE INDEX idx_violation_detection_id ON violation_events(detection_id);
```

### 5. 快照保存

#### 5.1 快照存储位置

快照图片保存在文件系统中，路径结构：

```
output/
└── processed_images/
    └── {camera_id}/
        └── {year}/
            └── {month}/
                └── {day}/
                    └── {timestamp}_{violation_type}_{hash}.jpg
```

例如：
```
output/processed_images/vid1/2025/11/13/1635678900_123456_no_hairnet_abc123.jpg
```

#### 5.2 快照信息保存

快照信息保存在两个地方：
1. **检测记录的metadata**：`record.metadata["snapshots"]`（JSONB格式）
2. **违规事件的snapshot_path**：`violation_events.snapshot_path`（字符串路径）

### 6. 数据汇总关系

#### 6.1 实时统计 vs 数据库记录

| 数据项 | 实时统计 | 数据库记录 |
|--------|---------|-----------|
| **检测人数** | `detected_persons`（累计所有帧） | `person_count`（每帧记录） |
| **发网检测** | `detected_hairnets`（累计`has_hairnet=True`） | `hairnet_violations`（违规数） |
| **洗手检测** | `detected_handwash`（累计`is_handwashing=True`） | `handwash_events`（事件数） |
| **存储位置** | 内存（Redis缓存） | PostgreSQL数据库 |
| **持久化** | ❌ 不持久化 | ✅ 持久化 |
| **查询方式** | Redis Pub/Sub | SQL查询 |

#### 6.2 统计数据汇总方式

**实时统计**（内存）：
- 累计值：所有帧的总和
- 更新频率：每帧更新，每5秒发布
- 生命周期：进程运行期间

**数据库记录**（持久化）：
- 按帧记录：每帧的详细检测结果
- 保存频率：违规帧必保存，正常帧按间隔保存
- 生命周期：永久保存（除非手动删除）

### 7. 数据查询和展示

#### 7.1 实时统计查询

前端通过以下方式获取实时统计：
1. **Redis Pub/Sub**：实时推送统计数据
2. **API接口**：`GET /api/v1/cameras/{camera_id}/stats`
   - 优先从Redis缓存获取
   - 回退到analytics数据

#### 7.2 历史数据查询

前端通过以下API查询历史数据：
1. **检测记录**：`GET /api/v1/records/detection-records/{camera_id}`
2. **违规记录**：`GET /api/v1/records/violations?camera_id={camera_id}`
3. **统计摘要**：`GET /api/v1/records/summary?period={period}`

### 8. 关键差异说明

#### 8.1 为什么三个统计值可能相同？

如果`detected_persons`、`detected_hairnets`、`detected_handwash`相同（如都是644），可能的原因：

1. **所有检测到的人员都有发网且正在洗手**（正常情况）
2. **统计逻辑问题**：检查日志中的`hairnet_detected_count`和`handwash_detected_count`是否为0
3. **检测结果结构问题**：检查`hairnet_results`和`handwash_results`中的`has_hairnet`和`is_handwashing`字段是否正确

**排查方法**：
- 查看日志中的"统计更新"和"发网检测结果示例" / "洗手检测结果示例"
- 检查`hairnet_results`和`handwash_results`的实际内容

#### 8.2 实时统计 vs 数据库统计

- **实时统计**：累计所有帧的总和，用于实时展示
- **数据库统计**：按帧记录，用于历史查询和数据分析

两者可能不一致，因为：
- 实时统计包含所有帧
- 数据库记录只保存部分帧（违规帧 + 按间隔保存的正常帧）

## 总结

检测数据的汇总、记录和保存流程：

1. **实时统计**：每帧更新，累计所有帧的统计值，通过Redis实时推送
2. **检测记录**：按智能策略保存，包含完整的检测结果和元数据
3. **违规事件**：单独保存到`violation_events`表，包含快照路径和违规详情
4. **快照图片**：保存在文件系统中，路径存储在检测记录和违规事件的metadata中

这种设计既保证了实时性（通过内存统计和Redis推送），又保证了数据的持久化（通过数据库保存详细记录）。

