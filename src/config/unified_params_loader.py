"""统一参数配置加载器 - 支持从数据库和YAML加载."""

import logging
import os
from typing import Any, Optional

from src.config.unified_params import UnifiedParams

logger = logging.getLogger(__name__)

# 全局配置实例缓存
_global_params_cache: Optional[UnifiedParams] = None
_db_config_loaded = False


def get_unified_params(
    camera_id: Optional[str] = None,
    force_reload: bool = False,
) -> UnifiedParams:
    """获取全局统一参数配置（优先从数据库读取，失败时从YAML读取）

    Args:
        camera_id: 摄像头ID（可选，用于按相机加载配置）
        force_reload: 是否强制重新加载配置

    Returns:
        UnifiedParams: 统一参数配置实例

    注意：此函数是同步的，主要用于向后兼容。
    在FastAPI环境中，应使用 load_unified_params_from_db() 异步函数。
    """
    global _global_params_cache, _db_config_loaded

    # 如果已加载且不需要强制重新加载，直接返回缓存
    if _global_params_cache is not None and not force_reload and _db_config_loaded:
        return _global_params_cache

    # 同步函数无法直接调用异步函数，所以这里从YAML加载（回退）
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "config",
        "unified_params.yaml",
    )
    _global_params_cache = UnifiedParams.load_from_yaml(config_path)
    _db_config_loaded = False

    return _global_params_cache


async def load_unified_params_from_db(
    camera_id: Optional[str] = None,
    config_repository: Optional[Any] = None,
) -> UnifiedParams:
    """从数据库加载统一参数配置（异步）

    Args:
        camera_id: 摄像头ID（可选，用于按相机加载配置）
        config_repository: 检测参数配置仓储（可选，如果不提供则自动创建）

    Returns:
        UnifiedParams: 统一参数配置实例
    """
    global _global_params_cache, _db_config_loaded

    try:
        # 如果没有提供仓储，尝试创建
        if config_repository is None:
            try:
                from src.infrastructure.repositories.postgresql_detection_config_repository import (
                    PostgreSQLDetectionConfigRepository,
                )
                from src.services.database_service import get_db_service

                db_service = await get_db_service()
                if db_service.pool:
                    config_repository = PostgreSQLDetectionConfigRepository(
                        db_service.pool
                    )
                else:
                    logger.warning("数据库连接池未初始化，从YAML加载配置")
                    return get_unified_params(camera_id, force_reload=True)
            except Exception as e:
                logger.warning(f"创建配置仓储失败: {e}，从YAML加载配置")
                return get_unified_params(camera_id, force_reload=True)

        # 从数据库加载配置
        from src.domain.services.detection_config_service import DetectionConfigService

        config_service = DetectionConfigService(config_repository)
        all_configs = await config_service.get_all_configs(camera_id)

        # 转换为UnifiedParams格式
        config_dict = {}
        for config_type, config_values in all_configs.items():
            config_dict[config_type] = config_values

        # 如果数据库中没有配置，使用默认配置
        if not config_dict:
            logger.warning("数据库中未找到配置，使用YAML默认配置")
            return get_unified_params(camera_id, force_reload=True)

        # 从字典加载配置
        _global_params_cache = UnifiedParams.load_from_dict(config_dict)
        _db_config_loaded = True

        logger.info(f"从数据库加载配置成功: camera_id={camera_id}, " f"配置类型数={len(config_dict)}")
        return _global_params_cache

    except Exception as e:
        logger.warning(f"从数据库加载配置失败: {e}，从YAML加载配置")
        return get_unified_params(camera_id, force_reload=True)


def clear_cache():
    """清除配置缓存（用于测试或强制重新加载）"""
    global _global_params_cache, _db_config_loaded
    _global_params_cache = None
    _db_config_loaded = False
