# 任务1.1和1.3统一数据载体设计

## 📋 问题分析

### 核心问题

**任务1.1（状态保持）**和**任务1.3（异步处理）**都需要：
- 帧ID管理
- 时间戳同步
- 检测结果关联
- 状态一致性保证

**当前问题**：
- 没有统一的数据载体
- 帧ID和时间戳管理分散
- 异步处理可能导致结果错位
- 状态管理无法准确关联到具体帧

---

## 🎯 解决方案：统一数据载体设计

### 设计原则

1. **单一数据源**：所有检测相关数据都通过统一的数据载体传递
2. **不可变性**：数据载体一旦创建，核心字段不可变
3. **可追溯性**：每个检测结果都能追溯到原始帧
4. **线程安全**：支持异步处理

---

## 📐 统一数据载体设计

### 1. FrameMetadata（帧元数据）

**文件**：`src/core/frame_metadata.py`（新建）

**设计**：
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

class FrameSource(Enum):
    """帧来源"""
    REALTIME_STREAM = "realtime_stream"
    VIDEO_FILE = "video_file"
    IMAGE_FILE = "image_file"
    API_REQUEST = "api_request"

@dataclass(frozen=True)  # 不可变，保证线程安全
class FrameMetadata:
    """帧元数据 - 统一的数据载体

    所有检测相关的数据都通过此载体传递，确保：
    1. 帧ID和时间戳一致性
    2. 检测结果可追溯
    3. 状态管理可关联
    4. 异步处理安全
    """

    # 核心标识（不可变）
    frame_id: str  # 全局唯一帧ID
    timestamp: datetime  # 帧时间戳（精确到微秒）
    camera_id: str  # 摄像头ID
    source: FrameSource  # 帧来源

    # 帧数据
    frame: Optional[np.ndarray] = None  # 原始帧数据（可选，可能很大）
    frame_hash: Optional[str] = None  # 帧哈希值（用于缓存）

    # 检测结果（可变，通过方法更新）
    person_detections: List[Dict] = field(default_factory=list)
    hairnet_results: List[Dict] = field(default_factory=list)
    pose_detections: List[Dict] = field(default_factory=list)
    handwash_results: List[Dict] = field(default_factory=list)
    sanitize_results: List[Dict] = field(default_factory=list)

    # 状态信息
    detection_state: Optional[str] = None  # 检测状态（normal, violation, transition）
    state_confidence: float = 0.0  # 状态置信度

    # 处理信息
    processing_times: Dict[str, float] = field(default_factory=dict)
    processing_stage: str = "pending"  # pending, processing, completed, failed

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """后处理：确保frame_id唯一性"""
        if not self.frame_id:
            object.__setattr__(self, 'frame_id', str(uuid.uuid4()))

    def with_detection_results(
        self,
        person_detections: Optional[List[Dict]] = None,
        hairnet_results: Optional[List[Dict]] = None,
        pose_detections: Optional[List[Dict]] = None,
        handwash_results: Optional[List[Dict]] = None,
        sanitize_results: Optional[List[Dict]] = None,
    ) -> 'FrameMetadata':
        """创建包含检测结果的新实例（不可变对象需要创建新实例）"""
        return FrameMetadata(
            frame_id=self.frame_id,
            timestamp=self.timestamp,
            camera_id=self.camera_id,
            source=self.source,
            frame=self.frame,
            frame_hash=self.frame_hash,
            person_detections=person_detections or self.person_detections,
            hairnet_results=hairnet_results or self.hairnet_results,
            pose_detections=pose_detections or self.pose_detections,
            handwash_results=handwash_results or self.handwash_results,
            sanitize_results=sanitize_results or self.sanitize_results,
            detection_state=self.detection_state,
            state_confidence=self.state_confidence,
            processing_times=self.processing_times,
            processing_stage=self.processing_stage,
            metadata=self.metadata,
        )

    def with_state(
        self,
        detection_state: str,
        state_confidence: float,
    ) -> 'FrameMetadata':
        """创建包含状态信息的新实例"""
        return FrameMetadata(
            frame_id=self.frame_id,
            timestamp=self.timestamp,
            camera_id=self.camera_id,
            source=self.source,
            frame=self.frame,
            frame_hash=self.frame_hash,
            person_detections=self.person_detections,
            hairnet_results=self.hairnet_results,
            pose_detections=self.pose_detections,
            handwash_results=self.handwash_results,
            sanitize_results=self.sanitize_results,
            detection_state=detection_state,
            state_confidence=state_confidence,
            processing_times=self.processing_times,
            processing_stage=self.processing_stage,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "camera_id": self.camera_id,
            "source": self.source.value,
            "frame_hash": self.frame_hash,
            "person_detections": self.person_detections,
            "hairnet_results": self.hairnet_results,
            "pose_detections": self.pose_detections,
            "handwash_results": self.handwash_results,
            "sanitize_results": self.sanitize_results,
            "detection_state": self.detection_state,
            "state_confidence": self.state_confidence,
            "processing_times": self.processing_times,
            "processing_stage": self.processing_stage,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FrameMetadata':
        """从字典创建（用于反序列化）"""
        return cls(
            frame_id=data["frame_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            camera_id=data["camera_id"],
            source=FrameSource(data["source"]),
            frame_hash=data.get("frame_hash"),
            person_detections=data.get("person_detections", []),
            hairnet_results=data.get("hairnet_results", []),
            pose_detections=data.get("pose_detections", []),
            handwash_results=data.get("handwash_results", []),
            sanitize_results=data.get("sanitize_results", []),
            detection_state=data.get("detection_state"),
            state_confidence=data.get("state_confidence", 0.0),
            processing_times=data.get("processing_times", {}),
            processing_stage=data.get("processing_stage", "pending"),
            metadata=data.get("metadata", {}),
        )
```

---

### 2. FrameMetadataManager（帧元数据管理器）

**文件**：`src/core/frame_metadata_manager.py`（新建）

**功能**：
- 帧元数据生命周期管理
- 帧ID生成和管理
- 时间戳同步
- 检测结果关联

**设计**：
```python
from collections import deque
from threading import Lock
from typing import Dict, Optional, List
from datetime import datetime, timedelta

class FrameMetadataManager:
    """帧元数据管理器

    负责：
    1. 生成和管理帧ID
    2. 维护帧元数据索引
    3. 确保时间戳同步
    4. 支持异步处理
    """

    def __init__(
        self,
        max_history: int = 1000,  # 最大历史记录数
        sync_window: float = 0.1,  # 同步时间窗口（秒）
    ):
        self.max_history = max_history
        self.sync_window = sync_window

        # 索引结构
        self.frame_index: Dict[str, FrameMetadata] = {}  # frame_id -> FrameMetadata
        self.timestamp_index: Dict[datetime, List[str]] = {}  # timestamp -> [frame_ids]
        self.camera_index: Dict[str, List[str]] = {}  # camera_id -> [frame_ids]

        # 历史记录（LRU）
        self.history: deque = deque(maxlen=max_history)

        # 线程安全
        self.lock = Lock()

        # 帧ID生成器
        self.frame_counter: Dict[str, int] = {}  # camera_id -> counter

    def create_frame_metadata(
        self,
        frame: np.ndarray,
        camera_id: str,
        source: FrameSource = FrameSource.REALTIME_STREAM,
        timestamp: Optional[datetime] = None,
    ) -> FrameMetadata:
        """创建帧元数据"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # 生成唯一帧ID
        if camera_id not in self.frame_counter:
            self.frame_counter[camera_id] = 0
        self.frame_counter[camera_id] += 1

        frame_id = f"{camera_id}_{self.frame_counter[camera_id]}_{timestamp.timestamp()}"

        # 生成帧哈希
        frame_hash = self._generate_frame_hash(frame)

        # 创建帧元数据
        frame_meta = FrameMetadata(
            frame_id=frame_id,
            timestamp=timestamp,
            camera_id=camera_id,
            source=source,
            frame=frame,  # 可选：可以只保存哈希，不保存完整帧
            frame_hash=frame_hash,
        )

        # 添加到索引
        with self.lock:
            self.frame_index[frame_id] = frame_meta
            self.history.append(frame_meta)

            # 时间戳索引（使用时间窗口）
            timestamp_key = self._round_timestamp(timestamp)
            if timestamp_key not in self.timestamp_index:
                self.timestamp_index[timestamp_key] = []
            self.timestamp_index[timestamp_key].append(frame_id)

            # 摄像头索引
            if camera_id not in self.camera_index:
                self.camera_index[camera_id] = []
            self.camera_index[camera_id].append(frame_id)

        return frame_meta

    def update_detection_results(
        self,
        frame_id: str,
        person_detections: Optional[List[Dict]] = None,
        hairnet_results: Optional[List[Dict]] = None,
        pose_detections: Optional[List[Dict]] = None,
        handwash_results: Optional[List[Dict]] = None,
        sanitize_results: Optional[List[Dict]] = None,
    ) -> Optional[FrameMetadata]:
        """更新检测结果"""
        with self.lock:
            if frame_id not in self.frame_index:
                logger.warning(f"Frame {frame_id} not found in index")
                return None

            old_meta = self.frame_index[frame_id]
            new_meta = old_meta.with_detection_results(
                person_detections=person_detections,
                hairnet_results=hairnet_results,
                pose_detections=pose_detections,
                handwash_results=handwash_results,
                sanitize_results=sanitize_results,
            )

            # 更新索引
            self.frame_index[frame_id] = new_meta

            # 更新历史记录
            for i, meta in enumerate(self.history):
                if meta.frame_id == frame_id:
                    self.history[i] = new_meta
                    break

        return new_meta

    def update_state(
        self,
        frame_id: str,
        detection_state: str,
        state_confidence: float,
    ) -> Optional[FrameMetadata]:
        """更新状态信息"""
        with self.lock:
            if frame_id not in self.frame_index:
                return None

            old_meta = self.frame_index[frame_id]
            new_meta = old_meta.with_state(
                detection_state=detection_state,
                state_confidence=state_confidence,
            )

            self.frame_index[frame_id] = new_meta

            # 更新历史记录
            for i, meta in enumerate(self.history):
                if meta.frame_id == frame_id:
                    self.history[i] = new_meta
                    break

        return new_meta

    def get_frame_metadata(self, frame_id: str) -> Optional[FrameMetadata]:
        """根据frame_id获取帧元数据"""
        with self.lock:
            return self.frame_index.get(frame_id)

    def get_frames_by_timestamp_range(
        self,
        start: datetime,
        end: datetime,
        camera_id: Optional[str] = None,
    ) -> List[FrameMetadata]:
        """根据时间范围获取帧元数据"""
        result = []

        with self.lock:
            # 遍历时间戳索引
            for timestamp_key, frame_ids in self.timestamp_index.items():
                if start <= timestamp_key <= end:
                    for frame_id in frame_ids:
                        frame_meta = self.frame_index.get(frame_id)
                        if frame_meta:
                            if camera_id is None or frame_meta.camera_id == camera_id:
                                result.append(frame_meta)

        # 按时间戳排序
        result.sort(key=lambda x: x.timestamp)
        return result

    def _generate_frame_hash(self, frame: np.ndarray) -> str:
        """生成帧哈希值"""
        import hashlib
        h, w = frame.shape[:2]
        sample_pixels = frame[:: h // 10, :: w // 10].flatten()[:100]
        hash_obj = hashlib.md5(sample_pixels.tobytes())
        return hash_obj.hexdigest()

    def _round_timestamp(self, timestamp: datetime) -> datetime:
        """将时间戳四舍五入到同步窗口"""
        # 将时间戳四舍五入到最近的sync_window秒
        seconds = timestamp.timestamp()
        rounded = round(seconds / self.sync_window) * self.sync_window
        return datetime.fromtimestamp(rounded)
```

---

## 🔄 任务1.1和1.3的集成设计

### 任务1.1：状态保持（使用FrameMetadata）

**修改**：`src/core/state_manager.py`

```python
class StateManager:
    """状态管理器 - 使用FrameMetadata作为数据载体"""

    def __init__(self, ...):
        # ... 现有代码 ...
        self.frame_metadata_manager: Optional[FrameMetadataManager] = None

    def update_state(
        self,
        frame_meta: FrameMetadata,  # 使用统一的数据载体
        current_confidence: float,
    ) -> Tuple[str, float]:
        """
        更新状态并返回稳定状态

        Args:
            frame_meta: 帧元数据（包含frame_id, timestamp等）
            current_confidence: 当前置信度

        Returns:
            (stable_state_type, stable_confidence)
        """
        track_id = frame_meta.metadata.get("track_id")
        if track_id is None:
            # 如果没有track_id，使用frame_id
            track_id = frame_meta.frame_id

        # 更新状态（使用frame_id确保唯一性）
        stable_state, stable_confidence = self._update_track_state(
            track_id,
            current_confidence,
            frame_meta.frame_id,
            frame_meta.timestamp
        )

        # 更新帧元数据的状态信息
        if self.frame_metadata_manager:
            self.frame_metadata_manager.update_state(
                frame_meta.frame_id,
                stable_state,
                stable_confidence
            )

        return stable_state, stable_confidence
```

---

### 任务1.3：异步处理（使用FrameMetadata）

**修改**：`src/core/async_detection_pipeline.py`

```python
class AsyncDetectionPipeline:
    """异步检测管道 - 使用FrameMetadata作为数据载体"""

    def __init__(
        self,
        ...,
        frame_metadata_manager: Optional[FrameMetadataManager] = None,
    ):
        # ... 现有代码 ...
        self.frame_metadata_manager = frame_metadata_manager or FrameMetadataManager()

    async def detect_comprehensive_async(
        self,
        frame_meta: FrameMetadata,  # 使用统一的数据载体
        enable_hairnet: bool = True,
        enable_handwash: bool = True,
        enable_sanitize: bool = True,
    ) -> FrameMetadata:
        """异步综合检测 - 输入和输出都是FrameMetadata"""

        # 更新处理阶段
        frame_meta = frame_meta.with_processing_stage("processing")

        # 阶段1: 人体检测（必须串行）
        person_detections = await asyncio.to_thread(
            self.human_detector.detect, frame_meta.frame
        )

        # 更新检测结果
        frame_meta = self.frame_metadata_manager.update_detection_results(
            frame_meta.frame_id,
            person_detections=person_detections
        )

        if not person_detections:
            return frame_meta.with_processing_stage("completed")

        # 阶段2-3: 并行执行发网检测和姿态检测
        futures = {}

        if enable_hairnet:
            futures['hairnet'] = asyncio.to_thread(
                self.hairnet_detector.detect_hairnet_compliance,
                frame_meta.frame, person_detections
            )

        if self.pose_detector:
            person_bboxes = [det.get("bbox") for det in person_detections]
            futures['pose'] = asyncio.to_thread(
                self.pose_detector.detect_in_rois,
                frame_meta.frame, person_bboxes
            )

        # 等待所有并行任务完成
        results = await asyncio.gather(*futures.values(), return_exceptions=True)

        # 处理结果并更新frame_meta
        hairnet_results = results[0] if 'hairnet' in futures else []
        pose_detections = results[1] if 'pose' in futures else []

        frame_meta = self.frame_metadata_manager.update_detection_results(
            frame_meta.frame_id,
            hairnet_results=hairnet_results,
            pose_detections=pose_detections
        )

        # 阶段4: 行为检测（依赖姿态检测结果）
        # ... 后续逻辑 ...

        return frame_meta.with_processing_stage("completed")
```

---

## 🔗 任务依赖关系调整

### 新的任务顺序

**任务0（前置任务）**：实现统一数据载体（1-2天）
- 必须在任务1.1和1.3之前完成
- 提供基础数据结构

**任务1.1**：状态保持（依赖任务0）
- 使用FrameMetadata作为数据载体
- 通过FrameMetadataManager管理状态

**任务1.3**：异步处理（依赖任务0）
- 使用FrameMetadata作为数据载体
- 确保异步处理结果正确关联

---

## 📊 数据流设计

### 完整数据流

```
视频帧输入
    ↓
[任务0] FrameMetadataManager.create_frame_metadata()
    ↓
FrameMetadata (frame_id, timestamp, camera_id, frame)
    ↓
[任务1.3] AsyncDetectionPipeline.detect_comprehensive_async(frame_meta)
    ├─ 异步任务1: 人体检测
    ├─ 异步任务2: 发网检测（并行）
    └─ 异步任务3: 姿态检测（并行）
    ↓
FrameMetadata (更新检测结果)
    ↓
[任务1.1] StateManager.update_state(frame_meta)
    ↓
FrameMetadata (更新状态信息)
    ↓
最终结果输出
```

---

## ⚠️ 关键设计决策

### 1. 不可变数据载体

**决策**：使用`@dataclass(frozen=True)`使FrameMetadata不可变

**原因**：
- 线程安全（异步处理需要）
- 防止意外修改
- 支持函数式编程风格

**代价**：
- 每次更新需要创建新实例（性能开销小）

### 2. 帧数据存储策略

**决策**：FrameMetadata中的`frame`字段可选

**原因**：
- 帧数据可能很大，占用内存
- 可以通过frame_hash从缓存获取
- 只在需要时保存完整帧

**实现**：
```python
# 选项1：不保存完整帧（节省内存）
frame_meta = FrameMetadata(
    frame_id=...,
    frame=None,  # 不保存
    frame_hash=hash_value,  # 只保存哈希
)

# 选项2：保存完整帧（需要时）
frame_meta = FrameMetadata(
    frame_id=...,
    frame=frame_array,  # 保存完整帧
    frame_hash=hash_value,
)
```

### 3. 时间戳同步策略

**决策**：使用时间窗口（sync_window）进行时间戳同步

**原因**：
- 不同模型处理时间不同
- 需要在一定时间窗口内匹配结果
- 支持异步处理的延迟

**实现**：
```python
# 时间戳四舍五入到0.1秒窗口
timestamp_key = round(timestamp.timestamp() / 0.1) * 0.1
```

---

## 🧪 测试策略

### 单元测试

1. **FrameMetadata测试**：
   - 不可变性测试
   - 序列化/反序列化测试
   - 方法调用测试

2. **FrameMetadataManager测试**：
   - 帧ID生成唯一性测试
   - 时间戳索引测试
   - 并发访问测试

### 集成测试

1. **任务1.1 + 任务0**：
   - 状态更新与帧元数据关联测试
   - 多帧状态一致性测试

2. **任务1.3 + 任务0**：
   - 异步处理结果关联测试
   - 时间戳同步测试

3. **任务1.1 + 任务1.3 + 任务0**：
   - 端到端测试
   - 并发处理测试
   - 数据一致性测试

---

## 📝 实施计划调整

### 新增任务0：统一数据载体（1-2天）

**优先级**：⭐⭐⭐（最高，其他任务依赖）

**步骤**：
1. 实现FrameMetadata类（0.5天）
2. 实现FrameMetadataManager类（0.5天）
3. 单元测试（0.5天）
4. 集成测试（0.5天）

### 任务1.1调整：依赖任务0

**修改**：
- 使用FrameMetadata作为输入/输出
- 通过FrameMetadataManager管理状态
- 确保frame_id和时间戳一致性

### 任务1.3调整：依赖任务0

**修改**：
- 使用FrameMetadata作为输入/输出
- 异步任务返回结果时关联frame_id
- 确保异步处理结果正确更新到FrameMetadata

---

## ✅ 验收标准

### 任务0验收标准

- [ ] FrameMetadata类实现完成
- [ ] FrameMetadataManager类实现完成
- [ ] 单元测试覆盖率 > 90%
- [ ] 线程安全测试通过
- [ ] 性能测试：创建/更新 < 1ms

### 集成验收标准

- [ ] 任务1.1和1.3都能正确使用FrameMetadata
- [ ] 异步处理结果正确关联到frame_id
- [ ] 状态更新正确关联到frame_id
- [ ] 时间戳同步测试通过
- [ ] 并发处理测试通过

---

## 📚 相关文档

- `docs/OPTIMIZATION_IMPLEMENTATION_PLAN.md` - 完整实施计划
- `src/core/frame_metadata.py` - FrameMetadata实现（待创建）
- `src/core/frame_metadata_manager.py` - FrameMetadataManager实现（待创建）
