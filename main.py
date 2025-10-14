#!/usr/bin/env python3
"""
人体行为检测系统主入口文件
Human Behavior Detection System Main Entry Point

作者: AI Assistant
版本: 1.0.0
创建时间: 2024
"""

import argparse
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    import time

    from utils.gpu_acceleration import initialize_gpu_acceleration
    from utils.logger import setup_project_logger
except ImportError:
    # This is a workaround for running scripts directly from the repository root.
    # It adds the 'src' directory to the Python path.
    src_path = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_path))
    import time

    from utils.gpu_acceleration import initialize_gpu_acceleration
    from utils.logger import setup_project_logger

# GPU加速优化（在导入其他模块之前）
try:
    gpu_status = initialize_gpu_acceleration()
except (ImportError, NameError):
    gpu_status = {"device": "cpu", "gpu_available": False}


def create_argument_parser():
    """创建并配置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="人体行为检测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --mode detection --source 0                    # 使用摄像头进行检测
  python main.py --mode detection --source video.mp4           # 使用视频文件进行检测
  python main.py --mode api --port 8000                        # 启动API服务
  python main.py --mode training --config config/train.yaml    # 训练模型
        """,
    )

    # 基础参数
    parser.add_argument(
        "--mode",
        choices=["detection", "api", "training", "demo", "supervisor"],
        default="detection",
        help="运行模式 (默认: detection)",
    )
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)",
    )

    # 输入输出参数
    parser.add_argument(
        "--source", type=str, default="0", help="输入源: 摄像头索引(0,1...) 或 视频文件路径 (默认: 0)"
    )
    parser.add_argument("--output", type=str, help="输出目录路径")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="配置文件路径 (默认: config/default.yaml)",
    )
    parser.add_argument(
        "--regions-file",
        type=str,
        default="config/regions.json",
        help="区域配置文件路径 (默认: config/regions.json)",
    )

    # API服务参数
    parser.add_argument("--port", type=int, default=8000, help="API服务端口 (默认: 8000)")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="API服务主机 (默认: 0.0.0.0)"
    )

    # GPU和性能参数
    parser.add_argument("--gpu-optimize", action="store_true", help="启用GPU加速优化")
    parser.add_argument("--batch-size", type=int, help="批处理大小（自动检测最优值）")

    # 自适应相关参数
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="fast|balanced|accurate（优先级: CLI>ENV>YAML)",
    )
    parser.add_argument(
        "--device", type=str, default=None, help="cpu|cuda|mps（优先级: CLI>ENV>auto)"
    )
    parser.add_argument("--imgsz", type=int, default=None, help="YOLO 输入尺寸（覆盖配置）")
    parser.add_argument(
        "--human-weights", type=str, default=None, help="YOLO 人体检测权重路径（覆盖配置）"
    )

    # 性能优化参数
    parser.add_argument(
        "--no-window", action="store_true", help="禁用可视化窗口，仅输出统计信息（提高性能）"
    )
    parser.add_argument("--osd-minimal", action="store_true", help="最小化OSD绘制，减少可视化开销")
    parser.add_argument("--frame-skip", type=int, default=0, help="跳帧数量，0表示不跳帧（默认: 0）")
    parser.add_argument("--cascade-enable", action="store_true", help="启用级联二次检测")
    parser.add_argument("--log-interval", type=int, default=None, help="日志限流间隔（帧）")
    parser.add_argument(
        "--osd-regions", action="store_true", help="在窗口叠加显示已加载的区域多边形与名称"
    )
    parser.add_argument(
        "--camera-id", type=str, default=None, help="当前检测进程的摄像头标识（用于事件/指标打标）"
    )

    return parser


def setup_logging_and_gpu(args):
    """设置日志和GPU配置"""
    logger = setup_project_logger()
    if args.debug:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel(args.log_level)

    # 提升根日志级别，确保子模块日志可见
    try:
        import logging as _logging

        _logging.getLogger().setLevel(logger.level)
    except Exception:
        pass

    logger.info("=" * 50)
    logger.info("人体行为检测系统启动")
    logger.info(f"运行模式: {args.mode}")

    # 显示GPU状态
    if gpu_status["gpu_available"]:
        logger.info(f"🚀 GPU加速已启用: {gpu_status['device']}")
        if args.gpu_optimize:
            logger.info("⚙️  GPU优化模式已启用")
    else:
        logger.info("⚠️  GPU不可用，使用CPU模式")
        if args.gpu_optimize:
            logger.warning("⚠️  GPU优化参数已忽略（GPU不可用）")

    logger.info("=" * 50)
    return logger


