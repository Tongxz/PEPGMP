#!/usr/bin/env python3
"""
GPU性能测试脚本
GPU Performance Test Script

快速测试GPU加速效果，对比优化前后的性能差异
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logger = logging.getLogger(__name__)


def create_test_frames(
    count: int = 50, size: Tuple[int, int] = (640, 480)
) -> List[np.ndarray]:
    """创建测试帧"""
    logger.info(f"创建 {count} 个测试帧 ({size[0]}x{size[1]})")

    frames = []
    for i in range(count):
        # 创建模拟的检测场景
        frame = np.random.randint(0, 256, (size[1], size[0], 3), dtype=np.uint8)

        # 添加一些模拟的人体区域
        cv2.rectangle(frame, (100, 100), (200, 300), (255, 255, 255), -1)  # 模拟人体
        cv2.rectangle(frame, (400, 150), (500, 350), (200, 200, 200), -1)  # 模拟人体

        frames.append(frame)

    return frames


def test_cpu_baseline(frames: List[np.ndarray]) -> Dict[str, float]:
    """测试CPU基线性能"""
    logger.info("🔄 测试CPU基线性能...")

    try:
        from core.optimized_detection_pipeline import OptimizedDetectionPipeline

        pipeline = OptimizedDetectionPipeline()

        start_time = time.time()
        results = []

        for i, frame in enumerate(frames):
            result = pipeline.detect_comprehensive(frame)
            results.append(result)

            if (i + 1) % 10 == 0:
                logger.info(f"  处理进度: {i + 1}/{len(frames)}")

        total_time = time.time() - start_time
        avg_time = total_time / len(frames)
        fps = len(frames) / total_time

        metrics = {
            "total_time": total_time,
            "avg_time_per_frame": avg_time,
            "fps": fps,
            "device": "cpu",
        }

        logger.info(f"✅ CPU基线测试完成: {fps:.1f} FPS")
        return metrics

    except Exception as e:
        logger.error(f"CPU基线测试失败: {e}")
        return {"error": str(e)}


def test_gpu_accelerated(frames: List[np.ndarray]) -> Dict[str, float]:
    """测试GPU加速性能"""
    logger.info("🚀 测试GPU加速性能...")

    try:
        from core.accelerated_detection_pipeline import AcceleratedDetectionPipeline
        from utils.gpu_acceleration import initialize_gpu_acceleration

        # 初始化GPU加速
        gpu_status = initialize_gpu_acceleration()
        logger.info(f"GPU状态: {gpu_status['device']}")

        # 创建加速流水线
        pipeline = AcceleratedDetectionPipeline(
            enable_batch_processing=True, enable_async_processing=True, max_batch_size=8
        )

        start_time = time.time()

        # 批量处理
        batch_size = 8
        results = []

        for i in range(0, len(frames), batch_size):
            batch = frames[i : i + batch_size]
            batch_results = pipeline.detect_batch(batch)
            results.extend(batch_results)

            logger.info(f"  批次进度: {i + len(batch)}/{len(frames)}")

        total_time = time.time() - start_time
        avg_time = total_time / len(frames)
        fps = len(frames) / total_time

        # 获取性能报告
        perf_report = pipeline.get_performance_report()

        metrics = {
            "total_time": total_time,
            "avg_time_per_frame": avg_time,
            "fps": fps,
            "device": gpu_status["device"],
            "gpu_utilization": perf_report.get("avg_gpu_utilization", 0),
            "memory_usage_gb": perf_report.get("avg_memory_usage_gb", 0),
            "batch_processing": True,
        }

        logger.info(f"✅ GPU加速测试完成: {fps:.1f} FPS")

        # 清理资源
        pipeline.cleanup()

        return metrics

    except Exception as e:
        logger.error(f"GPU加速测试失败: {e}")
        return {"error": str(e)}


def compare_performance(cpu_metrics: Dict, gpu_metrics: Dict) -> Dict[str, float]:
    """对比性能指标"""
    logger.info("📊 对比性能指标...")

    if "error" in cpu_metrics or "error" in gpu_metrics:
        logger.error("测试中有错误，无法对比")
        return {}

    comparison = {
        "cpu_fps": cpu_metrics["fps"],
        "gpu_fps": gpu_metrics["fps"],
        "speedup_ratio": gpu_metrics["fps"] / cpu_metrics["fps"],
        "cpu_time_per_frame_ms": cpu_metrics["avg_time_per_frame"] * 1000,
        "gpu_time_per_frame_ms": gpu_metrics["avg_time_per_frame"] * 1000,
        "time_reduction_ratio": cpu_metrics["avg_time_per_frame"]
        / gpu_metrics["avg_time_per_frame"],
        "gpu_device": gpu_metrics["device"],
    }

    if "gpu_utilization" in gpu_metrics:
        comparison["gpu_utilization"] = gpu_metrics["gpu_utilization"]

    if "memory_usage_gb" in gpu_metrics:
        comparison["gpu_memory_usage_gb"] = gpu_metrics["memory_usage_gb"]

    return comparison


def print_performance_report(comparison: Dict[str, float]):
    """打印性能报告"""
    print("\n" + "=" * 60)
    print("🏆 GPU性能测试报告")
    print("=" * 60)

    print(f"📊 基准性能对比:")
    print(f"  CPU FPS:           {comparison['cpu_fps']:.1f}")
    print(f"  GPU FPS:           {comparison['gpu_fps']:.1f}")
    print(f"  性能提升:           {comparison['speedup_ratio']:.2f}x")

    print(f"\n⏱️  处理时间对比:")
    print(f"  CPU 每帧时间:       {comparison['cpu_time_per_frame_ms']:.1f}ms")
    print(f"  GPU 每帧时间:       {comparison['gpu_time_per_frame_ms']:.1f}ms")
    print(f"  时间减少:           {comparison['time_reduction_ratio']:.2f}x")

    print(f"\n🔧 GPU信息:")
    print(f"  设备:              {comparison['gpu_device']}")

    if "gpu_utilization" in comparison:
        print(f"  GPU利用率:          {comparison['gpu_utilization']:.1f}%")

    if "gpu_memory_usage_gb" in comparison:
        print(f"  显存使用:           {comparison['gpu_memory_usage_gb']:.1f}GB")

    print(f"\n🎯 优化效果评估:")
    if comparison["speedup_ratio"] >= 3.0:
        print("  ✅ 优秀 - GPU加速效果显著")
    elif comparison["speedup_ratio"] >= 2.0:
        print("  ✅ 良好 - GPU加速效果明显")
    elif comparison["speedup_ratio"] >= 1.5:
        print("  ⚠️  一般 - GPU加速有提升空间")
    else:
        print("  ❌ 需要优化 - GPU加速效果不佳")

    print("\n💡 优化建议:")
    if comparison["speedup_ratio"] < 2.0:
        print("  - 检查GPU驱动和CUDA安装")
        print("  - 增加批处理大小")
        print("  - 启用混合精度推理")
        print("  - 考虑TensorRT优化")
    else:
        print("  - 当前优化效果良好")
        print("  - 可考虑进一步TensorRT优化")
        print("  - 监控生产环境性能")

    print("=" * 60)


def main():
    """主函数"""
    print("🚀 GPU性能测试启动")
    print("测试将对比CPU和GPU加速的性能差异")

    # 设置日志
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        # 1. 创建测试数据
        frames = create_test_frames(count=50, size=(640, 480))

        # 2. CPU基线测试
        cpu_metrics = test_cpu_baseline(frames)

        # 3. GPU加速测试
        gpu_metrics = test_gpu_accelerated(frames)

        # 4. 性能对比
        comparison = compare_performance(cpu_metrics, gpu_metrics)

        # 5. 输出报告
        if comparison:
            print_performance_report(comparison)

            # 保存结果
            result_file = Path("performance_test_results.json")
            import json

            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "cpu_metrics": cpu_metrics,
                        "gpu_metrics": gpu_metrics,
                        "comparison": comparison,
                        "timestamp": time.time(),
                    },
                    f,
                    indent=4,
                )

            print(f"📄 详细结果已保存到: {result_file}")
        else:
            print("❌ 测试失败，无法生成对比报告")

    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
