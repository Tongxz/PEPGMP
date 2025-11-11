# 视频流功能修复报告

## 问题描述

前端点击启动摄像头后，查看视频功能显示"已连接"，但无法看到视频内容。

## 问题分析

### 1. 前端功能
- ✅ WebSocket连接正常：前端可以连接到 `/api/v1/video-stream/ws/{camera_id}`
- ✅ 连接状态显示正常：前端显示"🟢 已连接"
- ✅ 数据接收逻辑正常：前端正确处理JPEG二进制数据

### 2. 后端接口
- ✅ WebSocket端点正常：`/api/v1/video-stream/ws/{camera_id}` 可以接收连接
- ✅ VideoStreamManager已初始化：在FastAPI lifespan中调用 `init_stream_manager()`
- ✅ 后台任务已启动：发送循环和Redis订阅循环都在运行

### 3. 问题根源
❌ **main.py 第669-671行：视频流推送逻辑被注释掉了！**
```python
if stream_enabled and frame_count % STREAM_INTERVAL == 0:
    # ... (video stream logic remains unchanged)
    pass  # ← 这里只是pass，没有实际推送逻辑
```

**结果**：
- 检测进程没有将视频帧编码为JPEG
- 没有通过Redis发布视频帧
- VideoStreamManager没有收到任何帧数据
- 前端连接后没有收到任何数据

## 修复方案

### 1. 实现视频流推送逻辑（main.py）

在 `_run_detection_loop` 函数中，当 `stream_enabled` 且满足推送间隔时：

1. **选择帧**：使用标注后的图像（如果有）或原始帧
2. **调整大小**：如果配置了 `VIDEO_STREAM_WIDTH` 和 `VIDEO_STREAM_HEIGHT`，调整帧大小
3. **编码为JPEG**：使用OpenCV的 `cv2.imencode()` 编码为JPEG格式
4. **发布到Redis**：通过Redis Pub/Sub发布到 `video:{camera_id}` 频道

### 2. 数据流

```
检测进程 (main.py)
  ↓ 每STREAM_INTERVAL帧处理一次
  ↓ 编码为JPEG
  ↓ 发布到Redis: video:{camera_id}
  ↓
VideoStreamManager (Redis订阅)
  ↓ 接收视频帧
  ↓ 更新帧缓存
  ↓ 发送到WebSocket队列
  ↓
前端WebSocket客户端
  ↓ 接收JPEG数据
  ↓ 显示在img标签中
```

### 3. 配置参数

- `VIDEO_STREAM_INTERVAL`: 推送间隔（默认3，每3帧推送一次）
- `VIDEO_STREAM_QUALITY`: JPEG质量（默认70，范围0-100）
- `VIDEO_STREAM_WIDTH`: 视频宽度（默认1280）
- `VIDEO_STREAM_HEIGHT`: 视频高度（默认720）
- `VIDEO_STREAM_USE_REDIS`: 是否使用Redis（默认1）

## 修复内容

### main.py 修复

在 `_run_detection_loop` 函数中，替换了空的视频流推送逻辑：

```python
if stream_enabled and frame_count % STREAM_INTERVAL == 0:
    # 视频流推送：将帧编码为JPEG并通过Redis发布
    try:
        # 使用标注后的图像（如果有）或原始帧
        stream_frame = result.annotated_image if result.annotated_image is not None else frame

        # 调整帧大小（如果配置了）
        STREAM_WIDTH = int(os.getenv("VIDEO_STREAM_WIDTH", "1280"))
        STREAM_HEIGHT = int(os.getenv("VIDEO_STREAM_HEIGHT", "720"))
        if STREAM_WIDTH > 0 and STREAM_HEIGHT > 0:
            stream_frame = cv2.resize(stream_frame, (STREAM_WIDTH, STREAM_HEIGHT))

        # 编码为JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, VIDEO_QUALITY]
        success, jpeg_data = cv2.imencode('.jpg', stream_frame, encode_params)

        if success and jpeg_data is not None:
            jpeg_bytes = jpeg_data.tobytes()

            # 通过Redis发布到video:{camera_id}频道
            if redis_client_stats:
                try:
                    redis_client_stats.publish(f"video:{camera_id}", jpeg_bytes)
                except Exception as e:
                    logger.debug(f"发布视频帧到Redis失败: {e}")
            else:
                logger.debug("Redis未连接，无法发布视频帧")
    except Exception as e:
        logger.debug(f"视频流推送失败: {e}")
```

## 验证步骤

1. **启动后端服务**：确保VideoStreamManager已初始化
2. **启动摄像头检测**：确保检测进程正在运行
3. **检查Redis连接**：确保Redis已连接且正常
4. **前端连接WebSocket**：打开视频流弹窗
5. **检查帧数据**：查看前端是否收到JPEG数据并显示

## 预期结果

- ✅ 前端WebSocket连接成功
- ✅ 前端收到视频帧数据（JPEG格式）
- ✅ 前端正确显示视频画面
- ✅ FPS和延迟统计正常显示

## 注意事项

1. **Redis必须运行**：视频流通过Redis Pub/Sub传递，Redis必须正常运行
2. **摄像头必须启动**：检测进程必须正在运行才能推送视频帧
3. **帧率控制**：通过 `VIDEO_STREAM_INTERVAL` 控制推送频率，避免过度占用带宽
4. **质量平衡**：通过 `VIDEO_STREAM_QUALITY` 平衡视频质量和带宽占用
