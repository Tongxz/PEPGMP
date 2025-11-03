# 检测场景完整分析：实时流 vs 视频文件 vs 图片上传

## 日期
2025-11-03

## 📋 三种核心场景

你提出的问题非常关键！让我重新分析三种不同的检测场景：

### 场景1: 实时摄像头视频流（最重要）
**特点**：
- 连续的视频帧流
- 需要实时处理（低延迟）
- 高频率（25-30 FPS）
- **不能每帧都保存到数据库**（性能瓶颈）
- 需要在线可视化

**当前实现**：
```python
# main.py run_detection()
while True:
    ret, frame = cap.read()
    result = pipeline.detect_comprehensive(frame)

    # 每N帧保存一次（性能考虑）
    if frame_count % save_interval == 0:
        asyncio.run(db_service.save_detection_record(...))
```

### 场景2: 上传视频文件
**特点**：
- 离线处理，非实时
- 需要处理整个视频
- 可以批量保存结果
- 需要返回处理后的视频

**当前实现**：
```python
# src/services/detection_service.py
def _process_video_with_recording(video_path, filename, pipeline):
    while True:
        ret, frame = cap.read()
        if frame_count % 5 == 0:  # 每5帧处理一次
            result = pipeline.detect_comprehensive(frame)
            # 注释：录制到视频，但未保存到数据库
```

### 场景3: 上传单张图片
**特点**：
- 单次请求
- 快速响应
- 可以保存每次检测

**当前实现**：
```python
# src/api/routers/comprehensive.py
@router.post("/comprehensive")
async def detect_comprehensive(file: UploadFile):
    result = comprehensive_detection_logic(
        contents, filename, pipeline, hairnet_pipeline
    )
    # 注意：当前未保存到数据库
    return result
```

---

## 🎯 重新设计：考虑不同场景的应用服务

### 完整的 DetectionApplicationService

