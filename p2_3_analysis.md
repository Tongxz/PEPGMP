# P2.3 阶段分析报告：多模型批处理优化

## 当前状态分析

### 已实现的批处理功能

#### 1. HumanDetector (src/detection/detector.py)
- ✅ **已实现**: `detect_batch()` 方法
- ✅ **特点**:
  - 使用YOLO模型的批量推理能力
  - 支持多张图像同时处理
  - 保持后处理过滤逻辑
  - 详细的日志记录和错误处理

**实现细节**:
```python
def detect_batch(self, images: List[np.ndarray]) -> List[List[Dict]]:
    # 批量推理
    batch_results = self.model(
        images, conf=self.confidence_threshold, iou=self.iou_threshold
    )
    # 后处理过滤
    for result in batch_results:
        # 应用面积、宽高比、尺寸过滤
```

#### 2. YOLOv8PoseDetector (src/detection/pose_detector.py)
- ✅ **已实现**: `_batch_detect_pose_in_rois()` 方法
- ✅ **特点**:
  - 批量检测多个人体ROI的姿态
  - 自动坐标映射回原图
  - 支持失败回退到逐个检测

**实现细节**:
```python
def _batch_detect_pose_in_rois(
    self,
    image: np.ndarray,
    person_bboxes: List[List[float]],
) -> List[Dict[str, Any]]:
    # 步骤1：收集所有人体ROI
    person_rois = [...]
    # 步骤2：批量推理（YOLO支持批量输入）
    batch_results = self.model(person_rois, ...)
    # 步骤3：处理批量结果并映射坐标
    ...
```

### 需要批处理优化的模型

#### 1. HairnetDetector (src/detection/hairnet_detector.py)
- ❌ **未实现批量推理**
- **当前问题**: 逐个处理每个人体头部ROI
- **优化潜力**: 如果使用基于CNN的模型，可以批量推理

#### 2. DeepBehaviorRecognizer (src/detection/deep_behavior_recognizer.py)
- ❌ **未实现批量推理**
- **当前问题**: 实时流处理，一次处理一个时间窗口
- **优化潜力**:
  - 批量分析历史数据
  - 批量验证多个时序窗口
  - 批量特征提取

### 检测管道现状

#### OptimizedDetectionPipeline
- ❌ **未实现多帧批处理**
- **当前流程**:
  1. 人体检测 (单帧)
  2. 发网检测 (基于人体ROI)
  3. 行为检测 (基于人体检测)
- **问题**: 每个检测都是逐帧进行的

### Celery任务现状

#### src/worker/tasks.py
- ✅ **已有**: `batch_process_videos()` 任务
- ⚠️ **问题**:
  - 只是简单循环调用单视频处理任务
  - 没有利用模型批处理能力
  - 没有智能任务调度
  - 模拟实现，缺少实际推理

## 性能瓶颈分析

### 1. 单帧处理开销
- **问题**: 每帧都独立调用模型推理
- **影响**: GPU/CPU资源利用率低
- **数据**: 假设单帧处理50ms，批处理10帧可降至~30-35ms

### 2. 数据传输开销
- **问题**: 频繁的数据拷贝和设备传输
- **影响**: 增加延迟，降低吞吐量

### 3. 模型加载/切换开销
- **问题**: 多个模型交替使用，上下文切换开销
- **影响**: 降低并发处理能力

### 4. 缓存利用不足
- **问题**: 缓存只用于单帧，跨帧相似性未利用
- **影响**: 重复计算相似帧

## 批处理优化策略

### 策略1: 帧级批处理 (Frame-Level Batching)
**适用场景**: 视频流批量分析

