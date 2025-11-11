# 视频流跨进程通信修复

## 问题描述

摄像头检测进程已启动，但实时监控大屏没有视频画面。

## 根本原因

检测进程和API服务器运行在不同的进程中，它们各自有独立的 `VideoStreamManager` 实例：

1. **检测进程**（子进程）：
   - 通过 `main.py --mode detection` 启动
   - 创建自己的 `VideoStreamManager` 实例
   - 调用 `video_stream_service.push_frame()` 更新本地实例的帧缓存

2. **API服务器**（父进程）：
   - 运行 FastAPI 应用
   - 有自己的 `VideoStreamManager` 实例
   - WebSocket 客户端连接到此实例

**问题**：检测进程推送的帧数据无法到达API服务器的 `VideoStreamManager`，因为它们是不同的进程实例。

## 解决方案

### 1. 使用 Redis Pub/Sub 跨进程通信

`VideoStreamManager` 已经支持 Redis 订阅机制，但检测进程需要**发布**帧到 Redis。

### 2. 修改 `VideoStreamApplicationService.push_frame()`

在 `VideoStreamApplicationService.push_frame()` 方法中：

1. **优先使用 Redis 发布**：如果 Redis 可用，将帧发布到 Redis 频道 `video:{camera_id}`
2. **回退到本地管理器**：如果 Redis 不可用，回退到本地 `VideoStreamManager.update_frame()`

### 3. 数据流

```
检测进程 (子进程)
  ↓ VideoStreamApplicationService.push_frame()
  ↓ 编码为JPEG
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

## 实现细节

### 1. 添加 `_push_via_redis()` 方法

```python
async def _push_via_redis(self, camera_id: str, jpeg_data: bytes) -> bool:
    """通过Redis发布视频帧（用于跨进程通信）"""
    # 1. 检查是否启用Redis
    # 2. 导入redis.asyncio
    # 3. 连接到Redis
    # 4. 发布到频道 video:{camera_id}
    # 5. 关闭连接
```

### 2. 修改 `push_frame()` 方法

```python
async def push_frame(...):
    # 1. 调整大小
    # 2. 编码为JPEG
    # 3. 优先尝试Redis发布
    # 4. 如果Redis失败，回退到本地管理器
```

## 配置要求

### 环境变量

- `VIDEO_STREAM_USE_REDIS`: 是否使用Redis（默认 "1"）
- `REDIS_URL`: Redis连接URL（可选）
- `REDIS_HOST`: Redis主机（默认 "localhost"）
- `REDIS_PORT`: Redis端口（默认 "6379"）
- `REDIS_DB`: Redis数据库（默认 "0"）
- `REDIS_PASSWORD`: Redis密码（可选）

### 依赖

- `redis.asyncio`: Redis异步客户端（可选依赖）

## 测试步骤

1. **确认Redis运行**：
   ```bash
   redis-cli ping
   # 应该返回 PONG
   ```

2. **启动API服务器**：
   ```bash
   python main.py --mode api
   ```
   查看日志，确认：
   - `视频流管理器已启动`
   - `视频流Redis订阅已启动: redis://...`

3. **启动检测进程**（通过API）：
   ```bash
   curl -X POST http://localhost:8000/api/v1/cameras/{camera_id}/start
   ```
   查看日志，确认：
   - `视频帧已通过Redis推送: camera=xxx`

4. **连接前端WebSocket**：
   - 打开实时监控大屏
   - 查看浏览器控制台，确认收到视频帧数据

5. **检查Redis消息**（可选）：
   ```bash
   redis-cli
   > PSUBSCRIBE video:*
   ```
   应该能看到视频帧数据在频道中发布

## 注意事项

1. **性能考虑**：
   - Redis 发布是异步的，不会阻塞检测进程
   - 如果 Redis 不可用，会自动回退到本地管理器（仅适用于同进程场景）

2. **错误处理**：
   - Redis 连接失败不影响检测进程运行
   - 仅记录调试日志，不抛出异常

3. **兼容性**：
   - 如果未安装 `redis`，自动跳过 Redis 推送
   - 如果 Redis 未启用（`VIDEO_STREAM_USE_REDIS=0`），跳过 Redis 推送

## 后续优化

1. **连接池**：使用 Redis 连接池，避免每次发布都创建新连接
2. **批量发布**：如果有多帧待发布，可以批量发布以减少网络开销
3. **监控指标**：添加 Redis 发布成功率、延迟等监控指标
