# 核心检测功能架构深度分析

## 日期
2025-11-03

## 📋 执行摘要

**当前状态**: ⚠️ **架构分层不清晰，职责混乱**

**核心问题**: 检测功能完整且性能良好，但缺乏清晰的架构分层，导致业务逻辑分散、难以维护和扩展。

**建议**: 明确架构分层，将检测（技术关注）与检测记录管理（业务关注）分离。

---

## 🎯 架构分析：现状 vs 目标

### 当前架构（存在问题）

```
表现层（API）
    ↓
├─ /api/v1/detect/comprehensive
│   ↓
│   comprehensive_detection_logic()  ← 服务层函数
│   ↓
│   OptimizedDetectionPipeline      ← 直接调用基础设施
│   ↓
│   返回检测结果                     ← 不保存、不分析、不检测违规
│   ❌ 问题：绕过了领域层和业务逻辑
│
├─ main.py run_detection()
│   ↓
│   OptimizedDetectionPipeline      ← 直接调用基础设施
│   ↓
│   db_service.save_detection_record() ← 直接调用数据库服务
│   ❌ 问题：绕过了领域层，未使用领域模型
│
└─ /api/v1/statistics/* (已重构)
    ↓
    DetectionServiceDomain          ← 使用领域服务
    ↓
    IDetectionRepository            ← 使用仓储接口
    ✅ 正确：通过领域层访问数据
```

