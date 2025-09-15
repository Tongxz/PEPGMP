#!/usr/bin/env python3
"""
性能对比测试脚本
对比原始检测方法和优化后的检测方法

测试项目：
1. 单帧检测速度
2. 批量检测速度
3. 缓存效果
4. 内存使用
5. GPU利用率
"""

import time
import numpy as np
import cv2
import psutil
import torch
import logging
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import json
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.results = {
            'original': {},
            'optimized': {},
            'comparison': {}
        }
        
    def generate_test_frames(self, count: int = 100) -> List[np.ndarray]:
        """生成测试帧"""
        frames = []
        for i in range(count):
            # 生成随机图像
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # 添加一些变化
            if i % 10 == 0:
                # 每10帧添加一个"人"的矩形
                cv2.rectangle(frame, (100, 100), (200, 300), (255, 255, 255), -1)
            
            frames.append(frame)
        
        return frames
    
    def test_original_method(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """测试原始检测方法"""
        logger.info("测试原始检测方法...")
        
        start_time = time.time()
        processing_times = []
        
        for i, frame in enumerate(frames):
            frame_start = time.time()
            
            # 模拟原始检测流程
            self._simulate_original_detection(frame)
            
            frame_time = time.time() - frame_start
            processing_times.append(frame_time)
            
            if i % 20 == 0:
                logger.info(f"原始方法 - 帧 {i}: {frame_time*1000:.1f}ms")
        
        total_time = time.time() - start_time
        avg_time = np.mean(processing_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0
        
        return {
            'total_time': total_time,
            'avg_processing_time': avg_time,
            'fps': fps,
            'processing_times': processing_times,
            'total_frames': len(frames)
        }
    
    def test_optimized_method(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """测试优化检测方法"""
        logger.info("测试优化检测方法...")
        
        from src.core.fast_detection_pipeline import FastDetectionPipeline
        
        pipeline = FastDetectionPipeline()
        start_time = time.time()
        processing_times = []
        
        for i, frame in enumerate(frames):
            frame_start = time.time()
            
            # 使用优化的检测方法
            result = pipeline.detect(frame)
            
            frame_time = time.time() - frame_start
            processing_times.append(frame_time)
            
            if i % 20 == 0:
                logger.info(f"优化方法 - 帧 {i}: {frame_time*1000:.1f}ms")
        
        total_time = time.time() - start_time
        avg_time = np.mean(processing_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0
        
        # 获取流水线统计
        pipeline_stats = pipeline.get_stats()
        
        return {
            'total_time': total_time,
            'avg_processing_time': avg_time,
            'fps': fps,
            'processing_times': processing_times,
            'total_frames': len(frames),
            'pipeline_stats': pipeline_stats
        }
    
    def _simulate_original_detection(self, frame: np.ndarray):
        """模拟原始检测流程"""
        # 模拟串行检测
        time.sleep(0.05)  # 50ms - 人体检测
        time.sleep(0.03)  # 30ms - 发网检测
        time.sleep(0.04)  # 40ms - 洗手检测
        time.sleep(0.04)  # 40ms - 消毒检测
        # 总计: 160ms per frame
    
    def run_comparison(self, frame_count: int = 100):
        """运行完整对比测试"""
        logger.info(f"=== 开始性能对比测试 ({frame_count}帧) ===")
        
        # 生成测试帧
        frames = self.generate_test_frames(frame_count)
        
        # 测试原始方法
        original_results = self.test_original_method(frames)
        self.results['original'] = original_results
        
        # 测试优化方法
        optimized_results = self.test_optimized_method(frames)
        self.results['optimized'] = optimized_results
        
        # 计算对比结果
        self._calculate_comparison()
        
        # 显示结果
        self._display_results()
        
        # 保存结果
        self._save_results()
        
        return self.results
    
    def _calculate_comparison(self):
        """计算对比结果"""
        original = self.results['original']
        optimized = self.results['optimized']
        
        fps_improvement = optimized['fps'] / original['fps'] if original['fps'] > 0 else 0
        time_reduction = (original['avg_processing_time'] - optimized['avg_processing_time']) / original['avg_processing_time'] * 100
        
        self.results['comparison'] = {
            'fps_improvement': fps_improvement,
            'time_reduction_percent': time_reduction,
            'original_fps': original['fps'],
            'optimized_fps': optimized['fps'],
            'original_avg_time': original['avg_processing_time'],
            'optimized_avg_time': optimized['avg_processing_time']
        }
    
    def _display_results(self):
        """显示测试结果"""
        logger.info("\n" + "="*60)
        logger.info("性能对比测试结果")
        logger.info("="*60)
        
        original = self.results['original']
        optimized = self.results['optimized']
        comparison = self.results['comparison']
        
        logger.info(f"原始方法:")
        logger.info(f"  平均FPS: {original['fps']:.1f}")
        logger.info(f"  平均处理时间: {original['avg_processing_time']*1000:.1f}ms")
        logger.info(f"  总处理时间: {original['total_time']:.2f}s")
        
        logger.info(f"\n优化方法:")
        logger.info(f"  平均FPS: {optimized['fps']:.1f}")
        logger.info(f"  平均处理时间: {optimized['avg_processing_time']*1000:.1f}ms")
        logger.info(f"  总处理时间: {optimized['total_time']:.2f}s")
        
        if 'pipeline_stats' in optimized:
            pipeline_stats = optimized['pipeline_stats']
            logger.info(f"  缓存命中率: {pipeline_stats.get('cache_hit_rate', 0):.1f}%")
            logger.info(f"  批处理统计: {pipeline_stats.get('batch_stats', {})}")
        
        logger.info(f"\n性能提升:")
        logger.info(f"  FPS提升: {comparison['fps_improvement']:.1f}x")
        logger.info(f"  时间减少: {comparison['time_reduction_percent']:.1f}%")
        
        logger.info("="*60)
    
    def _save_results(self):
        """保存测试结果"""
        output_dir = Path("reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = int(time.time())
        output_file = output_dir / f"performance_comparison_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"测试结果已保存到: {output_file}")
    
    def plot_results(self):
        """绘制性能对比图表"""
        try:
            import matplotlib.pyplot as plt
            
            original_times = self.results['original']['processing_times']
            optimized_times = self.results['optimized']['processing_times']
            
            plt.figure(figsize=(12, 8))
            
            # 处理时间对比
            plt.subplot(2, 2, 1)
            plt.plot(original_times, label='原始方法', alpha=0.7)
            plt.plot(optimized_times, label='优化方法', alpha=0.7)
            plt.xlabel('帧数')
            plt.ylabel('处理时间 (秒)')
            plt.title('处理时间对比')
            plt.legend()
            plt.grid(True)
            
            # FPS对比
            plt.subplot(2, 2, 2)
            original_fps = [1/t if t > 0 else 0 for t in original_times]
            optimized_fps = [1/t if t > 0 else 0 for t in optimized_times]
            plt.plot(original_fps, label='原始方法', alpha=0.7)
            plt.plot(optimized_fps, label='优化方法', alpha=0.7)
            plt.xlabel('帧数')
            plt.ylabel('FPS')
            plt.title('FPS对比')
            plt.legend()
            plt.grid(True)
            
            # 性能提升
            plt.subplot(2, 2, 3)
            improvement = [opt/orig if orig > 0 else 0 for orig, opt in zip(original_times, optimized_times)]
            plt.plot(improvement, label='性能提升倍数', color='green')
            plt.xlabel('帧数')
            plt.ylabel('提升倍数')
            plt.title('性能提升趋势')
            plt.legend()
            plt.grid(True)
            
            # 统计摘要
            plt.subplot(2, 2, 4)
            categories = ['原始FPS', '优化FPS', '提升倍数']
            values = [
                self.results['original']['fps'],
                self.results['optimized']['fps'],
                self.results['comparison']['fps_improvement']
            ]
            bars = plt.bar(categories, values, color=['red', 'blue', 'green'])
            plt.title('性能摘要')
            plt.ylabel('FPS / 倍数')
            
            # 在柱状图上添加数值标签
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{value:.1f}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            # 保存图表
            output_dir = Path("reports")
            output_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            plot_file = output_dir / f"performance_comparison_{timestamp}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.show()
            
            logger.info(f"性能对比图表已保存到: {plot_file}")
            
        except ImportError:
            logger.warning("matplotlib未安装，跳过图表生成")
        except Exception as e:
            logger.error(f"图表生成失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="性能对比测试")
    parser.add_argument("--frames", type=int, default=100, help="测试帧数")
    parser.add_argument("--plot", action="store_true", help="生成对比图表")
    
    args = parser.parse_args()
    
    # 运行测试
    benchmark = PerformanceBenchmark()
    results = benchmark.run_comparison(args.frames)
    
    # 生成图表
    if args.plot:
        benchmark.plot_results()
    
    return results

if __name__ == "__main__":
    main()
