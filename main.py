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

import json
import time

import cv2

from config import Settings
from utils.logger import setup_project_logger

# GPU加速优化（在导入其他模块之前）
try:
    from utils.gpu_acceleration import initialize_gpu_acceleration

    gpu_status = initialize_gpu_acceleration()
except ImportError:
    gpu_status = {"device": "cpu", "gpu_available": False}


def main():
    """
    主函数
    """
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

    parser.add_argument(
        "--mode",
        choices=["detection", "api", "training", "demo", "supervisor"],
        default="detection",
        help="运行模式 (默认: detection)",
    )

    parser.add_argument(
        "--gpu-optimize",
        action="store_true",
        help="启用GPU加速优化",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        help="批处理大小（自动检测最优值）",
    )

    parser.add_argument(
        "--source", type=str, default="0", help="输入源: 摄像头索引(0,1...) 或 视频文件路径 (默认: 0)"
    )

    parser.add_argument(
        "--regions-file",
        type=str,
        default="config/regions.json",
        help="区域配置文件路径 (默认: config/regions.json)",
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="配置文件路径 (默认: config/default.yaml)",
    )

    parser.add_argument("--output", type=str, help="输出目录路径")

    parser.add_argument("--port", type=int, default=8000, help="API服务端口 (默认: 8000)")

    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="API服务主机 (默认: 0.0.0.0)"
    )

    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)",
    )

    # 自适应相关 CLI
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

    # 性能优化相关 CLI
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

    args = parser.parse_args()

    # 设置日志
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

    try:
        if args.mode == "detection":
            run_detection(args, logger)
        elif args.mode == "api":
            run_api_server(args, logger)
        elif args.mode == "training":
            run_training(args, logger)
        elif args.mode == "demo":
            run_demo(args, logger)
        elif args.mode == "supervisor":
            try:
                run_supervisor(args, logger)
            except NameError:
                logger.error("supervisor 模式暂未实现，请稍后再试")
        else:
            logger.error(f"未知的运行模式: {args.mode}")
            sys.exit(1)

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


