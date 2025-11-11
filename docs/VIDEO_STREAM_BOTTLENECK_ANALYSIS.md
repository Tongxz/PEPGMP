# 视频推送卡顿瓶颈分析

## 统计数据

- **frames_received**: 53（Redis收到53帧）
- **frames_sent**: 34（WebSocket发送了34帧）
- **发送率**: 34/53 = **64%** ❌
- **丢帧率**: 36%

这说明有约36%的帧没有被发送出去！

## 主要瓶颈分析

### 1. ⚠️ WebSocket发送阻塞（最可能）

**问题**：
- `await websocket.send_bytes()` 是同步阻塞的
- 如果客户端接收慢，会阻塞整个发送循环
- 多个客户端时，会串行发送（for循环）

**当前代码**：
```python
for websocket in clients:
    try:
        await websocket.send_bytes(frame_data)  # 串行发送，阻塞
        self.stats["frames_sent"] += 1
    except Exception as e:
        logger.debug(f"发送失败，标记断开: {e}")
        disconnected.add(websocket)
```

**影响**：
- 如果客户端接收慢，会阻塞发送
- 队列会堆积，导致丢帧
- 发送率只有64%

### 2. ⚠️ 队列处理速度慢

**问题**：
- 队列大小200，但处理可能跟不上
- 如果发送慢，队列会堆积
- 队列满时会丢帧

**当前代码**：
```python
# 如果队列快满了，尝试丢弃旧帧
if self.send_queue.qsize() > 150:
    try:
        self.send_queue.get_nowait()  # 丢弃旧帧
        self.stats["frames_dropped"] += 1
    except asyncio.QueueEmpty:
        pass
```

### 3. ⚠️ 前端渲染速度慢

**问题**：
- requestAnimationFrame受浏览器刷新率限制（60fps）
- 如果接收快但渲染慢，会导致卡顿
- Blob URL创建开销大

**当前代码**：
```typescript
ws.onmessage = (event) => {
  const blob = new Blob([event.data], { type: 'image/jpeg' })
  const url = URL.createObjectURL(blob)  // 创建Blob URL
  // ...
}
```

### 4. ⚠️ 网络带宽限制

**数据量**：
- 每帧约168KB（800x450 JPEG质量60）
- 15fps需要约2.5MB/s
- 如果网络带宽不足，会阻塞发送

### 5. ⚠️ Redis Pub/Sub延迟

**影响**：
- 检测进程 → Redis → VideoStreamManager
- 增加了一层延迟（但影响较小）

### 6. ⚠️ JPEG编码时间

**影响**：
- 编码时间约1.34ms（影响较小）
- 但如果在检测进程中同步进行，可能影响检测

## 优化建议

### 1. 优化WebSocket发送（并行发送）

**方案**：使用`asyncio.gather()`并行发送给多个客户端

```python
# 并行发送给所有客户端
if clients:
    send_tasks = [
        self._send_frame_safe(ws, frame_data, camera_id)
        for ws in clients
    ]
    results = await asyncio.gather(*send_tasks, return_exceptions=True)
    # 处理结果...
```

**优势**：
- 并行发送，不阻塞
- 单个客户端慢不影响其他客户端
- 提高发送速度

### 2. 优化队列处理

**方案**：增加队列处理速度，丢弃旧帧保留新帧

```python
# 如果队列满，丢弃旧帧
if self.send_queue.qsize() > 150:
    try:
        self.send_queue.get_nowait()  # 丢弃旧帧
        self.stats["frames_dropped"] += 1
    except asyncio.QueueEmpty:
        pass
```

**优势**：
- 确保队列不阻塞
- 保留最新帧，丢弃旧帧

### 3. 优化前端渲染

**方案**：使用更高效的渲染方式

```typescript
// 使用Image对象直接显示，避免Blob URL
const img = new Image()
img.onload = () => {
  currentFrame.value = img.src
  img.onerror = null
}
img.src = URL.createObjectURL(blob)
```

**优势**：
- 减少Blob URL创建开销
- 更高效的渲染

### 4. 降低数据量

**方案**：进一步降低分辨率或质量

```python
# 降低分辨率
STREAM_WIDTH = 640
STREAM_HEIGHT = 360

# 降低质量
VIDEO_QUALITY = 50
```

**优势**：
- 减少数据传输量
- 提高传输速度

### 5. 使用更高效的编码方式

**方案**：使用WebP或更高效的编码

```python
# 使用WebP编码（更小文件）
encode_params = [cv2.IMWRITE_WEBP_QUALITY, 60]
success, webp_data = cv2.imencode('.webp', stream_frame, encode_params)
```

**优势**：
- 文件更小
- 传输更快

## 优先级

1. **高优先级**：优化WebSocket发送（并行发送）
2. **中优先级**：优化队列处理
3. **低优先级**：优化前端渲染、降低数据量
