"""
批处理框架单元测试

测试内容：
1. BatchableDetector接口
2. BatchScheduler调度器
3. BatchPerformanceMonitor性能监控
4. BatchUtils工具函数
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.core.batch_processor import (
    BatchPerformanceMonitor,
    BatchScheduler,
    BatchUtils,
    BatchableDetector,
)


# ============ 测试用检测器 ============


class MockBatchableDetector(BatchableDetector):
    """模拟批处理检测器"""

    def __init__(self, delay: float = 0.01):
        self.delay = delay
        self.call_count = 0
        self.batch_count = 0

    def detect(self, data, **kwargs):
        """模拟单个检测"""
        time.sleep(self.delay)
        self.call_count += 1
        return [{"detection": f"result_{self.call_count}"}]

    def detect_batch(self, data_list, batch_size=None, **kwargs):
        """模拟批量检测"""
        time.sleep(self.delay * len(data_list) * 0.7)  # 批处理更快
        self.batch_count += 1
        return [[{"detection": f"batch_result_{i}"}] for i in range(len(data_list))]


class FailingDetector(BatchableDetector):
    """总是失败的检测器"""

    def detect(self, data, **kwargs):
        raise RuntimeError("检测失败")

    def detect_batch(self, data_list, batch_size=None, **kwargs):
        raise RuntimeError("批量检测失败")


# ============ BatchPerformanceMonitor 测试 ============


class TestBatchPerformanceMonitor:
    """批处理性能监控测试"""

    def test_init(self):
        """测试初始化"""
        monitor = BatchPerformanceMonitor()
        assert monitor.history_size == 1000
        assert monitor.cache_hits == 0
        assert monitor.cache_misses == 0

    def test_init_custom_history_size(self):
        """测试自定义历史大小"""
        monitor = BatchPerformanceMonitor(history_size=100)
        assert monitor.history_size == 100

    def test_record_batch(self):
        """测试记录批处理"""
        monitor = BatchPerformanceMonitor()
        monitor.record_batch(batch_size=10, batch_time=1.0)

        assert len(monitor.batch_sizes) == 1
        assert monitor.batch_sizes[0] == 10
        assert monitor.batch_times[0] == 1.0
        assert len(monitor.per_item_times) == 1
        assert monitor.per_item_times[0] == 0.1  # 1.0 / 10

    def test_record_batch_custom_per_item_time(self):
        """测试自定义每项时间"""
        monitor = BatchPerformanceMonitor()
        monitor.record_batch(batch_size=10, batch_time=1.0, per_item_time=0.15)

        assert monitor.per_item_times[0] == 0.15

    def test_record_cache(self):
        """测试记录缓存"""
        monitor = BatchPerformanceMonitor()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()

        assert monitor.cache_hits == 2
        assert monitor.cache_misses == 1

    def test_get_stats_empty(self):
        """测试空统计"""
        monitor = BatchPerformanceMonitor()
        stats = monitor.get_stats()

        assert stats["total_batches"] == 0
        assert stats["avg_batch_size"] == 0
        assert stats["avg_batch_time"] == 0
        assert stats["throughput"] == 0

    def test_get_stats_with_data(self):
        """测试有数据的统计"""
        monitor = BatchPerformanceMonitor()
        monitor.record_batch(batch_size=10, batch_time=1.0)
        monitor.record_batch(batch_size=20, batch_time=1.5)
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()

        stats = monitor.get_stats()

        assert stats["total_batches"] == 2
        assert stats["avg_batch_size"] == 15.0  # (10 + 20) / 2
        assert stats["avg_batch_time"] == 1.25  # (1.0 + 1.5) / 2
        assert stats["cache_hit_rate"] == 0.6666666666666666  # 2 / 3

    def test_reset(self):
        """测试重置"""
        monitor = BatchPerformanceMonitor()
        monitor.record_batch(batch_size=10, batch_time=1.0)
        monitor.record_cache_hit()

        monitor.reset()

        assert len(monitor.batch_sizes) == 0
        assert monitor.cache_hits == 0
        assert monitor.cache_misses == 0

    def test_history_size_limit(self):
        """测试历史大小限制"""
        monitor = BatchPerformanceMonitor(history_size=5)

        # 添加10个批次
        for i in range(10):
            monitor.record_batch(batch_size=i + 1, batch_time=0.1 * (i + 1))

        # 应该只保留最后5个
        assert len(monitor.batch_sizes) == 5
        assert monitor.batch_sizes == [6, 7, 8, 9, 10]


# ============ BatchScheduler 测试 ============


class TestBatchScheduler:
    """批处理调度器测试"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        scheduler = BatchScheduler(max_batch_size=16, max_wait_time=0.05)
        assert scheduler.max_batch_size == 16
        assert scheduler.max_wait_time == 0.05
        assert len(scheduler.pending_items) == 0

    @pytest.mark.asyncio
    async def test_schedule_single_item(self):
        """测试调度单个项目"""
        scheduler = BatchScheduler(max_batch_size=4, max_wait_time=0.1)
        detector = MockBatchableDetector(delay=0.01)

        # 调度单个项目
        result = await scheduler.schedule("item1", detector)

        # 等待超时处理
        await asyncio.sleep(0.15)

        assert result == [{"detection": "result_1"}]
        assert detector.call_count == 1

    @pytest.mark.asyncio
    async def test_schedule_multiple_items(self):
        """测试调度多个项目"""
        scheduler = BatchScheduler(max_batch_size=3, max_wait_time=0.05)
        detector = MockBatchableDetector(delay=0.01)

        # 并发调度多个项目
        tasks = [scheduler.schedule(f"item{i}", detector) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert len(results) == 5
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_schedule_reaches_max_batch_size(self):
        """测试达到最大批大小立即处理"""
        scheduler = BatchScheduler(max_batch_size=3, max_wait_time=1.0)
        detector = MockBatchableDetector(delay=0.01)

        # 调度3个项目（达到批大小）
        tasks = [
            scheduler.schedule("item1", detector),
            scheduler.schedule("item2", detector),
            scheduler.schedule("item3", detector),
        ]

        results = await asyncio.gather(*tasks)

        # 应该使用批处理
        assert detector.batch_count == 1
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_schedule_timeout(self):
        """测试超时触发批处理"""
        scheduler = BatchScheduler(max_batch_size=10, max_wait_time=0.05)
        detector = MockBatchableDetector(delay=0.001)

        # 调度2个项目（小于批大小）
        tasks = [
            scheduler.schedule("item1", detector),
            scheduler.schedule("item2", detector),
        ]

        # 等待超时
        await asyncio.sleep(0.1)

        results = await asyncio.gather(*tasks)

        # 应该使用批处理
        assert detector.batch_count == 1
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_flush(self):
        """测试立即刷新"""
        scheduler = BatchScheduler(max_batch_size=10, max_wait_time=1.0)
        detector = MockBatchableDetector(delay=0.01)

        # 调度2个项目
        task1 = scheduler.schedule("item1", detector)
        task2 = scheduler.schedule("item2", detector)

        # 立即刷新
        await scheduler.flush(detector)

        results = await asyncio.gather(task1, task2)

        # 应该使用批处理
        assert detector.batch_count == 1
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_failing_detector(self):
        """测试失败的检测器"""
        scheduler = BatchScheduler(max_batch_size=2, max_wait_time=0.05)
        detector = FailingDetector()

        # 调度应该抛出异常
        with pytest.raises(RuntimeError, match="检测失败"):
            await scheduler.schedule("item1", detector)


# ============ BatchUtils 测试 ============


class TestBatchUtils:
    """批处理工具函数测试"""

    def test_group_rois_by_size_empty(self):
        """测试空ROI列表"""
        rois = []
        groups = BatchUtils.group_rois_by_size(rois)
        assert groups == []

    def test_group_rois_by_size_single(self):
        """测试单个ROI"""
        rois = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)]
        groups = BatchUtils.group_rois_by_size(rois)
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_group_rois_by_size_similar(self):
        """测试相似尺寸ROI"""
        rois = [
            np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
            np.random.randint(0, 255, (110, 110, 3), dtype=np.uint8),
            np.random.randint(0, 255, (90, 90, 3), dtype=np.uint8),
        ]
        groups = BatchUtils.group_rois_by_size(rois, max_size_diff=0.3)
        # 所有ROI应该在同一组
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_group_rois_by_size_different(self):
        """测试不同尺寸ROI"""
        rois = [
            np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8),
            np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8),
        ]
        groups = BatchUtils.group_rois_by_size(rois, max_size_diff=0.3)
        # ROI应该在不同组
        assert len(groups) == 2

    def test_pad_roi_to_size_same(self):
        """测试填充相同尺寸ROI"""
        roi = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        padded = BatchUtils.pad_roi_to_size(roi, (100, 100))
        assert np.array_equal(padded, roi)

    def test_pad_roi_to_size_smaller(self):
        """测试填充较小ROI"""
        roi = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        padded = BatchUtils.pad_roi_to_size(roi, (100, 100))
        assert padded.shape == (100, 100, 3)
        # 中间应该是原始ROI
        assert np.array_equal(padded[25:75, 25:75], roi)

    def test_pad_roi_to_size_larger(self):
        """测试裁剪较大ROI"""
        roi = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        cropped = BatchUtils.pad_roi_to_size(roi, (100, 100))
        assert cropped.shape == (100, 100, 3)
        # 应该是中心裁剪
        assert np.array_equal(cropped, roi[50:150, 50:150])

    def test_map_results_to_original(self):
        """测试映射结果到原始顺序"""
        batch_results = [
            [{"detection": "result_0"}],
            [{"detection": "result_1"}],
            [{"detection": "result_2"}],
        ]
        mappings = [(0,), (1,), (2,)]

        mapped = BatchUtils.map_results_to_original(batch_results, mappings)

        assert len(mapped) == 3
        assert mapped[0] == batch_results[0]
        assert mapped[1] == batch_results[1]
        assert mapped[2] == batch_results[2]

    def test_map_results_to_original_shuffle(self):
        """测试打乱顺序的映射"""
        batch_results = [
            [{"detection": "result_0"}],
            [{"detection": "result_1"}],
            [{"detection": "result_2"}],
        ]
        # 打乱顺序
        mappings = [(2,), (0,), (1,)]

        mapped = BatchUtils.map_results_to_original(batch_results, mappings)

        assert len(mapped) == 3
        assert mapped[0] == batch_results[1]  # 原始索引0 -> 批结果1
        assert mapped[1] == batch_results[2]  # 原始索引1 -> 批结果2
        assert mapped[2] == batch_results[0]  # 原始索引2 -> 批结果0

    def test_calculate_optimal_batch_size_empty(self):
        """测试空列表计算批大小"""
        item_sizes = []
        batch_size = BatchUtils.calculate_optimal_batch_size(
            item_sizes, max_memory=100 * 1024 * 1024
        )
        assert batch_size == 1

    def test_calculate_optimal_batch_size(self):
        """测试计算最优批大小"""
        item_sizes = [10 * 1024 * 1024, 10 * 1024 * 1024, 10 * 1024 * 1024]  # 10MB each
        batch_size = BatchUtils.calculate_optimal_batch_size(
            item_sizes, max_memory=100 * 1024 * 1024, base_memory_per_item=10 * 1024 * 1024
        )
        # 应该可以处理所有3个
        assert batch_size == 3

    def test_calculate_optimal_batch_size_limited(self):
        """测试内存限制"""
        item_sizes = [50 * 1024 * 1024] * 10  # 50MB each
        batch_size = BatchUtils.calculate_optimal_batch_size(
            item_sizes, max_memory=200 * 1024 * 1024, base_memory_per_item=10 * 1024 * 1024
        )
        # 只能处理3个 (50+10)*3 = 180MB < 200MB
        assert batch_size == 3

    def test_adaptive_batch_size_empty(self):
        """测试空历史"""
        recent_times = []
        recent_sizes = []
        new_size = BatchUtils.adaptive_batch_size(
            recent_times, recent_sizes, target_time=0.05
        )
        assert new_size == 8  # 默认值

    def test_adaptive_batch_size_decrease(self):
        """测试减少批大小"""
        recent_times = [0.1, 0.12, 0.11]  # 比目标慢
        recent_sizes = [10, 10, 10]
        new_size = BatchUtils.adaptive_batch_size(
            recent_times, recent_sizes, target_time=0.05
        )
        assert new_size < 10  # 应该减少

    def test_adaptive_batch_size_increase(self):
        """测试增加批大小"""
        recent_times = [0.02, 0.03, 0.025]  # 比目标快
        recent_sizes = [10, 10, 10]
        new_size = BatchUtils.adaptive_batch_size(
            recent_times, recent_sizes, target_time=0.05
        )
        assert new_size > 10  # 应该增加

    def test_adaptive_batch_size_stable(self):
        """测试稳定批大小"""
        recent_times = [0.048, 0.052, 0.05]  # 接近目标
        recent_sizes = [10, 10, 10]
        new_size = BatchUtils.adaptive_batch_size(
            recent_times, recent_sizes, target_time=0.05
        )
        assert new_size == 10  # 应该保持


# ============ BatchableDetector 测试 ============


class TestBatchableDetector:
    """批处理检测器接口测试"""

    def test_detect_batch_default_implementation(self):
        """测试默认批处理实现"""
        detector = MockBatchableDetector()
        data_list = ["item1", "item2", "item3"]

        results = detector.detect_batch(data_list)

        assert len(results) == 3
        assert all(isinstance(r, list) for r in results)

    def test_detect_batch_empty_list(self):
        """测试空列表"""
        detector = MockBatchableDetector()
        results = detector.detect_batch([])
        assert results == []

    def test_detect_batch_with_batch_size(self):
        """测试指定批大小"""
        detector = MockBatchableDetector()
        data_list = ["item1", "item2", "item3", "item4", "item5"]

        # 注意：默认实现不使用batch_size参数
        results = detector.detect_batch(data_list, batch_size=2)

        # 默认实现会处理所有项目
        assert len(results) == 5