def run_detection(args, logger):
    """
    运行检测模式
    """
    logger.info(f"开始检测，输入源: {args.source}")

    # 1) 加载统一参数并应用 profiles/CLI 覆盖
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
    except Exception as e:
        logger.error(f"加载/合并配置失败: {e}")
        return

    # 2) 统一设备选择（结合硬件自适应）
    try:
        # 新增：自适应性能优化
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
                recommended_model = adaptive_config.get(
                    "model_recommendations", {}
                ).get("human_model", "yolov8s.pt")
                args.human_weights = f"models/yolo/{recommended_model}"

            logger.info(f"自适应优化已启用: {adaptive_config['description']}")
            logger.info(
                f"推荐配置 - 设备: {args.device}, 图像尺寸: {args.imgsz}, 模型: {args.human_weights}"
            )

        except Exception as e:
            logger.debug(f"自适应优化跳过: {e}")
            # 回退到原有的硬件探测逻辑
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
        from config.model_config import ModelConfig

        mc = ModelConfig()
        dev_req = args.device or None
        device = mc.select_device(requested=dev_req)
        logger.info(f"Device selected: {device}")
    except Exception as e:
        logger.error(f"选择设备失败: {e}")
        device = "cpu"

    # 3) 输出配置摘要
    hd = effective.get("human_detection", {})
    imgsz = hd.get("imgsz", None)
    weights = hd.get("model_path", None)
    prof = effective.get("inference", {}).get("profile", "fast")
    logger.info(
        f"配置摘要: device={device}, profile={prof}, imgsz={imgsz}, weights={weights}"
    )

    # 4) 构建“优化综合管线”并运行（启用 YOLO 人体与可选级联）
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

        from src.core.behavior import BehaviorRecognizer
        from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline
        from src.core.region import RegionManager
        from src.core.tracker import MultiObjectTracker
        from src.detection.detector import HumanDetector
        from src.detection.pose_detector import PoseDetectorFactory
        from src.detection.yolo_hairnet_detector import YOLOHairnetDetector
        from src.services.capture_service import CaptureService
        from src.services.process_engine import (  # 记录用（默认关闭）
            Event,
            ProcessConfig,
            ProcessEngine,
        )
        from src.services.region_service import initialize_region_service

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

        # 初始化流程引擎（record-only），默认关闭，由配置 process.enable 控制
        proc_cfg_src = effective.get("process", {}) or {}
        proc_cfg = ProcessConfig(
            enable=bool(proc_cfg_src.get("enable", False)),
            min_dwell_seconds_stand=float(
                (proc_cfg_src.get("min_dwell_seconds", {}) or {}).get("stand", 3)
            ),
            min_dwell_seconds_sink=float(
                (proc_cfg_src.get("min_dwell_seconds", {}) or {}).get("sink", 3)
            ),
            min_dwell_seconds_dryer=float(
                (proc_cfg_src.get("min_dwell_seconds", {}) or {}).get("dryer", 3)
            ),
            cooldown_seconds=float(proc_cfg_src.get("cooldown_seconds", 10)),
            region_entrance=str(
                (proc_cfg_src.get("region_names", {}) or {}).get("entrance", "入口线")
            ),
            region_stand=str(
                (proc_cfg_src.get("region_names", {}) or {}).get("stand", "洗手站立区域")
            ),
            region_sink=str(
                (proc_cfg_src.get("region_names", {}) or {}).get("sink", "洗手池区域")
            ),
            region_dryer=str(
                (proc_cfg_src.get("region_names", {}) or {}).get("dryer", "烘干区域")
            ),
            region_work=str(
                (proc_cfg_src.get("region_names", {}) or {}).get("work", "工作区区域")
            ),
            handwash_min_consecutive=int(
                proc_cfg_src.get("handwash_min_consecutive", 3)
            ),
        )
        process_engine = ProcessEngine(proc_cfg)
        events_path = Path("logs/events_record.jsonl")
        events_path.parent.mkdir(parents=True, exist_ok=True)

        # 抓拍服务与帧环形缓冲
        cap_cfg = effective.get("capture", {}) or {}
        capture = CaptureService(
            output_dir="output/captures",
            pre_seconds=2.0,
            post_seconds=0.0,
            clip_fps=25.0,
            anonymize_head=bool(cap_cfg.get("anonymize_head", False)),
            anonymize_ratio=float(cap_cfg.get("anonymize_ratio", 0.4)),
            blur_kernel=int(cap_cfg.get("blur_kernel", 31)),
        )
        frame_buffer_maxlen = 200  # 约等于 8s@25fps；pre_seconds=2 够用
        frame_buffer: list = []  # 退化实现；保持简单

        # 初始化区域服务（检测模式）
        try:
            # 统一来源：优先 CLI --regions-file，其次环境变量 HBD_REGIONS_FILE，最后严格模式使用默认 config/regions.json
            regions_file = args.regions_file or str(
                os.environ.get("HBD_REGIONS_FILE") or ""
            )
            if not regions_file:
                regions_file = "config/regions.json"
            if not Path(regions_file).exists():
                logger.error(f"区域文件不存在: {regions_file}")
                return
            initialize_region_service(regions_file)
            logger.info(f"Regions config initialized: {regions_file}")
        except Exception as e:
            logger.warning(f"Initialize regions failed: {e}")

        # 打开输入源
        src_str = str(args.source)
        if src_str.isdigit():
            cam_index = int(src_str)
            cap = cv2.VideoCapture(cam_index, cv2.CAP_AVFOUNDATION)
            if not cap or not cap.isOpened():
                cap = cv2.VideoCapture(cam_index)
            if not cap or not cap.isOpened():
                logger.error("无法打开摄像头")
                return
        else:
            if not Path(src_str).exists():
                # 允许 RTSP/网络流（非本地文件）
                if not src_str.lower().startswith("rtsp://"):
                    logger.error(f"视频文件不存在: {src_str}")
                    return
            cap = cv2.VideoCapture(src_str)
            if not cap or not cap.isOpened():
                if src_str.lower().startswith("rtsp://"):
                    logger.warning(f"RTSP 打开失败，稍后重试: {src_str}")
                else:
                    logger.error(f"无法打开视频文件: {src_str}")
                    return

        # RTSP 重连配置
        is_rtsp_source = (not src_str.isdigit()) and src_str.lower().startswith(
            "rtsp://"
        )
        backoff_seconds = 1.0
        backoff_max = 30.0

        def _reconnect_rtsp() -> bool:
            nonlocal cap, backoff_seconds
            try:
                if cap:
                    try:
                        cap.release()
                    except Exception:
                        pass
                logger.warning(f"尝试重连 RTSP 源（等待 {backoff_seconds:.1f}s）: {src_str}")
            except Exception:
                pass
            try:
                time.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2.0, backoff_max)
                cap = cv2.VideoCapture(src_str)
                if cap and cap.isOpened():
                    logger.info("RTSP 重连成功")
                    backoff_seconds = 1.0
                    return True
                return False
            except Exception:
                return False

        # 保存源帧率（若可获取）
        try:
            src_fps = cap.get(cv2.CAP_PROP_FPS)
            Path("logs").mkdir(parents=True, exist_ok=True)
            with open("logs/source_fps.txt", "w", encoding="utf-8") as _f:
                _f.write(str(src_fps))
            logger.info(f"Source FPS saved: {src_fps}")
        except Exception:
            pass

        # 运行循环（简单可视化）
        frame_idx = 0
        # 日志间隔控制 - CLI参数优先级最高
        log_iv = (
            args.log_interval
            if args.log_interval is not None
            else int(effective.get("runtime", {}).get("log_interval", 120) or 0)
        )

        # 性能模式：减少日志频率
        if args.no_window and log_iv == 0:
            log_iv = 60  # 无窗口模式默认60帧间隔日志
        # 多目标跟踪器（替代简易最近邻）
        mot = MultiObjectTracker(
            max_disappeared=15,
            iou_threshold=0.3,
            dist_threshold=120.0,
            match_strategy="hungarian",
            iou_weight=0.6,
            recycle_ids=True,
            force_revival=True,
        )
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    if is_rtsp_source:
                        # 尝试指数退避重连，直到成功为止
                        while True:
                            if _reconnect_rtsp():
                                ok, frame = cap.read()
                                if ok:
                                    break
                            else:
                                # 继续指数退避
                                continue
                    else:
                        # 本地文件/摄像头：读帧失败则退出
                        break
                frame_idx += 1

                # 保存首帧原始图像
                try:
                    if frame_idx == 1:
                        Path("logs").mkdir(parents=True, exist_ok=True)
                        cv2.imwrite("logs/first_frame.jpg", frame)
                        logger.info("Saved first frame to logs/first_frame.jpg")
                except Exception:
                    pass

                now_ts = time.time()
                # 维护简易帧缓冲（时间戳, frame）
                try:
                    frame_buffer.append((now_ts, frame.copy()))
                    if len(frame_buffer) > frame_buffer_maxlen:
                        frame_buffer = frame_buffer[-frame_buffer_maxlen:]
                except Exception:
                    pass

                # 根据CLI参数控制检测和可视化行为
                result = pipeline.detect_comprehensive(
                    frame,
                    enable_hairnet=True,
                    enable_handwash=True,
                    enable_sanitize=False,
                    # 可考虑未来添加: osd_minimal=args.osd_minimal
                )

                annotated = (
                    result.annotated_image
                    if result.annotated_image is not None
                    else frame
                )

                # 实时区域叠加与首次覆盖图保存（不依赖流程引擎开关）
                try:
                    from src.services.region_service import get_region_manager_for_frame

                    fh, fw = frame.shape[:2]
                    _rm = get_region_manager_for_frame(fw, fh)
                    if _rm is not None:
                        # 首次打印区域摘要
                        if not globals().get("_regions_logged_always", False):
                            _names = []
                            try:
                                for _rid, _r in _rm.regions.items():
                                    _names.append(_r.name or _rid)
                            except Exception:
                                pass
                            logger.info(
                                f"[OSD] Regions loaded: count={len(getattr(_rm,'regions',{}))} names={_names}"
                            )
                            globals()["_regions_logged_always"] = True
                        # 首帧覆盖图（使用原始帧尺寸坐标系）
                        if frame_idx == 1 and not globals().get(
                            "_overlay_first_saved", False
                        ):
                            import cv2 as _cv2
                            import numpy as _np

                            _overlay = frame.copy()
                            for _rid, _r in _rm.regions.items():
                                _pts = _np.array(
                                    [(int(px), int(py)) for (px, py) in _r.polygon],
                                    dtype=_np.int32,
                                )
                                _cv2.polylines(
                                    _overlay,
                                    [_pts],
                                    isClosed=True,
                                    color=(0, 255, 0),
                                    thickness=2,
                                )
                                if len(_pts) > 0:
                                    _cv2.putText(
                                        _overlay,
                                        (_r.name or _rid),
                                        (int(_pts[0][0]), int(_pts[0][1]) - 5),
                                        _cv2.FONT_HERSHEY_SIMPLEX,
                                        0.6,
                                        (0, 255, 0),
                                        2,
                                    )
                            Path("logs").mkdir(parents=True, exist_ok=True)
                            _cv2.imwrite("logs/overlay_first_frame.jpg", _overlay)
                            globals()["_overlay_first_saved"] = True
                            logger.info("Saved overlay_first_frame.jpg")
                        # 在窗口叠加（若 annotated 与 frame 尺寸不同，则按比例缩放坐标）
                        if args.osd_regions:
                            import numpy as _np

                            ah, aw = annotated.shape[:2]
                            sx = (float(aw) / float(fw)) if fw > 0 else 1.0
                            sy = (float(ah) / float(fh)) if fh > 0 else 1.0
                            for _rid, _r in _rm.regions.items():
                                _pts = _np.array(
                                    [
                                        (int(px * sx), int(py * sy))
                                        for (px, py) in _r.polygon
                                    ],
                                    dtype=_np.int32,
                                )
                                cv2.polylines(
                                    annotated,
                                    [_pts],
                                    isClosed=True,
                                    color=(0, 255, 0),
                                    thickness=2,
                                )
                                if len(_pts) > 0:
                                    cv2.putText(
                                        annotated,
                                        (_r.name or _rid),
                                        (int(_pts[0][0]), int(_pts[0][1]) - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.6,
                                        (0, 255, 0),
                                        2,
                                    )
                    # 将区域管理器挂到全局供后续使用
                    globals()["region_manager"] = _rm
                except Exception as _e:
                    logger.debug(f"OSD region overlay skip: {_e}")

                # record-only：若启用，则记录事件到 jsonl，不做抓拍
                if process_engine.cfg.enable:
                    # 区域管理器：按需初始化一次并缩放到当前帧尺寸
                    # 统一入口（带热更新/缓存）：取映射后的 RegionManager
                    # record-only 分支内的区域加载逻辑已上移，此处仅依赖全局 region_manager

                    # 保存一次区域覆盖叠加图（首帧）
                    try:
                        if not globals().get("_overlay_saved", False):
                            rm = globals().get("region_manager")
                            if rm is not None:
                                import cv2 as _cv2
                                import numpy as _np

                                overlay = annotated.copy()
                                for _rid, _r in rm.regions.items():
                                    pts = _np.array(
                                        [(int(px), int(py)) for (px, py) in _r.polygon],
                                        dtype=_np.int32,
                                    )
                                    color = (0, 255, 0)
                                    _cv2.polylines(
                                        overlay,
                                        [pts],
                                        isClosed=True,
                                        color=color,
                                        thickness=2,
                                    )
                                    if len(pts) > 0:
                                        _cv2.putText(
                                            overlay,
                                            (_r.name or _rid),
                                            (int(pts[0][0]), int(pts[0][1]) - 5),
                                            _cv2.FONT_HERSHEY_SIMPLEX,
                                            0.6,
                                            color,
                                            2,
                                        )
                                Path("logs").mkdir(parents=True, exist_ok=True)
                                _cv2.imwrite("logs/overlay_debug.jpg", overlay)
                                globals()["_overlay_saved"] = True
                                logger.info(
                                    "Saved region overlay to logs/overlay_debug.jpg"
                                )
                    except Exception:
                        pass

                    # 按需在窗口叠加绘制区域（annotated 需要按比例缩放显示）
                    try:
                        if args.osd_regions:
                            rm = globals().get("region_manager")
                            if rm is not None:
                                import numpy as _np

                                ah, aw = annotated.shape[:2]
                                fh2, fw2 = frame.shape[:2]
                                sx = (float(aw) / float(fw2)) if fw2 > 0 else 1.0
                                sy = (float(ah) / float(fh2)) if fh2 > 0 else 1.0
                                for _rid, _r in rm.regions.items():
                                    pts = _np.array(
                                        [
                                            (int(px * sx), int(py * sy))
                                            for (px, py) in _r.polygon
                                        ],
                                        dtype=_np.int32,
                                    )
                                    cv2.polylines(
                                        annotated,
                                        [pts],
                                        isClosed=True,
                                        color=(0, 255, 0),
                                        thickness=2,
                                    )
                                    if len(pts) > 0:
                                        cv2.putText(
                                            annotated,
                                            (_r.name or _rid),
                                            (int(pts[0][0]), int(pts[0][1]) - 5),
                                            cv2.FONT_HERSHEY_SIMPLEX,
                                            0.6,
                                            (0, 255, 0),
                                            2,
                                        )
                    except Exception:
                        pass

                    # 最小 UOD：附加区域名称
                    uod_persons = []

                    # 简单BBox重叠
                    def _bbox_overlap(b1, b2, thr: float = 0.1) -> bool:
                        if not b1 or not b2:
                            return False
                        x11, y11, x12, y12 = map(float, b1)
                        x21, y21, x22, y22 = map(float, b2)
                        ix1 = max(x11, x21)
                        iy1 = max(y11, y21)
                        ix2 = min(x12, x22)
                        iy2 = min(y12, y22)
                        if ix2 <= ix1 or iy2 <= iy1:
                            return False
                        inter = (ix2 - ix1) * (iy2 - iy1)
                        a1 = max(1.0, (x12 - x11) * (y12 - y11))
                        return inter / a1 >= float(thr)

                    try:
                        person_dets = getattr(result, "person_detections", []) or []
                        hairnet_results = getattr(result, "hairnet_results", []) or []
                        # 构造用于跟踪器的输入
                        dets_for_track = []
                        for det in person_dets:
                            bbox = det.get("bbox") or det.get("box") or det.get("xyxy")
                            conf = float(det.get("confidence", det.get("score", 0.0)))
                            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                                dets_for_track.append(
                                    {
                                        "bbox": [
                                            int(bbox[0]),
                                            int(bbox[1]),
                                            int(bbox[2]),
                                            int(bbox[3]),
                                        ],
                                        "confidence": conf,
                                    }
                                )
                        tracks = mot.update(dets_for_track)
                        # 生成 UOD 并附加区域与发网
                        # 预取洗手池区域（按名称匹配）
                        sink_region_obj = None
                        try:
                            _rm_ref = globals().get("region_manager")
                            if _rm_ref is not None:
                                for _rid, _r in _rm_ref.regions.items():
                                    if (
                                        _r.name or _rid
                                    ) == process_engine.cfg.region_sink:
                                        sink_region_obj = _r
                                        break
                        except Exception:
                            sink_region_obj = None
                        from src.core.schemas import UODPerson

                        for tr in tracks:
                            tb = tr.get("bbox")
                            tid_assigned = int(tr.get("track_id", 0))
                            region_name = None
                            try:
                                rm = globals().get("region_manager")
                                if (
                                    rm is not None
                                    and isinstance(tb, (list, tuple))
                                    and len(tb) >= 4
                                ):
                                    cur_regions = rm.update_track_regions(
                                        tid_assigned,
                                        [
                                            int(tb[0]),
                                            int(tb[1]),
                                            int(tb[2]),
                                            int(tb[3]),
                                        ],
                                    )
                                    if cur_regions:
                                        rid = cur_regions[0]
                                        region_name = (
                                            rm.regions.get(rid).name
                                            if rid in rm.regions
                                            else rid
                                        )
                            except Exception:
                                region_name = None
                            # 发网结果匹配
                            has_hairnet = False
                            try:
                                for hr in hairnet_results:
                                    pb = hr.get("person_bbox") or hr.get("bbox")
                                    if _bbox_overlap(
                                        [
                                            int(tb[0]),
                                            int(tb[1]),
                                            int(tb[2]),
                                            int(tb[3]),
                                        ],
                                        pb,
                                        thr=0.1,
                                    ):
                                        has_hairnet = bool(hr.get("has_hairnet", False))
                                        break
                            except Exception:
                                has_hairnet = False
                            # 手部关键点落入“洗手水池”区域判定（使用关键点而非手框中心）
                            hand_in_sink = False
                            try:
                                if sink_region_obj is not None:
                                    hand_regions = pipeline.get_hand_regions_for_person(
                                        frame,
                                        [
                                            int(tb[0]),
                                            int(tb[1]),
                                            int(tb[2]),
                                            int(tb[3]),
                                        ],
                                    )
                                    if hand_regions:
                                        h_img, w_img = frame.shape[:2]
                                        pts_inside = 0
                                        pts_total = 0
                                        for hres in hand_regions:
                                            lms = hres.get("landmarks")
                                            if not lms:
                                                continue
                                            for lm in lms:
                                                px = int(
                                                    float(lm.get("x", 0.0))
                                                    * float(w_img)
                                                )
                                                py = int(
                                                    float(lm.get("y", 0.0))
                                                    * float(h_img)
                                                )
                                                pts_total += 1
                                                try:
                                                    if sink_region_obj.point_in_region(
                                                        (px, py)
                                                    ):
                                                        pts_inside += 1
                                                except Exception:
                                                    pass
                                        if pts_total > 0:
                                            ratio = float(pts_inside) / float(pts_total)
                                            hand_in_sink = (pts_inside >= 3) and (
                                                ratio >= 0.2
                                            )
                            except Exception:
                                hand_in_sink = False
                            uod = UODPerson(
                                track_id=tid_assigned,
                                bbox=[int(tb[0]), int(tb[1]), int(tb[2]), int(tb[3])],
                                confidence=float(tr.get("confidence", 0.0)),
                                has_hairnet=has_hairnet,
                                region=region_name,
                                hand_in_sink=hand_in_sink,
                                ts=time.time(),
                            )
                            uod_persons.append(uod.to_dict())
                    except Exception:
                        uod_persons = []

                    # 调试：逐帧打印 track 与 region（前若干帧），便于排查区域命中
                    try:
                        if frame_idx <= 240:
                            for _p in uod_persons:
                                logger.info(
                                    f"track={_p['track_id']} region={_p.get('region')} bbox={_p.get('bbox')} hairnet={_p.get('has_hairnet')}"
                                )
                    except Exception:
                        pass
                    events = process_engine.step(uod_persons)
                    if events:
                        with events_path.open("a", encoding="utf-8") as f:
                            for ev in events:
                                f.write(
                                    json.dumps(
                                        {
                                            "type": ev.type,
                                            "track_id": ev.track_id,
                                            "ts": ev.ts,
                                            "evidence": ev.evidence,
                                            "camera_id": (args.camera_id or None),
                                        },
                                        ensure_ascii=False,
                                    )
                                    + "\n"
                                )
                                # 抓拍输出
                                try:
                                    # 查找相同 track_id 的上下文
                                    ctx = {}
                                    for _p in uod_persons:
                                        if int(_p.get("track_id", -1)) == int(
                                            ev.track_id
                                        ):
                                            ctx = {
                                                "region": _p.get("region"),
                                                "has_hairnet": _p.get("has_hairnet"),
                                                "bbox": _p.get("bbox"),
                                                "type": ev.type,
                                                "track_id": ev.track_id,
                                                "ts": ev.ts,
                                                "evidence": ev.evidence,
                                                "camera_id": (args.camera_id or None),
                                            }
                                            break
                                    # 使用 annotated 以便有可视叠加；若为 None 则使用原帧
                                    frame_for_save = (
                                        annotated if annotated is not None else frame
                                    )
                                    # 传入帧缓冲（转换为 deque 以符合类型）
                                    from collections import deque

                                    _buf = deque(
                                        frame_buffer, maxlen=frame_buffer_maxlen
                                    )
                                    capture.save_event(ev, frame_for_save, ctx, _buf)
                                except Exception:
                                    pass

                if log_iv and frame_idx % log_iv == 0:
                    cs = pipeline.cascade_stats
                    logger.info(
                        f"进度帧={frame_idx} 级联: 触发={cs.get('triggers',0)} 细化={cs.get('refined',0)} 耗时累计={cs.get('time_total',0.0):.3f}s"
                    )
                    # 打印当前帧 track 与 region 概要
                    try:
                        # 按区域分组统计 - 降到DEBUG级别减少日志开销
                        if logger.isEnabledFor(_logging.DEBUG):
                            by_region = {}
                            for _p in uod_persons:
                                rn = _p.get("region") or "None"
                                by_region[rn] = by_region.get(rn, 0) + 1
                            logger.debug(f"活跃目标={len(uod_persons)} 分布={by_region}")
                    except Exception:
                        pass

                # 展示窗口（放在绘制之后）- 可选择禁用以提高性能
                if not args.no_window:
                    cv2.imshow("HBD - Main", annotated)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q") or key == 27:  # 'q' 或 ESC 键退出
                        break

                    # 检查窗口是否被用户关闭（点击X按钮）
                    try:
                        if (
                            cv2.getWindowProperty("HBD - Main", cv2.WND_PROP_VISIBLE)
                            < 1
                        ):
                            logger.info("检测到窗口被关闭，正在退出...")
                            break
                    except cv2.error:
                        # 窗口已被销毁
                        logger.info("窗口已被销毁，正在退出...")
                        break
                else:
                    # 无窗口模式，检查键盘中断
                    import msvcrt

                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b"q":
                            break
        finally:
            cap.release()
            cv2.destroyAllWindows()
    except Exception as e:
        logger.error(f"主入口综合管线运行失败: {e}")
        return


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

        # 直接导入 FastAPI app 实例
        from api.app import app as fastapi_app

        uvicorn.run(
            fastapi_app,
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
