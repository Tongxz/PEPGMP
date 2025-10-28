"""
智能检测系统集成示例

展示如何在主检测循环中集成智能检测系统，实现自适应性能优化
"""

import logging
import time
from typing import Any, Dict, Optional

import cv2

from .intelligent_detection_system import DetectionConfig, IntelligentDetectionSystem
from .performance_monitor import PerformanceAlert

logger = logging.getLogger(__name__)


def create_intelligent_detection_system(
    detection_pipeline, config: Optional[Dict[str, Any]] = None
):
    """
    创建智能检测系统

    Args:
        detection_pipeline: 检测管道实例
        config: 配置参数

    Returns:
        IntelligentDetectionSystem: 智能检测系统实例
    """
    # 默认配置
    default_config = DetectionConfig(
        target_fps=15.0,
        enable_adaptive_processing=True,
        enable_performance_monitoring=True,
        enable_gpu_monitoring=True,
        base_skip_rate=3,
        motion_threshold=0.1,
        complexity_threshold=0.5,
        max_skip_frames=15,
        min_processing_interval=0.1,
    )

    # 合并用户配置
    if config:
        for key, value in config.items():
            if hasattr(default_config, key):
                setattr(default_config, key, value)

    # 创建告警回调
    def alert_callback(alert: PerformanceAlert):
        logger.warning(f"性能告警 [{alert.severity}]: {alert.message}")
        if alert.recommendations:
            for rec in alert.recommendations:
                logger.info(f"建议: {rec}")

    # 创建智能检测系统
    intelligent_system = IntelligentDetectionSystem(
        detection_pipeline=detection_pipeline,
        config=default_config,
        alert_callback=alert_callback,
    )

    return intelligent_system


def enhanced_detection_loop(
    video_source,
    detection_pipeline,
    config: Optional[Dict[str, Any]] = None,
    output_callback: Optional[callable] = None,
):
    """
    增强的检测循环 - 集成智能检测系统

    Args:
        video_source: 视频源（摄像头索引或文件路径）
        detection_pipeline: 检测管道
        config: 配置参数
        output_callback: 输出回调函数
    """
    # 创建智能检测系统
    intelligent_system = create_intelligent_detection_system(detection_pipeline, config)

    # 打开视频源
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        logger.error(f"无法打开视频源: {video_source}")
        return

    # 获取视频信息
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    logger.info(f"视频信息: {width}x{height} @ {fps}FPS")
    logger.info("智能检测系统已启动，开始处理...")

    frame_count = 0
    start_time = time.time()
    last_stats_time = start_time

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("视频流读取失败")
                break

            frame_count += 1

            # 使用智能检测系统处理帧
            detection_result, processing_info = intelligent_system.process_frame(
                frame=frame,
                force_process=False,  # 让系统自动决定是否处理
                enable_hairnet=True,
                enable_handwash=True,
                enable_sanitize=True,
            )

            # 处理检测结果
            if detection_result is not None:
                # 这里可以添加结果处理逻辑
                if output_callback:
                    output_callback(detection_result, processing_info)

                # 记录处理信息
                if processing_info["should_process"]:
                    logger.debug(f"帧 {frame_count} 已处理: {processing_info['reason']}")
                else:
                    logger.debug(f"帧 {frame_count} 已跳过: {processing_info['reason']}")

            # 定期输出统计信息
            current_time = time.time()
            if current_time - last_stats_time >= 10.0:  # 每10秒输出一次统计
                stats = intelligent_system.get_comprehensive_stats()
                logger.info(
                    f"检测统计 - 总帧数: {stats['detection_stats']['total_frames']}, "
                    f"处理帧数: {stats['detection_stats']['processed_frames']}, "
                    f"跳过帧数: {stats['detection_stats']['skipped_frames']}, "
                    f"平均FPS: {stats['detection_stats']['avg_fps']:.2f}, "
                    f"性能评分: {stats['detection_stats']['performance_score']:.1f}"
                )

                # 输出优化建议
                recommendations = intelligent_system.get_optimization_recommendations()
                if recommendations:
                    logger.info("优化建议:")
                    for rec in recommendations:
                        logger.info(f"  - {rec}")

                last_stats_time = current_time

            # 检查是否需要调整目标FPS
            if frame_count % 1000 == 0:  # 每1000帧检查一次
                current_fps = frame_count / (current_time - start_time)
                target_fps = intelligent_system.config.target_fps

                if current_fps < target_fps * 0.7:  # 如果实际FPS远低于目标
                    logger.warning(f"实际FPS ({current_fps:.2f}) 远低于目标FPS ({target_fps})")
                    # 可以在这里添加自动调整逻辑
                    # intelligent_system.adjust_target_fps(target_fps * 0.8)

    except KeyboardInterrupt:
        logger.info("检测循环被用户中断")
    except Exception as e:
        logger.error(f"检测循环异常: {e}")
    finally:
        # 清理资源
        cap.release()
        intelligent_system.shutdown()

        # 输出最终统计
        final_stats = intelligent_system.get_comprehensive_stats()
        logger.info("=== 最终检测统计 ===")
        logger.info(f"总帧数: {final_stats['detection_stats']['total_frames']}")
        logger.info(f"处理帧数: {final_stats['detection_stats']['processed_frames']}")
        logger.info(f"跳过帧数: {final_stats['detection_stats']['skipped_frames']}")
        logger.info(
            f"处理效率: {final_stats['detection_stats']['processed_frames'] / max(final_stats['detection_stats']['total_frames'], 1) * 100:.1f}%"
        )
        logger.info(f"平均FPS: {final_stats['detection_stats']['avg_fps']:.2f}")
        logger.info(f"性能评分: {final_stats['detection_stats']['performance_score']:.1f}")

        # 输出性能报告
        try:
            performance_report = intelligent_system.get_performance_report(
                duration_minutes=1
            )
            if "metrics" in performance_report:
                logger.info("=== 性能指标 ===")
                for metric_name, metric_data in performance_report["metrics"].items():
                    logger.info(
                        f"{metric_name}: 平均={metric_data['avg']:.2f}, "
                        f"最小={metric_data['min']:.2f}, "
                        f"最大={metric_data['max']:.2f}"
                    )
        except Exception as e:
            logger.debug(f"性能报告生成失败: {e}")


