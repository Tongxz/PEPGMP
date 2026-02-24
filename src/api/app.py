#!/usr/bin/env python3
"""FastAPI应用程序入口点.

这个模块包含了FastAPI应用程序的主要配置和路由设置.
"""
import asyncio
import logging
import logging.handlers
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.schemas.error_schemas import ErrorCode
from src.api.utils.error_helpers import create_error_response, is_development
from src.api.lifespan_utils import (
    reset_domain_service_singleton,
    startup_database,
    startup_video_stream_manager,
    startup_detection,
    startup_regions,
    startup_legacy_region_manager,
    startup_monitoring,
    startup_redis_listener,
    startup_workflow_engine,
    shutdown_workflows,
    shutdown_redis_listener,
    shutdown_video_stream_manager,
    shutdown_database,
    shutdown_monitoring,
)

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
        cache,
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
        cache,
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
async def lifespan(app: FastAPI):
    """应用程序生命周期管理（重构版，使用工具函数模块）."""
    # Startup
    logger.info("Starting up the application...")

    try:
        # 按顺序启动各个服务（保持原有启动顺序）
        
        # 1. 重置领域服务单例
        await reset_domain_service_singleton()
        
        # 2. 初始化数据库服务
        await startup_database(app)
        
        # 3. 初始化视频流管理器
        await startup_video_stream_manager()
        
        # 4. 初始化检测服务（包含生产环境硬约束）
        await startup_detection(app)
        
        # 5. 初始化区域服务（数据库存储）
        await startup_regions(app)
        
        # 6. 初始化旧的RegionManager（向后兼容）
        await startup_legacy_region_manager()
        
        # 7. 启动监控系统
        await startup_monitoring()
        
        # 8. 启动Redis监听器
        await startup_redis_listener()
        
        # 9. 从数据库加载工作流到工作流引擎
        await startup_workflow_engine()
        
        logger.info("✅ 所有服务启动完成")
        
        # 应用程序运行阶段
        yield
        
    except asyncio.CancelledError:
        # 当收到 CTRL+C 或其他取消信号时，正常处理关闭流程
        logger.info("收到取消信号，开始优雅关闭...")
        # 继续执行关闭逻辑
    except Exception as e:
        logger.error(f"应用程序运行时发生错误: {e}", exc_info=True)
        raise
    finally:
        # Shutdown - 无论是否发生异常都执行关闭流程
        logger.info("Shutting down the application...")
        
        # 按逆序关闭服务（与启动顺序相反）
        
        # 1. 停止所有正在运行的工作流
        await shutdown_workflows()
        
        # 2. 关闭Redis监听器
        await shutdown_redis_listener()
        
        # 3. 关闭视频流管理器
        await shutdown_video_stream_manager()
        
        # 4. 关闭数据库服务
        await shutdown_database()
        
        # 5. 停止监控系统
        await shutdown_monitoring()
        
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


# 添加全局异常处理器，确保所有错误都使用统一格式
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理HTTP异常，转换为统一格式"""
    request_id = getattr(request.state, "request_id", f"req_{int(time.time() * 1000)}")

    # 检查detail是否已经是统一格式（字典）
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        # 已经是统一格式，添加request_id（如果缺失）
        error_response = exc.detail.copy()
        if "error" in error_response and isinstance(error_response["error"], dict):
            if (
                "request_id" not in error_response["error"]
                or error_response["error"]["request_id"] is None
            ):
                error_response["error"]["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=error_response)
    else:
        # 旧格式（字符串），转换为统一格式
        error_response = create_error_response(
            status_code=exc.status_code,
            message=str(exc.detail) if exc.detail else "HTTP错误",
            request_id=request_id,
        )
        return JSONResponse(status_code=exc.status_code, content=error_response)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """处理404错误（路由不存在）"""
    request_id = getattr(request.state, "request_id", f"req_{int(time.time() * 1000)}")
    error_response = create_error_response(
        status_code=404,
        message="端点不存在",
        request_id=request_id,
    )
    return JSONResponse(status_code=404, content=error_response)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    request_id = getattr(request.state, "request_id", f"req_{int(time.time() * 1000)}")
    error_response = create_error_response(
        status_code=422,
        message="请求参数验证失败",
        error_code=ErrorCode.VALIDATION_ERROR,
        details=str(exc.errors()) if is_development() else None,
        request_id=request_id,
    )
    return JSONResponse(status_code=422, content=error_response)


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
# 缓存管理路由
app.include_router(cache.router, prefix="/api/v1", tags=["Cache Management"])


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