```python
# src/application/detection_application_service.py

from enum import Enum
from typing import Optional, AsyncGenerator

class DetectionMode(Enum):
    """检测模式"""
    SINGLE_IMAGE = "single_image"      # 单张图片
    VIDEO_FILE = "video_file"          # 视频文件
    REALTIME_STREAM = "realtime_stream"  # 实时流

class DetectionApplicationService:
    """检测应用服务 - 支持多种场景"""

    def __init__(
        self,
        detection_pipeline: OptimizedDetectionPipeline,
        detection_domain_service: DetectionServiceDomain,
    ):
        self.detection_pipeline = detection_pipeline
        self.detection_domain_service = detection_domain_service
        self.logger = logging.getLogger(__name__)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 场景1: 单张图片检测
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def process_image_detection(
        self,
        camera_id: str,
        image_bytes: bytes,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        处理单张图片检测

        Args:
            camera_id: 摄像头ID
            image_bytes: 图像字节数据
            save_to_db: 是否保存到数据库（默认True）

        Returns:
            检测结果字典
        """
        # 1. 图像解码
        image = self._decode_image(image_bytes)

        # 2. 执行检测（基础设施层）
        start_time = time.time()
        detection_result = self.detection_pipeline.detect_comprehensive(image)
        processing_time = time.time() - start_time

        # 3. 转换为领域模型格式
        detected_objects = self._convert_to_domain_format(detection_result)

        # 4. 业务处理（领域层）
        if save_to_db:
            record = await self.detection_domain_service.process_detection(
                camera_id=camera_id,
                detected_objects=detected_objects,
                processing_time=processing_time
            )
            detection_id = record.id
        else:
            # 不保存，只返回结果
            detection_id = f"temp_{int(time.time() * 1000)}"
            record = None

        # 5. 构建响应
        return {
            "ok": True,
            "mode": DetectionMode.SINGLE_IMAGE.value,
            "camera_id": camera_id,
            "detection_id": detection_id,
            "processing_time": processing_time,
            "result": {
                "person_count": len(detection_result.person_detections),
                "hairnet_results": detection_result.hairnet_results,
                "handwash_results": detection_result.handwash_results,
                "sanitize_results": detection_result.sanitize_results,
            },
            "quality": record.metadata.get("quality_analysis") if record else None,
            "violations": record.metadata.get("violations", []) if record else [],
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 场景2: 视频文件处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def process_video_file(
        self,
        camera_id: str,
        video_path: str,
        output_dir: str = "./output/processed_videos",
        save_interval: int = 30,  # 每30帧保存一次
        process_interval: int = 5,  # 每5帧处理一次
    ) -> Dict[str, Any]:
        """
        处理视频文件

        Args:
            camera_id: 摄像头ID
            video_path: 视频文件路径
            output_dir: 输出目录
            save_interval: 保存间隔（帧数）
            process_interval: 处理间隔（帧数）

        Returns:
            处理结果字典
        """
        self.logger.info(f"开始处理视频文件: {video_path}")

        # 1. 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        # 获取视频信息
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 2. 准备输出视频
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"processed_{Path(video_path).stem}_{int(time.time())}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 3. 处理统计
        stats = {
            "total_frames": total_frames,
            "processed_frames": 0,
            "saved_records": 0,
            "total_violations": 0,
            "processing_times": [],
        }

        # 4. 逐帧处理
        frame_count = 0
        tracker = MultiObjectTracker(max_disappeared=5, iou_threshold=0.5)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1

                # 每process_interval帧处理一次（性能优化）
                if frame_count % process_interval == 0:
                    # 执行检测
                    start_time = time.time()
                    detection_result = self.detection_pipeline.detect_comprehensive(frame)
                    processing_time = time.time() - start_time

                    stats["processed_frames"] += 1
                    stats["processing_times"].append(processing_time)

                    # 更新跟踪器
                    detections = [
                        {"bbox": p["bbox"], "confidence": p["confidence"]}
                        for p in detection_result.person_detections
                    ]
                    tracked_objects = tracker.update(detections)

                    # 可视化
                    annotated_frame = self._draw_detections(
                        frame.copy(), detection_result, tracked_objects
                    )
                    out.write(annotated_frame)

                    # 每save_interval帧保存到数据库
                    if frame_count % save_interval == 0:
                        detected_objects = self._convert_to_domain_format(detection_result)
                        record = await self.detection_domain_service.process_detection(
                            camera_id=camera_id,
                            detected_objects=detected_objects,
                            processing_time=processing_time,
                            frame_id=frame_count
                        )
                        stats["saved_records"] += 1
                        stats["total_violations"] += len(record.metadata.get("violations", []))

                else:
                    # 不处理的帧直接写入
                    out.write(frame)

                # 进度日志
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    self.logger.info(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames})")

        finally:
            cap.release()
            out.release()

        # 5. 计算统计信息
        avg_processing_time = (
            sum(stats["processing_times"]) / len(stats["processing_times"])
            if stats["processing_times"]
            else 0
        )

        self.logger.info(f"视频处理完成: {output_path}")

        return {
            "ok": True,
            "mode": DetectionMode.VIDEO_FILE.value,
            "camera_id": camera_id,
            "input_video": video_path,
            "output_video": output_path,
            "stats": {
                **stats,
                "avg_processing_time": avg_processing_time,
                "estimated_fps": 1.0 / avg_processing_time if avg_processing_time > 0 else 0,
            },
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 场景3: 实时视频流处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def process_realtime_stream(
        self,
        camera_id: str,
        frame: np.ndarray,
        frame_count: int,
        save_to_db: bool = False,  # 实时流默认不保存每帧
    ) -> Dict[str, Any]:
        """
        处理实时流帧

        Args:
            camera_id: 摄像头ID
            frame: 视频帧
            frame_count: 帧计数
            save_to_db: 是否保存到数据库（默认False，由调用方控制保存频率）

        Returns:
            检测结果字典（轻量级）
        """
        # 1. 执行检测（基础设施层）
        start_time = time.time()
        detection_result = self.detection_pipeline.detect_comprehensive(frame)
        processing_time = time.time() - start_time

        # 2. 如果需要保存（由调用方根据save_interval决定）
        record = None
        if save_to_db:
            detected_objects = self._convert_to_domain_format(detection_result)
            record = await self.detection_domain_service.process_detection(
                camera_id=camera_id,
                detected_objects=detected_objects,
                processing_time=processing_time,
                frame_id=frame_count
            )

        # 3. 构建轻量级响应（用于实时可视化）
        return {
            "ok": True,
            "mode": DetectionMode.REALTIME_STREAM.value,
            "camera_id": camera_id,
            "frame_count": frame_count,
            "processing_time": processing_time,
            "fps": 1.0 / processing_time if processing_time > 0 else 0,
            # 轻量级结果，不包含完整的领域模型
            "result": {
                "person_count": len(detection_result.person_detections),
                "has_violations": len(detection_result.hairnet_results) > 0,
                "persons": [
                    {
                        "bbox": p["bbox"],
                        "confidence": p["confidence"],
                        "track_id": p.get("track_id"),
                    }
                    for p in detection_result.person_detections
                ],
                "hairnet_results": detection_result.hairnet_results,
            },
            "saved_to_db": save_to_db,
            "detection_id": record.id if record else None,
        }

    async def process_realtime_stream_generator(
        self,
        camera_id: str,
        video_source: str,  # 摄像头源（rtsp://, 0, video.mp4等）
        save_interval: int = 30,  # 每30帧保存一次到数据库
        process_interval: int = 1,  # 每帧都处理（实时流）
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        实时流生成器 - 用于持续处理视频流

        Args:
            camera_id: 摄像头ID
            video_source: 视频源
            save_interval: 保存间隔（帧数）
            process_interval: 处理间隔（帧数）

        Yields:
            每帧的检测结果
        """
        self.logger.info(f"开始实时流处理: camera={camera_id}, source={video_source}")

        # 1. 打开视频流
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频源: {video_source}")

        frame_count = 0
        tracker = MultiObjectTracker(max_disappeared=5, iou_threshold=0.5)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    self.logger.warning(f"无法读取帧: camera={camera_id}")
                    break

                frame_count += 1

                # 每process_interval帧处理一次
                if frame_count % process_interval == 0:
                    # 决定是否保存到数据库
                    save_to_db = (frame_count % save_interval == 0)

                    # 处理帧
                    result = await self.process_realtime_stream(
                        camera_id=camera_id,
                        frame=frame,
                        frame_count=frame_count,
                        save_to_db=save_to_db
                    )

                    # 添加帧图像（用于可视化）
                    result["frame"] = frame

                    yield result

        finally:
            cap.release()
            self.logger.info(f"实时流处理结束: camera={camera_id}, 总帧数={frame_count}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 辅助方法
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
        # ... (与之前相同)
        pass

    def _draw_detections(
        self,
        frame: np.ndarray,
        detection_result: DetectionResult,
        tracked_objects: List,
    ) -> np.ndarray:
        """在帧上绘制检测结果"""
        # 绘制人体检测框
        for person in detection_result.person_detections:
            bbox = person["bbox"]
            confidence = person["confidence"]
            track_id = person.get("track_id")

            cv2.rectangle(
                frame,
                (int(bbox[0]), int(bbox[1])),
                (int(bbox[2]), int(bbox[3])),
                (0, 255, 0),
                2
            )

            label = f"Person {track_id}: {confidence:.2f}" if track_id else f"Person: {confidence:.2f}"
            cv2.putText(
                frame, label,
                (int(bbox[0]), int(bbox[1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
            )

        # 绘制发网检测
        for hairnet in detection_result.hairnet_results:
            if not hairnet.get("has_hairnet"):
                bbox = hairnet.get("bbox")
                if bbox:
                    cv2.rectangle(
                        frame,
                        (int(bbox[0]), int(bbox[1])),
                        (int(bbox[2]), int(bbox[3])),
                        (0, 0, 255),
                        2
                    )
                    cv2.putText(
                        frame, "NO HAIRNET!",
                        (int(bbox[0]), int(bbox[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2
                    )

        return frame
```

