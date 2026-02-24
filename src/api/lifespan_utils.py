"""lifespan 工具函数模块.

包含从主lifespan函数提取出来的子功能函数，用于拆分复杂的lifespan函数。
"""
import asyncio
import logging
import os
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def reset_domain_service_singleton() -> bool:
    """重置领域服务单例."""
    try:
        from src.services.detection_service_domain import reset_detection_service_domain

        reset_detection_service_domain()
        logger.info("领域服务单例已重置")
        return True
    except Exception as e:
        logger.warning(f"领域服务单例重置失败: {e}")
        return False


async def startup_database(app) -> bool:
    """初始化数据库服务."""
    try:
        from src.database.connection import init_database
        from src.services.database_service import close_db_service, get_db_service

        await get_db_service()
        await init_database()
        logger.info("数据库服务已初始化")
        return True
    except Exception as e:
        logger.warning(f"数据库服务初始化失败 (非关键): {e}")
        return False


async def startup_video_stream_manager() -> bool:
    """初始化视频流管理器."""
    try:
        from src.services.video_stream_manager import init_stream_manager

        await init_stream_manager()
        logger.info("视频流管理器已初始化")
        return True
    except Exception as e:
        logger.warning(f"视频流管理器初始化失败 (非关键): {e}")
        return False


async def startup_detection(app) -> Tuple[Optional[object], Optional[object]]:
    """初始化检测服务.
    
    Args:
        app: FastAPI应用实例
        
    Returns:
        Tuple[optimized_pipeline, hairnet_pipeline] 或 (None, None) 如果失败
    """
    try:
        max_concurrency_raw = os.getenv("DETECTION_MAX_CONCURRENCY", "1")
        try:
            max_concurrency = max(1, int(max_concurrency_raw))
        except ValueError:
            logger.warning(
                f"DETECTION_MAX_CONCURRENCY 无效: {max_concurrency_raw}, 使用默认值 1"
            )
            max_concurrency = 1

        app.state.detection_lock = threading.Lock()
        app.state.detection_semaphore = asyncio.Semaphore(max_concurrency)

        from src.services import detection_service
        optimized_pipeline, hairnet_pipeline = (
            detection_service.initialize_detection_services()
        )
        app.state.optimized_pipeline = optimized_pipeline
        app.state.hairnet_pipeline = hairnet_pipeline
        logger.info(f"检测服务已初始化，最大并发推理数: {max_concurrency}")
        return optimized_pipeline, hairnet_pipeline
    except Exception as e:
        # 生产环境硬约束：检测服务必须成功初始化
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.error(f"检测服务初始化失败(生产必需): {e}")
            raise
        
        # 非生产：避免因模型缺失或环境问题导致 API 启动失败
        app.state.optimized_pipeline = None
        app.state.hairnet_pipeline = None
        app.state.detection_lock = None
        app.state.detection_semaphore = None
        logger.warning(f"检测服务初始化失败 (非生产非关键): {e}")
        return None, None


async def startup_regions(app) -> bool:
    """初始化区域服务（数据库存储）."""
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
                "HBD_REGIONS_FILE", 
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "regions.json")
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
        
        return True
    except Exception as e:
        logger.warning(f"区域服务初始化失败（非关键）: {e}")
        return False


async def startup_legacy_region_manager() -> bool:
    """初始化旧的RegionManager（用于向后兼容旧的get_region_service依赖）."""
    try:
        from src.services.region_service import initialize_region_service
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        regions_file = os.environ.get(
            "HBD_REGIONS_FILE", 
            os.path.join(project_root, "config", "regions.json")
        )
        initialize_region_service(regions_file)
        logger.info("RegionManager已初始化（向后兼容）")
        return True
    except Exception as e:
        logger.warning(f"RegionManager初始化失败（非关键，可能影响旧接口）: {e}")
        return False


async def startup_monitoring() -> bool:
    """启动监控系统."""
    try:
        from src.utils.error_monitor import start_error_monitoring
        from src.monitoring.advanced_monitoring import start_monitoring
        
        start_error_monitoring()
        logger.info("错误监控已启动")
        
        start_monitoring()
        logger.info("高级监控系统已启动")
        return True
    except Exception as e:
        logger.warning(f"监控系统启动失败: {e}")
        return False


async def startup_redis_listener() -> bool:
    """启动Redis监听器."""
    try:
        from src.api.redis_listener import start_redis_listener
        await start_redis_listener()
        logger.info("Redis监听器已启动")
        return True
    except Exception as e:
        logger.error(f"Redis监听器启动失败: {e}")
        return False


async def startup_workflow_engine() -> bool:
    """从数据库加载工作流到工作流引擎."""
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
        
        return True
    except Exception as e:
        logger.warning(f"工作流加载初始化失败（非关键）: {e}")
        return False


async def shutdown_workflows() -> bool:
    """停止所有正在运行的工作流."""
    try:
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
        
        return True
    except (asyncio.CancelledError, KeyboardInterrupt):
        # 如果是取消信号，记录但不抛出异常
        logger.info("关闭过程中收到取消信号，继续关闭流程...")
        return True
    except Exception as e:
        logger.warning(f"停止工作流失败（非关键）: {e}", exc_info=True)
        return False


async def shutdown_redis_listener() -> bool:
    """关闭Redis监听器."""
    try:
        from src.api.redis_listener import shutdown_redis_listener as stop_redis_listener
        await stop_redis_listener()
        logger.info("Redis监听器已关闭")
        return True
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Redis监听器关闭过程中收到取消信号")
        return True
    except Exception as e:
        logger.warning(f"Redis监听器关闭失败: {e}")
        return False


async def shutdown_video_stream_manager() -> bool:
    """关闭视频流管理器."""
    try:
        from src.services.video_stream_manager import shutdown_stream_manager
        await shutdown_stream_manager()
        logger.info("视频流管理器已关闭")
        return True
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("视频流管理器关闭过程中收到取消信号")
        return True
    except Exception as e:
        logger.warning(f"视频流管理器关闭失败: {e}")
        return False


async def shutdown_database() -> bool:
    """关闭数据库服务."""
    try:
        from src.services.database_service import close_db_service
        await close_db_service()
        logger.info("数据库服务已关闭")
        return True
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("数据库服务关闭过程中收到取消信号")
        return True
    except Exception as e:
        logger.warning(f"数据库服务关闭失败: {e}")
        return False


async def shutdown_monitoring() -> bool:
    """停止监控系统."""
    try:
        from src.utils.error_monitor import stop_error_monitoring
        from src.monitoring.advanced_monitoring import stop_monitoring as stop_advanced_monitoring
        
        stop_error_monitoring()
        logger.info("错误监控已停止")
        
        stop_advanced_monitoring()
        logger.info("高级监控系统已停止")
        return True
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("监控停止过程中收到取消信号")
        return True
    except Exception as e:
        logger.warning(f"监控停止失败: {e}")
        return False