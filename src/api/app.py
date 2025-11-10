#!/usr/bin/env python3
"""FastAPI应用程序入口点.

这个模块包含了FastAPI应用程序的主要配置和路由设置.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 触发依赖注入容器的服务配置（包括 USE_DOMAIN_SERVICE 开关与仓储绑定）
try:
    import src.container.service_config  # noqa: F401

    logger.info("依赖注入服务配置已加载")
except Exception as e:
    logger.warning(f"依赖注入服务配置加载失败（不影响启动）: {e}")


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
        # 避免因模型缺失或环境问题导致 API 启动失败
        app.state.optimized_pipeline = None
        app.state.hairnet_pipeline = None
        logger.warning(f"检测服务初始化失败 (非关键): {e}")
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

    yield

    # Shutdown
    logger.info("Shutting down the application...")

    # 关闭Redis监听器
    try:
        await shutdown_redis_listener()
        logger.info("Redis监听器已关闭")
    except Exception as e:
        logger.warning(f"Redis监听器关闭失败: {e}")

    # 关闭视频流管理器
    try:
        from src.services.video_stream_manager import shutdown_stream_manager

        await shutdown_stream_manager()
        logger.info("视频流管理器已关闭")
    except Exception as e:
        logger.warning(f"视频流管理器关闭失败: {e}")

    # 关闭数据库服务
    try:
        await close_db_service()
        logger.info("数据库服务已关闭")
    except Exception as e:
        logger.warning(f"数据库服务关闭失败: {e}")

    # 停止错误监控
    try:
        stop_error_monitoring()
        logger.info("错误监控已停止")
    except Exception as e:
        logger.warning(f"错误监控停止失败: {e}")

    # 停止高级监控
    try:
        stop_monitoring()
        logger.info("高级监控系统已停止")
    except Exception as e:
        logger.warning(f"高级监控停止失败: {e}")


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