---

## 🎯 不同场景的API端点设计

### 1. 单张图片检测端点

```python
# src/api/routers/comprehensive.py

@router.post("/image", summary="单张图片检测")
async def detect_image(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    save_to_db: bool = Query(True, description="是否保存到数据库"),
    app_service: DetectionApplicationService = Depends(get_detection_app_service),
) -> Dict[str, Any]:
    """
    单张图片检测

    - 快速响应
    - 可选择是否保存到数据库
    - 返回完整的检测结果和分析
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    contents = await file.read()

    try:
        result = await app_service.process_image_detection(
            camera_id=camera_id,
            image_bytes=contents,
            save_to_db=save_to_db
        )
        return result
    except Exception as e:
        logger.exception(f"图片检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
```

### 2. 视频文件处理端点

```python
@router.post("/video", summary="视频文件处理")
async def detect_video(
    file: UploadFile = File(...),
    camera_id: str = Query("api_upload", description="摄像头ID"),
    save_interval: int = Query(30, description="保存间隔（帧数）"),
    app_service: DetectionApplicationService = Depends(get_detection_app_service),
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    视频文件处理

    - 异步处理（后台任务）
    - 返回任务ID
    - 可以通过任务ID查询处理进度
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    # 保存上传的视频文件
    temp_dir = "./temp/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    video_path = os.path.join(temp_dir, f"{int(time.time())}_{file.filename}")

    with open(video_path, "wb") as f:
        f.write(await file.read())

    # 创建后台任务
    task_id = f"video_{int(time.time() * 1000)}"

    background_tasks.add_task(
        process_video_task,
        task_id=task_id,
        camera_id=camera_id,
        video_path=video_path,
        save_interval=save_interval,
        app_service=app_service
    )

    return {
        "ok": True,
        "task_id": task_id,
        "message": "视频处理任务已启动",
        "status_url": f"/api/v1/detect/video/status/{task_id}"
    }

async def process_video_task(
    task_id: str,
    camera_id: str,
    video_path: str,
    save_interval: int,
    app_service: DetectionApplicationService
):
    """后台视频处理任务"""
    try:
        result = await app_service.process_video_file(
            camera_id=camera_id,
            video_path=video_path,
            save_interval=save_interval
        )
        # 保存任务结果到Redis或数据库
        # ...
        logger.info(f"视频处理任务完成: {task_id}")
    except Exception as e:
        logger.exception(f"视频处理任务失败: {task_id}, {e}")
    finally:
        # 清理临时文件
        if os.path.exists(video_path):
            os.remove(video_path)
```

