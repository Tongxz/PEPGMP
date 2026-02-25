"""
批处理Celery任务 - 支持智能批处理的异步任务

主要功能：
1. 批量视频处理
2. 批量帧处理
3. 批量检测结果
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .celery_app import celery_app
from src.core.batch_detection_pipeline import BatchDetectionPipeline
from src.core.batch_processor import BatchPerformanceMonitor, BatchResult

logger = logging.getLogger(__name__)


# 全局检测管道实例（在应用启动时初始化）
_detection_pipeline: Optional[BatchDetectionPipeline] = None


def get_detection_pipeline() -> BatchDetectionPipeline:
    """获取检测管道实例（单例）"""
    global _detection_pipeline

    if _detection_pipeline is None:
        try:
            from src.detection.detector import HumanDetector
            from src.detection.hairnet_detection_factory import (
                HairnetDetectionFactory,
            )
            from src.config.unified_params import get_unified_params

            # 初始化检测器
            human_detector = HumanDetector()

            try:
                hairnet_detector = HairnetDetectionFactory.create()
            except Exception as e:
                logger.warning(f"发网检测器初始化失败: {e}")
                hairnet_detector = None

            # 创建批量检测管道
            _detection_pipeline = BatchDetectionPipeline(
                human_detector=human_detector,
                hairnet_detector=hairnet_detector,
                behavior_recognizer=None,  # 行为识别暂不支持批处理
                enable_cache=True,
                enable_batch_processing=True,
                max_batch_size=16,
            )

            logger.info("批量检测管道初始化成功")

        except Exception as e:
            logger.error(f"批量检测管道初始化失败: {e}")
            # 返回一个空管道，任务会失败但有明确的错误信息
            raise RuntimeError("检测管道初始化失败") from e

    return _detection_pipeline


@celery_app.task(name="src.worker.batch_tasks.health_check")
def batch_health_check():
    """
    健康检查任务
    """
    try:
        pipeline = get_detection_pipeline()
        stats = pipeline.get_batch_stats()

        return {
            "status": "ok",
            "message": "Batch Celery worker is healthy",
            "batch_stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@celery_app.task(name="src.worker.batch_tasks.process_video_batch", bind=True)
def process_video_batch(
    self,
    video_path: str,
    batch_size: int = 16,
    skip_frames: int = 5,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    批量处理视频文件

    Args:
        self: Celery任务实例（用于进度更新）
        video_path: 视频文件路径
        batch_size: 批处理大小
        skip_frames: 跳帧数
        config: 处理配置

    Returns:
        处理结果
    """
    logger.info(f"开始批量处理视频: {video_path}, 批大小: {batch_size}")

    try:
        # 验证视频文件
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 打开视频
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(
            f"视频信息: 总帧数={total_frames}, FPS={fps}, "
            f"分辨率={width}x{height}"
        )

        # 获取检测管道
        pipeline = get_detection_pipeline()

        # 处理视频
        frame_buffer = []
        frame_indices = []
        all_results = []
        all_frame_indices = []
        processed_frames = 0

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 跳帧处理
            if frame_idx % (skip_frames + 1) != 0:
                frame_idx += 1
                continue

            # 添加到缓冲区
            frame_buffer.append(frame)
            frame_indices.append(frame_idx)

            # 批处理
            if len(frame_buffer) >= batch_size:
                # 批量检测
                batch_results = pipeline.detect_batch(frame_buffer, batch_size=batch_size)
                all_results.extend(batch_results)
                all_frame_indices.extend(frame_indices)

                # 清空缓冲区
                frame_buffer.clear()
                frame_indices.clear()

                # 更新进度
                processed_frames = frame_idx + 1
                progress = min(100.0, (processed_frames / total_frames) * 100)
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current_frame": processed_frames,
                        "total_frames": total_frames,
                        "progress": f"{progress:.1f}%",
                        "fps": fps,
                    },
                )

            frame_idx += 1

        # 处理剩余帧
        if frame_buffer:
            batch_results = pipeline.detect_batch(frame_buffer, batch_size=batch_size)
            all_results.extend(batch_results)
            all_frame_indices.extend(frame_indices)
            processed_frames = frame_idx

        # 关闭视频
        cap.release()

        # 汇总结果
        total_detections = sum(len(r.person_detections) for r in all_results)
        total_hairnet_violations = sum(
            1
            for r in all_results
            for h in r.hairnet_results
            if not h.get("has_hairnet", True)
        )

        # 获取批处理统计
        batch_stats = pipeline.get_batch_stats()

        result = {
            "video_path": video_path,
            "status": "completed",
            "processed_at": datetime.now().isoformat(),
            "video_info": {
                "total_frames": total_frames,
                "processed_frames": processed_frames,
                "fps": fps,
                "resolution": f"{width}x{height}",
            },
            "statistics": {
                "total_batches": batch_stats.get("total_batches", 0),
                "avg_batch_size": batch_stats.get("avg_batch_size", 0),
                "avg_processing_time": batch_stats.get("avg_per_item_time", 0),
                "throughput": batch_stats.get("throughput", 0),
                "total_detections": total_detections,
                "hairnet_violations": total_hairnet_violations,
            },
            "results": [
                {
                    "frame_idx": all_frame_indices[i],
                    "person_count": len(r.person_detections),
                }
                for i, r in enumerate(all_results)
                if i < len(all_frame_indices)
            ],
        }

        logger.info(f"视频处理完成: {video_path}")
        return result

    except Exception as e:
        logger.error(f"视频处理失败: {video_path}, 错误: {e}", exc_info=True)
        return {
            "video_path": video_path,
            "status": "failed",
            "error": str(e),
            "processed_at": datetime.now().isoformat(),
        }


