# 摄像头检测流程架构评审

## 📋 概览

本文档评审从前端点击启动检测到记录保存、视频查看、日志查看的完整流程，判断是否符合最新的领域驱动设计(DDD)架构。

评审时间：2025-11-04
评审范围：摄像头检测全流程

---

## 🔍 完整流程分析

### 1. 启动检测流程

#### 1.1 前端发起
```typescript
// frontend/src/stores/camera.ts
async function startCamera(id: string) {
  await cameraApi.startCamera(id)  // POST /cameras/{id}/start
  await refreshRuntimeStatus()     // 刷新状态
}
```

#### 1.2 后端API层
```python
# src/api/routers/cameras.py
@router.post("/cameras/{camera_id}/start")
async def start_camera(camera_id: str, force_domain: bool = None):
    # ✅ 灰度切换：支持新旧两种实现
    if should_use_domain(force_domain):
        control_service = await get_camera_control_service()
        return control_service.start_camera(camera_id)  # 新架构

    # 回退到旧实现
    scheduler = get_scheduler()
    return scheduler.start_detection(camera_id)
```

**架构评分：⭐⭐⭐⭐ (4/5)**
- ✅ 有灰度切换机制
- ✅ 新架构使用领域服务 `CameraControlService`
- ⚠️ 默认仍使用旧实现（scheduler）

#### 1.3 领域服务层（新架构）
```python
# src/domain/services/camera_control_service.py
class CameraControlService:
    def start_camera(self, camera_id: str) -> Dict[str, Any]:
        res = self.scheduler.start_detection(camera_id)
        if not res.get("ok"):
            raise ValueError("启动失败")
        return res
```

**架构评分：⭐⭐⭐ (3/5)**
- ✅ 封装了启动逻辑
- ⚠️ 但只是简单包装 scheduler，未体现领域逻辑
- ⚠️ 应该包含：激活检查、权限验证、状态转换等业务规则

#### 1.4 基础设施层
```python
# src/services/executors/local.py
class LocalProcessExecutor:
    def start(self, camera_id: str) -> Dict[str, Any]:
        # 1. 读取摄像头配置
        # 2. 构建命令行：python main.py --mode detection ...
        # 3. 启动子进程
        # 4. 写入PID文件
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, env=env)
        return {"ok": True, "pid": proc.pid, "log": log_path}
```

**架构评分：⭐⭐⭐⭐⭐ (5/5)**
- ✅ 职责清晰：纯技术实现
- ✅ 与业务逻辑解耦
- ✅ 易于替换（可以切换到容器、K8s等）

---

### 2. 检测循环流程（核心）

#### 2.1 检测循环入口
```python
# main.py - run_detection()
def run_detection(args, logger):
    # 初始化检测管线（基础设施层）
    pipeline = OptimizedDetectionPipeline(...)

    # ✅ 尝试初始化应用服务（新架构）
    try:
        detection_app_service = DetectionApplicationService(
            detection_pipeline=pipeline,
            detection_domain_service=get_detection_service_domain(),
            save_policy=SavePolicy(...)  # 智能保存策略
        )
        args.detection_app_service = detection_app_service
    except Exception as e:
        logger.warning("应用服务初始化失败，使用传统逻辑")
        args.detection_app_service = None

    # 运行检测循环
    _run_detection_loop(args, logger, pipeline, device)
```

**架构评分：⭐⭐⭐⭐ (4/5)**
- ✅ 支持新旧两种实现
- ✅ 有降级机制
- ⚠️ 应用服务初始化失败会静默降级

#### 2.2 帧处理流程（新架构）
```python
# main.py - _run_detection_loop() 第610-634行
while not shutdown_requested["flag"]:
    ret, frame = cap.read()

    # ✅ 使用应用服务处理（新架构）
    if args.detection_app_service:
        try:
            app_result = run_async(
                args.detection_app_service.process_realtime_stream(
                    camera_id=camera_id,
                    frame=frame,
                    frame_count=frame_count,
                )
            )
            # 智能保存：只在有意义时才保存
            if app_result.get("saved_to_db"):
                logger.debug(f"✓ 帧 {frame_count}: 已保存 ({save_reason})")
        except Exception as e:
            logger.warning("智能保存失败，回退到原有逻辑")
            # 回退到旧逻辑...
```

**架构评分：⭐⭐⭐⭐ (4/5)**
- ✅ 使用应用服务 `DetectionApplicationService`
- ✅ 智能保存策略（避免冗余记录）
- ✅ 有降级机制
- ⚠️ 回退逻辑仍然直接调用 `DatabaseService`

