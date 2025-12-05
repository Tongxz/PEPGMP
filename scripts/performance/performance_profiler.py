#!/usr/bin/env python
"""
性能分析工具

用于分析检测管道的性能瓶颈
"""

import cProfile
import logging
import pstats

# 添加项目根目录到Python路径
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.core.behavior import BehaviorRecognizer
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.detector import HumanDetector

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def profile_detection_pipeline(
    image: np.ndarray,
    pipeline: OptimizedDetectionPipeline,
    num_iterations: int = 10,
    output_file: str = "performance_profile.prof",
) -> Dict[str, any]:
    """
    分析检测管道的性能

    Args:
        image: 测试图像
        pipeline: 检测管道
        num_iterations: 迭代次数
        output_file: 输出文件路径

    Returns:
        性能统计信息
    """
    profiler = cProfile.Profile()

    # 开始性能分析
    profiler.enable()

    times = []
    for i in range(num_iterations):
        start = time.time()
        result = pipeline.detect_comprehensive(
            image,
            enable_hairnet=True,
            enable_handwash=True,
            enable_sanitize=True,
        )
        elapsed = time.time() - start
        times.append(elapsed)

    profiler.disable()

    # 保存性能数据
    profiler.dump_stats(output_file)

    # 分析统计信息
    stats = pstats.Stats(profiler)

    # 获取最耗时的函数
    stats.sort_stats("cumulative")

    # 打印统计信息
    logger.info("=" * 80)
    logger.info("性能分析结果（Top 20 最耗时函数）")
    logger.info("=" * 80)
    stats.print_stats(20)

    # 计算平均时间
    avg_time = np.mean(times)
    std_time = np.std(times)
    min_time = np.min(times)
    max_time = np.max(times)

    logger.info("=" * 80)
    logger.info("时间统计")
    logger.info("=" * 80)
    logger.info(f"平均耗时: {avg_time:.3f}s")
    logger.info(f"标准差: {std_time:.3f}s")
    logger.info(f"最小耗时: {min_time:.3f}s")
    logger.info(f"最大耗时: {max_time:.3f}s")
    logger.info(f"FPS: {1.0/avg_time:.2f}")

    return {
        "avg_time": avg_time,
        "std_time": std_time,
        "min_time": min_time,
        "max_time": max_time,
        "fps": 1.0 / avg_time if avg_time > 0 else 0,
        "profile_file": output_file,
    }


def analyze_processing_times(
    pipeline: OptimizedDetectionPipeline,
    image: np.ndarray,
    num_iterations: int = 10,
) -> Dict[str, List[float]]:
    """
    分析各个处理阶段的耗时

    Args:
        pipeline: 检测管道
        image: 测试图像
        num_iterations: 迭代次数

    Returns:
        各阶段耗时统计
    """
    stage_times: Dict[str, List[float]] = {}

    for i in range(num_iterations):
        result = pipeline.detect_comprehensive(
            image,
            enable_hairnet=True,
            enable_handwash=True,
            enable_sanitize=True,
        )

        # 收集各阶段耗时
        for stage, time_val in result.processing_times.items():
            if stage not in stage_times:
                stage_times[stage] = []
            stage_times[stage].append(time_val)

    # 计算统计信息
    stats = {}
    for stage, times in stage_times.items():
        stats[stage] = {
            "avg": np.mean(times),
            "std": np.std(times),
            "min": np.min(times),
            "max": np.max(times),
            "total": np.sum(times),
        }

    # 打印统计信息
    logger.info("=" * 80)
    logger.info("各处理阶段耗时统计")
    logger.info("=" * 80)
    for stage, stat in sorted(stats.items(), key=lambda x: x[1]["avg"], reverse=True):
        logger.info(
            f"{stage:30s}: "
            f"平均={stat['avg']:.3f}s, "
            f"最小={stat['min']:.3f}s, "
            f"最大={stat['max']:.3f}s, "
            f"总计={stat['total']:.3f}s"
        )

    return stats


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("性能分析工具")
    logger.info("=" * 80)

    # 创建测试图像
    test_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    logger.info(f"测试图像尺寸: {test_image.shape}")

    # 创建检测管道
    human_detector = HumanDetector()
    behavior_recognizer = BehaviorRecognizer()

    pipeline = OptimizedDetectionPipeline(
        human_detector=human_detector,
        behavior_recognizer=behavior_recognizer,
        enable_cache=True,
        enable_state_management=True,
        enable_async=False,
    )

    logger.info("检测管道初始化完成")

    # 分析各阶段耗时
    logger.info("\n1. 分析各处理阶段耗时...")
    stage_stats = analyze_processing_times(pipeline, test_image, num_iterations=5)

    # 性能分析
    logger.info("\n2. 进行性能分析...")
    perf_stats = profile_detection_pipeline(
        test_image, pipeline, num_iterations=5, output_file="performance_profile.prof"
    )

    logger.info("\n性能分析完成！")
    logger.info(f"性能数据已保存到: performance_profile.prof")
    logger.info("可以使用以下命令查看详细报告:")
    logger.info("  python -m pstats performance_profile.prof")


if __name__ == "__main__":
    main()
