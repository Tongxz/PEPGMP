# 架构日志规范

## 📋 概述

本文档定义了基于DDD架构的日志规范，确保日志记录符合架构分层原则和软件工程最佳实践。

**更新日期**: 2025-11-06
**架构状态**: ✅ **符合DDD架构要求**

---

## 1. 日志工具和配置

### 1.1 日志工具

统一使用 `src.utils.logger.get_logger()` 获取日志记录器：

```python
import logging

# 使用模块名作为日志记录器名称
logger = logging.getLogger(__name__)
```

### 1.2 日志文件位置

- **所有日志文件**统一存放在 `logs/` 目录下
- 日志文件命名：`{module_name}_{timestamp}.log`
- 支持日志轮转和压缩

### 1.3 日志格式

标准日志格式：
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

时间格式：
```
%Y-%m-%d %H:%M:%S
```

示例输出：
```
2025-11-06 11:23:47.079 - src.services.video_stream_manager - INFO - 客户端已连接到视频流 [vid1]
```

---

## 2. 日志级别定义

### DEBUG - 详细调试信息
- **用途**: 开发调试、问题排查
- **输出频率**: 低频或摘要（每N次操作）
- **生产环境**: 通常关闭
- **示例**:
  ```python
  logger.debug(f"帧已加入发送队列: camera={camera_id}, queue_size={queue_size}")
  logger.debug(f"查询完成: camera_id={camera_id}, count={len(records)}")
  ```

### INFO - 一般信息
- **用途**: 系统运行状态、重要事件
- **输出频率**: 事件驱动或周期性（每N次操作）
- **生产环境**: 保留
- **示例**:
  ```python
  logger.info(f"客户端已连接到视频流 [camera_id]")
  logger.info(f"检测记录已保存: id={record_id}")
  logger.info(f"Redis已接收帧: 30 (camera=vid1, size=50KB, clients=2)")
  ```

### WARNING - 警告信息
- **用途**: 潜在问题、异常情况（但不影响功能）
- **输出频率**: 每次发生
- **生产环境**: 保留
- **示例**:
  ```python
  logger.warning(f"发送队列已满，丢弃帧: camera={camera_id}")
  logger.warning(f"配置项缺失，使用默认值: {config_key}")
  ```

### ERROR - 错误信息
- **用途**: 错误、异常、功能失败
- **输出频率**: 每次发生
- **生产环境**: 必须保留
- **示例**:
  ```python
  logger.error(f"客户端连接失败 [camera_id]: {error}")
  logger.error(f"保存检测记录失败: camera_id={camera_id}, error={e}", exc_info=True)
  ```

---

## 3. 日志输出频率规范

### 3.1 高频操作（每帧或每N帧）

| 操作 | 级别 | 频率 | 示例 |
|------|------|------|------|
| 视频帧推送成功 | INFO | 每30帧 | `视频帧推送成功: camera=vid1, frame=90` |
| Redis接收帧 | INFO | 每30帧 | `Redis已接收帧: 30 (camera=vid1, size=50KB, clients=2)` |
| 无客户端连接 | DEBUG | 每100帧 | `无客户端连接，跳过发送队列: camera=vid1 (已接收100帧)` |
| 帧加入队列 | DEBUG | 每100帧 | `帧已加入发送队列: camera=vid1, queue_size=5` |

### 3.2 中频操作（周期性）

| 操作 | 级别 | 频率 | 示例 |
|------|------|------|------|
| 性能统计 | INFO | 每5-10分钟 | `性能统计: 处理帧数=3000, 平均FPS=25.5` |
| 状态检查 | INFO | 每30秒-1分钟 | `视频流统计: active_cameras=2, frames_sent=5000` |

### 3.3 低频操作（事件驱动）