#### 2.3 应用服务层
```python
# src/application/detection_application_service.py
class DetectionApplicationService:
    async def process_realtime_stream(
        self, camera_id: str, frame: np.ndarray, frame_count: int
    ) -> Dict[str, Any]:
        # 1. 执行检测（基础设施层）
        detection_result = self.detection_pipeline.detect_comprehensive(frame)

        # 2. 分析违规（业务逻辑）
        has_violations, severity = self._analyze_violations(detection_result)

        # 3. 智能保存策略（业务规则）
        should_save = self.save_policy.should_save_frame(
            frame_count=frame_count,
            has_violations=has_violations,
            violation_severity=severity,
        )

        # 4. 如果需要保存，调用领域服务
        if should_save:
            detected_objects = self._convert_to_domain_format(detection_result)
            record = await self.detection_domain_service.process_detection(
                camera_id=camera_id,
                detected_objects=detected_objects,
                processing_time=processing_time,
                frame_id=frame_count,
            )

        return {"saved_to_db": should_save, "result": {...}}
```

**架构评分：⭐⭐⭐⭐⭐ (5/5)**
- ✅ 应用服务职责清晰：协调基础设施层和领域层
- ✅ 包含智能保存策略（业务规则）
- ✅ 格式转换（基础设施格式 → 领域模型）
- ✅ 调用领域服务处理业务逻辑

#### 2.4 领域服务层
```python
# src/services/detection_service_domain.py
class DetectionServiceDomain:
    async def process_detection(
        self, camera_id: str, detected_objects: List[Dict], ...
    ) -> DetectionRecord:
        # 1. 获取摄像头信息（仓储）
        camera = await self.camera_repository.find_by_id(camera_id)

        # 2. 转换为领域模型
        domain_objects = [DetectedObject(...) for obj in detected_objects]

        # 3. 创建检测记录实体
        record = DetectionRecord(
            id=f"{camera_id}_{timestamp}",
            camera_id=camera_id,
            objects=domain_objects,
            timestamp=Timestamp.now(),
            region_id=camera.region_id,
        )

        # 4. 分析检测质量（领域服务）
        quality = self.detection_service.analyze_detection_quality(record)
        record.add_metadata("quality_analysis", quality)

        # 5. 检测违规行为（领域服务）
        violations = self.violation_service.detect_violations(record)
        if violations:
            record.add_metadata("violations", [v.__dict__ for v in violations])
            # 发布违规事件
            for violation in violations:
                event = ViolationDetectedEvent.from_violation(violation)
                await self._publish_event(event)

        # 6. 保存检测记录（仓储）
        await self.detection_repository.save(record)

        # 7. 发布检测创建事件
        await self._publish_event(DetectionCreatedEvent.from_record(record))

        return record
```

**架构评分：⭐⭐⭐⭐⭐ (5/5)**
- ✅ 使用领域模型（DetectionRecord, DetectedObject等）
- ✅ 业务逻辑清晰（质量分析、违规检测）
- ✅ 发布领域事件
- ✅ 通过仓储接口保存，不依赖具体实现

#### 2.5 仓储层
```python
# src/infrastructure/repositories/postgresql_detection_repository.py
class PostgreSQLDetectionRepository(IDetectionRepository):
    async def save(self, record: DetectionRecord) -> str:
        # 1. 序列化领域模型为JSON
        objects_dict = [
            {
                "class_id": obj.class_id,
                "class_name": obj.class_name,
                "confidence": float(obj.confidence.value),
                "bbox": obj.bbox.to_dict(),
                ...
            }
            for obj in record.objects
        ]

        # 2. 插入数据库
        record_id = await conn.fetchval(
            "INSERT INTO detection_records (...) VALUES (...)",
            record.camera_id,
            json.dumps(objects_dict),
            timestamp_value,
            ...
        )

        return str(record_id)
```

**架构评分：⭐⭐⭐⭐⭐ (5/5)**
- ✅ 实现仓储接口 `IDetectionRepository`
- ✅ 处理领域模型与数据库之间的映射
- ✅ 职责单一：纯数据持久化

---

### 3. 视频流查看

#### 3.1 前端WebSocket连接
```typescript
// frontend/src/components/VideoStreamModal.vue
const wsUrl = `ws://${host}/api/v1/video-stream/ws/${cameraId}`
ws = new WebSocket(wsUrl)
ws.binaryType = 'arraybuffer'

