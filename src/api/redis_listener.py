"""
Redis Pub/Sub Listener and Cache.

This module handles listening to Redis channels for real-time updates from
detection processes and caching the latest information in memory.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

# In a real application, this would come from a shared Redis client utility
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

# Global in-memory cache to store the latest stats for each camera.
# The key is camera_id, the value is the latest stats dictionary.
CAMERA_STATS_CACHE: Dict[str, Dict[str, Any]] = {}

# Global reference to the listener task so it can be cancelled on shutdown
listener_task: asyncio.Task | None = None


async def redis_stats_listener():
    """Lisens to the 'hbd:stats' channel and updates the in-memory cache."""
    while True:
        try:
            # 优先使用REDIS_URL，然后回退到单独的环境变量
            redis_url = os.getenv("REDIS_URL")

            if redis_url:
                # 从URL解析连接参数
                from urllib.parse import urlparse

                parsed = urlparse(redis_url)
                redis_host = parsed.hostname or "localhost"
                redis_port = parsed.port or 6379
                redis_password = parsed.password
                # 从路径中解析db编号
                redis_db = (
                    int(parsed.path.lstrip("/"))
                    if parsed.path and parsed.path != "/"
                    else 0
                )
            else:
                # 回退到单独的环境变量
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_db = int(os.getenv("REDIS_DB", "0"))
                redis_password = os.getenv("REDIS_PASSWORD", None)

            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                encoding="utf-8",
                decode_responses=True,
            )
            async with r.pubsub() as pubsub:
                await pubsub.subscribe("hbd:stats")
                logger.info(
                    "Successfully subscribed to 'hbd:stats' channel. Listening for messages..."
                )
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=10
                    )
                    if message:
                        try:
                            data = json.loads(message["data"])
                            if data.get("type") == "stats":
                                camera_id = data.get("camera_id")
                                if camera_id:
                                    CAMERA_STATS_CACHE[camera_id] = data
                                    # 广播状态更新到WebSocket客户端
                                    try:
                                        from src.api.routers.websocket import (
                                            broadcast_status_update,
                                        )

                                        await broadcast_status_update(camera_id, data)
                                    except Exception as e:
                                        logger.debug(f"广播状态更新失败: {e}")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(
                                f"Could not parse message data: {message['data']}. Error: {e}"
                            )
        except RedisConnectionError as e:
            logger.error(f"Redis connection failed: {e}. Retrying in 5 seconds...")
            CAMERA_STATS_CACHE.clear()  # Clear cache on disconnect
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred in redis_stats_listener: {e}. Retrying in 10 seconds..."
            )
            await asyncio.sleep(10)


async def start_redis_listener():
    """Starts the Redis listener as a background task."""
    global listener_task
    if listener_task is None or listener_task.done():
        logger.info("Starting Redis listener background task...")
        listener_task = asyncio.create_task(redis_stats_listener())
    else:
        logger.warning("Redis listener task is already running.")


async def shutdown_redis_listener():
    """Stops the Redis listener background task."""
    global listener_task
    if listener_task and not listener_task.done():
        logger.info("Stopping Redis listener background task...")
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            logger.info("Redis listener task successfully cancelled.")
    listener_task = None
