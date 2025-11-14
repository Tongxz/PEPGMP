"""配置变更通知服务（Redis Pub/Sub）."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def publish_config_change_notification(
    camera_id: Optional[str],
    config_type: str,
    config_key: str,
    config_value: Any,
    change_type: str = "update",  # update, delete
) -> bool:
    """发布配置变更通知到Redis（同步）

    Args:
        camera_id: 摄像头ID（None表示全局配置）
        config_type: 配置类型（human_detection, hairnet_detection等）
        config_key: 配置项名称
        config_value: 配置值
        change_type: 变更类型（update, delete）

    Returns:
        bool: 是否成功发布
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.debug("REDIS_URL未设置，跳过配置变更通知")
            return False

        redis_client = redis.from_url(redis_url, decode_responses=False)

        # 构建通知消息
        notification = {
            "type": "config_change",
            "camera_id": camera_id,
            "config_type": config_type,
            "config_key": config_key,
            "config_value": config_value,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 发布到配置变更频道
        # 全局配置变更：detection_config:change:global
        # 相机特定配置变更：detection_config:change:camera:{camera_id}
        if camera_id:
            channel = f"detection_config:change:camera:{camera_id}"
        else:
            channel = "detection_config:change:global"

        payload = json.dumps(notification).encode("utf-8")
        subscribers = redis_client.publish(channel, payload)

        # 同时发布到全局频道（所有检测进程都可以订阅）
        global_channel = "detection_config:change"
        redis_client.publish(global_channel, payload)

        logger.info(
            f"配置变更通知已发布: channel={channel}, "
            f"config_type={config_type}, config_key={config_key}, "
            f"subscribers={subscribers}"
        )
        return True

    except Exception as e:
        logger.warning(f"发布配置变更通知失败: {e}")
        return False


async def publish_config_change_notification_async(
    camera_id: Optional[str],
    config_type: str,
    config_key: str,
    config_value: Any,
    change_type: str = "update",
) -> bool:
    """发布配置变更通知到Redis（异步）

    Args:
        camera_id: 摄像头ID（None表示全局配置）
        config_type: 配置类型
        config_key: 配置项名称
        config_value: 配置值
        change_type: 变更类型（update, delete）

    Returns:
        bool: 是否成功发布
    """
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.debug("REDIS_URL未设置，跳过配置变更通知")
            return False

        redis_client = aioredis.from_url(redis_url, decode_responses=False)

        # 构建通知消息
        notification = {
            "type": "config_change",
            "camera_id": camera_id,
            "config_type": config_type,
            "config_key": config_key,
            "config_value": config_value,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 发布到配置变更频道
        if camera_id:
            channel = f"detection_config:change:camera:{camera_id}"
        else:
            channel = "detection_config:change:global"

        payload = json.dumps(notification).encode("utf-8")
        subscribers = await redis_client.publish(channel, payload)

        # 同时发布到全局频道
        global_channel = "detection_config:change"
        await redis_client.publish(global_channel, payload)

        await redis_client.aclose()

        logger.info(
            f"配置变更通知已发布: channel={channel}, "
            f"config_type={config_type}, config_key={config_key}, "
            f"subscribers={subscribers}"
        )
        return True

    except Exception as e:
        logger.warning(f"发布配置变更通知失败: {e}")
        return False
