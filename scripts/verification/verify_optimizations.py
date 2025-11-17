#!/usr/bin/env python3
"""
优化功能验证脚本

用于验证已实现的优化功能是否正常工作
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

import cv2
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.core.frame_metadata import FrameMetadata, FrameSource
from src.services.detection_service import initialize_detection_services, optimized_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_optimization_status() -> Dict[str, Any]:
    """检查优化功能状态"""
    logger.info("=== 检查优化功能状态 ===")
    
    status = {
        "frame_metadata_available": False,
        "state_management_enabled": False,
        "async_detection_enabled": False,
        "cache_enabled": False,
        "roi_optimization_enabled": False,
    }
    
    # 检查FrameMetadata是否可用
    try:
        from src.core.frame_metadata import FrameMetadata
        status["frame_metadata_available"] = True
        logger.info("✅ FrameMetadata 可用")
    except ImportError as e:
        logger.error(f"❌ FrameMetadata 不可用: {e}")
    
    # 检查检测管道
    if optimized_pipeline is None:
        logger.error("❌ 检测管道未初始化")
        return status
    
    # 检查状态管理
    if hasattr(optimized_pipeline, "enable_state_management"):
        status["state_management_enabled"] = optimized_pipeline.enable_state_management
        if status["state_management_enabled"]:
            logger.info("✅ 状态管理已启用")
            if hasattr(optimized_pipeline, "state_manager") and optimized_pipeline.state_manager:
                stats = optimized_pipeline.state_manager.get_stats()
                logger.info(f"   状态管理统计: {stats}")
        else:
            logger.warning("⚠️  状态管理未启用")
    
    # 检查异步检测
    if hasattr(optimized_pipeline, "enable_async"):
        status["async_detection_enabled"] = optimized_pipeline.enable_async
        if status["async_detection_enabled"]:
            logger.info("✅ 异步检测已启用")
        else:
            logger.info("ℹ️  异步检测未启用（默认禁用）")
    
    # 检查缓存
    if hasattr(optimized_pipeline, "enable_cache"):
        status["cache_enabled"] = optimized_pipeline.enable_cache
        if status["cache_enabled"]:
            logger.info("✅ 缓存已启用")
            if hasattr(optimized_pipeline, "frame_cache") and optimized_pipeline.frame_cache:
                stats = optimized_pipeline.frame_cache.get_stats()
                logger.info(f"   缓存统计: {stats}")
        else:
            logger.warning("⚠️  缓存未启用")
    
    # 检查ROI优化（通过检查方法是否存在）
    if hasattr(optimized_pipeline, "_detect_hairnet_for_persons"):
        status["roi_optimization_enabled"] = True
        logger.info("✅ ROI优化已启用")
    else:
        logger.warning("⚠️  ROI优化未启用")
    
    return status


def test_detection_performance(image_path: str, iterations: int = 5) -> Dict[str, Any]:
    """测试检测性能"""
    logger.info(f"=== 测试检测性能: {image_path} ===")
    
    if optimized_pipeline is None:
        logger.error("❌ 检测管道未初始化")
        return {}
    
    # 加载测试图像
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"❌ 无法加载图像: {image_path}")
        return {}
    
    logger.info(f"图像尺寸: {image.shape}")
    
    # 预热
    logger.info("预热检测管道...")
    for _ in range(2):
        optimized_pipeline.detect_comprehensive(image, camera_id="test")
    
    # 性能测试
    logger.info(f"执行 {iterations} 次检测...")
    times = []
    for i in range(iterations):
        start_time = time.time()
        result = optimized_pipeline.detect_comprehensive(image, camera_id="test")
        elapsed = time.time() - start_time
        times.append(elapsed)
        logger.info(f"  第 {i+1} 次: {elapsed:.3f}s, 检测到 {len(result.person_detections)} 个人")
    
    # 统计
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    performance = {
        "iterations": iterations,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "times": times,
    }
    
    logger.info(f"平均检测时间: {avg_time:.3f}s")
    logger.info(f"最短检测时间: {min_time:.3f}s")
    logger.info(f"最长检测时间: {max_time:.3f}s")
    
    return performance


def test_roi_optimization(image_path: str) -> Dict[str, Any]:
    """测试ROI优化"""
    logger.info(f"=== 测试ROI优化: {image_path} ===")
    
    if optimized_pipeline is None:
        logger.error("❌ 检测管道未初始化")
        return {}
    
    # 加载测试图像
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"❌ 无法加载图像: {image_path}")
        return {}
    
    # 检测人体
    person_detections = optimized_pipeline._detect_persons(image)
    logger.info(f"检测到 {len(person_detections)} 个人")
    
    if len(person_detections) == 0:
        logger.warning("⚠️  未检测到人体，无法测试ROI优化")
        return {}
    
    # 测试ROI检测
    logger.info("测试发网ROI检测...")
    start_time = time.time()
    hairnet_results = optimized_pipeline._detect_hairnet_for_persons(image, person_detections)
    roi_time = time.time() - start_time
    logger.info(f"ROI检测时间: {roi_time:.3f}s")
    logger.info(f"发网检测结果: {len(hairnet_results)} 个")
    
    # 测试姿态ROI检测
    logger.info("测试姿态ROI检测...")
    start_time = time.time()
    pose_results = optimized_pipeline._detect_pose_for_persons(image, person_detections)
    pose_roi_time = time.time() - start_time
    logger.info(f"姿态ROI检测时间: {pose_roi_time:.3f}s")
    logger.info(f"姿态检测结果: {len(pose_results)} 个")
    
    roi_stats = {
        "person_count": len(person_detections),
        "hairnet_roi_time": roi_time,
        "pose_roi_time": pose_roi_time,
        "hairnet_results_count": len(hairnet_results),
        "pose_results_count": len(pose_results),
    }
    
    return roi_stats


def test_cache_performance(image_path: str, iterations: int = 10) -> Dict[str, Any]:
    """测试缓存性能"""
    logger.info(f"=== 测试缓存性能: {image_path} ===")
    
    if optimized_pipeline is None:
        logger.error("❌ 检测管道未初始化")
        return {}
    
    if not optimized_pipeline.enable_cache:
        logger.warning("⚠️  缓存未启用")
        return {}
    
    # 加载测试图像
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"❌ 无法加载图像: {image_path}")
        return {}
    
    # 清空缓存
    if optimized_pipeline.frame_cache:
        optimized_pipeline.frame_cache.clear()
    
    # 第一次检测（缓存未命中）
    logger.info("第一次检测（缓存未命中）...")
    start_time = time.time()
    result1 = optimized_pipeline.detect_comprehensive(image, camera_id="test")
    first_time = time.time() - start_time
    logger.info(f"第一次检测时间: {first_time:.3f}s")
    
    # 后续检测（缓存命中）
    logger.info(f"执行 {iterations} 次检测（缓存命中）...")
    cache_times = []
    for i in range(iterations):
        start_time = time.time()
        result2 = optimized_pipeline.detect_comprehensive(image, camera_id="test")
        elapsed = time.time() - start_time
        cache_times.append(elapsed)
        logger.info(f"  第 {i+1} 次: {elapsed:.3f}s")
    
    # 统计
    avg_cache_time = sum(cache_times) / len(cache_times)
    speedup = first_time / avg_cache_time if avg_cache_time > 0 else 0
    
    # 获取缓存统计
    cache_stats = optimized_pipeline.frame_cache.get_stats() if optimized_pipeline.frame_cache else {}
    pipeline_stats = optimized_pipeline.stats
    
    cache_performance = {
        "first_detection_time": first_time,
        "avg_cache_time": avg_cache_time,
        "speedup": speedup,
        "cache_stats": cache_stats,
        "pipeline_stats": pipeline_stats,
    }
    
    logger.info(f"第一次检测时间: {first_time:.3f}s")
    logger.info(f"平均缓存时间: {avg_cache_time:.3f}s")
    logger.info(f"加速比: {speedup:.2f}x")
    logger.info(f"缓存命中率: {pipeline_stats.get('cache_hits', 0) / (pipeline_stats.get('cache_hits', 0) + pipeline_stats.get('cache_misses', 1)) * 100:.2f}%")
    
    return cache_performance


def generate_report(status: Dict[str, Any], performance: Dict[str, Any], 
                   roi_stats: Dict[str, Any], cache_performance: Dict[str, Any]) -> str:
    """生成验证报告"""
    report = []
    report.append("=" * 60)
    report.append("优化功能验证报告")
    report.append("=" * 60)
    report.append("")
    
    # 状态检查
    report.append("## 优化功能状态")
    report.append("")
    report.append(f"- FrameMetadata可用: {'✅' if status.get('frame_metadata_available') else '❌'}")
    report.append(f"- 状态管理启用: {'✅' if status.get('state_management_enabled') else '❌'}")
    report.append(f"- 异步检测启用: {'✅' if status.get('async_detection_enabled') else 'ℹ️  (默认禁用)'}")
    report.append(f"- 缓存启用: {'✅' if status.get('cache_enabled') else '❌'}")
    report.append(f"- ROI优化启用: {'✅' if status.get('roi_optimization_enabled') else '❌'}")
    report.append("")
    
    # 性能测试
    if performance:
        report.append("## 检测性能")
        report.append("")
        report.append(f"- 平均检测时间: {performance.get('avg_time', 0):.3f}s")
        report.append(f"- 最短检测时间: {performance.get('min_time', 0):.3f}s")
        report.append(f"- 最长检测时间: {performance.get('max_time', 0):.3f}s")
        report.append("")
    
    # ROI优化
    if roi_stats:
        report.append("## ROI优化")
        report.append("")
        report.append(f"- 检测到人数: {roi_stats.get('person_count', 0)}")
        report.append(f"- 发网ROI检测时间: {roi_stats.get('hairnet_roi_time', 0):.3f}s")
        report.append(f"- 姿态ROI检测时间: {roi_stats.get('pose_roi_time', 0):.3f}s")
        report.append("")
    
    # 缓存性能
    if cache_performance:
        report.append("## 缓存性能")
        report.append("")
        report.append(f"- 第一次检测时间: {cache_performance.get('first_detection_time', 0):.3f}s")
        report.append(f"- 平均缓存时间: {cache_performance.get('avg_cache_time', 0):.3f}s")
        report.append(f"- 加速比: {cache_performance.get('speedup', 0):.2f}x")
        report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="优化功能验证脚本")
    parser.add_argument("--image", type=str, help="测试图像路径")
    parser.add_argument("--iterations", type=int, default=5, help="性能测试迭代次数")
    parser.add_argument("--output", type=str, help="报告输出文件路径")
    
    args = parser.parse_args()
    
    # 初始化检测服务
    logger.info("初始化检测服务...")
    try:
        initialize_detection_services()
        logger.info("✅ 检测服务初始化成功")
    except Exception as e:
        logger.error(f"❌ 检测服务初始化失败: {e}")
        return 1
    
    # 检查优化功能状态
    status = check_optimization_status()
    
    # 性能测试
    performance = {}
    roi_stats = {}
    cache_performance = {}
    
    if args.image:
        image_path = args.image
        if not Path(image_path).exists():
            logger.error(f"❌ 图像文件不存在: {image_path}")
            return 1
        
        # 测试检测性能
        performance = test_detection_performance(image_path, args.iterations)
        
        # 测试ROI优化
        roi_stats = test_roi_optimization(image_path)
        
        # 测试缓存性能
        cache_performance = test_cache_performance(image_path, args.iterations)
    else:
        logger.warning("⚠️  未提供测试图像，跳过性能测试")
    
    # 生成报告
    report = generate_report(status, performance, roi_stats, cache_performance)
    
    # 输出报告
    print("\n" + report + "\n")
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"报告已保存到: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

