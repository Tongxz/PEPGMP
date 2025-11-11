# 日志输出策略规范

## 1. 日志级别定义

### DEBUG - 详细调试信息
- **用途**：开发调试、问题排查
- **输出频率**：低（每N次操作或重要状态变化）
- **生产环境**：通常关闭
- **示例**：
  - 函数进入/退出
  - 详细的中间状态
  - 高频操作的摘要（每100次记录一次）

### INFO - 一般信息
- **用途**：系统运行状态、重要事件
- **输出频率**：中等（每N次操作或定期）
- **生产环境**：保留
- **示例**：
  - 服务启动/停止
  - 连接建立/断开
  - 重要操作完成
  - 性能指标摘要

### WARNING - 警告信息
- **用途**：潜在问题、异常情况（但不影响功能）
- **输出频率**：低（每次发生）
- **生产环境**：保留
- **示例**：
  - 配置项缺失（使用默认值）
  - 性能下降
  - 资源使用率过高

### ERROR - 错误信息
- **用途**：错误、异常、功能失败
- **输出频率**：低（每次发生）
- **生产环境**：必须保留
- **示例**：
  - 连接失败
  - 操作失败
  - 异常捕获

## 2. 视频流日志策略

### 2.1 连接相关日志

#### 客户端连接
- **级别**：INFO
- **频率**：每次连接
- **内容**：
  ```
  INFO - 客户端已连接到视频流 [camera_id], 当前客户端数: X, 是否有缓存帧: True/False
  ```

#### 客户端断开
- **级别**：INFO
- **频率**：每次断开
- **内容**：
  ```
  INFO - 客户端已断开 [camera_id], 剩余客户端数: X
  ```

#### 连接失败
- **级别**：ERROR
- **频率**：每次失败
- **内容**：
  ```
  ERROR - 客户端连接失败 [camera_id]: {error}
  ```

### 2.2 Redis相关日志

#### Redis订阅启动
- **级别**：INFO
- **频率**：启动时一次
- **内容**：
  ```
  INFO - 视频流Redis订阅使用连接: redis://***@localhost:6379/0
  INFO - Redis连接测试成功: redis://***@localhost:6379/0
  INFO - 视频流Redis订阅已启动: redis://***@localhost:6379/0 (pattern=video:*)
  ```

#### Redis订阅失败
- **级别**：WARNING/ERROR
- **频率**：每次失败
- **内容**：
  ```
  ERROR - Redis连接测试失败: {error}
  WARNING - 视频流Redis订阅启动失败: {error}
  ```

#### Redis接收帧
- **级别**：INFO
- **频率**：每30帧或每100帧记录一次
- **内容**：
  ```
  INFO - Redis已接收帧: X (camera=vid1, size=XXX bytes, clients=Y)
  ```

### 2.3 视频帧推送日志

#### 检测进程推送
- **级别**：INFO（成功）/ WARNING（失败）
- **频率**：每N帧记录一次（可配置）
- **内容**：
  ```
  INFO - 准备推送视频帧: camera=vid1, frame=XXX, interval=3, has_annotations=True/False
  INFO - 视频帧已通过Redis推送: camera=vid1, size=XXX bytes
  INFO - Redis发布成功: channel=video:vid1, size=XXX bytes, subscribers=X
  WARNING - 视频帧推送失败: camera=vid1, frame=XXX
  ```

#### 推送频率建议
- **每帧推送**：每100帧记录一次
- **每3帧推送**：每30帧记录一次
- **每10帧推送**：每10帧记录一次

### 2.4 WebSocket发送日志

#### 帧发送成功
- **级别**：DEBUG
- **频率**：每100帧记录一次
- **内容**：
  ```
  DEBUG - 视频帧已发送到WebSocket: camera=vid1, total_sent=XXX, size=XXX bytes
  ```

#### 帧发送失败
- **级别**：WARNING
- **频率**：每次失败
- **内容**：
  ```
  WARNING - 发送失败，标记断开: camera=vid1, error={error}
  ```

#### 发送队列状态
- **级别**：DEBUG
- **频率**：每100帧记录一次
- **内容**：
  ```
  DEBUG - 帧已加入发送队列: camera=vid1, queue_size=X, total_received=XXX
  ```

#### 无客户端连接
- **级别**：DEBUG
- **频率**：每100帧记录一次（减少日志量）
- **内容**：
  ```
  DEBUG - 无客户端连接，跳过发送队列: camera=vid1 (已接收XXX帧)
  ```

### 2.5 性能统计日志

#### 统计摘要
- **级别**：INFO
- **频率**：每N分钟或重要事件
- **内容**：
  ```
  INFO - 视频流统计: total_connections=X, active_cameras=Y, frames_sent=Z, frames_dropped=W
  ```

