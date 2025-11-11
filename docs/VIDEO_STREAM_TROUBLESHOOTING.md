# 视频流问题排查指南

## 当前状态

✅ WebSocket连接成功（状态码101）
✅ 前端连接无报错
✅ 后端无报错
❌ Redis频道订阅数为0（关键问题）
❌ 没有视频数据

## 问题分析

### 1. Redis订阅数为0 ⚠️

**现象**：`docker exec pyt-redis-dev redis-cli -a pyt_dev_redis PUBSUB NUMSUB video:vid1` 返回 `0`

**原因**：API服务器的Redis订阅任务没有成功启动或连接失败

**可能的原因**：
1. Redis连接配置错误（密码不匹配）
2. Redis订阅任务启动失败
3. 环境变量 `VIDEO_STREAM_USE_REDIS` 被设置为 "0"
4. `redis.asyncio` 未安装

### 2. 检测进程日志为空 ⚠️

**现象**：检测进程日志中没有视频流相关日志

**可能的原因**：
1. 检测进程已停止
2. 日志文件路径错误
3. 视频流服务未初始化

## 修复步骤

### 步骤1：检查API服务器启动日志

查看API服务器启动时的日志，查找：
- `正在初始化视频流管理器...`
- `视频流管理器已初始化并启动`
- `视频流Redis订阅配置: enable_redis=...`
- `视频流Redis订阅使用连接: ...`
- `Redis连接测试成功`
- `视频流Redis订阅已启动`

**如果没有看到这些日志**，说明：
- VideoStreamManager初始化失败
- Redis订阅任务启动失败

### 步骤2：检查Redis连接配置

确保API服务器启动时设置了正确的Redis环境变量：

```bash
# 检查环境变量
echo $REDIS_URL
echo $REDIS_PASSWORD
```

**如果没有设置**，API服务器会使用默认值：
- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`
- `REDIS_PASSWORD=pyt_dev_redis`（已修复，现在有默认值）
- `REDIS_DB=0`

### 步骤3：重启API服务器

重启API服务器以应用修复：

```bash
# 停止API服务器（Ctrl+C）
# 然后重新启动
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**查看启动日志**，确认：
- `视频流管理器已初始化并启动`
- `视频流Redis订阅已启动`
- `Redis连接测试成功`

### 步骤4：重启检测进程

重启检测进程以应用修复：

```bash
# 停止
curl -X POST http://localhost:8000/api/v1/cameras/vid1/stop

# 启动
curl -X POST http://localhost:8000/api/v1/cameras/vid1/start
```

**查看检测进程日志**：
```bash
tail -f logs/detect_vid1.log | grep -i "视频\|推送\|redis\|stream"
```

**应该看到**：
- `检测循环服务已初始化: camera=vid1, stream_interval=3, video_stream_service=已配置`
- `准备推送视频帧` 或 `跳过检测但推送视频流`
- `Redis发布成功: channel=video:vid1`

### 步骤5：验证Redis订阅

重启API服务器后，检查Redis订阅数：

```bash
docker exec pyt-redis-dev redis-cli -a pyt_dev_redis PUBSUB NUMSUB video:vid1
```

**应该返回**：`1`（表示有1个订阅者）

### 步骤6：监控Redis频道

在另一个终端监控Redis频道：

```bash
docker exec -it pyt-redis-dev redis-cli -a pyt_dev_redis
> PSUBSCRIBE video:*
```

**如果看到消息**，说明检测进程正在发布，API服务器应该能接收到。

## 已应用的修复

### 1. Redis密码默认值 ✅
- `VideoStreamManager._redis_subscribe_loop()` 现在使用默认密码 `pyt_dev_redis`
- `VideoStreamApplicationService._push_via_redis()` 现在使用默认密码 `pyt_dev_redis`
- `LocalProcessExecutor` 现在自动设置Redis环境变量

### 2. 增强日志 ✅
- 所有关键日志提升为 `INFO` 级别
- 添加Redis连接测试日志
- 添加Redis订阅任务启动日志

### 3. 跳帧逻辑修复 ✅
- 视频流推送不受 `log_interval` 影响
- 即使跳过检测，也会推送原始帧

## 下一步操作

1. **重启API服务器**，查看启动日志中是否有Redis订阅启动信息
2. **重启检测进程**，查看日志中是否有视频帧推送信息
3. **检查Redis订阅数**，确认是否有订阅者
4. **测试前端**，确认视频画面是否显示

如果仍然没有视频数据，请提供：
- API服务器启动日志（特别是VideoStreamManager相关）
- 检测进程日志（特别是视频流推送相关）
- Redis订阅数检查结果
