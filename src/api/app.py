#!/usr/bin/env python3
"""FastAPI应用程序入口点.

这个模块包含了FastAPI应用程序的主要配置和路由设置.
"""
import asyncio
import logging
import logging.handlers
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# 加载环境配置文件
try:
    from dotenv import load_dotenv

    # 按优先级加载配置文件
    env_file = os.getenv("ENV_FILE")  # 允许通过环境变量指定配置文件
    if env_file:
        load_dotenv(env_file, override=True)
        logging.getLogger(__name__).info(f"已加载指定配置文件: {env_file}")
    else:
        # 默认加载.env文件
        default_env = os.path.join(project_root, ".env")
        if os.path.exists(default_env):
            load_dotenv(default_env)
            logging.getLogger(__name__).info(f"已加载默认配置文件: {default_env}")

        # 加载环境特定配置
        environment = os.getenv("ENVIRONMENT", "development")
        env_specific = os.path.join(project_root, f".env.{environment}")
        if os.path.exists(env_specific):
            load_dotenv(env_specific, override=True)
            logging.getLogger(__name__).info(f"已加载环境特定配置: {env_specific}")

        # 加载测试环境配置（如果存在）
        test_env = os.path.join(project_root, ".env.test")
        if os.path.exists(test_env) and os.getenv("ENVIRONMENT", "").lower() in (
            "test",
            "testing",
        ):
            load_dotenv(test_env, override=True)
            logging.getLogger(__name__).info(f"已加载测试环境配置: {test_env}")
except ImportError:
    logging.getLogger(__name__).warning("python-dotenv未安装，无法从.env文件加载配置")

try:
    from src.api.middleware.error_middleware import setup_error_middleware
    from src.api.middleware.metrics_middleware import MetricsMiddleware
    from src.api.middleware.security_middleware import setup_security_middleware
    from src.api.redis_listener import shutdown_redis_listener, start_redis_listener
    from src.api.routers import (
        alerts,
        cameras,
        comprehensive,
        config,
        detection_config,
        download,
        error_monitoring,
        events,
        export,
        metrics,
        mlops,
        monitoring,
        records,
        region_management,
        security,
        statistics,
        system,
        video_stream,
        websocket,
    )
    from src.monitoring.advanced_monitoring import start_monitoring, stop_monitoring
    from src.services import detection_service
    from src.utils.error_monitor import start_error_monitoring, stop_error_monitoring
except ImportError:
    # Add project root to Python path
    sys.path.append(project_root)
    from src.api.middleware.error_middleware import setup_error_middleware
    from src.api.middleware.metrics_middleware import MetricsMiddleware
    from src.api.middleware.security_middleware import setup_security_middleware
    from src.api.redis_listener import shutdown_redis_listener, start_redis_listener
    from src.api.routers import (
        alerts,
        cameras,
        comprehensive,
        config,
        detection_config,
        download,
        error_monitoring,
        events,
        export,
        metrics,
        mlops,
        monitoring,
        records,
        region_management,
        security,
        statistics,
        system,
        video_stream,
        websocket,
    )
    from src.monitoring.advanced_monitoring import start_monitoring, stop_monitoring
    from src.services import detection_service
    from src.utils.error_monitor import start_error_monitoring, stop_error_monitoring

# 配置日志
logging.basicConfig(level=logging.INFO)

# 设置API日志到 logs/api/ 目录
api_log_dir = Path("logs/api")
api_log_dir.mkdir(parents=True, exist_ok=True)
api_log_file = api_log_dir / "api.log"

# 配置API日志文件处理器（使用轮转）
api_file_handler = logging.handlers.RotatingFileHandler(
    str(api_log_file),
    maxBytes=50 * 1024 * 1024,  # 50MB
    backupCount=5,  # 保留5个备份
    encoding="utf-8",
)
api_file_handler.setLevel(logging.INFO)
api_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
api_file_handler.setFormatter(api_formatter)

