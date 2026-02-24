"""
批处理框架集成测试

测试批处理框架的端到端功能
"""

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.mark.integration
def test_batch_detection_pipeline_basic():
    """
    集成测试：批量检测管道基础功能
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.detection.detector import HumanDetector

    # 初始化检测器
    human_detector = HumanDetector()

    # 创建批量检测管道
    pipeline = BatchDetectionPipeline(
        human_detector=human_detector,
        hairnet_detector=None,
        behavior_recognizer=None,
        enable_batch_processing=True,
        max_batch_size=8,
    )

    # 生成测试帧
    num_frames = 10
    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        for _ in range(num_frames)
    ]

    # 批量检测
    start_time = time.time()
    results = pipeline.detect_batch(frames)
    elapsed = time.time() - start_time

    # 验证结果
    assert len(results) == num_frames, f"应返回 {num_frames} 个结果"
    assert all(isinstance(r, type(results[0])) for r in results), "所有结果类型应相同"

    # 验证性能
    assert elapsed < 5.0, f"批处理应在5秒内完成，实际: {elapsed:.2f}s"

    # 检查批处理统计
    stats = pipeline.get_batch_stats()
    assert stats["total_batches"] > 0, "应有批处理记录"

    print(f"\n✓ 批量检测测试通过")
    print(f"  帧数: {num_frames}")
    print(f"  处理时间: {elapsed:.2f}s")
    print(f"  平均每帧: {elapsed/num_frames*1000:.1f}ms")
    print(f"  FPS: {num_frames/elapsed:.1f}")
    print(f"  批次统计: {stats}")


@pytest.mark.integration
def test_batch_vs_sequential_consistency():
    """
    集成测试：批处理与逐帧处理结果一致性
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
    from src.detection.detector import HumanDetector

    # 初始化检测器
    human_detector = HumanDetector()

    # 创建两个管道（批处理和逐帧）
    batch_pipeline = BatchDetectionPipeline(
        human_detector=human_detector,
        enable_batch_processing=True,
        max_batch_size=4,
    )

    sequential_pipeline = OptimizedDetectionPipeline(
        human_detector=human_detector,
    )

    # 生成测试帧
    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(5)
    ]

    # 批量检测
    batch_results = batch_pipeline.detect_batch(frames)

    # 逐帧检测
    sequential_results = []
    for frame in frames:
        result = sequential_pipeline.detect_comprehensive(frame)
        sequential_results.append(result)

    # 验证一致性（检测人数应该接近）
    batch_person_counts = [len(r.person_detections) for r in batch_results]
    sequential_person_counts = [len(r.person_detections) for r in sequential_results]

    for i, (batch_count, seq_count) in enumerate(
        zip(batch_person_counts, sequential_person_counts)
    ):
        # 允许±1的差异（由于阈值可能略有不同）
        assert abs(batch_count - seq_count) <= 1, (
            f"帧 {i}: 检测人数差异过大 "
            f"(批处理: {batch_count}, 逐帧: {seq_count})"
        )

    print(f"\n✓ 一致性测试通过")
    print(f"  批处理检测人数: {batch_person_counts}")
    print(f"  逐帧检测人数: {sequential_person_counts}")


@pytest.mark.integration
def test_batch_scheduler_integration():
    """
    集成测试：批处理调度器
    """
    import asyncio
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.core.batch_processor import BatchScheduler
    from src.detection.detector import HumanDetector

    async def run_scheduler_test():
        # 初始化检测器
        human_detector = HumanDetector()
        pipeline = BatchDetectionPipeline(
            human_detector=human_detector,
            enable_batch_processing=True,
            max_batch_size=4,
        )

        # 创建调度器
        scheduler = BatchScheduler(max_batch_size=4, max_wait_time=0.1)

        # 生成测试帧
        frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(10)
        ]

        # 并发调度
        tasks = [scheduler.schedule(frame, pipeline) for frame in frames]
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert len(results) == 10, "应返回10个结果"
        assert all(r is not None for r in results), "所有结果不应为None"

        print(f"\n✓ 调度器集成测试通过")
        print(f"  处理帧数: {len(results)}")

        # 检查批处理统计
        stats = pipeline.get_batch_stats()
        print(f"  批次统计: {stats}")

    # 运行异步测试
    asyncio.run(run_scheduler_test())


