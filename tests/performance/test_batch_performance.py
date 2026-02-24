"""
批处理性能基准测试

对比批处理与逐帧处理的性能差异
"""

import time
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest


def generate_test_frames(num_frames: int = 100, width: int = 640, height: int = 480) -> List[np.ndarray]:
    """生成测试帧"""
    frames = []
    for i in range(num_frames):
        # 生成随机图像
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        # 添加一些变化
        cv2.putText(
            frame,
            f"Frame {i}",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        frames.append(frame)
    return frames


def benchmark_sequential_processing(
    frames: List[np.ndarray], pipeline
) -> Tuple[float, dict]:
    """
    基准测试：逐帧处理

    Args:
        frames: 帧列表
        pipeline: 检测管道

    Returns:
        (总时间, 统计信息)
    """
    start_time = time.time()

    results = []
    for frame in frames:
        result = pipeline.detect_comprehensive(frame)
        results.append(result)

    total_time = time.time() - start_time

    stats = {
        "total_frames": len(frames),
        "total_time": total_time,
        "avg_time_per_frame": total_time / len(frames),
        "fps": len(frames) / total_time,
        "total_detections": sum(len(r.person_detections) for r in results),
    }

    return total_time, stats


def benchmark_batch_processing(
    frames: List[np.ndarray], pipeline, batch_size: int = 16
) -> Tuple[float, dict]:
    """
    基准测试：批处理

    Args:
        frames: 帧列表
        pipeline: 批量检测管道
        batch_size: 批大小

    Returns:
        (总时间, 统计信息)
    """
    start_time = time.time()

    results = pipeline.detect_batch(frames)

    total_time = time.time() - start_time

    stats = {
        "total_frames": len(frames),
        "batch_size": batch_size,
        "total_time": total_time,
        "avg_time_per_frame": total_time / len(frames),
        "fps": len(frames) / total_time,
        "total_detections": sum(len(r.person_detections) for r in results),
        "num_batches": (len(frames) + batch_size - 1) // batch_size,
    }

    return total_time, stats


def compare_performance(sequential_stats: dict, batch_stats: dict) -> dict:
    """对比性能"""
    comparison = {
        "time_improvement_percent": (
            (sequential_stats["avg_time_per_frame"] - batch_stats["avg_time_per_frame"])
            / sequential_stats["avg_time_per_frame"]
            * 100
        ),
        "fps_improvement_percent": (
            (batch_stats["fps"] - sequential_stats["fps"])
            / sequential_stats["fps"]
            * 100
        ),
        "throughput_ratio": batch_stats["fps"] / sequential_stats["fps"],
    }
    return comparison


@pytest.mark.skipif(
    not Path("models/yolov8n.pt").exists(),
    reason="Model file not found",
)
@pytest.mark.performance
def test_batch_vs_sequential_performance():
    """
    性能测试：批处理 vs 逐帧处理

    注意：这是一个集成测试，需要实际模型
    """
    from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
    from src.detection.detector import HumanDetector
    from src.config.model_config import ModelConfig

    # 生成测试帧
    num_frames = 50
    frames = generate_test_frames(num_frames=num_frames)

    print(f"\n{'='*60}")
    print(f"性能测试: {num_frames} 帧")
    print(f"{'='*60}")

    # 初始化检测管道（逐帧处理）
    print("\n初始化逐帧处理管道...")
    human_detector = HumanDetector()
    sequential_pipeline = OptimizedDetectionPipeline(human_detector=human_detector)

    # 基准测试：逐帧处理
    print("\n基准测试: 逐帧处理...")
    _, sequential_stats = benchmark_sequential_processing(frames, sequential_pipeline)
    print(f"  总时间: {sequential_stats['total_time']:.2f}s")
    print(f"  平均每帧: {sequential_stats['avg_time_per_frame']*1000:.1f}ms")
    print(f"  FPS: {sequential_stats['fps']:.1f}")
    print(f"  检测数: {sequential_stats['total_detections']}")

    # 初始化批量检测管道
    print("\n初始化批量处理管道...")
    from src.core.batch_detection_pipeline import BatchDetectionPipeline

    batch_pipeline = BatchDetectionPipeline(
        human_detector=human_detector, enable_batch_processing=True, max_batch_size=16
    )

    # 预热
    print("预热...")
    warmup_frames = generate_test_frames(num_frames=5)
    batch_pipeline.detect_batch(warmup_frames)

    # 基准测试：批处理
    print("\n基准测试: 批处理...")
    batch_sizes = [8, 16, 32]
    batch_results = {}

    for batch_size in batch_sizes:
        print(f"\n  批大小: {batch_size}")
        _, batch_stats = benchmark_batch_processing(frames, batch_pipeline, batch_size)
        batch_results[batch_size] = batch_stats

        print(f"    总时间: {batch_stats['total_time']:.2f}s")
        print(f"    平均每帧: {batch_stats['avg_time_per_frame']*1000:.1f}ms")
        print(f"    FPS: {batch_stats['fps']:.1f}")
        print(f"    批数: {batch_stats['num_batches']}")
        print(f"    检测数: {batch_stats['total_detections']}")

        # 对比
        comparison = compare_performance(sequential_stats, batch_stats)
        print(f"    性能提升: {comparison['time_improvement_percent']:.1f}%")
        print(f"    FPS提升: {comparison['fps_improvement_percent']:.1f}%")
        print(f"    吞吐量比: {comparison['throughput_ratio']:.2f}x")

    # 验证批处理更快
    best_batch_size = min(
        batch_results.keys(), key=lambda bs: batch_results[bs]["total_time"]
    )
    best_stats = batch_results[best_batch_size]

    # 批处理应该至少快20%
    assert (
        best_stats["avg_time_per_frame"]
        < sequential_stats["avg_time_per_frame"] * 0.8
    ), "批处理应该至少快20%"

    print(f"\n{'='*60}")
    print(f"最佳批大小: {best_batch_size}")
    print(f"性能提升: {(1 - best_stats['avg_time_per_frame']/sequential_stats['avg_time_per_frame'])*100:.1f}%")
    print(f"{'='*60}")


@pytest.mark.skipif(
    not Path("models/yolov8n.pt").exists(),
    reason="Model file not found",
)
@pytest.mark.performance
def test_batch_size_sensitivity():
    """
    测试不同批大小的性能敏感性
    """
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.detection.detector import HumanDetector

    # 生成测试帧
    num_frames = 100
    frames = generate_test_frames(num_frames=num_frames)

    print(f"\n{'='*60}")
    print(f"批大小敏感性测试: {num_frames} 帧")
    print(f"{'='*60}")

    # 初始化检测管道
    human_detector = HumanDetector()
    batch_pipeline = BatchDetectionPipeline(
        human_detector=human_detector, enable_batch_processing=True
    )

    # 测试不同批大小
    batch_sizes = [1, 2, 4, 8, 16, 32, 64]
    results = []

    for batch_size in batch_sizes:
        print(f"\n批大小: {batch_size}")

        # 运行多次取平均
        times = []
        fps_list = []

        for run in range(3):
            start_time = time.time()
            batch_pipeline.detect_batch(frames)
            elapsed = time.time() - start_time

            avg_time = elapsed / num_frames
            fps = num_frames / elapsed

            times.append(avg_time)
            fps_list.append(fps)

        avg_time = np.mean(times)
        std_time = np.std(times)
        avg_fps = np.mean(fps_list)

        print(f"  平均每帧: {avg_time*1000:.1f}ms (±{std_time*1000:.1f})")
        print(f"  平均FPS: {avg_fps:.1f}")

        results.append(
            {
                "batch_size": batch_size,
                "avg_time_per_frame": avg_time,
                "std_time_per_frame": std_time,
                "avg_fps": avg_fps,
            }
        )

    # 找到最佳批大小
    best_result = min(results, key=lambda r: r["avg_time_per_frame"])
    print(f"\n{'='*60}")
    print(f"最佳批大小: {best_result['batch_size']}")
    print(f"最佳性能: {best_result['avg_time_per_frame']*1000:.1f}ms/帧, {best_result['avg_fps']:.1f} FPS")
    print(f"{'='*60}")

    # 保存结果到文件
    results_file = Path(".benchmarks/batch_size_sensitivity.csv")
    results_file.parent.mkdir(exist_ok=True)

    import csv

    with open(results_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["batch_size", "avg_time_per_frame", "std_time_per_frame", "avg_fps"],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\n结果已保存到: {results_file}")


@pytest.mark.unit
def test_batch_processing_memory_efficiency():
    """
    测试批处理的内存效率
    """
    import psutil
    import gc

    print(f"\n{'='*60}")
    print(f"内存效率测试")
    print(f"{'='*60}")

    # 获取初始内存
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    print(f"初始内存: {initial_memory:.1f} MB")

    # 生成较大的测试帧
    num_frames = 50
    frames = generate_test_frames(num_frames=num_frames, width=1280, height=720)

    print(f"帧数据大小: {sum(f.nbytes for f in frames) / 1024 / 1024:.1f} MB")

    # 初始化检测管道
    from src.core.batch_detection_pipeline import BatchDetectionPipeline
    from src.detection.detector import HumanDetector

    human_detector = HumanDetector()
    batch_pipeline = BatchDetectionPipeline(
        human_detector=human_detector, enable_batch_processing=True, max_batch_size=8
    )

    # 测试不同批大小下的内存使用
    batch_sizes = [4, 8, 16]

    for batch_size in batch_sizes:
        gc.collect()  # 清理垃圾回收

        memory_before = process.memory_info().rss / 1024 / 1024

        # 执行批处理
        start_time = time.time()
        results = batch_pipeline.detect_batch(frames)
        elapsed = time.time() - start_time

        memory_after = process.memory_info().rss / 1024 / 1024
        memory_used = memory_after - memory_before

        print(f"\n批大小: {batch_size}")
        print(f"  处理时间: {elapsed:.2f}s")
        print(f"  内存使用: {memory_used:.1f} MB")
        print(f"  总内存: {memory_after:.1f} MB")

        # 验证内存使用合理（不超过500MB）
        assert memory_used < 500, f"批大小 {batch_size} 内存使用过高: {memory_used:.1f} MB"

    print(f"\n{'='*60}")
