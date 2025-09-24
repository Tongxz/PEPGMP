"""
GPU加速检测流水线
Accelerated Detection Pipeline

提供GPU优化的高性能检测流水线：
1. 自动GPU设备选择和优化
2. 批处理推理
3. 异步并行处理
4. 内存优化管理
5. 性能监控
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

import numpy as np

from ..utils.gpu_acceleration import get_gpu_manager
from .optimized_detection_pipeline import DetectionResult, OptimizedDetectionPipeline

logger = logging.getLogger(__name__)


@dataclass
class AcceleratedDetectionResult(DetectionResult):
    """加速检测结果"""

    device_used: str = "cpu"
    batch_size: int = 1
    gpu_memory_used_mb: float = 0.0
    inference_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0


class BatchProcessor:
    """批处理器"""

    def __init__(self, max_batch_size: int = 8, max_wait_time: float = 0.016):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time  # 16ms = 60FPS

        self.batch_queue = Queue()
        self.result_futures = {}
        self.processing = False

        self.stats = {
            "total_batches": 0,
            "total_frames": 0,
            "avg_batch_time": 0.0,
            "avg_frames_per_batch": 0.0,
        }

    def add_frame(self, frame: np.ndarray, frame_id: str) -> threading.Event:
        """添加帧到批处理队列"""
        result_event = threading.Event()

        self.batch_queue.put(
            {
                "frame": frame,
                "frame_id": frame_id,
                "timestamp": time.time(),
                "result_event": result_event,
            }
        )

        return result_event

    def start_processing(self, process_batch_func):
        """开始批处理"""
        self.processing = True
        self.process_batch_func = process_batch_func

        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()

    def stop_processing(self):
        """停止批处理"""
        self.processing = False

    def _process_loop(self):
        """批处理循环"""
        batch = []
        last_process_time = time.time()

        while self.processing:
            try:
                # 尝试获取帧
                try:
                    item = self.batch_queue.get(timeout=0.001)
                    batch.append(item)
                except Empty:
                    pass

                current_time = time.time()
                should_process = len(batch) >= self.max_batch_size or (
                    batch and (current_time - last_process_time) >= self.max_wait_time
                )

                if should_process and batch:
                    self._process_current_batch(batch)
                    batch = []
                    last_process_time = current_time

            except Exception as e:
                logger.error(f"批处理循环错误: {e}")

        # 处理剩余批次
        if batch:
            self._process_current_batch(batch)

    def _process_current_batch(self, batch: List[Dict]):
        """处理当前批次"""
        start_time = time.time()

        try:
            # 提取帧数据
            frames = [item["frame"] for item in batch]
            frame_ids = [item["frame_id"] for item in batch]

            # 批量处理
            results = self.process_batch_func(frames, frame_ids)

            # 通知结果
            for i, item in enumerate(batch):
                item["result"] = results[i] if i < len(results) else None
                item["result_event"].set()

            # 更新统计
            batch_time = time.time() - start_time
            self.stats["total_batches"] += 1
            self.stats["total_frames"] += len(batch)
            self.stats["avg_batch_time"] = (
                self.stats["avg_batch_time"] * (self.stats["total_batches"] - 1)
                + batch_time
            ) / self.stats["total_batches"]
            self.stats["avg_frames_per_batch"] = (
                self.stats["total_frames"] / self.stats["total_batches"]
            )

            logger.debug(
                f"批处理完成: {len(batch)}帧, {batch_time*1000:.1f}ms, "
                f"{len(batch)/batch_time:.1f} FPS"
            )

        except Exception as e:
            logger.error(f"批处理失败: {e}")
            # 通知所有等待的线程
            for item in batch:
                item["result"] = None
                item["result_event"].set()


class AcceleratedDetectionPipeline:
    """GPU加速检测流水线"""

    def __init__(
        self,
        enable_batch_processing: bool = True,
        enable_async_processing: bool = True,
        max_batch_size: Optional[int] = None,
        enable_performance_monitoring: bool = True,
    ):
        """
        初始化加速检测流水线

        Args:
            enable_batch_processing: 启用批处理
            enable_async_processing: 启用异步处理
            max_batch_size: 最大批处理大小
            enable_performance_monitoring: 启用性能监控
        """
        logger.info("🚀 初始化GPU加速检测流水线...")

        # 初始化GPU管理器
        self.gpu_manager = get_gpu_manager()
        gpu_info = self.gpu_manager.initialize_gpu_acceleration()

        self.device = gpu_info["device"]
        self.gpu_available = gpu_info["gpu_available"]

        # 获取优化配置
        self.config = self.gpu_manager.get_optimized_model_config("yolo")

        # 设置批处理
        self.enable_batch_processing = enable_batch_processing and self.gpu_available
        if self.enable_batch_processing:
            self.max_batch_size = max_batch_size or self.config["batch_size"]
            self.batch_processor = BatchProcessor(
                max_batch_size=self.max_batch_size, max_wait_time=0.016  # 60 FPS
            )
            self.batch_processor.start_processing(self._process_batch)
        else:
            self.max_batch_size = 1

        # 设置异步处理
        self.enable_async_processing = enable_async_processing
        if self.enable_async_processing:
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.config["num_workers"]
            )

        # 初始化基础流水线
        self.base_pipeline = OptimizedDetectionPipeline()

        # 性能监控
        self.enable_monitoring = enable_performance_monitoring
        self.performance_stats = {
            "total_detections": 0,
            "total_inference_time": 0.0,
            "total_processing_time": 0.0,
            "avg_fps": 0.0,
            "gpu_utilization": [],
            "memory_usage": [],
        }

        # 优化模型
        self._optimize_models()

        logger.info(
            f"✅ GPU加速流水线初始化完成 - 设备: {self.device}, "
            f"批处理: {self.enable_batch_processing}, "
            f"批大小: {self.max_batch_size}"
        )

    def _optimize_models(self):
        """优化模型"""
        try:
            # 优化人体检测器
            if hasattr(self.base_pipeline, "human_detector"):
                if hasattr(self.base_pipeline.human_detector, "model"):
                    self.base_pipeline.human_detector.model = (
                        self.gpu_manager.optimize_model(
                            self.base_pipeline.human_detector.model, "yolo"
                        )
                    )

            # 优化发网检测器
            if hasattr(self.base_pipeline, "hairnet_detector"):
                if hasattr(self.base_pipeline.hairnet_detector, "model"):
                    self.base_pipeline.hairnet_detector.model = (
                        self.gpu_manager.optimize_model(
                            self.base_pipeline.hairnet_detector.model, "yolo"
                        )
                    )

            logger.info("✅ 模型GPU优化完成")

        except Exception as e:
            logger.warning(f"模型优化失败: {e}")

    def detect_single(self, frame: np.ndarray, **kwargs) -> AcceleratedDetectionResult:
        """单帧检测"""
        start_time = time.time()

        try:
            # 获取GPU内存使用情况
            gpu_memory_used = self._get_gpu_memory_usage()

            # 执行检测
            inference_start = time.time()

            if self.enable_batch_processing:
                # 使用批处理（即使只有一帧）
                frame_id = f"single_{int(time.time() * 1000000)}"
                result_event = self.batch_processor.add_frame(frame, frame_id)
                result_event.wait(timeout=1.0)  # 等待结果

                # 获取结果（这里需要一个机制来存储和检索单帧结果）
                base_result = self._get_single_frame_result(frame_id)
            else:
                # 直接处理
                base_result = self.base_pipeline.detect_comprehensive(frame, **kwargs)

            inference_time = time.time() - inference_start
            total_time = time.time() - start_time

            # 创建加速检测结果
            result = AcceleratedDetectionResult(
                **base_result.__dict__,
                device_used=self.device,
                batch_size=1,
                gpu_memory_used_mb=gpu_memory_used,
                inference_time_ms=inference_time * 1000,
                total_processing_time_ms=total_time * 1000,
            )

            # 更新性能统计
            self._update_performance_stats(inference_time, total_time)

            return result

        except Exception as e:
            logger.error(f"单帧检测失败: {e}")
            # 返回空结果
            return AcceleratedDetectionResult(
                device_used=self.device, batch_size=1, error=str(e)
            )

    def detect_batch(
        self, frames: List[np.ndarray], **kwargs
    ) -> List[AcceleratedDetectionResult]:
        """批量检测"""
        if not self.enable_batch_processing:
            # 逐帧处理
            return [self.detect_single(frame, **kwargs) for frame in frames]

        start_time = time.time()

        try:
            # 批量处理
            frame_ids = [
                f"batch_{i}_{int(time.time() * 1000000)}" for i in range(len(frames))
            ]
            base_results = self._process_batch(frames, frame_ids)

            total_time = time.time() - start_time
            gpu_memory_used = self._get_gpu_memory_usage()

            # 创建结果
            results = []
            for i, base_result in enumerate(base_results):
                result = AcceleratedDetectionResult(
                    **base_result.__dict__,
                    device_used=self.device,
                    batch_size=len(frames),
                    gpu_memory_used_mb=gpu_memory_used,
                    inference_time_ms=(total_time * 1000) / len(frames),
                    total_processing_time_ms=total_time * 1000,
                )
                results.append(result)

            # 更新性能统计
            self._update_performance_stats(total_time / len(frames), total_time)

            return results

        except Exception as e:
            logger.error(f"批量检测失败: {e}")
            return [
                AcceleratedDetectionResult(device_used=self.device, error=str(e))
                for _ in frames
            ]

    def _process_batch(
        self, frames: List[np.ndarray], frame_ids: List[str]
    ) -> List[DetectionResult]:
        """处理批量帧"""
        results = []

        try:
            # TODO: 实现真正的批量推理
            # 当前逐帧处理，后续可以优化为真正的批量推理
            for frame in frames:
                result = self.base_pipeline.detect_comprehensive(frame)
                results.append(result)

        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            # 返回空结果
            for _ in frames:
                results.append(DetectionResult())

        return results

    def _get_single_frame_result(self, frame_id: str) -> DetectionResult:
        """获取单帧结果（临时实现）"""
        # TODO: 实现结果缓存和检索机制
        return DetectionResult()

    def _get_gpu_memory_usage(self) -> float:
        """获取GPU内存使用量（MB）"""
        if not self.gpu_available:
            return 0.0

        try:
            import torch

            if torch.cuda.is_available():
                return torch.cuda.memory_allocated(0) / (1024 * 1024)
        except:
            pass

        return 0.0

    def _update_performance_stats(self, inference_time: float, total_time: float):
        """更新性能统计"""
        if not self.enable_monitoring:
            return

        self.performance_stats["total_detections"] += 1
        self.performance_stats["total_inference_time"] += inference_time
        self.performance_stats["total_processing_time"] += total_time

        # 计算平均FPS
        if self.performance_stats["total_processing_time"] > 0:
            self.performance_stats["avg_fps"] = (
                self.performance_stats["total_detections"]
                / self.performance_stats["total_processing_time"]
            )

        # 记录GPU利用率（如果可用）
        try:
            import torch

            if torch.cuda.is_available():
                utilization = torch.cuda.utilization(0)
                self.performance_stats["gpu_utilization"].append(utilization)

                memory_info = torch.cuda.mem_get_info(0)
                memory_used_gb = (memory_info[1] - memory_info[0]) / (1024**3)
                self.performance_stats["memory_usage"].append(memory_used_gb)
        except:
            pass

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        stats = self.performance_stats.copy()

        # 计算平均值
        if stats["gpu_utilization"]:
            stats["avg_gpu_utilization"] = np.mean(stats["gpu_utilization"])
            stats["max_gpu_utilization"] = np.max(stats["gpu_utilization"])

        if stats["memory_usage"]:
            stats["avg_memory_usage_gb"] = np.mean(stats["memory_usage"])
            stats["max_memory_usage_gb"] = np.max(stats["memory_usage"])

        # 添加配置信息
        stats["configuration"] = {
            "device": self.device,
            "batch_processing_enabled": self.enable_batch_processing,
            "max_batch_size": self.max_batch_size,
            "async_processing_enabled": self.enable_async_processing,
            "gpu_available": self.gpu_available,
        }

        return stats

    def optimize_for_video_stream(self, target_fps: int = 30) -> Dict[str, Any]:
        """为视频流优化"""
        logger.info(f"🎥 优化视频流处理 - 目标FPS: {target_fps}")

        # 计算最佳设置
        1.0 / target_fps

        optimization_config = {
            "frame_skip": max(1, int(30 / target_fps)),  # 跳帧策略
            "batch_size": min(self.max_batch_size, max(1, target_fps // 10)),
            "quality_level": "balanced",  # 平衡质量和速度
            "enable_caching": True,
            "cache_size": target_fps * 2,  # 缓存2秒
        }

        logger.info(f"视频流优化配置: {optimization_config}")
        return optimization_config

    def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理GPU加速流水线...")

        try:
            # 停止批处理
            if hasattr(self, "batch_processor"):
                self.batch_processor.stop_processing()

            # 关闭线程池
            if hasattr(self, "thread_pool"):
                self.thread_pool.shutdown(wait=True)

            # 清理GPU缓存
            if self.gpu_available:
                try:
                    import torch

                    torch.cuda.empty_cache()
                except:
                    pass

            logger.info("✅ 资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")


def create_accelerated_pipeline(**kwargs) -> AcceleratedDetectionPipeline:
    """创建加速检测流水线（便捷函数）"""
    return AcceleratedDetectionPipeline(**kwargs)
