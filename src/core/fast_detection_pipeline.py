#!/usr/bin/env python3
"""
快速检测流水线 - 专门针对API模式优化

主要优化策略：
1. 批处理推理 - 减少GPU调用次数
2. 模型融合 - 单次推理完成多项检测
3. 智能缓存 - 基于帧相似度的缓存策略
4. 异步处理 - 非阻塞检测流程
"""

import asyncio
import time
import threading
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
import torch
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class FastDetectionResult:
    """快速检测结果"""
    person_detections: List[Dict]
    hairnet_results: List[Dict]
    handwash_results: List[Dict]
    sanitize_results: List[Dict]
    processing_time: float
    fps: float
    cached: bool = False

class FrameSimilarityCache:
    """基于帧相似度的智能缓存"""
    
    def __init__(self, max_size: int = 50, similarity_threshold: float = 0.95):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.cache = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def _calculate_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """计算两帧的相似度"""
        # 使用直方图比较
        hist1 = cv2.calcHist([frame1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([frame2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        # 使用相关系数
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return correlation
    
    def get(self, frame: np.ndarray) -> Optional[FastDetectionResult]:
        """获取缓存结果"""
        with self.lock:
            for cached_frame, result in self.cache:
                similarity = self._calculate_similarity(frame, cached_frame)
                if similarity > self.similarity_threshold:
                    result.cached = True
                    return result
            return None
    
    def put(self, frame: np.ndarray, result: FastDetectionResult):
        """存储结果到缓存"""
        with self.lock:
            self.cache.append((frame.copy(), result))

class BatchDetector:
    """批处理检测器"""
    
    def __init__(self, device: str = "cuda", batch_size: int = 8):
        self.device = device
        self.batch_size = batch_size
        self.buffer = []
        self.lock = threading.Lock()
        
        # 性能统计
        self.stats = {
            'total_batches': 0,
            'total_frames': 0,
            'avg_batch_time': 0,
            'avg_fps': 0
        }
    
    def add_frame(self, frame: np.ndarray) -> Optional[List[FastDetectionResult]]:
        """添加帧到批处理缓冲区"""
        with self.lock:
            self.buffer.append(frame)
            
            if len(self.buffer) >= self.batch_size:
                batch = self.buffer.copy()
                self.buffer.clear()
                return self._process_batch(batch)
            return None
    
    def flush(self) -> Optional[List[FastDetectionResult]]:
        """强制处理缓冲区中的帧"""
        with self.lock:
            if self.buffer:
                batch = self.buffer.copy()
                self.buffer.clear()
                return self._process_batch(batch)
            return None
    
    def _process_batch(self, batch: List[np.ndarray]) -> List[FastDetectionResult]:
        """批量处理帧"""
        start_time = time.time()
        
        # 模拟批量推理（实际应该调用真实的模型）
        batch_time = 0.08  # 80ms for 8 frames = 10ms per frame
        time.sleep(batch_time)
        
        # 生成结果
        results = []
        for i, frame in enumerate(batch):
            result = FastDetectionResult(
                person_detections=[{'bbox': [100, 100, 200, 300], 'confidence': 0.9}],
                hairnet_results=[{'has_hairnet': True, 'confidence': 0.8}],
                handwash_results=[{'is_handwashing': False, 'confidence': 0.3}],
                sanitize_results=[{'is_sanitizing': False, 'confidence': 0.2}],
                processing_time=batch_time / len(batch),
                fps=len(batch) / batch_time
            )
            results.append(result)
        
        # 更新统计
        self.stats['total_batches'] += 1
        self.stats['total_frames'] += len(batch)
        self.stats['avg_batch_time'] = (
            self.stats['avg_batch_time'] * (self.stats['total_batches'] - 1) + batch_time
        ) / self.stats['total_batches']
        self.stats['avg_fps'] = self.stats['total_frames'] / (
            self.stats['total_batches'] * self.stats['avg_batch_time']
        )
        
        logger.info(f"批量处理完成: {len(batch)}帧, {batch_time*1000:.1f}ms, {len(batch)/batch_time:.1f} FPS")
        
        return results

class FastDetectionPipeline:
    """快速检测流水线"""
    
    def __init__(self, device: str = "cuda"):
        self.device = device
        self.batch_detector = BatchDetector(device=device)
        self.cache = FrameSimilarityCache()
        
        # 异步处理
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0,
            'avg_fps': 0
        }
        
        logger.info("快速检测流水线初始化完成")
    
    def _run_async_loop(self):
        """运行异步事件循环"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    async def detect_async(self, frame: np.ndarray) -> FastDetectionResult:
        """异步检测"""
        start_time = time.time()
        
        # 检查缓存
        cached_result = self.cache.get(frame)
        if cached_result is not None:
            self.stats['cache_hits'] += 1
            logger.debug("使用缓存结果")
            return cached_result
        
        self.stats['cache_misses'] += 1
        
        # 添加到批处理器
        batch_results = self.batch_detector.add_frame(frame)
        
        if batch_results is not None:
            # 找到当前帧的结果
            result = batch_results[-1]  # 简化：取最后一个结果
        else:
            # 使用默认结果（等待批处理）
            result = FastDetectionResult(
                person_detections=[],
                hairnet_results=[],
                handwash_results=[],
                sanitize_results=[],
                processing_time=0.001,
                fps=self.stats['avg_fps']
            )
        
        # 存储到缓存
        self.cache.put(frame, result)
        
        # 更新统计
        processing_time = time.time() - start_time
        self.stats['total_detections'] += 1
        self.stats['avg_processing_time'] = (
            self.stats['avg_processing_time'] * (self.stats['total_detections'] - 1) + processing_time
        ) / self.stats['total_detections']
        
        if processing_time > 0:
            self.stats['avg_fps'] = 1.0 / processing_time
        
        return result
    
    def detect(self, frame: np.ndarray) -> FastDetectionResult:
        """同步检测接口"""
        future = asyncio.run_coroutine_threadsafe(
            self.detect_async(frame), self.loop
        )
        return future.result(timeout=1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_hit_rate = (
            self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
        ) * 100
        
        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'batch_stats': self.batch_detector.stats
        }
    
    def flush_batch(self):
        """强制处理当前批次"""
        results = self.batch_detector.flush()
        return results

# 使用示例
async def test_fast_pipeline():
    """测试快速检测流水线"""
    pipeline = FastDetectionPipeline()
    
    # 模拟视频帧
    for i in range(100):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        start_time = time.time()
        result = await pipeline.detect_async(frame)
        processing_time = time.time() - start_time
        
        if i % 10 == 0:
            stats = pipeline.get_stats()
            logger.info(f"帧 {i}: {processing_time*1000:.1f}ms, "
                       f"缓存命中率: {stats['cache_hit_rate']:.1f}%, "
                       f"平均FPS: {stats['avg_fps']:.1f}")
    
    # 最终统计
    final_stats = pipeline.get_stats()
    logger.info("=== 最终性能统计 ===")
    logger.info(f"总检测次数: {final_stats['total_detections']}")
    logger.info(f"缓存命中率: {final_stats['cache_hit_rate']:.1f}%")
    logger.info(f"平均处理时间: {final_stats['avg_processing_time']*1000:.1f}ms")
    logger.info(f"平均FPS: {final_stats['avg_fps']:.1f}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_fast_pipeline())
