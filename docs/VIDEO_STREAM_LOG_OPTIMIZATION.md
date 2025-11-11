# 视频流日志优化

## 问题

视频流功能正常工作，但后台日志一直在刷：
```
DEBUG - 无客户端连接，跳过发送队列: camera=vid1
```

## 原因

在Redis订阅循环中，每次接收到视频帧时都会检查是否有客户端连接。如果没有客户端连接，就会输出DEBUG日志。由于视频帧接收频率很高（每3帧推送一次），导致日志输出频繁。

## 修复方案

### 1. 减少日志输出频率

**修改前**：每帧都输出日志
```python
if not has_clients:
    logger.debug(f"无客户端连接，跳过发送队列: camera={camera_id}")
```

**修改后**：只在第一次或每100帧记录一次
```python
if not has_clients:
    # 只在第一次或每100帧记录一次（减少日志输出）
    if self.stats["frames_received"] == 1 or self.stats["frames_received"] % 100 == 0:
        logger.debug(f"无客户端连接，跳过发送队列: camera={camera_id} (已接收{self.stats['frames_received']}帧)")
```

### 2. 优化队列日志

**修改前**：每帧都输出队列日志
```python
logger.debug(f"帧已加入发送队列: camera={camera_id}, queue_size={self.send_queue.qsize()}")
```

**修改后**：每100帧记录一次
```python
# 每100帧记录一次队列日志（减少日志输出）
if self.stats["frames_received"] % 100 == 0:
    logger.debug(f"帧已加入发送队列: camera={camera_id}, queue_size={self.send_queue.qsize()}")
```

### 3. 提升缓存帧发送日志级别

**修改前**：DEBUG级别
```python
logger.debug(f"已发送缓存帧到新客户端 [{camera_id}]")
```

**修改后**：INFO级别（因为这是一个重要事件）
```python
logger.info(f"已发送缓存帧到新客户端 [{camera_id}], 帧大小={len(self.frame_cache[camera_id])} bytes")
```

## 效果

- ✅ 减少不必要的DEBUG日志输出
- ✅ 保持关键信息日志（每100帧或重要事件）
- ✅ 不影响功能正常运行
- ✅ 日志更清晰，便于排查问题

## 日志输出策略

### 高频日志（减少输出）
- 无客户端连接：每100帧记录一次
- 帧加入队列：每100帧记录一次

### 中频日志（保持）
- Redis接收帧：每30帧记录一次（INFO级别）
- WebSocket发送帧：每100帧记录一次（INFO级别）

### 重要事件（立即记录）
- 客户端连接/断开：立即记录（INFO级别）
- 发送缓存帧：立即记录（INFO级别）
- 错误和警告：立即记录（WARNING/ERROR级别）
