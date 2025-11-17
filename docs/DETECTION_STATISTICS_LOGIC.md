# 检测统计汇总逻辑说明

## 概述

检测统计汇总系统负责收集、发布和展示检测过程中的实时统计数据，包括：
- **检测人数** (`detected_persons`): 累计所有帧中检测到的人数总和
- **发网检测** (`detected_hairnets`): 累计所有帧中检测到**有发网**的人数总和（`has_hairnet=True`）
- **洗手检测** (`detected_handwash`): 累计所有帧中检测到**正在洗手**的人数总和（`is_handwashing=True`）
- **处理帧数** (`processed_frames`): 已处理的帧数
- **总帧数** (`total_frames`): 视频总帧数
- **平均FPS** (`avg_fps`): 平均处理帧率
- **平均检测时间** (`avg_detection_time`): 平均每帧检测耗时

## 数据流程

```
检测循环服务 (DetectionLoopService)
    ↓
每帧处理 (_process_frame)
    ↓
收集统计数据 (detection_stats)
    ↓
每5秒发布到Redis (hbd:stats channel)
    ↓
Redis监听器 (redis_listener.py)
    ↓
更新内存缓存 (CAMERA_STATS_CACHE)
    ↓
API接口 (get_camera_stats)
    ↓
前端显示 (CameraStatsModal)
```

## 详细逻辑

### 1. 统计数据收集 (`src/application/detection_loop_service.py`)

#### 1.1 初始化统计字典

在 `DetectionLoopService.__init__` 中初始化：

```python
self.detection_stats = {
    "total_frames": 0,
    "processed_frames": 0,
    "detected_persons": 0,
    "detected_hairnets": 0,
    "detected_handwash": 0,
    "total_detection_time": 0.0,
}
```

#### 1.2 每帧统计更新 (`_process_frame`)

在每帧处理完成后，更新统计数据：

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

**重要说明**：
- **检测人数** (`detected_persons`): 是**累计值**，等于所有帧中检测到的人数总和。例如：第1帧检测到2人，第2帧检测到3人，则 `detected_persons = 5`。
- **发网检测** (`detected_hairnets`): 只统计 `has_hairnet=True` 的人数，不是所有检测结果的数量。
- **洗手检测** (`detected_handwash`): 只统计 `is_handwashing=True` 的人数，不是所有检测结果的数量。

#### 1.3 统计重置

在 `run()` 方法开始时，重置所有统计数据：

```python
self.detection_stats = {
    "total_frames": 0,
    "processed_frames": 0,
    "detected_persons": 0,
    "detected_hairnets": 0,
    "detected_handwash": 0,
    "total_detection_time": 0.0,
}
```

### 2. 统计数据发布 (`_publish_stats_to_redis`)

#### 2.1 发布频率

每 **5秒** 发布一次统计数据（`stats_publish_interval = 5.0`）。

#### 2.2 发布内容

构建统计数据字典：

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
        "last_detection_time": now if self.detection_stats["processed_frames"] > 0 else None,
    }
}
```

#### 2.3 发布到Redis

通过 Redis Pub/Sub 发布到 `hbd:stats` channel：

```python
payload = json.dumps(stats_data).encode('utf-8')
redis_client.publish("hbd:stats", payload)
```

### 3. Redis监听和缓存 (`src/api/redis_listener.py`)

#### 3.1 订阅Redis Channel

`redis_stats_listener()` 函数订阅 `hbd:stats` channel，监听统计数据更新。

#### 3.2 更新内存缓存

接收到统计数据后，更新全局内存缓存：

```python
CAMERA_STATS_CACHE: Dict[str, Dict[str, Any]] = {}

# 接收到消息后
if data.get("type") == "stats":
    camera_id = data.get("camera_id")
    if camera_id:
        CAMERA_STATS_CACHE[camera_id] = data
```

### 4. API接口 (`src/api/routers/cameras.py`)

#### 4.1 获取统计数据

`get_camera_stats()` 接口优先从领域服务获取统计数据：

```python
@router.get("/cameras/{camera_id}/stats")
async def get_camera_stats(camera_id: str) -> Dict[str, Any]:
    # 优先使用领域服务
    domain_service = get_detection_service_domain()
    result = await domain_service.get_camera_stats_detailed(camera_id)
    return result
```

#### 4.2 领域服务获取统计 (`src/services/detection_service_domain.py`)

`get_camera_stats_detailed()` 方法：

1. **优先从Redis缓存获取** (`CAMERA_STATS_CACHE`)
2. **回退到analytics数据**（如果缓存为空）

```python
# 从Redis缓存获取实时统计数据（优先）
from src.api.redis_listener import CAMERA_STATS_CACHE
latest_stats_msg = CAMERA_STATS_CACHE.get(camera_id)