**实现方式**:
```python
def detect_frame_batch(self, frames: List[np.ndarray]) -> List[DetectionResult]:
    # 批量人体检测
    person_batches = self.human_detector.detect_batch(frames)

    # 并行处理每个检测
    results = []
    for i, persons in enumerate(person_batches):
        # 发网检测
        hairnet = self._detect_hairnet_for_frame(frames[i], persons)
        # 行为检测
        behavior = self._detect_behavior_for_frame(frames[i], persons)
        results.append(DetectionResult(...))
    return results
```

**优势**:
- 减少模型调用次数
- 提高GPU利用率
- 降低每帧平均延迟

**挑战**:
- 结果顺序维护
- 错误处理和恢复
- 内存管理

### 策略2: ROI级批处理 (ROI-Level Batching)
**适用场景**: 多人员检测、大规模监控

**实现方式**:
```python
def detect_rois_batch(
    self,
    image: np.ndarray,
    person_bboxes: List[List[float]]
) -> List[Dict]:
    # 收集所有ROI
    rois = [image[y1:y2, x1:x2] for (x1, y1, x2, y2) in person_bboxes]

    # 批量推理
    batch_results = self.model(rois, ...)

    # 映射回原图
    return self._map_results_to_original(batch_results, person_bboxes)
```

**优势**:
- 充分利用模型批处理能力
- 减少模型切换开销
- 提高吞吐量

**挑战**:
- ROI尺寸差异大
- 坐标映射复杂
- Padding策略

### 策略3: 任务级批处理 (Task-Level Batching)
**适用场景**: 异步任务队列、批量任务

**实现方式**:
```python
@celery_app.task(bind=True)
def batch_detection_task(self, frame_ids: List[str]):
    # 按相似性分组
    groups = self._group_frames_by_similarity(frame_ids)

    # 批量处理每组
    for group in groups:
        results = self._process_group_batch(group)

    return results
```

**优势**:
- 智能任务调度
- 资源利用率优化
- 降低队列压力

**挑战**:
- 任务分组策略
- 超时处理
- 优先级管理

### 策略4: 混合批处理 (Hybrid Batching)
**适用场景**: 复杂检测流水线

**实现方式**:
```python
def detect_comprehensive_batch(self, frames: List[np.ndarray]):
    # 阶段1: 批量人体检测
    person_batches = self.human_detector.detect_batch(frames)

    # 阶段2: 批量发网检测（跨帧ROI批处理）
    all_rois = []
    roi_mappings = []
    for i, persons in enumerate(person_batches):
        for bbox in persons:
            rois.append(frames[i][bbox[1]:bbox[3], bbox[0]:bbox[2]])
            roi_mappings.append((i, bbox))

    hairnet_results = self.hairnet_detector.detect_batch(all_rois)

    # 阶段3: 批量行为检测
    ...
```

**优势**:
- 最大化批处理收益
- 最小化数据传输
- 优化整体延迟

**挑战**:
- 复杂度高
- 难以调试
- 需要精心设计

## 设计方案

### 通用批处理接口设计

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np

class BatchableDetector(ABC):
    """可批处理检测器接口"""

    @abstractmethod
    def detect(self, data: Any) -> List[Dict]:
        """单个检测"""
        pass

    @abstractmethod
    def detect_batch(
        self,
        data_list: List[Any],
        batch_size: Optional[int] = None,
        **kwargs
    ) -> List[List[Dict]]:
        """
        批量检测

        Args:
            data_list: 输入数据列表
            batch_size: 批大小，None表示全部一次性处理
            **kwargs: 其他参数

        Returns:
            检测结果列表，每个元素对应一个输入
        """
        pass