## 3. 检测进程日志策略

### 3.1 初始化日志

#### 服务初始化
- **级别**：INFO
- **频率**：启动时一次
- **内容**：
  ```
  INFO - 检测循环服务已初始化: camera=vid1, stream_interval=3, video_stream_service=已配置
  ```

#### 视频流服务初始化
- **级别**：INFO
- **频率**：启动时一次
- **内容**：
  ```
  INFO - ✓ 视频流服务已启用
  WARNING - 视频流服务初始化失败: {error}，将禁用视频流推送
  ```

### 3.2 帧处理日志

#### 帧推送
- **级别**：INFO（成功）/ WARNING（失败）
- **频率**：每30帧记录一次（或可配置）
- **内容**：
  ```
  INFO - 准备推送视频帧: camera=vid1, frame=XXX, interval=3, has_annotations=True
  INFO - 视频帧推送成功: camera=vid1, frame=XXX
  INFO - 跳过检测但推送视频流: camera=vid1, frame=XXX, interval=3
  WARNING - 视频帧推送失败: camera=vid1, frame=XXX
  ```

#### 帧处理错误
- **级别**：ERROR
- **频率**：每次错误
- **内容**：
  ```
  ERROR - 处理帧 XXX 失败: {error}
  ERROR - 推送视频流失败: camera=vid1, frame=XXX, error={error}
  ```

### 3.3 性能统计日志

#### 统计报告
- **级别**：INFO
- **频率**：每N分钟或重要事件
- **内容**：
  ```
  INFO - 性能统计: 处理帧数=XXX, 处理时间=XXXs, 平均FPS=XX.X
  ```

## 4. 日志输出频率总结

### 高频操作（每帧或每N帧）
- **每帧推送**：每100帧记录一次
- **每3帧推送**：每30帧记录一次
- **每10帧推送**：每10帧记录一次

### 中频操作（周期性）
- **统计摘要**：每5-10分钟
- **性能报告**：每1-5分钟
- **状态检查**：每30秒-1分钟

### 低频操作（事件驱动）
- **连接/断开**：每次
- **错误/警告**：每次
- **服务启动/停止**：每次

## 5. 生产环境日志配置

### 推荐配置
- **DEBUG**：关闭（除非排查问题）
- **INFO**：保留（关键信息）
- **WARNING**：保留（必须）
- **ERROR**：保留（必须）

### 日志轮转
- **大小限制**：每个日志文件最大100MB
- **保留数量**：保留最近10个文件
- **压缩**：旧日志文件自动压缩

### 日志格式
- **时间戳**：ISO 8601格式
- **级别**：INFO/DEBUG/WARNING/ERROR
- **模块**：模块名称
- **消息**：详细描述

## 6. 调试模式日志配置

### 开发环境
- **DEBUG**：开启
- **INFO**：开启
- **WARNING**：开启
- **ERROR**：开启

### 日志输出频率
- **高频操作**：每10-30帧记录一次
- **中频操作**：每1-5分钟
- **低频操作**：每次

## 7. 日志性能考虑

### 避免日志阻塞
- 使用异步日志（如果支持）
- 避免在日志中执行复杂操作
- 使用合适的日志级别

### 减少日志量
- 避免在循环中频繁输出日志
- 使用摘要日志（每N次操作记录一次）
- 使用条件日志（只在特定条件下输出）

### 日志格式化
- 避免格式化大对象
- 使用延迟格式化（logger.debug(f"message: {value}") 只在DEBUG启用时格式化）
- 使用结构化日志（JSON格式）

## 8. 实施建议

### 当前优化
1. ✅ 减少"无客户端连接"日志频率（每100帧）
2. ✅ 减少队列日志频率（每100帧）
3. ✅ 提升关键事件日志级别（INFO）

### 进一步优化
1. 添加日志级别配置（环境变量控制）
2. 添加日志采样（每N帧采样一次）
3. 添加结构化日志（JSON格式）
4. 添加性能监控日志（延迟、吞吐量）

## 9. 示例配置

### 环境变量配置
```bash
# 日志级别
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# 视频流日志频率（每N帧记录一次）
VIDEO_STREAM_LOG_INTERVAL=30  # 每30帧记录一次

# 检测进程日志频率
DETECTION_LOG_INTERVAL=100  # 每100帧记录一次统计
```

### 代码配置
```python
# 使用环境变量控制日志频率
LOG_INTERVAL = int(os.getenv("VIDEO_STREAM_LOG_INTERVAL", "30"))

if frame_count % LOG_INTERVAL == 0:
    logger.info(f"视频帧推送: frame={frame_count}")
```
