"""Redis配置同步工具（用于相机配置）."""

import logging
import os
from typing import Any, Dict, List, Optional, Set

from src.infrastructure.notifications.config_change_notifier import (
    publish_config_change_notification,
)

logger = logging.getLogger(__name__)

# 运行时配置项（需要同步到Redis）
RUNTIME_CONFIG_KEYS: Set[str] = {
    "log_interval",  # 检测频率
    "stream_interval",  # 视频流推送间隔
}


def sync_camera_config_to_redis(
    camera_id: str,
    camera_config: Dict[str, Any],
    changed_keys: Optional[List[str]] = None,
) -> bool:
    """将相机配置同步到Redis（用于运行时配置）

    Args:
        camera_id: 摄像头ID
        camera_config: 相机配置字典（可以是Camera实体的to_dict()结果，也可以是metadata字典）
        changed_keys: 变更的配置项列表（如果提供，只同步变更的配置项并发送通知）

    Returns:
        bool: 是否成功同步
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.debug("REDIS_URL未设置，跳过Redis配置同步")
            return False

        redis_client = redis.from_url(redis_url)
        config_key = f"video_stream:config:{camera_id}"

        # 提取运行时配置
        # 支持两种格式：
        # 1. Camera实体的to_dict()结果：metadata字段包含配置
        # 2. 直接的配置字典：配置项在顶层
        metadata = camera_config.get("metadata", {})
        if not metadata:
            # 如果没有metadata字段，假设配置项在顶层
            metadata = camera_config

        # 构建Redis配置
        redis_config: Dict[str, str] = {}

        # 如果指定了changed_keys，只同步变更的配置项
        keys_to_sync = changed_keys if changed_keys else list(RUNTIME_CONFIG_KEYS)

        for key in keys_to_sync:
            if key not in RUNTIME_CONFIG_KEYS:
                continue

            # 获取配置值
            value = metadata.get(key) if metadata else None
            if value is None:
                # 如果metadata中没有，尝试从顶层获取
                value = camera_config.get(key)

            if value is not None:
                # 转换为字符串（Redis hash只支持字符串值）
                redis_config[key] = str(value)

                # 特殊处理：stream_interval 应该与 log_interval 保持一致
                if key == "log_interval":
                    redis_config["stream_interval"] = str(value)

        # 如果没有任何配置需要同步，直接返回
        if not redis_config:
            logger.debug(f"没有需要同步的配置项: camera_id={camera_id}")
            return True

        # 同步到Redis
        redis_client.hset(config_key, mapping=redis_config)
        redis_client.expire(config_key, 3600)  # 1小时过期

        logger.info(
            f"已同步相机配置到Redis: camera_id={camera_id}, "
            f"config={redis_config}, changed_keys={changed_keys}"
        )

        # 发布配置变更通知（针对每个变更的配置项）
        if changed_keys:
            for key in changed_keys:
                if key in RUNTIME_CONFIG_KEYS:
                    value = redis_config.get(key)
                    if value is not None:
                        try:
                            publish_config_change_notification(
                                camera_id=camera_id,
                                config_type="runtime",
                                config_key=key,
                                config_value=value,
                                change_type="update",
                            )
                        except Exception as e:
                            logger.warning(
                                f"发布配置变更通知失败: camera_id={camera_id}, "
                                f"config_key={key}, error={e}"
                            )

        return True

    except Exception as e:
        logger.warning(f"同步相机配置到Redis失败: camera_id={camera_id}, error={e}")
        return False


def get_camera_config_from_redis(camera_id: str) -> Optional[Dict[str, Any]]:
    """从Redis获取相机配置（运行时配置）

    Args:
        camera_id: 摄像头ID

    Returns:
        配置字典（如果存在），否则返回None
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return None

        redis_client = redis.from_url(redis_url)
        config_key = f"video_stream:config:{camera_id}"

        config_data = redis_client.hgetall(config_key)
        if not config_data:
            return None

        # 解码bytes为字符串
        config_dict = {
            k.decode(): v.decode() if isinstance(v, bytes) else v
            for k, v in config_data.items()
        }

        # 转换字符串值回原始类型
        result: Dict[str, Any] = {}
        for key, value in config_dict.items():
            # 尝试转换为整数
            try:
                result[key] = int(value)
            except ValueError:
                # 如果转换失败，保持字符串
                result[key] = value

        return result

    except Exception as e:
        logger.debug(f"从Redis获取相机配置失败: camera_id={camera_id}, error={e}")
        return None


def delete_camera_config_from_redis(camera_id: str) -> bool:
    """从Redis删除相机配置

    Args:
        camera_id: 摄像头ID

    Returns:
        bool: 是否成功删除
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return False

        redis_client = redis.from_url(redis_url)
        config_key = f"video_stream:config:{camera_id}"

        deleted = redis_client.delete(config_key)

        if deleted > 0:
            logger.info(f"已从Redis删除相机配置: camera_id={camera_id}")

        return deleted > 0

    except Exception as e:
        logger.warning(f"从Redis删除相机配置失败: camera_id={camera_id}, error={e}")
        return False