### 3. 实时流WebSocket端点

```python
# src/api/routers/video_stream.py

@router.websocket("/ws/{camera_id}/detect")
async def video_stream_detection_websocket(
    websocket: WebSocket,
    camera_id: str,
    save_interval: int = Query(30, description="保存间隔（帧数）"),
):
    """
    实时视频流检测WebSocket

    - 接收视频帧
    - 实时检测
    - 返回检测结果（轻量级）
    - 按间隔保存到数据库
    """
    app_service = get_detection_app_service()

    await websocket.accept()
    logger.info(f"WebSocket检测已连接: camera={camera_id}")

    frame_count = 0

    try:
        while True:
            # 接收视频帧（二进制数据）
            data = await websocket.receive_bytes()

            # 解码图像
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({"error": "无法解码帧"})
                continue

            frame_count += 1

            # 决定是否保存到数据库
            save_to_db = (frame_count % save_interval == 0)

            # 处理帧
            result = await app_service.process_realtime_stream(
                camera_id=camera_id,
                frame=frame,
                frame_count=frame_count,
                save_to_db=save_to_db
            )

            # 发送结果（不包含帧图像，只发送检测数据）
            await websocket.send_json({
                "frame_count": result["frame_count"],
                "processing_time": result["processing_time"],
                "fps": result["fps"],
                "person_count": result["result"]["person_count"],
                "has_violations": result["result"]["has_violations"],
                "persons": result["result"]["persons"],
                "saved_to_db": result["saved_to_db"],
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket检测已断开: camera={camera_id}")
    except Exception as e:
        logger.exception(f"WebSocket检测错误: camera={camera_id}, {e}")
    finally:
        await websocket.close()
```

---

## 📊 场景对比总结

| 场景 | 处理频率 | 保存策略 | 响应方式 | 性能要求 |
|-----|---------|---------|---------|---------|
| **单张图片** | 单次 | 可选保存 | 同步返回 | 中等 |
| **视频文件** | 批量 | 间隔保存（如每30帧） | 异步任务 | 中等 |
| **实时流** | 连续（25-30 FPS） | 间隔保存（如每30帧） | 实时流式 | **高** |