ws.onmessage = (event) => {
  // 接收JPEG帧
  const blob = new Blob([event.data], { type: 'image/jpeg' })
  const url = URL.createObjectURL(blob)
  // 显示在<img>标签中
}
```

#### 3.2 后端WebSocket端点
```python
# src/api/routers/video_stream.py
@router.websocket("/ws/{camera_id}")
async def video_stream_websocket(websocket: WebSocket, camera_id: str):
    stream_manager = get_stream_manager()
    await stream_manager.connect(websocket, camera_id)

    # 保持连接，接收心跳
    while True:
        data = await websocket.receive_text()
        if data == "ping":
            await websocket.send_text("pong")
```

#### 3.3 视频流管理器
```python
# src/services/video_stream_manager.py
class VideoStreamManager:
    async def _send_frames_loop(self):
        """后台任务：从帧缓存推送到WebSocket"""
        while True:
            for camera_id in list(self.frames.keys()):
                frame = self.frames.get(camera_id)
                clients = self.connections.get(camera_id, set())
                for ws in list(clients):
                    try:
                        await ws.send_bytes(frame)
                    except Exception:
                        clients.remove(ws)
            await asyncio.sleep(0.03)  # 30 FPS

    async def _subscribe_redis_loop(self):
        """后台任务：订阅Redis，接收检测进程推送的帧"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("video:*")
        async for message in pubsub.listen():
            if message["type"] == "message":
                camera_id = message["channel"].decode().split(":")[1]
                frame_data = message["data"]
                self.frames[camera_id] = frame_data
```

#### 3.4 检测进程推送帧
```python
# main.py - _run_detection_loop() 第730-750行（推测位置）
if stream_enabled and frame_count % STREAM_INTERVAL == 0:
    # 1. 选择帧（标注后或原始）
    stream_frame = annotated_frame if has_annotations else frame

    # 2. 调整大小（减少带宽）
    if STREAM_WIDTH and STREAM_HEIGHT:
        stream_frame = cv2.resize(stream_frame, (STREAM_WIDTH, STREAM_HEIGHT))

    # 3. 编码为JPEG
    _, jpeg_data = cv2.imencode('.jpg', stream_frame,
                                [cv2.IMWRITE_JPEG_QUALITY, VIDEO_QUALITY])

    # 4. 发布到Redis
    redis_client_stats.publish(f"video:{camera_id}", jpeg_data.tobytes())
```

**架构评分：⭐⭐⭐⭐ (4/5)**
- ✅ 解耦设计：检测进程 → Redis → WebSocket管理器 → 前端
- ✅ 异步处理，不阻塞检测
- ⚠️ 视频流推送代码在 `main.py` 中，不符合分层架构
- ⚠️ 应该抽取为独立的视频流服务

---

### 4. 日志查看

#### 4.1 前端调用
```typescript
// frontend/src/api/camera.ts
async getCameraLogs(id: string, lines: number = 100) {
  return await http.get(`/cameras/${id}/logs?lines=${lines}`)
}
```

#### 4.2 后端API
```python
# src/api/routers/cameras.py
@router.get("/cameras/{camera_id}/logs")
async def get_camera_logs(camera_id: str, lines: int = 100):
    # ✅ 灰度切换
    if should_use_domain(force_domain):
        control_service = await get_camera_control_service()
        return control_service.get_camera_logs(camera_id, lines)

    # 回退到直接读取日志文件
    scheduler = get_scheduler()
    status = scheduler.status(camera_id)
    log_path = Path(status["log"])

    with open(log_path, "r") as f:
        all_lines = f.readlines()
        recent_lines = all_lines[-lines:]

    return {
        "camera_id": camera_id,
        "log_file": str(log_path),
        "lines": recent_lines,
    }
```

**架构评分：⭐⭐⭐ (3/5)**
- ✅ 功能正常
- ⚠️ 直接读取文件，没有通过仓储抽象
- ⚠️ 日志查看应该也属于基础设施关注点

---

## 📊 整体架构评分

### 按模块评分

| 模块 | 旧实现 | 新实现 | 灰度切换 | 评分 |
|-----|--------|--------|---------|------|
| **摄像头启动** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **检测循环** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| **记录保存** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **视频查看** | ✅ | ❌ | ❌ | ⭐⭐⭐⭐ |
| **日志查看** | ✅ | ⚠️ | ⚠️ | ⭐⭐⭐ |
| **摄像头停止** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |

### 分层评分

| 分层 | 职责清晰 | 依赖方向 | 可测试性 | 评分 |
|-----|----------|---------|---------|------|
| **API层** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **应用服务层** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **领域服务层** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **领域模型** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **仓储接口** | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **基础设施** | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**总体评分：⭐⭐⭐⭐ (4.2/5)**

---

## ✅ 优点

### 1. 灰度切换机制
```python
# 所有API都有灰度切换
if should_use_domain(force_domain):
    # 新架构
    return new_implementation()
# 回退到旧实现
return old_implementation()
```
- ✅ 可以无风险地逐步迁移
- ✅ 出问题时可以快速回退
- ✅ 支持 A/B 测试

### 2. 领域模型清晰
```python
# 领域实体
DetectionRecord(
    id, camera_id, objects, timestamp, processing_time,
    region_id, metadata
)
DetectedObject(class_id, class_name, confidence, bbox, track_id)
```
- ✅ 表达业务概念
- ✅ 包含业务规则验证
- ✅ 与数据库结构解耦

### 3. 智能保存策略
```python
class SavePolicy:
    strategy: SaveStrategy  # SAVE_ALL, VIOLATION_ONLY, SMART
    save_interval: int
    violation_severity_threshold: float

    def should_save_frame(self, frame_count, has_violations, severity):
        if self.strategy == SaveStrategy.VIOLATION_ONLY:
            return has_violations
        elif self.strategy == SaveStrategy.SMART:
            if has_violations and severity >= self.threshold:
                return True  # 严重违规总是保存
            return frame_count % self.normal_sample_interval == 0
```
- ✅ 避免保存冗余数据
- ✅ 业务规则集中管理
- ✅ 易于调整策略

### 4. 仓储模式
```python
# 接口定义
class IDetectionRepository(ABC):
    async def save(self, record: DetectionRecord) -> str
    async def find_by_id(self, record_id: str) -> DetectionRecord
    async def find_by_camera(self, camera_id: str, ...) -> List[DetectionRecord]

# 实现可切换
PostgreSQLDetectionRepository  # 生产环境
RedisDetectionRepository        # 缓存/实时查询
InMemoryDetectionRepository     # 测试环境
```
- ✅ 解耦业务逻辑与数据存储
- ✅ 易于切换实现
- ✅ 易于测试

### 5. 事件驱动
```python
# 发布领域事件
await self._publish_event(ViolationDetectedEvent.from_violation(violation))
await self._publish_event(DetectionCreatedEvent.from_record(record))
```
- ✅ 解耦模块间依赖
- ✅ 支持异步处理
- ✅ 易于扩展功能（如通知、统计）

---

## ⚠️ 需要改进的地方

### 1. main.py 职责过重

**问题**：
```python
# main.py 包含了太多职责：
# - 检测循环
# - 视频流推送
# - 数据库保存
# - Redis发布
# - 性能统计
# - ...（1100+行代码）
```

**建议重构**：
```python
# 1. 抽取检测循环为独立服务
class DetectionLoopService:
    def __init__(self, pipeline, app_service, stream_service):
        self.pipeline = pipeline
        self.app_service = app_service
        self.stream_service = stream_service

    async def run(self, camera_id: str, source: str):
        cap = cv2.VideoCapture(source)
        while not self.shutdown:
            ret, frame = cap.read()
            # 检测
            result = self.pipeline.detect(frame)
            # 保存（通过应用服务）
            await self.app_service.process_frame(camera_id, frame, result)
            # 推送视频流（通过视频流服务）
            await self.stream_service.push_frame(camera_id, frame)

# 2. main.py 只负责启动
def main():
    args = parse_args()
    service = DetectionLoopService(...)
    asyncio.run(service.run(args.camera_id, args.source))
```

### 2. 视频流推送不符合分层架构

**问题**：
```python
# main.py 直接操作 Redis
redis_client_stats.publish(f"video:{camera_id}", jpeg_data.tobytes())
```

**建议**：
```python
# 创建视频流服务（应用服务层）
class VideoStreamApplicationService:
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager

    async def push_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        annotated: bool = False
    ):
        # 1. 调整大小
        resized = self._resize_frame(frame)
        # 2. 编码
        jpeg_data = self._encode_jpeg(resized)
        # 3. 发布（通过基础设施）
        await self.stream_manager.publish(camera_id, jpeg_data)

# 在检测循环中使用
await video_stream_service.push_frame(camera_id, frame, annotated=True)
```

### 3. 领域服务应该更"领域"

**问题**：
```python
# CameraControlService 只是简单包装 scheduler
class CameraControlService:
    def start_camera(self, camera_id: str):
        res = self.scheduler.start_detection(camera_id)
        if not res.get("ok"):
            raise ValueError("启动失败")
        return res
```

**建议**：
```python
# 应该包含更多业务逻辑
class CameraControlService:
    def start_camera(self, camera_id: str) -> CameraStartResult:
        # 1. 获取摄像头实体
        camera = await self.camera_repo.find_by_id(camera_id)

        # 2. 业务规则验证
        if not camera.is_active:
            raise CameraNotActiveError(f"摄像头 {camera_id} 未激活")

        if camera.is_running():
            raise CameraAlreadyRunningError(f"摄像头 {camera_id} 已在运行")

        # 3. 检查资源
        if not self._check_resources_available():
            raise InsufficientResourcesError("系统资源不足")

        # 4. 启动（委托给执行器）
        result = await self.executor.start(camera_id)

        # 5. 更新摄像头状态
        camera.mark_as_running(pid=result.pid)
        await self.camera_repo.save(camera)

        # 6. 发布事件
        await self.event_bus.publish(CameraStartedEvent(camera_id))

        return CameraStartResult(camera_id, result.pid, result.log_path)
```

### 4. 前端资源释放问题

**问题**：
- 前端停止摄像头后状态刷新可能不及时
- macOS上摄像头资源释放可能不完全

**已修复**：
- ✅ 信号处理器使用字典存储摄像头对象
- ✅ 增加 macOS 特定的资源释放逻辑
- ✅ 前端增加延迟和轮询确认机制

### 5. 日志查看没有抽象

**问题**：
```python
# 直接读取文件
with open(log_path, "r") as f:
    lines = f.readlines()
```

**建议**：
```python
# 创建日志仓储接口
class ILogRepository(ABC):
    async def get_recent_logs(
        self, camera_id: str, lines: int
    ) -> List[LogEntry]

# 实现
class FileSystemLogRepository(ILogRepository):
    async def get_recent_logs(self, camera_id: str, lines: int):
        log_path = self._get_log_path(camera_id)
        with open(log_path, "r") as f:
            all_lines = f.readlines()
        return [LogEntry.parse(line) for line in all_lines[-lines:]]

# 未来可切换到：
class ElasticsearchLogRepository(ILogRepository):  # 集中式日志
class LokiLogRepository(ILogRepository)            # Grafana Loki
```

---

## 🎯 推荐的重构优先级

### 高优先级（影响用户体验）
1. **✅ 修复摄像头资源释放问题**（已完成）
2. **前端停止摄像头状态刷新优化**（已完成）

### 中优先级（提升架构质量）
3. **重构 main.py**
   - 抽取 `DetectionLoopService`
   - 移除直接的Redis/数据库操作
   - 通过依赖注入使用应用服务

4. **增强领域服务**
   - `CameraControlService` 添加业务规则验证
   - 添加状态管理和事件发布

5. **视频流服务独立**
   - 创建 `VideoStreamApplicationService`
   - 封装编码、推送逻辑

### 低优先级（长期改进）
6. **日志查看抽象化**
   - 创建 `ILogRepository`
   - 支持集中式日志系统

7. **完善测试**
   - 应用服务单元测试
   - 领域服务单元测试
   - E2E测试

---

## 📝 结论

### 整体评价
当前摄像头检测流程**基本符合领域驱动设计架构**，关键流程已经通过应用服务和领域服务实现了业务逻辑的封装。

### 优势
- ✅ 核心流程（检测→保存）使用了新架构
- ✅ 灰度切换机制保证了平滑迁移
- ✅ 领域模型清晰，业务逻辑与技术实现分离
- ✅ 仓储模式实现良好

### 需要改进
- ⚠️ `main.py` 仍然包含过多职责
- ⚠️ 视频流推送逻辑耦合在检测循环中
- ⚠️ 领域服务应该包含更多业务规则

### 推荐行动
1. **短期**：完成摄像头资源释放修复（已完成）
2. **中期**：重构 `main.py`，抽取独立服务
3. **长期**：完善领域服务，增加测试覆盖

---

## 📚 相关文档

- [检测架构分析](./DETECTION_ARCHITECTURE_ANALYSIS.md)
- [检测场景分析](./DETECTION_SCENARIOS_ANALYSIS.md)
- [视频流修复报告](./VIDEO_STREAM_FIX_REPORT.md)
- [渐进式重构计划](./gradual_refactoring_plan.md)