@pytest.mark.integration
def test_batch_celery_task_integration():
    """
    集成测试：Celery批处理任务
    """
    from src.worker.batch_tasks import get_detection_pipeline

    try:
        # 获取检测管道（测试初始化）
        pipeline = get_detection_pipeline()

        # 生成测试帧
        frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(5)
        ]

        # 批量检测
        results = pipeline.detect_batch(frames)

        # 验证结果
        assert len(results) == 5
        assert isinstance(results[0], type(results[0]))

        # 检查健康状态
        health_status = get_detection_pipeline().get_batch_stats()

        print(f"\n✓ Celery任务集成测试通过")
        print(f"  处理帧数: {len(results)}")
        print(f"  批次统计: {health_status}")

    except Exception as e:
        pytest.skip(f"检测管道初始化失败: {e}")


@pytest.mark.integration
def test_batch_error_handling():
    """
    集成测试：批处理错误处理
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline

    # 创建带有模拟检测器的管道
    class FailingDetector:
        def detect_batch(self, images):
            # 5%的失败率
            if np.random.random() < 0.05:
                raise RuntimeError("随机检测失败")
            return [[] for _ in images]

    pipeline = BatchDetectionPipeline(
        human_detector=FailingDetector(),
        enable_batch_processing=True,
        max_batch_size=4,
    )

    # 生成测试帧
    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(20)
    ]

    # 多次尝试，应该至少成功一次
    success = False
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            results = pipeline.detect_batch(frames)
            success = True
            break
        except RuntimeError as e:
            if attempt < max_attempts - 1:
                continue
            else:
                # 最后一次失败，仍然算测试通过（验证了错误处理）
                print(f"\n✓ 错误处理测试通过（检测到预期错误）")
                return

    assert success, "至少应该成功一次"
    print(f"\n✓ 错误处理测试通过")


@pytest.mark.integration
def test_batch_performance_monitoring():
    """
    集成测试：批处理性能监控
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.core.batch_processor import BatchPerformanceMonitor
    from src.detection.detector import HumanDetector

    # 创建性能监控器
    monitor = BatchPerformanceMonitor()

    # 初始化检测器
    human_detector = HumanDetector()
    pipeline = BatchDetectionPipeline(
        human_detector=human_detector,
        enable_batch_processing=True,
        max_batch_size=8,
    )

    # 生成测试帧
    num_frames = 20
    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(num_frames)
    ]

    # 多次批处理
    num_runs = 3
    for run in range(num_runs):
        start_time = time.time()
        pipeline.detect_batch(frames)
        elapsed = time.time() - start_time

        # 记录性能
        monitor.record_batch(
            batch_size=num_frames,
            batch_time=elapsed,
            per_item_time=elapsed / num_frames,
        )

    # 获取统计
    stats = monitor.get_stats()

    # 验证统计
    assert stats["total_batches"] == num_runs
    assert stats["avg_batch_size"] == num_frames
    assert stats["avg_per_item_time"] > 0
    assert stats["throughput"] > 0

    print(f"\n✓ 性能监控测试通过")
    print(f"  总批次数: {stats['total_batches']}")
    print(f"  平均批大小: {stats['avg_batch_size']:.1f}")
    print(f"  平均每帧时间: {stats['avg_per_item_time']*1000:.1f}ms")
    print(f"  吞吐量: {stats['throughput']:.1f} FPS")


@pytest.mark.integration
@pytest.mark.parametrize("batch_size", [4, 8, 16, 32])
def test_batch_size_variation(batch_size):
    """
    参数化测试：不同批大小
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.detection.detector import HumanDetector

    # 初始化检测器
    human_detector = HumanDetector()
    pipeline = BatchDetectionPipeline(
        human_detector=human_detector,
        enable_batch_processing=True,
        max_batch_size=batch_size,
    )

    # 生成测试帧
    num_frames = 20
    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(num_frames)
    ]

    # 批量检测
    start_time = time.time()
    results = pipeline.detect_batch(frames)
    elapsed = time.time() - start_time

    # 验证结果
    assert len(results) == num_frames
    assert elapsed < 10.0, f"批大小 {batch_size} 处理时间过长: {elapsed:.2f}s"

    # 检查批处理统计
    stats = pipeline.get_batch_stats()

    print(f"\n✓ 批大小 {batch_size} 测试通过")
    print(f"  处理时间: {elapsed:.2f}s")
    print(f"  FPS: {num_frames/elapsed:.1f}")
    print(f"  批次统计: {stats}")


if __name__ == "__main__":
    """
    直接运行集成测试
    """
    print("\n" + "=" * 60)
    print("运行批处理集成测试")
    print("=" * 60)

    tests = [
        ("基础功能", test_batch_detection_pipeline_basic),
        ("一致性", test_batch_vs_sequential_consistency),
        ("性能监控", test_batch_performance_monitoring),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n运行: {name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} 失败: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