---

## ✅ 重要设计决策

### 1. 不是每帧都保存到数据库

**原因**：
- **性能瓶颈**：数据库写入是I/O密集型操作
- **数据爆炸**：30 FPS × 60秒 = 1800条记录/分钟
- **实用性**：不需要每帧的数据，间隔采样即可

**策略**：
```python
# 实时流：每30帧（约1秒）保存一次
if frame_count % save_interval == 0:
    await domain_service.process_detection(...)

# 视频文件：每5帧处理，每30帧保存
if frame_count % 5 == 0:  # 处理
    detection_result = pipeline.detect(frame)
    if frame_count % 30 == 0:  # 保存
        await domain_service.process_detection(...)
```

### 2. 轻量级实时响应

**实时流不需要完整的领域模型**：
```python
# ❌ 太重：完整的领域模型
return {
    "detection_record": record.to_dict(),  # 包含所有字段
    "quality_analysis": {...},
    "violations": [...]
}

# ✅ 轻量级：只返回必要数据
return {
    "person_count": 5,
    "has_violations": True,
    "persons": [{"bbox": [...], "track_id": 1}],
    "processing_time": 0.05
}
```

### 3. 不同场景的应用服务方法

```python
class DetectionApplicationService:
    # 场景1：单张图片（完整处理）
    async def process_image_detection(...)

    # 场景2：视频文件（批量处理）
    async def process_video_file(...)

    # 场景3：实时流（轻量级处理）
    async def process_realtime_stream(...)
    async def process_realtime_stream_generator(...)
```

---

## 🎯 最终架构图（包含所有场景）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
场景1: 单张图片上传
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST /api/v1/detect/image
    ↓
DetectionApplicationService.process_image_detection()
    ├─ Pipeline.detect()
    ├─ Domain.process_detection() [保存]
    └─ 返回完整结果

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
场景2: 视频文件上传
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST /api/v1/detect/video
    ↓
BackgroundTask (异步处理)
    ↓
DetectionApplicationService.process_video_file()
    ├─ 逐帧处理
    ├─ 每5帧检测一次（性能优化）
    ├─ 每30帧保存一次（性能优化）
    │   └─ Domain.process_detection() [保存]
    └─ 生成处理后的视频

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
场景3: 实时视频流（命令行）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main.py run_detection()
    ↓
while True:
    frame = cap.read()
    ↓
    DetectionApplicationService.process_realtime_stream()
        ├─ Pipeline.detect()
        ├─ 每30帧保存一次（性能优化）
        │   └─ Domain.process_detection() [保存]
        └─ 返回轻量级结果（用于可视化）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
场景4: 实时视频流（WebSocket）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WebSocket /api/v1/video-stream/ws/{camera_id}/detect
    ↓
while True:
    frame = await websocket.receive_bytes()
    ↓
    DetectionApplicationService.process_realtime_stream()
        ├─ Pipeline.detect()
        ├─ 每30帧保存一次（性能优化）
        │   └─ Domain.process_detection() [保存]
        └─ await websocket.send_json(轻量级结果)
```

---

## ✅ 总结

你的问题非常关键！重新设计后的架构**完全考虑了**三种场景：

### ✅ 已考虑的关键点

1. **实时流性能优化**：不是每帧都保存，按间隔保存
2. **视频文件批处理**：异步处理，批量保存
3. **单张图片快速响应**：同步处理，可选保存
4. **轻量级实时响应**：只返回必要数据，不返回完整领域模型
5. **统一的应用服务**：一个服务支持所有场景

### 📋 实施优先级

1. **优先级1**：完善 `DetectionApplicationService`，支持三种场景
2. **优先级2**：重构API端点，使用应用服务
3. **优先级3**：重构 `main.py`，使用应用服务
4. **优先级4**：实现WebSocket检测端点

---

**关键设计原则**：

> **技术层（Pipeline）负责检测，业务层（Domain）负责记录管理，应用层（Application）协调两者，并根据不同场景决定保存策略。**

这样既保证了架构清晰，又满足了不同场景的性能要求！