def create_optimized_main_loop_integration():
    """
    创建优化的主循环集成代码

    这个函数返回可以集成到main.py中的代码片段
    """
    integration_code = '''
# 在main.py的顶部添加导入
from src.detection.intelligent_detection_system import IntelligentDetectionSystem, DetectionConfig
from src.detection.performance_monitor import PerformanceAlert

# 在_run_detection_loop函数中，替换原有的检测循环
def _run_detection_loop_with_intelligent_system(args, logger, pipeline, device):
    """
    使用智能检测系统的检测循环
    """
    import cv2
    import time
    import json
    import redis
    from collections import defaultdict
    from datetime import datetime

    # 创建智能检测系统
    config = DetectionConfig(
        target_fps=15.0,
        enable_adaptive_processing=True,
        enable_performance_monitoring=True,
        enable_gpu_monitoring=True,
        base_skip_rate=3,
        motion_threshold=0.1,
        complexity_threshold=0.5,
        max_skip_frames=15,
        min_processing_interval=0.1
    )

    # 告警回调
    def alert_callback(alert: PerformanceAlert):
        logger.warning(f"性能告警 [{alert.severity}]: {alert.message}")
        if alert.recommendations:
            for rec in alert.recommendations:
                logger.info(f"建议: {rec}")

    intelligent_system = IntelligentDetectionSystem(
        detection_pipeline=pipeline,
        config=config,
        alert_callback=alert_callback
    )

    # Redis设置（保持原有逻辑）
    redis_client_stats = None
    camera_id = getattr(args, "camera_id", "unknown")
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD")
            redis_client_stats = redis.Redis(host=host, port=port, db=db, password=password)
        else:
            redis_client_stats = redis.Redis.from_url(redis_url)

        redis_client_stats.ping()
        logger.info("[STATS] Redis publisher for stats connected on channel hbd:stats")
    except Exception as e:
        logger.warning(f"[STATS] Could not connect to Redis for stats publishing: {e}")
        redis_client_stats = None

    def publish_stats_to_redis(data):
        if redis_client_stats:
            try:
                payload = json.dumps(data)
                redis_client_stats.publish("hbd:stats", payload)
            except Exception as e:
                logger.debug(f"[STATS] Failed to publish stats to Redis: {e}")

    # 打开视频源
    source = args.source
    try:
        source = int(source)
    except (ValueError, TypeError):
        pass

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error(f"无法打开视频源: {args.source}")
        return

    # 获取视频信息
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    logger.info(f"视频信息: {width}x{height} @ {fps}FPS, 总帧数: {total_frames if total_frames > 0 else '未知(实时流)'}")
    logger.info("智能检测系统已启动，开始处理...")

    frame_count = 0
    start_time = time.time()
    last_stats_time = start_time

    # 全局标志用于优雅退出
    shutdown_requested = {"flag": False}

    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，准备退出...")
        shutdown_requested["flag"] = True

    import signal
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        while not shutdown_requested["flag"]:
            ret, frame = cap.read()
            if not ret:
                if total_frames > 0:
                    logger.info("视频文件播放完成，重新开始循环播放...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_count = 0
                    continue
                else:
                    logger.warning("视频流读取失败")
                    break

            frame_count += 1

            # 使用智能检测系统处理帧
            detection_result, processing_info = intelligent_system.process_frame(
                frame=frame,
                force_process=False,
                enable_hairnet=True,
                enable_handwash=True,
                enable_sanitize=True
            )

            # 处理检测结果
            if detection_result is not None:
                # 原有的结果处理逻辑
                person_count = len(detection_result.person_detections)
                hairnet_count = len(detection_result.hairnet_results)
                handwash_count = len(detection_result.handwash_results)
                sanitize_count = len(detection_result.sanitize_results)

                # 发布统计信息到Redis
                if redis_client_stats:
                    stats_data = {
                        "type": "stats",
                        "camera_id": camera_id,
                        "timestamp": time.time(),
                        "data": {
                            "total_frames": frame_count,
                            "processed_frames": processing_info["processed_count"],
                            "skipped_frames": processing_info["skipped_count"],
                            "detected_persons": person_count,
                            "detected_hairnets": hairnet_count,
                            "detected_handwash": handwash_count,
                            "detected_sanitize": sanitize_count,
                            "avg_fps": processing_info.get("avg_fps", 0.0),
                            "processing_mode": processing_info["processing_mode"],
                            "performance_score": processing_info.get("performance_score", 0.0)
                        }
                    }
                    publish_stats_to_redis(stats_data)

                # 记录处理信息
                if processing_info["should_process"]:
                    logger.debug(f"帧 {frame_count} 已处理: {processing_info['reason']}")
                else:
                    logger.debug(f"帧 {frame_count} 已跳过: {processing_info['reason']}")

            # 定期输出统计信息
            current_time = time.time()
            if current_time - last_stats_time >= 10.0:  # 每10秒输出一次统计
                stats = intelligent_system.get_comprehensive_stats()
                logger.info(f"检测统计 - 总帧数: {stats['detection_stats']['total_frames']}, "
                          f"处理帧数: {stats['detection_stats']['processed_frames']}, "
                          f"跳过帧数: {stats['detection_stats']['skipped_frames']}, "
                          f"平均FPS: {stats['detection_stats']['avg_fps']:.2f}, "
                          f"性能评分: {stats['detection_stats']['performance_score']:.1f}")

                last_stats_time = current_time

    except KeyboardInterrupt:
        logger.info("检测循环被用户中断")
    except Exception as e:
        logger.error(f"检测循环异常: {e}")
    finally:
        # 清理资源
        cap.release()
        intelligent_system.shutdown()

        # 输出最终统计
        final_stats = intelligent_system.get_comprehensive_stats()
        logger.info("=== 最终检测统计 ===")
        logger.info(f"总帧数: {final_stats['detection_stats']['total_frames']}")
        logger.info(f"处理帧数: {final_stats['detection_stats']['processed_frames']}")
        logger.info(f"跳过帧数: {final_stats['detection_stats']['skipped_frames']}")
        logger.info(f"处理效率: {final_stats['detection_stats']['processed_frames'] / max(final_stats['detection_stats']['total_frames'], 1) * 100:.1f}%")
        logger.info(f"平均FPS: {final_stats['detection_stats']['avg_fps']:.2f}")
        logger.info(f"性能评分: {final_stats['detection_stats']['performance_score']:.1f}")
'''

    return integration_code


if __name__ == "__main__":
    # 示例用法
    logging.basicConfig(level=logging.INFO)

    # 这里需要实际的检测管道实例
    # detection_pipeline = YourDetectionPipeline()

    # 配置参数
    config = {
        "target_fps": 15.0,
        "enable_adaptive_processing": True,
        "enable_performance_monitoring": True,
        "base_skip_rate": 3,
        "motion_threshold": 0.1,
    }

    # 创建智能检测系统
    # intelligent_system = create_intelligent_detection_system(detection_pipeline, config)

    # 运行检测循环
    # enhanced_detection_loop(0, detection_pipeline, config)  # 使用摄像头0

    print("智能检测系统集成示例已准备就绪")
    print("请参考 integration_example.py 中的代码集成到您的项目中")
