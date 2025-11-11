# 视频流调试检查清单

## 问题现象
WebSocket连接成功（状态码101），但没有视频数据。

## 检查步骤

### 1. 检查检测进程是否在推送视频帧

查看检测进程日志（`logs/detect_{camera_id}.log`），查找：
- `准备推送视频帧: camera=xxx`
- `视频帧推送成功: camera=xxx`
- `视频帧已通过Redis推送: camera=xxx`

**如果没有这些日志，说明：**
- 检测进程没有调用 `push_frame()`
- `stream_interval` 配置可能太大
- `video_stream_service` 未正确初始化

### 2. 检查Redis连接和发布

查看检测进程日志，查找：
- `Redis发布成功: channel=video:xxx, subscribers=X`
- `通过Redis推送失败`

**如果看到推送失败，检查：**
- Redis服务是否运行：`redis-cli ping`
- Redis连接配置是否正确（`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`）
- 网络连接是否正常

### 3. 检查API服务器的Redis订阅

查看API服务器日志，查找：
- `视频流Redis订阅已启动: redis://...`
- `Redis已接收帧: X (camera=xxx)`

**如果没有这些日志，说明：**
- Redis订阅未启动
- Redis连接失败
- 环境变量 `VIDEO_STREAM_USE_REDIS` 可能被设置为 "0"

### 4. 检查WebSocket连接和客户端

查看API服务器日志，查找：
- `客户端已连接到视频流 [xxx], 当前客户端数: X, 是否有缓存帧: True/False`
- `帧已加入发送队列: camera=xxx`

**如果看到"是否有缓存帧: False"，说明：**
- 没有视频帧被推送到Redis
- Redis订阅未接收到帧
- 频道名称不匹配

### 5. 检查配置参数

#### stream_interval（推送间隔）
- 默认值：3（每3帧推送一次）
- 如果配置太大，推送频率会很低
- 检查方法：查看 `DetectionLoopConfig` 的初始化日志

#### VIDEO_STREAM_USE_REDIS
- 默认值：`"1"`（启用）
- 如果设置为 `"0"`，会禁用Redis
- 检查方法：查看环境变量或日志

### 6. 测试Redis Pub/Sub

手动测试Redis发布和订阅：

```bash
# 终端1：订阅频道
redis-cli
> PSUBSCRIBE video:*

# 终端2：发布测试消息
redis-cli
> PUBLISH video:vid1 "test message"
```

如果终端1能收到消息，说明Redis Pub/Sub工作正常。

### 7. 检查频道名称

确保频道名称匹配：
- 检测进程发布：`video:{camera_id}`
- API服务器订阅：`video:*`（通配符）
- 例如：摄像头ID为 `vid1`，频道应该是 `video:vid1`

## 常见问题

### 问题1：检测进程没有推送日志

**可能原因：**
- `video_stream_service` 为 `None`
- `stream_interval` 太大，还没到推送帧数
- 检测进程异常退出

**解决方法：**
1. 检查 `DetectionInitializer.initialize_services()` 的日志
2. 减小 `stream_interval` 值（例如改为1）
3. 检查检测进程是否正常运行

### 问题2：Redis订阅未启动

**可能原因：**
- `VIDEO_STREAM_USE_REDIS=0`
- Redis连接失败
- `redis.asyncio` 未安装

**解决方法：**
1. 检查环境变量
2. 检查Redis连接配置
3. 安装 `redis` 包：`pip install redis`

### 问题3：Redis接收了帧但没有发送到WebSocket

**可能原因：**
- 没有客户端连接
- 发送队列已满
- WebSocket连接异常

**解决方法：**
1. 检查 `has_clients()` 返回是否为 `True`
2. 检查发送队列大小
3. 检查WebSocket连接状态

## 调试命令

### 查看检测进程日志
```bash
tail -f logs/detect_{camera_id}.log | grep -i "video\|redis\|stream"
```

### 查看API服务器日志
```bash
# 如果使用uvicorn
# 查看包含video-stream的日志
```

### 测试Redis连接
```bash
redis-cli ping
redis-cli INFO clients
```

### 监控Redis频道
```bash
redis-cli
> PSUBSCRIBE video:*
```

## 快速修复

如果以上都正常但仍然没有视频数据，尝试：

1. **重启检测进程**：
   ```bash
   # 停止
   curl -X POST http://localhost:8000/api/v1/cameras/{camera_id}/stop
   # 启动
   curl -X POST http://localhost:8000/api/v1/cameras/{camera_id}/start
   ```

2. **重启API服务器**：
   - 确保Redis订阅重新启动

3. **检查stream_interval**：
   - 临时设置为1，确保每帧都推送
   - 查看日志确认推送频率

4. **检查Redis连接**：
   - 确认Redis服务运行
   - 测试发布和订阅