| 操作 | 级别 | 频率 | 示例 |
|------|------|------|------|
| 客户端连接 | INFO | 每次 | `客户端已连接到视频流 [vid1]` |
| 客户端断开 | INFO | 每次 | `客户端已断开 [vid1], 剩余客户端数: 0` |
| 服务启动 | INFO | 每次 | `检测循环服务已初始化: camera=vid1` |
| 服务停止 | INFO | 每次 | `检测循环服务已停止: camera=vid1` |
| 错误/警告 | WARNING/ERROR | 每次 | `保存检测记录失败: camera_id=vid1, error={error}` |

---

## 4. 分层架构日志规范

### 4.1 API层 (`src/api/`)

**职责**: HTTP请求处理、参数验证、响应格式化

**日志规范**:
- ✅ 记录请求开始和结束（INFO级别）
- ✅ 记录参数信息（DEBUG级别）
- ✅ 记录错误和异常（ERROR级别，包含 `exc_info=True`）
- ❌ 不记录业务逻辑细节

**示例**:
```python
@router.get("/detection/{camera_id}")
async def get_detection_records(
    camera_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[DetectionRecordDTO]:
    """获取检测记录列表"""
    try:
        logger.info(f"获取检测记录: camera_id={camera_id}, start_time={start_time}, end_time={end_time}")

        domain_service = _ensure_domain_service()
        records = await domain_service.get_detection_records_by_camera(
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time
        )

        logger.debug(f"查询完成: camera_id={camera_id}, count={len(records)}")
        return [record_to_dto(r) for r in records]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取检测记录失败: camera_id={camera_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")
```

### 4.2 应用层 (`src/application/`)

**职责**: 用例编排、DTO转换、事务协调

**日志规范**:
- ✅ 记录用例开始和结束（INFO级别）
- ✅ 记录关键业务步骤（DEBUG级别）
- ✅ 记录错误和异常（ERROR级别）

**示例**:
```python
class DetectionApplicationService:
    async def process_realtime_stream(
        self, camera_id: str, frame: np.ndarray, frame_count: int
    ) -> Dict[str, Any]:
        """处理实时流"""
        try:
            logger.info(f"处理实时流: camera_id={camera_id}, frame={frame_count}")

            # 1. 执行检测
            detection_result = await self.detection_service.process_detection(...)
            logger.debug(f"检测完成: camera_id={camera_id}, objects={len(detection_result.objects)}")

            # 2. 保存记录
            saved_record = await self.detection_repository.save(detection_result)
            logger.info(f"记录已保存: camera_id={camera_id}, record_id={saved_record.id}")

            return {"saved_to_db": True, "record_id": saved_record.id}

        except Exception as e:
            logger.error(f"处理实时流失败: camera_id={camera_id}, frame={frame_count}, error={e}", exc_info=True)
            raise
```

### 4.3 领域层 (`src/domain/`)

**职责**: 业务逻辑、领域规则、领域模型

**日志规范**:
- ✅ 记录领域规则验证（DEBUG级别）
- ✅ 记录业务逻辑执行（INFO级别）
- ✅ 记录领域异常（ERROR级别）
- ❌ 不记录技术实现细节（如数据库操作）

**示例**:
```python
class DetectionService:
    async def process_detection(self, record: DetectionRecord) -> DetectionRecord:
        """处理检测记录（领域服务）"""
        logger.info(f"处理检测记录: camera_id={record.camera_id}, frame_id={record.frame_id}")

        # 1. 验证领域规则
        if not record.objects:
            logger.warning(f"检测记录无对象: camera_id={record.camera_id}, frame_id={record.frame_id}")
            return record

        # 2. 检测违规行为
        violations = self.violation_service.detect_violations(record)
        if violations:
            logger.info(f"检测到违规: camera_id={record.camera_id}, violations={len(violations)}")
            record.add_metadata("violations", [v.__dict__ for v in violations])

        logger.debug(f"检测处理完成: camera_id={record.camera_id}, objects={len(record.objects)}, violations={len(violations)}")
        return record
```

### 4.4 基础设施层 (`src/infrastructure/`)