@celery_app.task(name="src.worker.batch_tasks.batch_process_videos", bind=True)
def batch_process_videos(
    self,
    video_paths: List[str],
    batch_size: int = 16,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    批量处理多个视频文件

    Args:
        self: Celery任务实例（用于进度更新）
        video_paths: 视频文件路径列表
        batch_size: 批处理大小
        config: 处理配置

    Returns:
        批量处理结果
    """
    logger.info(f"开始批量处理 {len(video_paths)} 个视频")

    try:
        results = []
        total_videos = len(video_paths)

        for i, video_path in enumerate(video_paths, 1):
            logger.info(f"处理视频 {i}/{total_videos}: {video_path}")

            # 调用单个视频处理任务
            result = process_video_batch(
                video_path, batch_size=batch_size, config=config
            )
            results.append(result)

            # 更新进度
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_videos,
                    "status": f"处理中 {i}/{total_videos}",
                    "current_video": video_path,
                },
            )

        # 汇总结果
        successful = sum(1 for r in results if r.get("status") == "completed")
        failed = total_videos - successful

        # 统计总检测数
        total_detections = sum(r.get("statistics", {}).get("total_detections", 0) for r in results)
        total_violations = sum(r.get("statistics", {}).get("hairnet_violations", 0) for r in results)

        summary = {
            "total_videos": total_videos,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_videos if total_videos > 0 else 0,
            "total_detections": total_detections,
            "total_violations": total_violations,
            "results": results,
        }

        logger.info(f"批量处理完成: 成功 {successful}, 失败 {failed}")
        return summary

    except Exception as e:
        logger.error(f"批量处理失败, 错误: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "total_videos": len(video_paths),
            "successful": 0,
            "failed": len(video_paths),
        }


@celery_app.task(name="src.worker.batch_tasks.detect_frames_batch")
def detect_frames_batch(
    frames_data: List[Dict[str, Any]], config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    批量检测多帧

    Args:
        frames_data: 帧数据列表，每个元素包含:
            - 'frame': 帧数据（numpy数组，需要序列化）
            - 'camera_id': 摄像头ID（可选）
        config: 处理配置

    Returns:
        批量检测结果
    """
    logger.info(f"开始批量检测 {len(frames_data)} 帧")

    try:
        # 反序列化帧数据
        frames = []
        camera_ids = []

        for idx, frame_data in enumerate(frames_data):
            # 从base64或字节还原numpy数组（这里简化处理）
            frame = np.frombuffer(frame_data["frame"], dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError(f"无法解码帧数据: index={idx}")
            frames.append(frame)

            camera_ids.append(frame_data.get("camera_id", "default"))

        # 获取检测管道
        pipeline = get_detection_pipeline()

        # 从配置获取批大小
        batch_size = 16
        if config and "batch_size" in config:
            batch_size = config["batch_size"]

        # 批量检测
        results = pipeline.detect_batch(frames, camera_ids=camera_ids, batch_size=batch_size)

        # 序列化结果
        serialized_results = []
        for result in results:
            serialized_result = {
                "person_count": len(result.person_detections),
                "hairnet_count": len(result.hairnet_results),
                "handwash_count": len(result.handwash_results),
                "sanitize_count": len(result.sanitize_results),
                # 注意：annotated_image是numpy数组，可能需要序列化
            }
            serialized_results.append(serialized_result)

        # 获取批处理统计
        batch_stats = pipeline.get_batch_stats()

        return {
            "status": "completed",
            "processed_at": datetime.now().isoformat(),
            "frame_count": len(frames),
            "batch_stats": batch_stats,
            "results": serialized_results,
        }

    except Exception as e:
        logger.error(f"批量检测失败: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "processed_at": datetime.now().isoformat(),
        }


@celery_app.task(name="src.worker.batch_tasks.process_video_segment_batch")
def process_video_segment_batch(
    video_path: str,
    start_time: float,
    end_time: float,
    batch_size: int = 16,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    批量处理视频片段

    Args:
        video_path: 视频文件路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        batch_size: 批处理大小
        config: 处理配置

    Returns:
        处理结果
    """
    logger.info(f"开始处理视频片段: {video_path}, {start_time}-{end_time}s")

    try:
        # 验证时间范围
        if start_time >= end_time:
            raise ValueError(f"无效的时间范围: {start_time} >= {end_time}")

        # 打开视频
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)

        # 设置开始时间
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)

        # 获取检测管道
        pipeline = get_detection_pipeline()

        # 处理片段
        frame_buffer = []
        frame_times = []
        results = []
        current_time = start_time

        while current_time < end_time:
            ret, frame = cap.read()
            if not ret:
                break

            # 添加到缓冲区
            frame_buffer.append(frame)
            frame_times.append(current_time)

            # 批处理
            if len(frame_buffer) >= batch_size:
                batch_results = pipeline.detect_batch(frame_buffer, batch_size=batch_size)
                results.extend(batch_results)

                # 清空缓冲区
                frame_buffer.clear()
                frame_times.clear()

            current_time += 1.0 / fps

        # 处理剩余帧
        if frame_buffer:
            batch_results = pipeline.detect_batch(frame_buffer, batch_size=batch_size)
            results.extend(batch_results)

        # 关闭视频
        cap.release()

        # 汇总结果
        total_detections = sum(len(r.person_detections) for r in results)
        batch_stats = pipeline.get_batch_stats()

        return {
            "video_path": video_path,
            "segment": f"{start_time}-{end_time}s",
            "status": "completed",
            "processed_at": datetime.now().isoformat(),
            "statistics": {
                "total_frames": len(results),
                "total_detections": total_detections,
                "avg_batch_size": batch_stats.get("avg_batch_size", 0),
                "throughput": batch_stats.get("throughput", 0),
            },
        }

    except Exception as e:
        logger.error(f"视频片段处理失败: {video_path}, 错误: {e}", exc_info=True)
        return {
            "video_path": video_path,
            "segment": f"{start_time}-{end_time}s",
            "status": "failed",
            "error": str(e),
            "processed_at": datetime.now().isoformat(),
        }
