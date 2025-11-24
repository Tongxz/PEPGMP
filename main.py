#!/usr/bin/env python3
"""
人体行为检测系统主入口文件
Human Behavior Detection System Main Entry Point

作者: AI Assistant
版本: 1.0.0
创建时间: 2025
"""

import argparse
import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    import time

    from utils.logger import setup_project_logger
except ImportError:
    # This is a workaround for running scripts directly from the repository root.
    # It adds the 'src' directory to the Python path.
    src_path = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_path))
    import time

    from utils.logger import setup_project_logger

# GPU加速优化已移除，设备选择由 ModelConfig.select_device() 处理
# gpu_status 变量已不再使用，设备选择逻辑在 select_device() 函数中


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
    # 对于 API 服务需要在局域网内可访问，因此默认绑定到 0.0.0.0
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",  # nosec B104: 需要在局域网内开放访问
        help="API服务主机 (默认: 0.0.0.0)",
    )

    # GPU和性能参数
    parser.add_argument("--gpu-optimize", action="store_true", help="启用GPU加速优化")
    parser.add_argument("--batch-size", type=int, help="批处理大小（自动检测最优值）")

    # 检测保存策略参数 (智能保存)
    parser.add_argument(
        "--save-strategy",
        choices=["all", "violations_only", "interval", "smart"],
        default="smart",
        help="保存策略: all=保存所有, violations_only=仅保存违规, interval=按间隔, smart=智能保存（默认）",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=30,
        help="保存间隔（帧数），用于 all/interval 策略 (默认: 30)",
    )
    parser.add_argument(
        "--violation-threshold",
        type=float,
        default=0.5,
        help="违规严重程度阈值（0.0-1.0），低于此值的违规不保存 (默认: 0.5)",
    )
    parser.add_argument(
        "--normal-sample-interval",
        type=int,
        default=300,
        help="正常样本采样间隔（帧数），用于 smart 策略 (默认: 300)",
    )

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
    # GPU加速状态检查已移除，设备选择由 ModelConfig.select_device() 处理
    # 设备信息会在 select_device() 函数中记录
    if args.gpu_optimize:
        logger.info("⚙️  GPU优化模式已启用")

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


# 配置加载函数已移至 src/config/config_loader.py
# 使用 ConfigLoader 类的静态方法替代


def run_detection(args, logger):
    """运行检测模式 - 简化版"""
    import asyncio

    from src.application.detection_initializer import DetectionInitializer
    from src.application.detection_loop_service import DetectionLoopService
    from src.config.config_loader import ConfigLoader

    logger.info(f"开始检测，输入源: {args.source}")

    # 1. 加载配置
    effective_config = ConfigLoader.load_and_merge(args, logger)
    if not effective_config:
        return

    # 2. 应用优化
    ConfigLoader.apply_optimizations(args, logger)

    # 3. 选择设备
    device = ConfigLoader.select_device(args, logger)

    # 4. 输出配置摘要
    hd = effective_config.get("human_detection", {})
    prof = effective_config.get("inference", {}).get("profile", "fast")
    logger.info(
        f"配置摘要: device={device}, profile={prof}, "
        f"imgsz={hd.get('imgsz')}, weights={hd.get('model_path')}"
    )

    try:
        # 5. 初始化检测管线
        pipeline = DetectionInitializer.initialize_pipeline(
            args, logger, effective_config
        )

        # 6. 初始化服务
        detection_service, stream_service = DetectionInitializer.initialize_services(
            args, logger, pipeline
        )

        if not detection_service:
            logger.error("检测服务初始化失败")
            return

        # 7. 创建检测循环配置
        loop_config = DetectionInitializer.create_loop_config(args)

        # 8. 创建并运行检测循环服务
        loop_service = DetectionLoopService(
            config=loop_config,
            detection_pipeline=pipeline,
            detection_app_service=detection_service,
            video_stream_service=stream_service,
        )

        logger.info("🚀 启动检测循环")
        asyncio.run(loop_service.run())

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
