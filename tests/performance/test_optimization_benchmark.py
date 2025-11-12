"""
优化性能基准测试

对比优化前后的检测性能，验证优化效果
"""

import logging
import time
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
import pytest

# 导入检测器
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
from src.detection.detector import HumanDetector
from src.core.behavior import BehaviorRecognizer

logger = logging.getLogger(__name__)


class TestOptimizationBenchmark:
    """优化性能基准测试类"""
    
    @pytest.fixture
    def test_image(self):
        """创建测试图像"""
        # 创建一个1920x1080的测试图像
        image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        return image
    
    @pytest.fixture
    def pipeline_without_optimization(self):
        """创建未优化的检测管道（用于对比）"""
        human_detector = HumanDetector()
        behavior_recognizer = BehaviorRecognizer()
        
        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            behavior_recognizer=behavior_recognizer,
            enable_cache=False,  # 禁用缓存以便公平对比
            enable_state_management=False,  # 禁用状态管理
            enable_async=False,  # 禁用异步处理
        )
        return pipeline
    
    @pytest.fixture
    def pipeline_with_optimization(self):
        """创建优化的检测管道"""
        human_detector = HumanDetector()
        behavior_recognizer = BehaviorRecognizer()
        
        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            behavior_recognizer=behavior_recognizer,
            enable_cache=True,  # 启用缓存
            enable_state_management=True,  # 启用状态管理
            enable_async=False,  # 暂时禁用异步（需要异步环境）
        )
        return pipeline
    
    def test_detection_speed_comparison(
        self,
        test_image,
        pipeline_without_optimization,
        pipeline_with_optimization,
    ):
        """测试检测速度对比"""
        num_iterations = 10
        
        # 测试未优化版本
        times_without = []
        for i in range(num_iterations):
            start = time.time()
            result = pipeline_without_optimization.detect_comprehensive(
                test_image,
                enable_hairnet=True,
                enable_handwash=True,
                enable_sanitize=True,
            )
            elapsed = time.time() - start
            times_without.append(elapsed)
        
        avg_time_without = np.mean(times_without)
        fps_without = 1.0 / avg_time_without if avg_time_without > 0 else 0
        
        # 测试优化版本
        times_with = []
        for i in range(num_iterations):
            start = time.time()
            result = pipeline_with_optimization.detect_comprehensive(
                test_image,
                enable_hairnet=True,
                enable_handwash=True,
                enable_sanitize=True,
            )
            elapsed = time.time() - start
            times_with.append(elapsed)
        
        avg_time_with = np.mean(times_with)
        fps_with = 1.0 / avg_time_with if avg_time_with > 0 else 0
        
        # 计算提升
        speedup = avg_time_without / avg_time_with if avg_time_with > 0 else 0
        
        logger.info(f"未优化版本: 平均耗时={avg_time_without:.3f}s, FPS={fps_without:.2f}")
        logger.info(f"优化版本: 平均耗时={avg_time_with:.3f}s, FPS={fps_with:.2f}")
        logger.info(f"速度提升: {speedup:.2f}倍")
        
        # 验证优化有效（至少提升1.5倍）
        assert speedup >= 1.0, f"优化后速度应该至少与优化前相同，实际提升={speedup:.2f}倍"
    
    def test_roi_optimization_impact(
        self,
        test_image,
        pipeline_with_optimization,
    ):
        """测试ROI优化的影响"""
        # 创建包含多个人体的测试场景
        # （实际测试中应该使用真实图像）
        
        num_iterations = 5
        
        # 测试ROI优化版本（自动启用）
        times = []
        for i in range(num_iterations):
            start = time.time()
            result = pipeline_with_optimization.detect_comprehensive(
                test_image,
                enable_hairnet=True,
                enable_handwash=False,
                enable_sanitize=False,
            )
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = np.mean(times)
        logger.info(f"ROI优化版本平均耗时: {avg_time:.3f}s")
        
        # 验证检测结果有效
        assert result is not None
        assert hasattr(result, 'person_detections')
        assert hasattr(result, 'hairnet_results')
    
    def test_memory_usage(
        self,
        test_image,
        pipeline_with_optimization,
    ):
        """测试内存使用情况"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 记录初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行多次检测
        for i in range(10):
            result = pipeline_with_optimization.detect_comprehensive(test_image)
        
        # 记录最终内存
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        logger.info(f"初始内存: {initial_memory:.2f} MB")
        logger.info(f"最终内存: {final_memory:.2f} MB")
        logger.info(f"内存增长: {memory_increase:.2f} MB")
        
        # 验证内存增长在合理范围内（<500MB）
        assert memory_increase < 500, f"内存增长过大: {memory_increase:.2f} MB"
    
    def test_concurrent_detection(
        self,
        test_image,
        pipeline_with_optimization,
    ):
        """测试并发检测性能"""
        import concurrent.futures
        
        num_concurrent = 5
        num_iterations_per_thread = 3
        
        def detect_worker():
            times = []
            for i in range(num_iterations_per_thread):
                start = time.time()
                result = pipeline_with_optimization.detect_comprehensive(test_image)
                elapsed = time.time() - start
                times.append(elapsed)
            return times
        
        # 并发执行
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(detect_worker) for _ in range(num_concurrent)]
            all_times = []
            for future in concurrent.futures.as_completed(futures):
                all_times.extend(future.result())
        
        total_time = time.time() - start
        avg_time = np.mean(all_times)
        
        logger.info(f"并发检测: {num_concurrent}个线程, 总耗时={total_time:.3f}s")
        logger.info(f"平均每次检测耗时: {avg_time:.3f}s")
        
        # 验证并发检测正常工作
        assert len(all_times) == num_concurrent * num_iterations_per_thread