# 配置API错误日志文件处理器
api_error_log_file = api_log_dir / "api_error.log"
api_error_handler = logging.handlers.RotatingFileHandler(
    str(api_error_log_file),
    maxBytes=50 * 1024 * 1024,  # 50MB
    backupCount=5,  # 保留5个备份
    encoding="utf-8",
)
api_error_handler.setLevel(logging.ERROR)
api_error_handler.setFormatter(api_formatter)

# 获取根日志记录器并添加处理器
root_logger = logging.getLogger()
root_logger.addHandler(api_file_handler)
root_logger.addHandler(api_error_handler)

logger = logging.getLogger(__name__)

# 触发依赖注入容器的服务配置（包括 USE_DOMAIN_SERVICE 开关与仓储绑定）
try:
    import src.container.service_config  # noqa: F401

    logger.info("依赖注入服务配置已加载")
except Exception as e:
    # 生产环境硬约束：依赖注入容器服务配置失败必须阻断启动，禁止隐性降级。
    if os.getenv("ENVIRONMENT", "development") == "production":
        logger.error(f"依赖注入服务配置加载失败(生产必需): {e}")
        raise
    logger.warning(f"依赖注入服务配置加载失败（非生产不影响启动）: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: C901
    """应用程序生命周期管理."""
    # Startup
    logger.info("Starting up the application...")

    # 初始化数据库服务
    try:
        from src.database.connection import init_database
        from src.services.database_service import close_db_service, get_db_service

        await get_db_service()
        await init_database()
        logger.info("数据库服务已初始化")
    except Exception as e:
        logger.warning(f"数据库服务初始化失败 (非关键): {e}")

    # 初始化视频流管理器
    try:
        from src.services.video_stream_manager import init_stream_manager

        await init_stream_manager()
        logger.info("视频流管理器已初始化")
    except Exception as e:
        logger.warning(f"视频流管理器初始化失败 (非关键): {e}")

    # Initialize services (non-fatal on failure)
    try:
        detection_service.initialize_detection_services()
        app.state.optimized_pipeline = detection_service.optimized_pipeline
        app.state.hairnet_pipeline = detection_service.hairnet_pipeline
        logger.info("检测服务已初始化")
    except Exception as e:
        # 生产环境硬约束：检测服务必须成功初始化，禁止“失败但继续运行”的隐性降级。
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.error(f"检测服务初始化失败(生产必需): {e}")
            raise
        # 非生产：避免因模型缺失或环境问题导致 API 启动失败
        app.state.optimized_pipeline = None
        app.state.hairnet_pipeline = None
        logger.warning(f"检测服务初始化失败 (非生产非关键): {e}")
    # 初始化区域服务（数据库存储）
    # 如果有配置文件，自动导入到数据库
    try:
        from src.domain.services.region_service import RegionDomainService
        from src.infrastructure.repositories.postgresql_region_repository import (
            PostgreSQLRegionRepository,
        )
        from src.services.database_service import get_db_service

        db_service = await get_db_service()
        if db_service and db_service.pool:
            region_repo = PostgreSQLRegionRepository(db_service.pool)
            region_domain_service = RegionDomainService(region_repo)

            # 检查是否有配置文件需要导入
            regions_file = os.environ.get(
                "HBD_REGIONS_FILE", os.path.join(project_root, "config", "regions.json")
            )

            if os.path.exists(regions_file):
                try:
                    # 检查数据库中是否已有区域
                    existing_regions = await region_domain_service.get_all_regions(
                        active_only=False
                    )
                    if not existing_regions:
                        # 如果数据库为空，导入配置文件
                        logger.info(f"数据库中没有区域数据，从配置文件导入: {regions_file}")
                        result = await region_domain_service.import_from_file(
                            regions_file
                        )
                        logger.info(
                            f"区域导入完成: 导入={result.get('imported', 0)}, "
                            f"跳过={result.get('skipped', 0)}, "
                            f"错误={result.get('errors', 0)}"
                        )
                    else:
                        logger.info(f"数据库中已有 {len(existing_regions)} 个区域，跳过配置文件导入")
                except Exception as e:
                    logger.warning(f"从配置文件导入区域失败（非关键）: {e}")
            else:
                logger.info(f"区域配置文件不存在，跳过导入: {regions_file}")
        else:
            logger.warning("数据库连接池未初始化，无法初始化区域服务")
    except Exception as e:
        logger.warning(f"区域服务初始化失败（非关键）: {e}")

    # 初始化旧的RegionManager（用于向后兼容旧的get_region_service依赖）
    try:
        from src.services.region_service import initialize_region_service

        regions_file = os.environ.get(
            "HBD_REGIONS_FILE", os.path.join(project_root, "config", "regions.json")
        )
        initialize_region_service(regions_file)
        logger.info("RegionManager已初始化（向后兼容）")
    except Exception as e:
        logger.warning(f"RegionManager初始化失败（非关键，可能影响旧接口）: {e}")

    # 启动错误监控
    try:
        start_error_monitoring()
        logger.info("错误监控已启动")
    except Exception as e:
        logger.warning(f"错误监控启动失败: {e}")

    # 启动高级监控
    try:
        start_monitoring()
        logger.info("高级监控系统已启动")
    except Exception as e:
        logger.warning(f"高级监控启动失败: {e}")

    # 启动Redis监听器
    try:
        await start_redis_listener()
        logger.info("Redis监听器已启动")
    except Exception as e:
        logger.error(f"Redis监听器启动失败: {e}")

    # 从数据库加载工作流到工作流引擎
    try:
        from src.database.connection import get_async_session
        from src.database.dao import WorkflowDAO
        from src.workflow.workflow_engine import workflow_engine

        # 执行状态自愈（修复因重启而中断的任务）
        await workflow_engine.recover_state()

        async for session in get_async_session():
            try:
                workflows = await WorkflowDAO.get_all(session)
                loaded_count = 0
                for workflow in workflows:
                    try:
                        workflow_dict = workflow.to_dict()
                        # 重新注册到工作流引擎（特别是调度工作流）
                        if (
                            workflow.status == "active"
                            and workflow.trigger == "schedule"
                        ):
                            engine_result = await workflow_engine.create_workflow(
                                workflow_dict
                            )
                            if engine_result.get("success"):
                                loaded_count += 1
                                logger.info(
                                    f"已加载调度工作流: {workflow.name} ({workflow.id})"
                                )
                        elif workflow.status == "active":
                            # 非调度工作流也注册到引擎（用于手动触发）
                            engine_result = await workflow_engine.create_workflow(
                                workflow_dict
                            )
                            if engine_result.get("success"):
                                loaded_count += 1
                                logger.info(f"已加载工作流: {workflow.name} ({workflow.id})")
                    except Exception as e:
                        logger.warning(f"加载工作流失败 {workflow.id}: {e}")

                if loaded_count > 0:
                    logger.info(f"✅ 从数据库加载了 {loaded_count} 个工作流到工作流引擎")
                else:
                    logger.info("数据库中没有需要加载的工作流")
            except Exception as e:
                logger.warning(f"从数据库加载工作流失败（非关键）: {e}")
            break  # 退出生成器循环
    except Exception as e:
        logger.warning(f"工作流加载初始化失败（非关键）: {e}")

    try:
        yield
    except asyncio.CancelledError:
        # 当收到 CTRL+C 或其他取消信号时，正常处理关闭流程
        logger.info("收到关闭信号，开始优雅关闭...")
        # 继续执行关闭逻辑
    except Exception as e:
        logger.error(f"应用程序运行时发生错误: {e}", exc_info=True)
        raise

    # Shutdown
    logger.info("Shutting down the application...")

    # 停止所有正在运行的工作流
    try:
        import asyncio

        from src.workflow.workflow_engine import workflow_engine

        # 获取所有正在运行的工作流ID
        running_workflow_ids = list(workflow_engine.running_workflows.keys())
        # 获取所有有取消事件的工作流ID（可能不在运行列表中，但训练任务还在运行）
        all_cancel_events = list(workflow_engine.cancel_events.keys())

        # 合并所有需要停止的工作流ID
        all_workflow_ids = set(running_workflow_ids) | set(all_cancel_events)

        if all_workflow_ids:
            logger.info(
                f"正在停止 {len(all_workflow_ids)} 个工作流（运行中: {len(running_workflow_ids)}, 有取消事件: {len(all_cancel_events)}）..."
            )

            # 首先设置所有取消事件
            for workflow_id in all_workflow_ids:
                if workflow_id in workflow_engine.cancel_events:
                    cancel_event = workflow_engine.cancel_events[workflow_id]
                    if not cancel_event.is_set():
                        cancel_event.set()
                        logger.info(f"已设置取消事件: {workflow_id}")

            # 然后停止所有运行中的工作流任务
            for workflow_id in running_workflow_ids:
                try:
                    stop_result = await workflow_engine.stop_workflow(workflow_id)
                    if stop_result.get("success"):
                        logger.info(f"已停止工作流: {workflow_id}")
                    else:
                        logger.warning(
                            f"停止工作流失败 {workflow_id}: {stop_result.get('message', '未知错误')}"
                        )
                except Exception as e:
                    logger.warning(f"停止工作流异常 {workflow_id}: {e}")

            # 等待一段时间让训练任务响应取消信号
            logger.info("等待训练任务响应取消信号...")

            # 分阶段等待，每阶段检查任务状态
            max_wait_time = 15.0  # 最多等待15秒
            check_interval = 1.0  # 每1秒检查一次
            waited_time = 0.0

            while waited_time < max_wait_time:
                await asyncio.sleep(check_interval)
                waited_time += check_interval

                # 检查是否还有运行中的任务
                remaining_tasks = [
                    wid
                    for wid in workflow_engine.running_workflows.keys()
                    if wid in all_workflow_ids
                ]
                if not remaining_tasks:
                    logger.info(f"所有工作流任务已停止（等待了 {waited_time:.1f} 秒）")
                    break

                logger.debug(
                    f"仍有 {len(remaining_tasks)} 个工作流任务运行中（已等待 {waited_time:.1f} 秒）..."
                )

            # 再次检查是否还有运行中的任务
            remaining_tasks = [
                wid
                for wid in workflow_engine.running_workflows.keys()
                if wid in all_workflow_ids
            ]
            if remaining_tasks:
                logger.warning(f"仍有 {len(remaining_tasks)} 个工作流任务未完成，强制取消...")
                for workflow_id in remaining_tasks:
                    try:
                        task = workflow_engine.running_workflows[workflow_id]
                        if not task.done():
                            task.cancel()
                            logger.info(f"已强制取消工作流任务: {workflow_id}")
                            try:
                                # 尝试等待任务取消完成（最多3秒，给训练线程更多时间响应）
                                await asyncio.wait_for(task, timeout=3.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                logger.warning(f"工作流任务 {workflow_id} 取消超时或已取消")
                                # 如果任务仍在运行，记录警告但继续关闭流程
                                if not task.done():
                                    logger.error(
                                        f"⚠️ 工作流任务 {workflow_id} 无法取消，训练线程可能仍在后台运行"
                                    )
                                    logger.error("   这可能导致训练进程无法完全停止，需要手动终止")
                    except Exception as e:
                        logger.warning(f"强制取消工作流任务失败 {workflow_id}: {e}")

                # 最后再等待一段时间，确保取消信号传播（增加到5秒）
                logger.info("等待训练线程响应取消信号（最多5秒）...")
                await asyncio.sleep(5.0)

            logger.info("工作流停止完成")
        else:
            logger.info("没有正在运行的工作流")
    except (asyncio.CancelledError, KeyboardInterrupt):
        # 如果是取消信号，记录但不抛出异常
        logger.info("关闭过程中收到取消信号，继续关闭流程...")
    except Exception as e:
        logger.warning(f"停止工作流失败（非关键）: {e}", exc_info=True)

    # 关闭Redis监听器
    try:
        await shutdown_redis_listener()
        logger.info("Redis监听器已关闭")
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Redis监听器关闭过程中收到取消信号")
    except Exception as e:
        logger.warning(f"Redis监听器关闭失败: {e}")

    # 关闭视频流管理器
    try:
        from src.services.video_stream_manager import shutdown_stream_manager

        await shutdown_stream_manager()
        logger.info("视频流管理器已关闭")
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("视频流管理器关闭过程中收到取消信号")
    except Exception as e:
        logger.warning(f"视频流管理器关闭失败: {e}")

    # 关闭数据库服务
    try:
        await close_db_service()
        logger.info("数据库服务已关闭")
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("数据库服务关闭过程中收到取消信号")
    except Exception as e:
        logger.warning(f"数据库服务关闭失败: {e}")

    # 停止错误监控
    try:
        stop_error_monitoring()
        logger.info("错误监控已停止")
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("错误监控停止过程中收到取消信号")
    except Exception as e:
        logger.warning(f"错误监控停止失败: {e}")

    # 停止高级监控
    try:
        stop_monitoring()
        logger.info("高级监控系统已停止")
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("高级监控停止过程中收到取消信号")
    except Exception as e:
        logger.warning(f"高级监控停止失败: {e}")

    logger.info("应用程序已完全关闭")


app = FastAPI(
    title="人体行为检测系统 API",
    description="基于深度学习的实时人体行为检测与分析系统",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置错误处理中间件
setup_error_middleware(app)

# 设置指标监控中间件
app.add_middleware(MetricsMiddleware)

# 设置安全中间件
setup_security_middleware(app)


@app.get("/health")
async def health_check():
    """健康检查端点."""
    return {"status": "healthy"}


@app.get("/api/ping")
async def ping():
    """API连通性测试端点."""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}


# Include routers
app.include_router(comprehensive.router, prefix="/api/v1/detect", tags=["Detection"])
app.include_router(
    region_management.router, prefix="/api/v1/management", tags=["Region Management"]
)
# 兼容旧版前端的 /api/regions 路由
app.include_router(region_management.compat_router, tags=["Compat"])
app.include_router(websocket.router, prefix="", tags=["WebSocket"])
app.include_router(statistics.router, prefix="/api/v1", tags=["Statistics"])
app.include_router(download.router, prefix="/api/v1/download", tags=["Download"])
app.include_router(export.router, tags=["Export"])
app.include_router(events.router, tags=["Events"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["Monitoring"])
app.include_router(cameras.router, prefix="/api/v1", tags=["Cameras"])
app.include_router(system.router, prefix="/api/v1", tags=["System"])
app.include_router(error_monitoring.router, prefix="/api/v1", tags=["Error Monitoring"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])
app.include_router(security.router, prefix="/api/v1", tags=["Security Management"])
app.include_router(records.router, tags=["Records"])
app.include_router(video_stream.router, prefix="/api/v1", tags=["Video Stream"])
# 配置管理路由
app.include_router(config.router, prefix="/api/v1/config", tags=["Config"])
app.include_router(detection_config.router, tags=["Detection Config"])
app.include_router(mlops.router)


@app.get("/", include_in_schema=False)
async def root():
    """根路径端点."""
    return RedirectResponse(url="/frontend/index.html")


# Mount frontend static files
frontend_path = os.path.join(project_root, "frontend")
frontend_dist_path = os.path.join(project_root, "frontend", "dist")

# 优先使用构建产物，如果不存在则使用源码目录
if os.path.exists(frontend_dist_path):
    app.mount(
        "/frontend",
        StaticFiles(directory=frontend_dist_path, html=True),
        name="frontend",
    )
    logger.info(
        f"Static file directory mounted: {frontend_dist_path} to /frontend (production build)"
    )
elif os.path.exists(frontend_path):
    app.mount(
        "/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend"
    )
    logger.info(
        f"Static file directory mounted: {frontend_path} to /frontend (development)"
    )
else:
    logger.warning("Frontend directory not found")
