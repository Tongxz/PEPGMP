"""配置变更监听器（Redis Pub/Sub）.

用于检测进程中监听配置变更通知，并自动重新加载配置。
"""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigChangeListener:
    """配置变更监听器"""

    def __init__(
        self,
        camera_id: str,
        on_config_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """初始化配置变更监听器

        Args:
            camera_id: 摄像头ID
            on_config_change: 配置变更回调函数
        """
        self.camera_id = camera_id
        self.on_config_change = on_config_change
        self.running = False
        self.listener_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动配置变更监听器"""
        if self.running:
            logger.warning("配置变更监听器已在运行")
            return

        self.running = True
        self.listener_task = asyncio.create_task(self._listen_for_config_changes())
        logger.info(f"配置变更监听器已启动: camera_id={self.camera_id}")

    async def stop(self):
        """停止配置变更监听器"""
        if not self.running:
            return

        self.running = False
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        logger.info(f"配置变更监听器已停止: camera_id={self.camera_id}")

    async def _listen_for_config_changes(self):
        """监听配置变更通知"""
        while self.running:
            try:
                import redis.asyncio as aioredis

                redis_url = os.getenv("REDIS_URL")
                if not redis_url:
                    logger.debug("REDIS_URL未设置，跳过配置变更监听")
                    await asyncio.sleep(10)
                    continue

                redis_client = aioredis.from_url(redis_url, decode_responses=True)
                pubsub = redis_client.pubsub()

                # 订阅全局配置变更频道和相机特定配置变更频道
                await pubsub.subscribe("detection_config:change")
                await pubsub.subscribe(
                    f"detection_config:change:camera:{self.camera_id}"
                )
                await pubsub.subscribe("detection_config:change:global")

                logger.info(
                    f"已订阅配置变更频道: detection_config:change, "
                    f"detection_config:change:camera:{self.camera_id}, "
                    f"detection_config:change:global"
                )

                try:
                    while self.running:
                        try:
                            message = await asyncio.wait_for(
                                pubsub.get_message(ignore_subscribe_messages=True),
                                timeout=1.0,
                            )
                            if message:
                                await self._handle_config_change(message)
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.error(f"处理配置变更消息失败: {e}")
                            await asyncio.sleep(1)
                finally:
                    # 关闭连接
                    try:
                        await pubsub.unsubscribe()
                        await pubsub.close()
                        await redis_client.aclose()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"配置变更监听器错误: {e}，5秒后重试")
                await asyncio.sleep(5)

    async def _handle_config_change(self, message: Dict[str, Any]):
        """处理配置变更消息"""
        try:
            data = message.get("data")
            if not data:
                return

            # 解析消息数据
            if isinstance(data, str):
                notification = json.loads(data)
            else:
                notification = data

            # 检查消息类型
            if notification.get("type") != "config_change":
                return

            # 检查是否适用于当前相机
            camera_id = notification.get("camera_id")
            if camera_id is not None and camera_id != self.camera_id:
                # 这是其他相机的配置变更，忽略
                return

            config_type = notification.get("config_type")
            config_key = notification.get("config_key")
            notification.get("config_value")
            change_type = notification.get("change_type", "update")

            logger.info(
                f"收到配置变更通知: camera_id={camera_id}, "
                f"config_type={config_type}, config_key={config_key}, "
                f"change_type={change_type}"
            )

            # 调用回调函数
            if self.on_config_change:
                try:
                    self.on_config_change(notification)
                except Exception as e:
                    logger.error(f"执行配置变更回调失败: {e}")

        except Exception as e:
            logger.error(f"处理配置变更消息失败: {e}")