def execute_mode(args, logger):
    """执行指定的运行模式"""
    mode_handlers = {
        "detection": run_detection,
        "api": run_api_server,
        "training": run_training,
        "demo": run_demo,
        "supervisor": run_supervisor,
    }

    handler = mode_handlers.get(args.mode)
    if not handler:
        logger.error(f"未知的运行模式: {args.mode}")
        sys.exit(1)

    if args.mode == "supervisor":
        try:
            handler(args, logger)
        except NameError:
            logger.error("supervisor 模式暂未实现，请稍后再试")
    else:
        handler(args, logger)


def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    logger = setup_logging_and_gpu(args)

    try:
        execute_mode(args, logger)
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("程序结束")


def load_unified_params(args, logger):
    """加载统一参数并应用CLI覆盖"""
    try:
        from config.unified_params import get_unified_params

        params = get_unified_params()
        cli_overrides = {"runtime": {}, "human_detection": {}, "cascade": {}}
        if args.imgsz:
            cli_overrides["human_detection"]["imgsz"] = int(args.imgsz)
        if args.human_weights:
            cli_overrides["human_detection"]["model_path"] = str(args.human_weights)
        if args.cascade_enable:
            cli_overrides["cascade"]["enable"] = True
        if args.log_interval is not None:
            cli_overrides["runtime"]["log_interval"] = int(args.log_interval)
        effective = params.build_effective_config(
            profile=args.profile, cli_overrides=cli_overrides
        )
        return effective
    except Exception as e:
        logger.error(f"加载/合并配置失败: {e}")
        return None


def apply_adaptive_optimizations(args, logger):
    """应用自适应性能优化"""
    try:
        from src.utils.adaptive_optimizer import apply_adaptive_optimizations

        adaptive_config = apply_adaptive_optimizations()

        # 应用自适应配置（如果用户未手动指定）
        auto_device = (args.device is None) or (str(args.device).lower() == "auto")
        auto_imgsz = (args.imgsz is None) or (str(args.imgsz).lower() == "auto")
        auto_weights = args.human_weights is None

        if auto_device:
            args.device = "cuda" if adaptive_config.get("enable_amp") else "cpu"
        if auto_imgsz:
            args.imgsz = adaptive_config.get("imgsz", 416)
        if auto_weights:
            recommended_model = adaptive_config.get("model_recommendations", {}).get(
                "human_model", "yolov8s.pt"
            )
            args.human_weights = f"models/yolo/{recommended_model}"

        logger.info(f"自适应优化已启用: {adaptive_config['description']}")
        logger.info(
            f"推荐配置 - 设备: {args.device}, 图像尺寸: {args.imgsz}, 模型: {args.human_weights}"
        )
        return True

    except Exception as e:
        logger.debug(f"自适应优化跳过: {e}")
        return False


def apply_hardware_probe_fallback(args, logger):
    """应用硬件探测回退逻辑"""
    auto_device = (args.device is None) or (str(args.device).lower() == "auto")
    auto_imgsz = (args.imgsz is None) or (str(args.imgsz).lower() == "auto")
    auto_weights = args.human_weights is None

    if auto_device or auto_imgsz or auto_weights:
        try:
            from src.utils.hardware_probe import decide_policy

            pol = decide_policy(
                preferred_profile=args.profile,
                user_device=args.device,
                user_imgsz=args.imgsz,
            )
            if auto_device:
                args.device = pol.get("device")
            if auto_imgsz:
                args.imgsz = pol.get("imgsz")
            if auto_weights and pol.get("human_weights"):
                args.human_weights = pol.get("human_weights")
            # 环境变量注入（线程数等）
            for k, v in (pol.get("env") or {}).items():
                os.environ[str(k)] = str(v)
            logger.info(f"Auto policy applied: {pol}")
        except Exception as _e:
            logger.debug(f"hardware_probe skipped: {_e}")


def select_device(args, logger):
    """选择计算设备"""
    try:
        from config.model_config import ModelConfig

        mc = ModelConfig()
        dev_req = args.device or None
        device = mc.select_device(requested=dev_req)
        logger.info(f"Device selected: {device}")
        return device
    except Exception as e:
        logger.error(f"选择设备失败: {e}")
        return "cpu"


