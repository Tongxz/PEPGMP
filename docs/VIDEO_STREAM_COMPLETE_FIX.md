# 视频流问题完整修复报告

## 问题总结

### 发现的问题

1. **❌ Redis连接问题**
   - Redis在Docker容器中运行，密码为 `pyt_dev_redis`
   - 检测进程启动时未设置Redis密码环境变量
   - 导致视频帧无法通过Redis发布

2. **❌ 跳帧逻辑问题**
   - `log_interval=120` 导致每120帧才处理一次
   - 视频流推送依赖 `_process_frame`，导致推送频率极低
   - 实际推送间隔：120帧（检测间隔） × 3（stream_interval）= 360帧

3. **❌ 视频流推送与检测逻辑耦合**
   - 视频流推送在 `_process_frame` 中，与检测逻辑绑定
   - 跳过的帧不会推送视频流

## 修复内容

### 1. 修复跳帧逻辑 ✅

**文件**: `src/application/detection_loop_service.py`

**修改**:
- 分离检测逻辑和视频流推送逻辑
- 即使跳过检测，也要推送视频流（使用原始帧）
- 确保视频流的实时性，不受检测频率影响

**效果**:
- 视频流推送频率：每 `stream_interval` 帧（默认3帧）
- 检测频率：每 `log_interval` 帧（默认120帧）
- 两者独立，互不影响

### 2. 修复Redis环境变量传递 ✅

**文件**: `src/services/executors/local.py`

**修改**:
- 检测进程启动时自动设置Redis环境变量
- 如果未设置 `REDIS_URL`，自动从环境变量构建
- 默认密码：`pyt_dev_redis`（Docker Redis默认密码）
- 确保 `VIDEO_STREAM_USE_REDIS=1`

**效果**:
- 检测进程启动时自动配置Redis连接
- 无需手动设置环境变量
- 视频帧可以正常发布到Redis

### 3. 增强日志和调试 ✅

**文件**:
- `src/application/detection_loop_service.py`
- `src/services/video_stream_manager.py`
- `src/application/video_stream_application_service.py`

**修改**:
- 添加详细的调试日志
- 记录Redis连接状态
- 记录视频帧推送成功/失败
- 记录Redis订阅状态

**效果**:
- 更容易排查问题
- 清晰的日志信息

## 数据流（修复后）

```
检测进程 (子进程)
  ↓ 读取每一帧
  ↓ frame_count++
  ↓
  ├─ log_interval匹配（每120帧）
  │  ├─ 处理检测和保存
  │  └─ 如果stream_interval匹配 → 推送标注后的帧
  │
  └─ log_interval不匹配
     └─ 如果stream_interval匹配（每3帧） → 推送原始帧
  ↓
  ↓ 通过Redis发布到 video:{camera_id}
  ↓ Redis连接: redis://:pyt_dev_redis@localhost:6379/0
  ↓
Redis Pub/Sub (Docker容器)
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

### 1. 验证Redis运行
```bash
docker exec pyt-redis-dev redis-cli -a pyt_dev_redis ping
# 应该返回 PONG
```

### 2. 重启检测进程
```bash
# 停止
curl -X POST http://localhost:8000/api/v1/cameras/vid1/stop

# 启动
curl -X POST http://localhost:8000/api/v1/cameras/vid1/start
```

### 3. 检查检测进程日志
```bash
tail -f logs/detect_vid1.log | grep -i "视频\|redis\|stream\|推送"
```

**应该看到**:
- `检测循环服务已初始化: camera=vid1, stream_interval=3, video_stream_service=已配置`
- `准备推送视频帧: camera=vid1, frame=X, interval=3`
- `视频帧已通过Redis推送: camera=vid1`
- `Redis发布成功: channel=video:vid1, subscribers=X`

### 4. 检查API服务器日志
查看API服务器日志，查找：
- `视频流Redis订阅已启动`
- `Redis已接收帧: X (camera=vid1)`
- `客户端已连接到视频流 [vid1], 是否有缓存帧: True`
- `帧已加入发送队列: camera=vid1`

### 5. 测试前端
- 打开实时监控大屏
- 应该能看到视频画面
- 浏览器控制台应该看到 `[VideoStreamCard] 收到视频帧数据`

## 配置参数

### 视频流相关环境变量
- `VIDEO_STREAM_USE_REDIS`: 是否使用Redis（默认 "1"）
- `VIDEO_STREAM_INTERVAL`: 推送间隔（默认 3，每3帧推送一次）
- `VIDEO_STREAM_QUALITY`: JPEG质量（默认 60，范围1-100）
- `VIDEO_STREAM_WIDTH`: 视频宽度（默认 800）
- `VIDEO_STREAM_HEIGHT`: 视频高度（默认 450）

### Redis连接环境变量
- `REDIS_URL`: Redis连接URL（优先）
- `REDIS_HOST`: Redis主机（默认 "localhost"）
- `REDIS_PORT`: Redis端口（默认 "6379"）
- `REDIS_PASSWORD`: Redis密码（默认 "pyt_dev_redis"）
- `REDIS_DB`: Redis数据库（默认 "0"）

### 检测相关参数
- `log_interval`: 检测间隔（默认从命令行参数，当前为120）
- `stream_interval`: 视频流推送间隔（默认3，从环境变量读取）

## 性能优化建议

### 当前配置
- **检测频率**: 每120帧检测一次（降低CPU使用）
- **视频流频率**: 每3帧推送一次（保证实时性）
- **视频质量**: 60（平衡质量和带宽）
- **视频尺寸**: 800x450（降低带宽）

### 优化建议
1. **降低stream_interval**: 如果网络带宽充足，可以设置为1（每帧推送）
2. **提高视频质量**: 如果带宽充足，可以提高到70-80
3. **调整视频尺寸**: 根据前端显示需求调整

## 故障排查

### 如果仍然没有视频画面

1. **检查Redis连接**
   ```bash
   docker exec pyt-redis-dev redis-cli -a pyt_dev_redis ping
   ```

2. **检查检测进程日志**
   - 查看是否有 `Redis发布成功` 日志
   - 查看是否有 `视频帧推送失败` 错误

3. **检查API服务器日志**
   - 查看是否有 `Redis已接收帧` 日志
   - 查看是否有 `Redis订阅启动失败` 错误

4. **检查WebSocket连接**
   - 浏览器控制台查看WebSocket连接状态
   - 查看是否有 `收到视频帧数据` 日志

5. **监控Redis频道**
   ```bash
   docker exec pyt-redis-dev redis-cli -a pyt_dev_redis
   > PSUBSCRIBE video:*
   ```
   应该能看到视频帧数据在频道中发布

## 总结

### 修复的问题
✅ Redis环境变量自动传递
✅ 跳帧逻辑修复（视频流推送不受log_interval影响）
✅ 增强日志和调试信息

### 修复后的效果
- 视频流推送频率：每3帧（可配置）
- 检测频率：每120帧（可配置）
- 两者独立，互不影响
- Redis连接自动配置

### 下一步
1. 重启检测进程，验证修复效果
2. 查看日志，确认视频帧正常推送
3. 测试前端，确认视频画面正常显示