```

### 批处理调度器设计

```python
class BatchScheduler:
    """批处理任务调度器"""

    def __init__(
        self,
        max_batch_size: int = 16,
        max_wait_time: float = 0.05,  # 50ms
        device: str = "auto"
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.pending_items: List[Any] = []
        self.futures: List[Any] = []

    async def schedule(
        self,
        item: Any,
        detector: BatchableDetector
    ) -> List[Dict]:
        """
        调度检测任务

        Args:
            item: 检测项
            detector: 检测器

        Returns:
            检测结果
        """
        # 创建Future
        future = asyncio.Future()
        self.futures.append(future)

        # 添加到待处理队列
        self.pending_items.append(item)

        # 检查是否触发批处理
        if len(self.pending_items) >= self.max_batch_size:
            await self._process_batch(detector)
        else:
            # 设置超时处理
            asyncio.create_task(self._timeout_process(detector))

        return await future

    async def _timeout_process(self, detector: BatchableDetector):
        """超时触发批处理"""
        await asyncio.sleep(self.max_wait_time)
        if self.pending_items:
            await self._process_batch(detector)

    async def _process_batch(self, detector: BatchableDetector):
        """处理批次"""
        batch = self.pending_items[:]
        self.pending_items.clear()

        # 批量推理
        results = detector.detect_batch(batch)

        # 设置Future结果
        for i, result in enumerate(results):
            self.futures[i].set_result(result)
```

### 性能监控设计

```python
class BatchPerformanceMonitor:
    """批处理性能监控"""

    def __init__(self):
        self.metrics = {
            "batch_sizes": [],
            "batch_times": [],
            "per_item_times": [],
            "cache_hit_rate": 0.0,
        }

    def record_batch(
        self,
        batch_size: int,
        batch_time: float,
        items: List[Any]
    ):
        """记录批处理性能"""
        self.metrics["batch_sizes"].append(batch_size)
        self.metrics["batch_times"].append(batch_time)
        per_item_time = batch_time / batch_size
        self.metrics["per_item_times"].append(per_item_time)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "avg_batch_size": np.mean(self.metrics["batch_sizes"]),
            "avg_batch_time": np.mean(self.metrics["batch_times"]),
            "avg_per_item_time": np.mean(self.metrics["per_item_times"]),
            "throughput": 1.0 / np.mean(self.metrics["per_item_times"]),
        }
```

## 实施计划

### 第一阶段：基础设施 (30分钟)
1. ✅ 分析现状（已完成）
2. 设计通用批处理接口
3. 实现批处理调度器
4. 实现性能监控

### 第二阶段：模型适配 (60分钟)
1. HairnetDetector批处理适配
2. DeepBehaviorRecognizer批处理适配
3. OptimizedDetectionPipeline批处理扩展

### 第三阶段：Celery任务优化 (60分钟)
1. 更新Celery任务支持批处理
2. 实现智能任务分组
3. 添加批处理性能指标

### 第四阶段：测试与优化 (60分钟)
1. 编写单元测试
2. 编写集成测试
3. 性能基准测试
4. 优化调整

## 预期收益

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 单帧处理延迟 | 50ms | 30-35ms | 30-40% |
| 批处理吞吐量 | 20 FPS | 30-35 FPS | 50-75% |
| GPU利用率 | 40-50% | 70-80% | 40-60% |
| 内存效率 | 中 | 高 | +20% |

## 风险与挑战

### 技术风险
1. **批处理顺序混乱**: 结果与输入顺序不对应
   - **缓解**: 严格维护索引映射

2. **内存溢出**: 大批次导致内存不足
   - **缓解**: 动态批大小、显存监控

3. **延迟增加**: 等待批次填满导致延迟增加
   - **缓解**: 超时机制、动态调整

### 兼容性风险
1. **接口破坏**: 批处理接口与现有代码不兼容
   - **缓解**: 保持单检测接口、渐进式迁移

2. **性能回退**: 批处理在某些场景下反而更慢
   - **缓解**: 自适应批处理、性能回退机制

## 下一步行动

1. ✅ 完成现状分析（已完成）
2. ⏭️ 实现通用批处理接口
3. ⏭️ 适配HairnetDetector
4. ⏭️ 扩展OptimizedDetectionPipeline
5. ⏭️ 更新Celery任务
6. ⏭️ 编写测试
7. ⏭️ 性能基准测试