### 目标架构（清晰分层）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
表现层 (Presentation Layer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API端点: /api/v1/detect/comprehensive
    ↓
    职责：HTTP请求处理、参数验证、响应格式化
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
应用层 (Application Layer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DetectionApplicationService (新增)
    ↓
    职责：协调基础设施和领域层
    ↓
    ┌─────────────────────┬──────────────────────┐
    ↓                     ↓                      ↓
基础设施层           领域层                  基础设施层
(图像检测)          (业务逻辑)              (持久化)
    ↓                     ↓                      ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
基础设施层 (Infrastructure Layer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OptimizedDetectionPipeline
    ↓
    职责：图像处理、模型推理、性能优化
    ├─ HumanDetector (YOLOv8)
    ├─ HairnetDetector (YOLOv8)
    ├─ BehaviorRecognizer (MediaPipe + XGBoost)
    └─ PoseDetector (YOLOv8-Pose/MediaPipe)
    ↓
返回：DetectionResult (技术数据结构)
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
领域层 (Domain Layer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DetectionServiceDomain
    ↓
    职责：业务逻辑、领域规则、质量分析、违规检测
    ├─ 将技术数据结构转换为领域模型（DetectionRecord）
    ├─ DetectionService.analyze_detection_quality()
    ├─ ViolationService.detect_violations()
    └─ 发布领域事件（DetectionCreatedEvent, ViolationDetectedEvent）
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
基础设施层 (Infrastructure Layer - Persistence)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IDetectionRepository
    ├─ PostgreSQLDetectionRepository
    ├─ RedisDetectionRepository (缓存)
    └─ HybridDetectionRepository
    ↓
持久化：DetectionRecord 到数据库
```

---

## 🔍 关键问题分析

### 问题1: 职责不清晰（违反SRP）

**OptimizedDetectionPipeline** 的职责应该是什么？

```python
# ❌ 当前：混合了技术和业务逻辑
class OptimizedDetectionPipeline:
    """优化的检测管道 - 统一处理所有检测任务"""

    def detect_comprehensive(self, image):
        # 1. 技术逻辑：图像检测 ✅ 正确
        persons = self._detect_persons(image)
        hairnets = self._detect_hairnet_for_persons(image, persons)
        behaviors = self._detect_behaviors(image, persons)

        # 2. 返回结果 ✅ 正确
        return DetectionResult(...)

        # ❌ 问题：没有业务逻辑（质量分析、违规检测、保存记录）
        # 这些业务逻辑被分散到了各个调用方
```

**正确的职责分离**:

```python
# ✅ 基础设施层：只负责技术实现
class OptimizedDetectionPipeline:
    """图像检测管道 - 纯技术组件"""

    def detect_comprehensive(self, image) -> DetectionResult:
        # 只负责图像处理和模型推理
        persons = self._detect_persons(image)
        hairnets = self._detect_hairnet_for_persons(image, persons)
        behaviors = self._detect_behaviors(image, persons)
        return DetectionResult(...)

# ✅ 领域层：负责业务逻辑
class DetectionServiceDomain:
    """检测业务服务 - 业务逻辑"""

    async def process_detection(
        self,
        camera_id: str,
        detected_objects: List[Dict],
        processing_time: float
    ) -> DetectionRecord:
        # 1. 创建领域模型
        record = DetectionRecord(...)

        # 2. 业务逻辑：质量分析
        quality = self.detection_service.analyze_detection_quality(record)
        record.add_metadata("quality_analysis", quality)

        # 3. 业务逻辑：违规检测
        violations = self.violation_service.detect_violations(record)
        if violations:
            record.add_metadata("violations", violations)
            # 发布领域事件
            for violation in violations:
                await self._publish_event(ViolationDetectedEvent(...))

        # 4. 持久化
        await self.detection_repository.save(record)

        # 5. 发布领域事件
        await self._publish_event(DetectionCreatedEvent(...))

        return record
```

### 问题2: 数据访问不一致

**当前状态**:
- 读取操作：通过 `DetectionServiceDomain` + `IDetectionRepository` ✅
- 写入操作：直接调用 `db_service.save_detection_record()` ❌

```python
# ❌ 不一致：读写使用不同的路径
# 读取
/api/v1/statistics/realtime -> DetectionServiceDomain -> IDetectionRepository

# 写入
/api/v1/detect/comprehensive -> comprehensive_detection_logic() -> (不保存)
main.py run_detection() -> db_service.save_detection_record() (直接数据库)
```

**问题**:
1. **违反CQRS原则**：读写路径不对称
2. **数据不一致风险**：直接数据库写入绕过了业务规则
3. **难以维护**：业务逻辑分散在多处
4. **无法扩展**：新增业务规则需要修改多处代码

### 问题3: 缺少应用层

**当前**:
```python
# ❌ API直接调用基础设施层
@router.post("/comprehensive")
async def detect_comprehensive(
    file: UploadFile,
    optimized_pipeline: OptimizedDetectionPipeline  # 直接依赖基础设施
):
    result = comprehensive_detection_logic(
        optimized_pipeline=optimized_pipeline  # 直接使用
    )
    return result  # 不保存、不分析
```

**应该**:
```python
# ✅ API调用应用服务，应用服务协调基础设施和领域层
@router.post("/comprehensive")
async def detect_comprehensive(
    file: UploadFile,
    detection_app_service: DetectionApplicationService  # 依赖应用服务
):
    # 应用服务协调所有层
    result = await detection_app_service.process_detection_request(
        camera_id="api_upload",
        image_bytes=await file.read()
    )
    return result  # 已保存、已分析、已检测违规
```

---

## 🎯 解决方案：清晰的架构分层

### 方案：引入应用服务层

创建 `DetectionApplicationService` 作为协调者：

```python
# src/application/detection_application_service.py

class DetectionApplicationService:
    """检测应用服务 - 协调基础设施和领域层"""

    def __init__(
        self,
        detection_pipeline: OptimizedDetectionPipeline,  # 基础设施
        detection_domain_service: DetectionServiceDomain,  # 领域服务
    ):
        self.detection_pipeline = detection_pipeline
        self.detection_domain_service = detection_domain_service

    async def process_detection_request(
        self,
        camera_id: str,
        image_bytes: bytes,
        frame_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """处理检测请求 - 完整流程"""

        # 1. 图像解码（基础设施层）
        image = self._decode_image(image_bytes)

        # 2. 执行检测（基础设施层 - 技术操作）
        start_time = time.time()
        detection_result = self.detection_pipeline.detect_comprehensive(image)
        processing_time = time.time() - start_time

        # 3. 转换为领域模型格式
        detected_objects = self._convert_to_domain_format(detection_result)

        # 4. 业务处理（领域层 - 业务逻辑）
        record = await self.detection_domain_service.process_detection(
            camera_id=camera_id,
            detected_objects=detected_objects,
            processing_time=processing_time,
            frame_id=frame_id
        )

        # 5. 构建响应
        return {
            "ok": True,
            "camera_id": camera_id,
            "detection_id": record.id,
            "timestamp": record.timestamp.iso_string,
            "person_count": record.person_count,
            "processing_time": processing_time,
            "quality": record.metadata.get("quality_analysis", {}),
            "violations": record.metadata.get("violations", []),
            "objects": [obj.to_dict() for obj in record.objects],
        }

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """解码图像字节为numpy数组"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("无法解码图像")
        return image

    def _convert_to_domain_format(
        self,
        detection_result: DetectionResult
    ) -> List[Dict[str, Any]]:
        """将检测结果转换为领域模型格式"""
        objects = []

        # 转换人体检测结果
        for person in detection_result.person_detections:
            objects.append({
                "class_id": 0,
                "class_name": "person",
                "confidence": person["confidence"],
                "bbox": person["bbox"],
                "track_id": person.get("track_id"),
                "metadata": {
                    "source": "human_detector",
                    **person.get("metadata", {})
                }
            })

        # 转换发网检测结果
        for hairnet in detection_result.hairnet_results:
            objects.append({
                "class_id": 1,
                "class_name": "hairnet" if hairnet.get("has_hairnet") else "no_hairnet",
                "confidence": hairnet["confidence"],
                "bbox": hairnet.get("bbox"),
                "track_id": hairnet.get("track_id"),
                "metadata": {
                    "source": "hairnet_detector",
                    "has_hairnet": hairnet.get("has_hairnet", False),
                    **hairnet.get("metadata", {})
                }
            })

        # 转换行为检测结果（洗手、消毒）
        for behavior in detection_result.handwash_results + detection_result.sanitize_results:
            objects.append({
                "class_id": 2 if behavior.get("is_handwash") else 3,
                "class_name": "handwashing" if behavior.get("is_handwash") else "sanitizing",
                "confidence": behavior["confidence"],
                "bbox": behavior.get("bbox"),
                "track_id": behavior.get("track_id"),
                "metadata": {
                    "source": "behavior_recognizer",
                    **behavior.get("metadata", {})
                }
            })

        return objects
```

### 重构API端点

```python
# src/api/routers/comprehensive.py

from src.application.detection_application_service import DetectionApplicationService

async def get_detection_app_service() -> DetectionApplicationService:
    """获取检测应用服务"""
    # 通过依赖注入容器或工厂创建
    pipeline = await get_optimized_pipeline()
    domain_service = get_detection_service_domain()
    return DetectionApplicationService(
        detection_pipeline=pipeline,
        detection_domain_service=domain_service
    )

@router.post("/comprehensive", summary="综合检测接口")
async def detect_comprehensive(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    app_service: DetectionApplicationService = Depends(get_detection_app_service),
) -> Dict[str, Any]:
    """
    执行综合检测，包括人体、发网、洗手、消毒等。

    完整流程：
    1. 图像解码
    2. 执行检测（基础设施层）
    3. 业务处理（领域层）：质量分析、违规检测
    4. 保存记录到数据库
    5. 发布领域事件
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    contents = await file.read()

    try:
        logger.info(f"开始综合检测: {file.filename}, 文件大小: {len(contents)} bytes")

        result = await app_service.process_detection_request(
            camera_id=camera_id,
            image_bytes=contents
        )

        logger.info(f"检测完成: {result['detection_id']}, 对象数: {len(result['objects'])}")
        return result

    except Exception as e:
        logger.exception(f"综合检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
```

### 重构实时检测

```python
# main.py

async def process_frame_with_domain_service(
    frame: np.ndarray,
    camera_id: str,
    frame_count: int,
    pipeline: OptimizedDetectionPipeline,
    domain_service: DetectionServiceDomain
):
    """使用领域服务处理帧"""

    # 1. 执行检测（基础设施层）
    start_time = time.time()
    detection_result = pipeline.detect_comprehensive(frame)
    processing_time = time.time() - start_time

    # 2. 转换为领域模型格式
    detected_objects = convert_detection_result_to_domain_format(detection_result)

    # 3. 业务处理（领域层）
    record = await domain_service.process_detection(
        camera_id=camera_id,
        detected_objects=detected_objects,
        processing_time=processing_time,
        frame_id=frame_count
    )

    # 4. 返回记录用于可视化
    return record

def run_detection(args, logger):
    """运行检测模式"""
    # ... 初始化代码 ...

    # 初始化检测管道
    pipeline = OptimizedDetectionPipeline(...)

    # 初始化领域服务
    domain_service = get_detection_service_domain()

    # ... 视频循环 ...
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 使用领域服务处理帧
        record = asyncio.run(
            process_frame_with_domain_service(
                frame, camera_id, frame_count, pipeline, domain_service
            )
        )

        # 可视化结果
        annotated_frame = visualize_detection_record(frame, record)
        cv2.imshow("Detection", annotated_frame)

        # ... 其他逻辑 ...
```

---

## 📊 架构对比总结

| 方面 | 当前架构 | 目标架构 |
|------|---------|---------|
| **分层清晰度** | ❌ 不清晰，职责混乱 | ✅ 清晰分层，职责明确 |
| **技术与业务分离** | ❌ 混合在一起 | ✅ 完全分离 |
| **数据访问一致性** | ❌ 读写路径不同 | ✅ 统一通过领域服务 |
| **业务逻辑位置** | ❌ 分散在各处 | ✅ 集中在领域层 |
| **可测试性** | ⚠️ 较低（依赖基础设施） | ✅ 高（可注入mock） |
| **可维护性** | ⚠️ 较低（逻辑分散） | ✅ 高（职责清晰） |
| **可扩展性** | ⚠️ 较低（修改多处） | ✅ 高（符合OCP） |
| **性能** | ✅ 良好 | ✅ 良好（架构改进不影响性能） |

---

## ✅ 关键收获

### 1. 架构分层的核心原则

**不是"要不要DDD"的问题，而是"如何正确分层"的问题**

```
技术关注 (OptimizedDetectionPipeline)
    ↓
    图像处理、模型推理、性能优化
    这是基础设施层的职责

业务关注 (DetectionServiceDomain)
    ↓
    质量分析、违规检测、业务规则
    这是领域层的职责
```

### 2. 当前实现的优点

- ✅ 检测功能完整
- ✅ 性能优化到位
- ✅ 缓存机制完善
- ✅ 支持多种检测类型

### 3. 需要改进的地方

- ⚠️ 架构分层不清晰
- ⚠️ 职责边界模糊
- ⚠️ 数据访问路径不一致
- ⚠️ 缺少应用服务层

---

## 📋 实施建议

### 优先级1: 引入应用服务层（高优先级）

**目标**: 创建 `DetectionApplicationService` 作为协调者

**步骤**:
1. 创建 `src/application/detection_application_service.py`
2. 实现 `process_detection_request()` 方法
3. 实现数据格式转换方法

**预计时间**: 2-3小时

### 优先级2: 重构API端点（高优先级）

**目标**: 将检测端点集成应用服务

**步骤**:
1. 修改 `/api/v1/detect/comprehensive` 使用应用服务
2. 完成 `/api/v1/detect/image` 实现
3. 添加单元测试和集成测试

**预计时间**: 3-4小时

### 优先级3: 重构实时检测（高优先级）

**目标**: 将实时检测集成领域服务

**步骤**:
1. 修改 `main.py run_detection()` 使用领域服务
2. 创建帧处理辅助函数
3. 测试和验证

**预计时间**: 2-3小时

---

## 🎯 最终架构图

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
完整的检测流程（目标架构）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

用户请求 (上传图像/视频帧)
    ↓
[表现层] API Router
    ├─ 参数验证
    ├─ HTTP请求处理
    └─ 响应格式化
    ↓
[应用层] DetectionApplicationService
    ├─ 协调基础设施和领域层
    ├─ 图像解码
    ├─ 数据格式转换
    └─ 流程编排
    ↓
    ┌─────────────────────┬──────────────────────────┐
    ↓                     ↓                          ↓
[基础设施] Pipeline   [领域层] Domain Service   [基础设施] Repository
    ↓                     ↓                          ↓
OptimizedDetection    DetectionServiceDomain    IDetectionRepository
Pipeline                  ├─ 创建领域模型              ↓
├─ 人体检测            ├─ 质量分析            PostgreSQL/Redis
├─ 发网检测            ├─ 违规检测
├─ 行为识别            ├─ 发布事件
└─ 姿态检测            └─ 调用仓储
    ↓                     ↓                          ↓
返回技术结果          业务处理完成              持久化完成
    ↓                     ↓                          ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
返回结果给用户
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ✅ 总结

### 核心问题

**不是DDD vs 非DDD的问题，而是架构分层不清晰的问题**

### 解决方案

1. **明确分层**：基础设施层（技术）、领域层（业务）、应用层（协调）
2. **职责分离**：OptimizedDetectionPipeline负责检测，DetectionServiceDomain负责业务
3. **引入应用服务**：DetectionApplicationService协调所有层
4. **统一数据访问**：所有读写操作通过领域服务和仓储

### 预期收益

- ✅ **更清晰的代码结构**：职责明确，易于理解
- ✅ **更好的可维护性**：修改业务规则只需修改领域层
- ✅ **更高的可测试性**：各层独立测试
- ✅ **更强的可扩展性**：新增功能符合开闭原则
- ✅ **保持高性能**：架构改进不影响检测性能

---

**状态**: ⚠️ **需要架构重构，但不影响功能**

**下一步**: 引入应用服务层，重构API端点和实时检测
