# 视频流调试指南

## 当前状态

✅ WebSocket连接成功（状态码101）
✅ 前端连接无报错
✅ 后端无报错
❌ 但没有视频数据

## 调试步骤

### 1. 检查检测进程是否在推送视频帧

查看检测进程日志：
```bash
tail -f logs/detect_vid1.log | grep -E "视频|推送|Redis|stream"
```

**应该看到**：
- `检测循环服务已初始化: camera=vid1, stream_interval=3, video_stream_service=已配置`
- `准备推送视频帧` 或 `跳过检测但推送视频流`
- `Redis发布成功: channel=video:vid1, subscribers=X`
- `视频帧已通过Redis推送: camera=vid1`

**如果没有看到**：
- 检查 `video_stream_service` 是否为 `None`
- 检查 `stream_interval` 配置
- 检查 `frame_count % stream_interval` 是否匹配

### 2. 检查Redis订阅状态

查看API服务器日志，查找：
- `视频流Redis订阅已启动`
- `Redis已接收帧: X (camera=vid1)`
- `帧已加入发送队列: camera=vid1`

**如果没有看到**：
- 检查Redis连接配置
- 检查 `VIDEO_STREAM_USE_REDIS` 环境变量
- 检查Redis密码是否正确

### 3. 检查WebSocket发送

查看API服务器日志，查找：
- `客户端已连接到视频流 [vid1], 是否有缓存帧: True/False`
- `视频帧已发送到WebSocket: camera=vid1`
- `帧已加入发送队列: camera=vid1`

**如果没有看到**：
- 检查是否有客户端连接
- 检查发送队列是否正常
- 检查WebSocket连接状态

### 4. 检查Redis频道订阅

使用Docker命令检查Redis订阅状态：
```bash
# 检查频道订阅数
docker exec pyt-redis-dev redis-cli -a pyt_dev_redis PUBSUB NUMSUB video:vid1

# 手动测试发布
docker exec pyt-redis-dev redis-cli -a pyt_dev_redis PUBLISH video:vid1 "test"
```

### 5. 检查前端接收

打开浏览器控制台，查看：
- `[VideoStreamCard] WebSocket连接成功: vid1`
- `[VideoStreamCard] 收到视频帧数据`
- WebSocket消息事件

**如果没有看到**：
- 检查WebSocket消息处理逻辑
- 检查帧数据格式
- 检查图像显示逻辑

## 常见问题排查

### 问题1：检测进程没有推送日志

**可能原因**：
- `video_stream_service` 未初始化
- `stream_interval` 配置错误
- 检测进程异常退出

**解决方法**：
1. 检查检测进程日志中的初始化信息
2. 检查 `DetectionInitializer.initialize_services()` 是否成功
3. 重启检测进程

### 问题2：Redis订阅没有接收帧

**可能原因**：
- Redis连接失败
- 频道名称不匹配
- Redis订阅未启动

**解决方法**：
1. 检查Redis连接配置
2. 检查频道名称：`video:vid1`
3. 检查API服务器启动日志中的Redis订阅信息

### 问题3：WebSocket没有发送帧

**可能原因**：
- 没有客户端连接
- 发送队列异常
- WebSocket连接断开

**解决方法**：
1. 检查客户端连接状态
2. 检查发送队列大小
3. 检查WebSocket连接状态

### 问题4：前端没有显示

**可能原因**：
- 帧数据格式错误
- 图像显示逻辑错误
- 帧渲染失败

**解决方法**：
1. 检查浏览器控制台错误
2. 检查帧数据格式
3. 检查图像URL创建逻辑

## 日志级别说明

已将所有关键日志提升为 `INFO` 级别，便于查看：
- ✅ 视频帧推送：`logger.info`
- ✅ Redis发布：`logger.info`
- ✅ Redis接收：`logger.info`
- ✅ WebSocket发送：`logger.info`（每100帧）

## 下一步

1. **重启检测进程**，查看日志中是否有视频帧推送信息
2. **查看API服务器日志**，确认Redis订阅是否接收到帧
3. **检查浏览器控制台**，查看是否有帧数据接收
4. **如果仍然没有数据**，提供详细的日志信息以便进一步排查
