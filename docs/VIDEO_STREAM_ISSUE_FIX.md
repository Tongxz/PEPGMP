# 视频流问题修复报告

## 问题分析

### 发现的问题

1. **❌ Redis未运行**
   - 视频流需要Redis进行跨进程通信
   - 检测进程通过Redis发布视频帧
   - API服务器通过Redis订阅接收视频帧
   - **影响**：视频帧无法从检测进程传递到API服务器

2. **❌ log_interval=120 导致推送频率过低**
   - 检测进程配置了 `--log-interval 120`
   - 这意味着每120帧才会处理一次（调用 `_process_frame`）
   - 视频流推送在 `_process_frame` 中，且需要 `frame_count % stream_interval == 0`
   - **实际效果**：如果 `stream_interval=3`，实际推送间隔是 120*3 = 360帧
   - **影响**：视频流推送频率极低，几乎看不到实时画面

3. **❌ 跳帧逻辑问题**
   - 当 `log_interval > 1` 时，大部分帧会被跳过
   - 跳过的帧不会调用 `_process_frame`，因此不会推送视频流
   - **影响**：视频流推送频率与检测频率绑定，无法独立控制

## 修复方案

### 1. 修复跳帧逻辑

**问题**：跳帧逻辑导致视频流推送也受影响

**解决方案**：
- 修改 `detection_loop_service.py` 的跳帧逻辑
- 即使跳过检测处理，也要单独推送视频流
- 使用原始帧（不进行检测）推送，保证实时性

**修改内容**：
```python
# 跳帧处理：只对检测和保存逻辑跳过，视频流推送不受影响
should_process_detection = (
    self.config.log_interval == 1
    or self.frame_count % self.config.log_interval == 0
)

if should_process_detection:
    # 处理检测和保存
    await self._process_frame(frame, self.frame_count)
else:
    # 即使跳过检测，也要推送视频流
    if self.video_stream_service and self.frame_count % self.config.stream_interval == 0:
        await self.video_stream_service.push_frame(...)
```

### 2. 启动Redis服务

**问题**：Redis未运行，导致跨进程通信失败

**解决方案**：
1. 启动Redis服务
2. 或者禁用Redis（如果不需要跨进程通信）

**启动Redis**：
```bash
# macOS (使用Homebrew)
brew services start redis

# 或者直接启动
redis-server

# 验证Redis运行
redis-cli ping
# 应该返回 PONG
```

**禁用Redis**（如果不需要）：
```bash
export VIDEO_STREAM_USE_REDIS=0
```
但这样会导致视频流无法工作，因为检测进程和API服务器不在同一进程。

### 3. 调整配置参数

**建议配置**：
- `log_interval`: 设置为1（每帧都检测）或较小的值（如10-30）
- `stream_interval`: 设置为1-3（保证视频流实时性）
- `VIDEO_STREAM_INTERVAL`: 默认3，可以调整为1

**修改检测进程启动参数**：
在 `src/services/executors/local.py` 中，将 `--log-interval 120` 改为更小的值，或者从配置中读取。

## 修复后的数据流

```
检测进程 (子进程)
  ↓ 读取每一帧
  ↓ frame_count++
  ↓
  ├─ log_interval匹配 → 处理检测和保存
  │  └─ 如果stream_interval匹配 → 推送标注后的帧
  │
  └─ log_interval不匹配 → 跳过检测
     └─ 如果stream_interval匹配 → 推送原始帧（保证实时性）
  ↓
  ↓ 发布到Redis: video:{camera_id}
  ↓
Redis Pub/Sub
  ↓
API服务器 VideoStreamManager (父进程)
  ↓ Redis订阅循环接收帧
  ↓ 更新帧缓存
  ↓ 发送到WebSocket队列
  ↓
前端WebSocket客户端
  ↓ 接收JPEG数据
  ↓ 显示视频画面
```

## 验证步骤

### 1. 启动Redis
```bash
redis-server
# 或
brew services start redis
```

### 2. 验证Redis运行
```bash
redis-cli ping
# 应该返回 PONG
```

### 3. 重启检测进程
```bash
# 停止
curl -X POST http://localhost:8000/api/v1/cameras/vid1/stop

# 启动
curl -X POST http://localhost:8000/api/v1/cameras/vid1/start
```

### 4. 检查日志
- 检测进程日志：应该看到 `视频流推送成功` 或 `Redis发布成功`
- API服务器日志：应该看到 `Redis已接收帧`

### 5. 测试前端
- 打开实时监控大屏
- 应该能看到视频画面

## 后续优化建议

1. **分离检测频率和视频流频率**
   - 检测频率：可以较低（如每120帧检测一次）
   - 视频流频率：应该较高（如每1-3帧推送一次）
   - 当前修复已实现这一点

2. **优化log_interval配置**
   - 考虑从配置文件读取，而不是硬编码
   - 或者分离 `detection_interval` 和 `log_interval`

3. **Redis连接池**
   - 当前每次推送都创建新连接，可以优化为连接池
   - 减少连接开销

4. **监控和告警**
   - 添加Redis连接状态监控
   - 添加视频流推送失败告警
