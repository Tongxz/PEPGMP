"""
批量处理框架 - 支持多模型批处理优化

提供通用的批处理接口、调度器和性能监控功能。

主要组件：
1. BatchableDetector - 可批处理检测器接口
2. BatchScheduler - 批处理调度器
3. BatchPerformanceMonitor - 性能监控
4. BatchUtils - 批处理工具函数
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """批处理结果"""

    results: List[Any]
    batch_size: int
    processing_time: float
    per_item_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BatchableDetector(ABC):
    """可批处理检测器接口

    所有支持批处理的检测器应该实现此接口
    """

    @abstractmethod
    def detect(self, data: Any, **kwargs) -> List[Dict]:
        """
        单个检测

        Args:
            data: 输入数据
            **kwargs: 其他参数

        Returns:
            检测结果列表
        """
        pass

    def detect_batch(
        self,
        data_list: List[Any],
        batch_size: Optional[int] = None,
        **kwargs,
    ) -> List[List[Dict]]:
        """
        批量检测（默认实现：循环调用单检测）

        Args:
            data_list: 输入数据列表
            batch_size: 批大小，None表示全部一次性处理
            **kwargs: 其他参数

        Returns:
            检测结果列表，每个元素对应一个输入
        """
        if not data_list:
            return []

        results = []
        for i, data in enumerate(data_list):
            try:
                result = self.detect(data, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"批处理中第 {i} 个检测失败: {e}")
                results.append([])  # 失败返回空结果

        return results


class BatchScheduler:
    """批处理任务调度器

    智能调度检测任务，动态批处理以提高性能
    """

    def __init__(
        self,
        max_batch_size: int = 16,
        max_wait_time: float = 0.05,  # 50ms
        min_batch_size: int = 2,
    ):
        """
        初始化批处理调度器

        Args:
            max_batch_size: 最大批大小
            max_wait_time: 最大等待时间（秒）
            min_batch_size: 最小批大小
        """
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.min_batch_size = min_batch_size

        self.pending_items: List[Tuple[Any, asyncio.Future]] = []
        self.lock = asyncio.Lock()
        self._timeout_task: Optional[asyncio.Task] = None

    async def schedule(
        self,
        item: Any,
        detector: BatchableDetector,
        **kwargs,
    ) -> List[Dict]:
        """
        调度检测任务

        Args:
            item: 检测项
            detector: 检测器
            **kwargs: 传递给检测器的参数

        Returns:
            检测结果
        """
        # 创建Future
        future = asyncio.Future()

        # 添加到待处理队列
        async with self.lock:
            self.pending_items.append((item, future))

            # 检查是否触发批处理
            if len(self.pending_items) >= self.max_batch_size:
                # 取消之前的超时任务
                if self._timeout_task is not None:
                    self._timeout_task.cancel()
                # 立即处理
                asyncio.create_task(self._process_batch(detector, **kwargs))
            else:
                # 设置超时处理（避免小批次永远不被处理）
                if self._timeout_task is None:
                    self._timeout_task = asyncio.create_task(
                        self._timeout_process(detector, **kwargs)
                    )

        return await future

    async def _timeout_process(self, detector: BatchableDetector, **kwargs):
        """超时触发批处理"""
        await asyncio.sleep(self.max_wait_time)

        # 检查是否需要处理批次
        async with self.lock:
            if not self.pending_items:
                return
        
        # 调用_process_batch，它会自己处理锁逻辑
        await self._process_batch(detector, **kwargs)

    def _extract_batch(self):
        """在锁内提取批次数据"""
        if not self.pending_items:
            return None, None

        batch = self.pending_items[:]
        self.pending_items.clear()

        if self._timeout_task is not None:
            self._timeout_task.cancel()
            self._timeout_task = None

        # 提取数据和Future
        items = [item for item, _ in batch]
        futures = [future for _, future in batch]
        return items, futures

    async def _process_batch(self, detector: BatchableDetector, **kwargs):
        """处理批次"""
        # 取出批次
        async with self.lock:
            if not self.pending_items:
                return
            items, futures = self._extract_batch()

        if not items:
            return

        # 批量推理
        try:
            if len(items) < self.min_batch_size and hasattr(detector, "detect"):
                results = [detector.detect(item, **kwargs) for item in items]
            else:
                results = detector.detect_batch(items, **kwargs)
            if results is None:
                results = []

            if len(results) != len(futures):
                logger.error(
                    "批处理结果数量不匹配: results=%s futures=%s",
                    len(results),
                    len(futures),
                )

            # 设置Future结果（多余结果忽略，不足填空）
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)

            if len(results) < len(futures):
                for future in futures[len(results):]:
                    if not future.done():
                        future.set_result([])
        except Exception as e:
            logger.error(f"批处理失败: {e}")
            # 设置所有Future为失败
            for future in futures:
                if not future.done():
                    future.set_exception(e)

    async def flush(self, detector: BatchableDetector, **kwargs):
        """立即处理所有待处理项"""
        # 检查是否有待处理项
        async with self.lock:
            if not self.pending_items:
                return
        
        # 调用_process_batch，它会自己处理锁逻辑
        await self._process_batch(detector, **kwargs)


class BatchPerformanceMonitor:
    """批处理性能监控"""

    def __init__(self, history_size: int = 1000):
        """
        初始化性能监控

        Args:
            history_size: 历史记录最大数量
        """
        self.history_size = history_size
        self.batch_sizes: List[int] = []
        self.batch_times: List[float] = []
        self.per_item_times: List[float] = []
        self.cache_hits: int = 0
        self.cache_misses: int = 0

    def record_batch(
        self,
        batch_size: int,
        batch_time: float,
        per_item_time: Optional[float] = None,
    ):
        """
        记录批处理性能

        Args:
            batch_size: 批大小
            batch_time: 批处理总时间
            per_item_time: 平均每项时间（可选，自动计算）
        """
        self.batch_sizes.append(batch_size)
        self.batch_times.append(batch_time)

        if per_item_time is None:
            per_item_time = batch_time / max(batch_size, 1)

        self.per_item_times.append(per_item_time)

        # 保持历史记录大小
        if len(self.batch_sizes) > self.history_size:
            self.batch_sizes = self.batch_sizes[-self.history_size :]
            self.batch_times = self.batch_times[-self.history_size :]
            self.per_item_times = self.per_item_times[-self.history_size :]

    def record_cache_hit(self):
        """记录缓存命中"""
        self.cache_hits += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.cache_misses += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.batch_sizes:
            return {
                "total_batches": 0,
                "avg_batch_size": 0,
                "avg_batch_time": 0,
                "avg_per_item_time": 0,
                "throughput": 0,
                "cache_hit_rate": 0.0,
            }

        total_batches = len(self.batch_sizes)
        avg_batch_size = np.mean(self.batch_sizes)
        avg_batch_time = np.mean(self.batch_times)
        avg_per_item_time = np.mean(self.per_item_times)

        # 计算吞吐量 (items/second)
        throughput = 1.0 / avg_per_item_time if avg_per_item_time > 0 else 0

        # 计算缓存命中率
        total_cache = self.cache_hits + self.cache_misses
        cache_hit_rate = (
            self.cache_hits / total_cache if total_cache > 0 else 0.0
        )

        return {
            "total_batches": total_batches,
            "avg_batch_size": avg_batch_size,
            "avg_batch_time": avg_batch_time,
            "avg_per_item_time": avg_per_item_time,
            "throughput": throughput,
            "cache_hit_rate": cache_hit_rate,
            "min_batch_size": np.min(self.batch_sizes) if self.batch_sizes else 0,
            "max_batch_size": np.max(self.batch_sizes) if self.batch_sizes else 0,
            "total_items": sum(self.batch_sizes),
        }

    def reset(self):
        """重置统计信息"""
        self.batch_sizes.clear()
        self.batch_times.clear()
        self.per_item_times.clear()
        self.cache_hits = 0
        self.cache_misses = 0


class BatchUtils:
    """批处理工具函数"""

    @staticmethod
    def group_rois_by_size(
        rois: List[np.ndarray], max_size_diff: float = 0.3
    ) -> List[List[Tuple[int, np.ndarray]]]:
        """
        按尺寸分组ROI

        Args:
            rois: ROI列表
            max_size_diff: 最大尺寸差异比例

        Returns:
            分组后的ROI列表，每组包含(索引, ROI)
        """
        groups = []

        for i, roi in enumerate(rois):
            if roi.size == 0:
                continue

            # 计算ROI尺寸
            h, w = roi.shape[:2]
            size = h * w

            # 尝试加入现有组
            added = False
            for group in groups:
                # 检查第一项的尺寸
                _, first_roi = group[0]
                first_h, first_w = first_roi.shape[:2]
                first_size = first_h * first_w

                # 计算尺寸差异
                size_diff = abs(size - first_size) / first_size

                if size_diff <= max_size_diff:
                    group.append((i, roi))
                    added = True
                    break

            # 创建新组
            if not added:
                groups.append([(i, roi)])

        return groups

    @staticmethod
    def pad_roi_to_size(roi: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        将ROI填充到目标尺寸

        Args:
            roi: 输入ROI
            target_size: 目标尺寸 (height, width)

        Returns:
            填充后的ROI
        """
        h, w = roi.shape[:2]
        target_h, target_w = target_size

        if h >= target_h and w >= target_w:
            # 裁剪
            start_h = (h - target_h) // 2
            start_w = (w - target_w) // 2
            return roi[start_h:start_h + target_h, start_w:start_w + target_w]

        # 填充
        padded = np.zeros((target_h, target_w) + roi.shape[2:], dtype=roi.dtype)

        # 计算起始位置
        start_h = (target_h - h) // 2
        start_w = (target_w - w) // 2

        # 复制ROI
        padded[start_h:start_h + h, start_w:start_w + w] = roi

        return padded

    @staticmethod
    def map_results_to_original(
        batch_results: List[List[Dict]],
        mappings: List[Tuple[int, ...]],
    ) -> List[List[Dict]]:
        """
        将批处理结果映射回原始顺序

        Args:
            batch_results: 批处理结果
            mappings: 映射关系列表，每个元素是(原始索引, ...)

        Returns:
            映射后的结果列表
        """
        # 创建结果列表
        num_items = len(mappings)
        results: List[List[Dict]] = [[] for _ in range(num_items)]

        # 填充结果
        for batch_idx, mapping in enumerate(mappings):
            original_idx = mapping[0]
            result = batch_results[batch_idx]
            results[original_idx] = result

        return results

    @staticmethod
    def calculate_optimal_batch_size(
        item_sizes: List[int],
        max_memory: int,
        base_memory_per_item: int = 10 * 1024 * 1024,  # 10MB
    ) -> int:
        """
        计算最优批大小

        Args:
            item_sizes: 每个项目的内存占用
            max_memory: 最大可用内存
            base_memory_per_item: 每个项目的基础内存占用

        Returns:
            最优批大小
        """
        # 按大小排序
        sorted_sizes = sorted(item_sizes)

        # 累加计算批大小
        total_memory = 0
        batch_size = 0

        for size in sorted_sizes:
            total_memory += size + base_memory_per_item
            if total_memory > max_memory:
                break
            batch_size += 1

        return max(1, batch_size)

    @staticmethod
    def adaptive_batch_size(
        recent_times: List[float],
        recent_sizes: List[int],
        target_time: float = 0.05,
    ) -> int:
        """
        自适应调整批大小

        Args:
            recent_times: 最近的批处理时间
            recent_sizes: 最近的批大小
            target_time: 目标处理时间

        Returns:
            推荐的批大小
        """
        if not recent_times:
            return 8  # 默认值

        # 计算平均处理时间
        avg_time = np.mean(recent_times)

        # 计算平均批大小
        avg_size = np.mean(recent_sizes)

        # 调整批大小
        if avg_time > target_time * 1.2:
            # 处理太慢，减少批大小
            new_size = int(avg_size * 0.8)
        elif avg_time < target_time * 0.8:
            # 处理很快，增加批大小
            new_size = int(avg_size * 1.2)
        else:
            # 合适，保持不变
            new_size = int(avg_size)

        # 限制范围
        new_size = max(1, min(new_size, 64))

        return new_size