def _run_detection_loop(args, logger, pipeline, device):
    """
    执行视频检测循环

    Args:
        args: 命令行参数
        logger: 日志记录器
        pipeline: 检测管线实例
        device: 设备类型 (cpu/cuda/mps)
    """
    import asyncio
    import signal
    from collections import defaultdict
    from datetime import datetime

    import cv2

    # 导入数据库服务
    try:
        from src.services.database_service import DatabaseService

        db_enabled = True
        logger.info("数据库服务已启用")
    except ImportError as e:
        db_enabled = False
        logger.warning(f"数据库服务未启用: {e}")

    # 全局标志用于优雅退出
    shutdown_requested = {"flag": False}

    def signal_handler(signum, frame):
        """处理退出信号"""
        logger.info(f"收到信号 {signum}，准备退出...")
        shutdown_requested["flag"] = True

    # 注册信号处理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # 打开视频源
    source = args.source
    # 尝试将源转换为整数（摄像头索引）
    try:
        source = int(source)
    except (ValueError, TypeError):
        pass  # 保持为字符串（文件路径）

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error(f"无法打开视频源: {args.source}")
        return

    # 获取视频信息
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    logger.info(
        f"视频信息: {width}x{height} @ {fps}FPS, 总帧数: {total_frames if total_frames > 0 else '未知(实时流)'}"
    )

    # 日志间隔设置（用于跳帧）
    log_interval = getattr(args, "log_interval", None) or 1
    if log_interval > 1:
        logger.info(f"启用帧跳过: 每 {log_interval} 帧处理 1 帧")

    frame_count = 0
    process_count = 0
    start_time = time.time()
    last_log_time = start_time

    # 数据库相关初始化
    db_service = None
    camera_id = getattr(args, "camera_id", "unknown")
    save_interval = int(os.getenv("DETECTION_SAVE_INTERVAL", "10"))  # 每10帧保存一次
    
    # 小时统计
    hour_stats = defaultdict(int)
    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)

    # 初始化数据库（如果启用）
    if db_enabled:
        try:
            db_service = DatabaseService()
            asyncio.run(db_service.init())
            logger.info(f"✅ 数据库服务初始化成功，每 {save_interval} 帧保存一次")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            db_service = None

    try:
        logger.info("开始视频处理循环...")

        while not shutdown_requested["flag"]:
            ret, frame = cap.read()
            if not ret:
                # 如果是视频文件，尝试循环播放
                if total_frames > 0:
                    logger.info("视频文件播放完成，重新开始循环播放...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置到第一帧
                    frame_count = 0  # 重置帧计数
                    continue
                else:
                    logger.warning("视频流读取失败")
                    break

            frame_count += 1

            # 根据 log_interval 决定是否处理这一帧
            if log_interval > 1 and frame_count % log_interval != 0:
                continue

            process_count += 1
            detection_start = time.time()

            try:
                # 使用管线进行检测
                result = pipeline.detect_comprehensive(
                    frame,
                    enable_hairnet=True,
                    enable_handwash=True,
                    enable_sanitize=True,
                )

                detection_time = time.time() - detection_start

                # 提取检测结果统计
                person_count = len(result.person_detections)
                hairnet_count = len(result.hairnet_results)
                handwash_count = len(result.handwash_results)
                sanitize_count = len(result.sanitize_results)

                # 更新小时统计
                hour_stats["frames"] += 1
                hour_stats["persons"] += person_count
                hour_stats["handwash_events"] += handwash_count
                hour_stats["sanitize_events"] += sanitize_count
                
                # 计算违规数量
                hairnet_violations = sum(
                    1 for h in result.hairnet_results if not h.get("has_hairnet", True)
                )
                hour_stats["hairnet_violations"] += hairnet_violations

                # 保存检测记录到数据库（每N帧保存一次）
                if db_service and process_count % save_interval == 0:
                    try:
                        elapsed = time.time() - start_time
                        avg_fps = process_count / elapsed if elapsed > 0 else 0

                        # 异步保存检测记录
                        record_id = asyncio.run(
                            db_service.save_detection_record(
                                camera_id=camera_id,
                                frame_number=frame_count,
                                result=result,
                                fps=avg_fps,
                            )
                        )

                        # 保存违规事件
                        for hairnet_result in result.hairnet_results:
                            if not hairnet_result.get("has_hairnet", True):
                                asyncio.run(
                                    db_service.save_violation_event(
                                        detection_id=record_id,
                                        camera_id=camera_id,
                                        violation_type="no_hairnet",
                                        track_id=hairnet_result.get("track_id"),
                                        confidence=hairnet_result.get("confidence", 0.0),
                                        bbox=hairnet_result.get("bbox"),
                                    )
                                )

                        logger.debug(f"已保存检测记录: {record_id}")

                    except Exception as e:
                        logger.error(f"保存检测记录失败: {e}")

                # 检查是否需要更新小时统计
                now = datetime.now()
                new_hour = now.replace(minute=0, second=0, microsecond=0)
                if new_hour > current_hour and db_service:
                    try:
                        # 保存上一小时的统计
                        asyncio.run(
                            db_service.update_hourly_statistics(
                                camera_id=camera_id,
                                hour_start=current_hour,
                                stats=dict(hour_stats),
                            )
                        )
                        logger.info(f"已保存小时统计: {current_hour}")

                        # 重置统计
                        hour_stats.clear()
                        current_hour = new_hour

                    except Exception as e:
                        logger.error(f"保存小时统计失败: {e}")

                # 定期打印统计信息（每10帧或每5秒）
                current_time = time.time()
                should_log = (
                    process_count % 10 == 0 or (current_time - last_log_time) >= 5.0
                )

                if should_log:
                    elapsed = current_time - start_time
                    avg_fps = process_count / elapsed if elapsed > 0 else 0
                    progress = (
                        f"{frame_count}/{total_frames}"
                        if total_frames > 0
                        else str(frame_count)
                    )

                    logger.info(
                        f"帧 {progress} | "
                        f"检测: 人={person_count}, 发网={hairnet_count}, 洗手={handwash_count}, 消毒={sanitize_count} | "
                        f"耗时: {detection_time:.3f}s | "
                        f"处理FPS: {avg_fps:.2f}"
                    )
                    last_log_time = current_time

                # 可选：保存结果到输出目录
                if args.output and result.annotated_image is not None:
                    output_dir = Path(args.output)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f"frame_{frame_count:06d}.jpg"
                    cv2.imwrite(str(output_file), result.annotated_image)

            except Exception as e:
                logger.error(f"处理第 {frame_count} 帧时出错: {e}")
                if args.debug:
                    import traceback

                    traceback.print_exc()
                continue

        # 打印最终统计
        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("检测完成统计:")
        logger.info(f"  总帧数: {frame_count}")
        logger.info(f"  处理帧数: {process_count}")
        logger.info(f"  总耗时: {total_time:.2f}s")
        logger.info(
            f"  平均处理FPS: {process_count / total_time:.2f}"
            if total_time > 0
            else "  平均处理FPS: N/A"
        )

        # 打印管线统计（如果可用）
        try:
            if hasattr(pipeline, "get_stats"):
                pipeline_stats = pipeline.get_stats()
                logger.info("  管线统计:")
                logger.info(f"    总检测次数: {pipeline_stats.get('total_detections', 0)}")
                logger.info(f"    缓存命中: {pipeline_stats.get('cache_hits', 0)}")
                logger.info(f"    缓存未命中: {pipeline_stats.get('cache_misses', 0)}")
                logger.info(
                    f"    平均处理时间: {pipeline_stats.get('avg_processing_time', 0):.3f}s"
                )
            elif hasattr(pipeline, "stats"):
                logger.info(f"  管线统计: {pipeline.stats}")
        except Exception as e:
            logger.debug(f"无法获取管线统计: {e}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("接收到键盘中断，正在退出...")

    except Exception as e:
        logger.error(f"检测循环出现异常: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()

    finally:
        # 保存最后的小时统计
        if db_service and hour_stats:
            try:
                asyncio.run(
                    db_service.update_hourly_statistics(
                        camera_id=camera_id, hour_start=current_hour, stats=dict(hour_stats)
                    )
                )
                logger.info("已保存最终小时统计")
            except Exception as e:
                logger.error(f"保存最终统计失败: {e}")

        # 关闭数据库连接
        if db_service:
            try:
                asyncio.run(db_service.close())
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}")

        # 资源清理
        logger.info("释放资源...")
        cap.release()
        cv2.destroyAllWindows()
        logger.info("资源释放完成")


def run_detection(args, logger):
    """运行检测模式"""
    logger.info(f"开始检测，输入源: {args.source}")

    # 1) 加载统一参数并应用 profiles/CLI 覆盖
    effective = load_unified_params(args, logger)
    if not effective:
        return

    # 2) 统一设备选择（结合硬件自适应）
    # 新增：自适应性能优化
    if not apply_adaptive_optimizations(args, logger):
        # 回退到原有的硬件探测逻辑
        apply_hardware_probe_fallback(args, logger)

    device = select_device(args, logger)

    # 3) 输出配置摘要
    hd = effective.get("human_detection", {})
    imgsz = hd.get("imgsz", None)
    weights = hd.get("model_path", None)
    prof = effective.get("inference", {}).get("profile", "fast")
    logger.info(
        f"配置摘要: device={device}, profile={prof}, imgsz={imgsz}, weights={weights}"
    )

    # 4) 构建"优化综合管线"并运行（启用 YOLO 人体与可选级联）
    try:
        # 将合并后的关键人检参数回填到全局配置，确保 HumanDetector 读取到
        from config.unified_params import update_global_param

        for k in [
            "model_path",
            "confidence_threshold",
            "iou_threshold",
            "min_box_area",
            "max_box_ratio",
            "min_width",
            "min_height",
            "nms_threshold",
            "max_detections",
            "device",
        ]:
            if k in hd:
                update_global_param("human_detection", k, hd[k])

        # 初始化检测器和管线
        from src.core.behavior import BehaviorRecognizer
        from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
        from src.detection.detector import HumanDetector
        from src.detection.pose_detector import PoseDetectorFactory
        from src.detection.yolo_hairnet_detector import YOLOHairnetDetector

        # 权重文件存在性检查与回退
        wpath = Path(weights) if weights else None
        if not (wpath and wpath.exists()):
            alt = Path("models/yolo/yolov8n.pt")
            logger.warning(f"指定权重不存在: {weights}，回退到 {alt}")
            weights = str(alt)
            update_global_param("human_detection", "model_path", weights)

        human_detector = HumanDetector(model_path=weights, device=device)

        # 根据配置和设备选择姿态检测后端
        from config.unified_params import get_unified_params

        params = get_unified_params()

        # 优先使用配置中的后端设置，如果配置为auto则根据设备选择
        pose_backend = params.pose_detection.backend
        if pose_backend == "auto":
            # 自动选择：CUDA设备优先使用YOLOv8，CPU设备使用MediaPipe
            pose_backend = "yolov8" if str(device).lower() == "cuda" else "mediapipe"

        pose_detector = PoseDetectorFactory.create(
            backend=pose_backend,
            device=params.pose_detection.device
            if params.pose_detection.device != "auto"
            else device,
        )
        logger.info(f"姿态检测器后端: {pose_backend}, 设备: {device}")

        behavior_recognizer = BehaviorRecognizer()
        hairnet_detector = YOLOHairnetDetector(device=device)
        cascade_cfg = effective.get("cascade", {})

        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            hairnet_detector=hairnet_detector,
            behavior_recognizer=behavior_recognizer,
            pose_detector=pose_detector,
            enable_cache=True,
            cache_size=50,
            cache_ttl=20.0,
            cascade_config=cascade_cfg,
        )

        logger.info("检测管线初始化完成，开始处理...")

        # 实现视频处理循环
        _run_detection_loop(args, logger, pipeline, device)

    except Exception as e:
        logger.error(f"检测过程中出现错误: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


def run_api_server(args, logger):
    """
    运行API服务器
    """
    logger.info(f"启动API服务器: {args.host}:{args.port}")

    try:
        # 预先打印一次设备选择结果（实际模型在应用生命周期内初始化）
        try:
            from config.model_config import ModelConfig as _MC

            dev_preview = _MC().select_device(requested=(args.device or None))
            logger.info(f"Device selected (preview): {dev_preview}")
        except Exception:
            pass

        import uvicorn

        # 使用字符串路径启动 FastAPI 应用，避免直接导入
        uvicorn.run(
            "src.api.app:app",
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),  # uvicorn 期望小写日志级别
            reload=args.debug,  # 在调试模式下启用热重载
        )
    except ImportError as e:
        logger.error(f"无法导入API模块或uvicorn: {e}")
        logger.info("请确保已安装uvicorn: pip install uvicorn")


def run_supervisor(args, logger):
    """托管 cameras.yaml 中的所有摄像头检测进程。"""
    try:
        from src.services.process_manager import get_process_manager
    except Exception as e:
        logger.error(f"无法导入进程管理器: {e}")
        return
    pm = get_process_manager()
    res = pm.start_all()
    logger.info(f"Supervisor started cameras: {res}")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("收到中断信号，准备停止所有摄像头...")
        pm.stop_all()
        logger.info("已停止全部摄像头进程。")


def run_training(args, logger):
    """
    运行训练模式
    """
    logger.info(f"开始训练，配置文件: {args.config}")

    # TODO: 实现训练逻辑
    logger.info("训练模式暂未实现，请等待后续版本")


def run_demo(args, logger):
    """
    运行演示模式
    """
    logger.info("启动演示模式")

    # TODO: 实现演示逻辑
    logger.info("演示模式暂未实现，请等待后续版本")


if __name__ == "__main__":
    main()