**职责**: 仓储实现、外部服务集成、技术实现

**日志规范**:
- ✅ 记录数据库操作（DEBUG级别）
- ✅ 记录连接状态（INFO级别）
- ✅ 记录技术错误（ERROR级别，包含 `exc_info=True`）
- ✅ 记录性能指标（INFO级别，周期性）

**示例**:
```python
class PostgreSQLDetectionRepository:
    async def save(self, record: DetectionRecord) -> str:
        """保存检测记录（仓储实现）"""
        conn = None
        try:
            logger.debug(f"保存检测记录: camera_id={record.camera_id}, id={record.id}")

            conn = await self._get_connection()
            # ... 数据库操作

            logger.info(f"检测记录已保存: id={saved_id}, camera_id={record.camera_id}")
            return saved_id

        except Exception as e:
            logger.error(f"保存检测记录失败: camera_id={record.camera_id}, error={e}", exc_info=True)
            raise RepositoryError(f"保存失败: {e}")
        finally:
            if conn:
                await self._release_connection(conn)
```

---

## 5. 日志性能优化

### 5.1 避免频繁日志输出

**❌ 错误做法**:
```python
# 在循环中每帧都输出日志
for frame in frames:
    logger.debug(f"处理帧: {frame.frame_id}")  # 每帧都输出，性能差
```

**✅ 正确做法**:
```python
# 每N帧记录一次摘要
for i, frame in enumerate(frames):
    if i % 100 == 0:
        logger.debug(f"已处理帧: {i}, 当前帧={frame.frame_id}")
```

### 5.2 使用条件日志

**❌ 错误做法**:
```python
# 即使DEBUG关闭，也会执行字符串格式化
logger.debug(f"复杂对象: {expensive_format_operation(obj)}")
```

**✅ 正确做法**:
```python
# 只在DEBUG启用时执行格式化
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"复杂对象: {expensive_format_operation(obj)}")
```

### 5.3 避免在日志中执行复杂操作

**❌ 错误做法**:
```python
# 在日志中执行数据库查询
logger.debug(f"记录数: {await db.count_records()}")
```

**✅ 正确做法**:
```python
# 先查询，再记录
count = await db.count_records()
logger.debug(f"记录数: {count}")
```

---

## 6. 生产环境日志配置

### 6.1 日志级别

```bash
# 生产环境
LOG_LEVEL=INFO  # 关闭DEBUG，保留INFO/WARNING/ERROR

# 开发环境
LOG_LEVEL=DEBUG  # 开启所有日志
```

### 6.2 日志轮转

- **单个文件最大**: 100MB
- **保留文件数**: 10个
- **自动压缩**: 旧日志文件自动压缩

### 6.3 日志格式

生产环境使用结构化日志（JSON格式）便于日志聚合和分析：

```json
{
  "timestamp": "2025-11-06T11:23:47.079Z",
  "level": "INFO",
  "module": "src.services.video_stream_manager",
  "message": "客户端已连接到视频流 [vid1]",
  "context": {
    "camera_id": "vid1",
    "client_count": 1
  }
}
```

---

## 7. 日志审查检查清单

在提交代码前，请确保：

- [ ] 使用 `logging.getLogger(__name__)` 获取日志记录器
- [ ] 日志文件存放在 `logs/` 目录下
- [ ] 日志级别使用正确（DEBUG/INFO/WARNING/ERROR）
- [ ] 高频操作使用摘要日志（每N次记录一次）
- [ ] 错误日志包含 `exc_info=True`
- [ ] 日志消息包含足够的上下文信息
- [ ] 避免在循环中频繁输出日志
- [ ] 避免在日志中执行复杂操作

---

## 8. 参考文档

- [日志输出策略规范](./LOGGING_STRATEGY.md)
- [视频流日志优化](./VIDEO_STREAM_LOG_OPTIMIZATION.md)
- [系统架构文档](./SYSTEM_ARCHITECTURE.md)
