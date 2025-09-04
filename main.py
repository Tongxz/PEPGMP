#!/usr/bin/env python3
"""
人体行为检测系统主入口文件
Human Behavior Detection System Main Entry Point

作者: AI Assistant
版本: 1.0.0
创建时间: 2024
"""

import argparse
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from config import Settings
from utils.logger import setup_project_logger
import cv2
import time


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
  python main.py --mode api --port 5000                        # 启动API服务
  python main.py --mode training --config config/train.yaml    # 训练模型
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["detection", "api", "training", "demo"],
        default="detection",
        help="运行模式 (默认: detection)",
    )

    parser.add_argument(
        "--source", type=str, default="0", help="输入源: 摄像头索引(0,1...) 或 视频文件路径 (默认: 0)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yaml",
        help="配置文件路径 (默认: config/default.yaml)",
    )

    parser.add_argument("--output", type=str, help="输出目录路径")

    parser.add_argument("--port", type=int, default=5000, help="API服务端口 (默认: 5000)")

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
    parser.add_argument("--profile", type=str, default=None, help="fast|balanced|accurate（优先级: CLI>ENV>YAML)")
    parser.add_argument("--device", type=str, default=None, help="cpu|cuda|mps（优先级: CLI>ENV>auto)")
    parser.add_argument("--imgsz", type=int, default=None, help="YOLO 输入尺寸（覆盖配置）")
    parser.add_argument("--human-weights", type=str, default=None, help="YOLO 人体检测权重路径（覆盖配置）")
    parser.add_argument("--cascade-enable", action="store_true", help="启用级联二次检测")
    parser.add_argument("--log-interval", type=int, default=None, help="日志限流间隔（帧）")

    args = parser.parse_args()

    # 设置日志
    logger = setup_project_logger()
    if args.debug:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel(args.log_level)

    logger.info("=" * 50)
    logger.info("人体行为检测系统启动")
    logger.info(f"运行模式: {args.mode}")
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
        effective = params.build_effective_config(profile=args.profile, cli_overrides=cli_overrides)
    except Exception as e:
        logger.error(f"加载/合并配置失败: {e}")
        return

    # 2) 统一设备选择
    try:
        from config.model_config import ModelConfig
        mc = ModelConfig()
        # 如 CLI 指定 device 覆盖
        dev_req = (args.device or None)
        device = mc.select_device(requested=dev_req)
    except Exception as e:
        logger.error(f"选择设备失败: {e}")
        device = "cpu"

    # 3) 输出配置摘要
    hd = effective.get("human_detection", {})
    imgsz = hd.get("imgsz", None)
    weights = hd.get("model_path", None)
    prof = effective.get("inference", {}).get("profile", "fast")
    logger.info(f"配置摘要: device={device}, profile={prof}, imgsz={imgsz}, weights={weights}")

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
        from src.core.detector import HumanDetector
        from src.core.pose_detector import PoseDetectorFactory
        from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline

        # 权重文件存在性检查与回退
        wpath = Path(weights) if weights else None
        if not (wpath and wpath.exists()):
            alt = Path("models/yolo/yolov8n.pt")
            logger.warning(f"指定权重不存在: {weights}，回退到 {alt}")
            weights = str(alt)
            update_global_param("human_detection", "model_path", weights)

        human_detector = HumanDetector(model_path=weights, device=device)
        pose_detector = PoseDetectorFactory.create(backend="mediapipe")
        behavior_recognizer = BehaviorRecognizer()
        cascade_cfg = effective.get("cascade", {})

        pipeline = OptimizedDetectionPipeline(
            human_detector=human_detector,
            hairnet_detector=None,
            behavior_recognizer=behavior_recognizer,
            pose_detector=pose_detector,
            enable_cache=True,
            cache_size=50,
            cache_ttl=20.0,
            cascade_config=cascade_cfg,
        )

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
                logger.error(f"视频文件不存在: {src_str}")
                return
            cap = cv2.VideoCapture(src_str)
            if not cap or not cap.isOpened():
                logger.error(f"无法打开视频文件: {src_str}")
                return

        # 运行循环（简单可视化）
        frame_idx = 0
        log_iv = int(effective.get("runtime", {}).get("log_interval", 120) or 0)
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_idx += 1

                result = pipeline.detect_comprehensive(
                    frame, enable_hairnet=False, enable_handwash=True, enable_sanitize=False
                )

                annotated = result.annotated_image if result.annotated_image is not None else frame
                cv2.imshow("HBD - Main", annotated)

                if log_iv and frame_idx % log_iv == 0:
                    cs = pipeline.cascade_stats
                    logger.info(
                        f"进度帧={frame_idx} 级联: 触发={cs.get('triggers',0)} 细化={cs.get('refined',0)} 耗时累计={cs.get('time_total',0.0):.3f}s"
                    )

                if cv2.waitKey(1) & 0xFF == ord('q'):
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