if latest_stats_msg and isinstance(latest_stats_msg, dict):
    realtime_data = latest_stats_msg.get("data", {})
    stats_data.update({
        "detected_persons": realtime_data.get("detected_persons", realtime_data.get("persons", 0)),
        "detected_hairnets": realtime_data.get("detected_hairnets", realtime_data.get("hairnets", 0)),
        "detected_handwash": realtime_data.get("detected_handwash", realtime_data.get("handwash", 0)),
        "avg_fps": realtime_data.get("avg_fps", realtime_data.get("fps", 0.0)),
        "processed_frames": realtime_data.get("processed_frames", 0),
        "total_frames": realtime_data.get("total_frames", 0),
        "avg_detection_time": realtime_data.get("avg_detection_time", 0.0),
    })
```

### 5. 前端显示 (`frontend/src/components/CameraStatsModal.vue`)

#### 5.1 获取统计数据

前端通过 `cameraApi.getCameraStats(cameraId)` 获取统计数据。

#### 5.2 显示统计信息

前端显示以下统计指标：

- **检测人数**: `stats.stats?.detected_persons`
- **发网检测**: `stats.stats?.detected_hairnets`
- **洗手检测**: `stats.stats?.detected_handwash`
- **处理帧数**: `stats.stats?.processed_frames`
- **处理FPS**: `stats.stats?.avg_fps`
- **平均检测时间**: `stats.stats?.avg_detection_time`
- **总帧数**: `stats.stats?.total_frames`

## 调试日志

### 1. 每100帧统计更新日志

```python
logger.info(
    f"统计更新: frame={frame_count}, person_count={person_count}, "
    f"total_persons={self.detection_stats['detected_persons']}, "
    f"hairnet_results={hairnet_results_count}, hairnet_detected={hairnet_detected_count}, "
    f"total_hairnets={self.detection_stats['detected_hairnets']}, "
    f"handwash_results={handwash_results_count}, handwash_detected={handwash_detected_count}, "
    f"total_handwash={self.detection_stats['detected_handwash']}"
)
```

### 2. 发网检测结果示例（每100帧）

```python
logger.info(
    f"发网检测结果示例 (前3个): {[{'has_hairnet': h.get('has_hairnet'), 'confidence': h.get('hairnet_confidence')} for h in result.hairnet_results[:3]]}"
)
```

### 3. 统计数据发布日志（每5秒）

```python
logger.info(
    f"统计数据已发布到Redis: camera={self.config.camera_id}, "
    f"total_frames={self.frame_count}, "
    f"processed={self.detection_stats['processed_frames']}, "
    f"detected_persons={self.detection_stats['detected_persons']}, "
    f"detected_hairnets={self.detection_stats['detected_hairnets']}, "
    f"detected_handwash={self.detection_stats['detected_handwash']}, "
    f"avg_fps={avg_fps:.2f}"
)
```

## 常见问题

### Q1: 为什么三个统计值（检测人数、发网检测、洗手检测）相同？

**A**: 如果三个值相同，可能的原因：
1. **所有检测到的人员都有发网且正在洗手**（正常情况）
2. **统计逻辑错误**：检查日志中的 `hairnet_detected_count` 和 `handwash_detected_count` 是否为0
3. **检测结果结构问题**：检查 `hairnet_results` 和 `handwash_results` 中的 `has_hairnet` 和 `is_handwashing` 字段是否正确

**排查方法**：
- 查看日志中的 "统计更新" 和 "发网检测结果示例" / "洗手检测结果示例"
- 检查 `hairnet_results` 和 `handwash_results` 的实际内容

### Q2: 统计数据不更新？

**A**: 检查以下内容：
1. **Redis连接**：确认Redis服务正常运行
2. **Redis监听器**：确认 `redis_stats_listener` 正在运行
3. **统计数据发布**：查看日志中的 "统计数据已发布到Redis"
4. **内存缓存**：检查 `CAMERA_STATS_CACHE` 是否更新

### Q3: 重启后统计数据未重置？

**A**: 检查 `run()` 方法中是否调用了统计重置逻辑。每次启动检测循环时，统计数据应该被重置为0。

## 总结

检测统计汇总系统采用**实时累计**的方式收集统计数据：
- **检测人数**：累计所有帧中检测到的人数总和
- **发网检测**：累计所有帧中 `has_hairnet=True` 的人数总和
- **洗手检测**：累计所有帧中 `is_handwashing=True` 的人数总和

统计数据通过 Redis Pub/Sub 实时发布，前端通过API接口获取并显示。

