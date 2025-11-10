"""
视频流管理服务

提供按需视频流推送功能，支持：
- WebSocket连接管理
- 帧共享缓存（编码一次，发送多次）
- 异步发送队列（不阻塞检测线程）
- 按需推送（无客户端时零影响）
"""

import asyncio
import os
from collections import defaultdict
from typing import Dict, Optional, Set

from fastapi import WebSocket
from loguru import logger

try:
    # Redis is optional; used to bridge frames from detection subprocesses
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    aioredis = None  # type: ignore


class VideoStreamManager:
    """视频流管理器 - 按需推送，帧共享，异步发送"""

    def __init__(self):
        # 每个摄像头的连接客户端集合
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

        # 每个摄像头的最新帧缓存 (帧共享机制)
        self.frame_cache: Dict[str, bytes] = {}

        # 发送队列 (异步发送机制，增加队列大小以减少丢帧)
        self.send_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # 后台发送任务
        self._sender_task: Optional[asyncio.Task] = None
        self._redis_task: Optional[asyncio.Task] = None
        self._redis: Optional[aioredis.Redis] = None  # type: ignore

        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_cameras": 0,
            "frames_sent": 0,
            "frames_dropped": 0,
            "frames_received": 0,
        }

    async def connect(self, websocket: WebSocket, camera_id: str) -> None:
        """
        客户端连接到指定摄像头视频流

        Args:
            websocket: WebSocket连接
            camera_id: 摄像头ID
        """
        try:
            await websocket.accept()
            self.active_connections[camera_id].add(websocket)
            self.stats["total_connections"] += 1

            logger.info(
                f"客户端已连接到视频流 [{camera_id}], "
                f"当前客户端数: {len(self.active_connections[camera_id])}, "
                f"是否有缓存帧: {camera_id in self.frame_cache}"
            )

            # 如果这是第一个客户端，记录活跃摄像头
            if len(self.active_connections[camera_id]) == 1:
                self.stats["active_cameras"] += 1
                logger.info(f"视频流已启动 [{camera_id}]")

            # 立即发送最新帧（如果有缓存）
            if camera_id in self.frame_cache:
                try:
                    await websocket.send_bytes(self.frame_cache[camera_id])
                    logger.info(
                        f"已发送缓存帧到新客户端 [{camera_id}], 帧大小={len(self.frame_cache[camera_id])} bytes"
                    )
                except Exception as e:
                    logger.warning(f"发送缓存帧失败: {e}")

        except Exception as e:
            logger.error(f"客户端连接失败 [{camera_id}]: {e}")
            raise

    async def disconnect(self, websocket: WebSocket, camera_id: str) -> None:
        """
        客户端断开连接

        Args:
            websocket: WebSocket连接
            camera_id: 摄像头ID
        """
        try:
            self.active_connections[camera_id].discard(websocket)
            self.stats["total_connections"] = max(
                0, self.stats["total_connections"] - 1
            )

            logger.info(
                f"客户端已断开 [{camera_id}], "
                f"剩余客户端数: {len(self.active_connections[camera_id])}"
            )

            # 如果没有客户端了，清理资源
            if len(self.active_connections[camera_id]) == 0:
                self.stats["active_cameras"] = max(0, self.stats["active_cameras"] - 1)
                logger.info(f"视频流已停止 [{camera_id}] (无客户端)")

                # 清理帧缓存
                if camera_id in self.frame_cache:
                    del self.frame_cache[camera_id]
                    logger.debug(f"已清理帧缓存 [{camera_id}]")

        except Exception as e:
            logger.error(f"客户端断开处理失败 [{camera_id}]: {e}")

    def has_clients(self, camera_id: str) -> bool:
        """
        检查某个摄像头是否有客户端连接

        Args:
            camera_id: 摄像头ID

        Returns:
            是否有客户端连接
        """
        return len(self.active_connections.get(camera_id, set())) > 0

    def get_client_count(self, camera_id: str) -> int:
        """
        获取某个摄像头的客户端数量

        Args:
            camera_id: 摄像头ID

        Returns:
            客户端数量
        """
        return len(self.active_connections.get(camera_id, set()))

    async def update_frame(self, camera_id: str, frame_jpeg: bytes) -> None:
        """
        更新帧缓存并异步广播

        这个方法会被检测进程调用（每N帧调用一次）

        Args:
            camera_id: 摄像头ID
            frame_jpeg: JPEG编码的帧数据
        """
        try:
            # 1. 更新帧共享缓存 (编码一次)
            self.frame_cache[camera_id] = frame_jpeg

            # 2. 如果有客户端，放入发送队列（异步发送，不阻塞）
            if self.has_clients(camera_id):
                try:
                    # 非阻塞放入队列
                    self.send_queue.put_nowait((camera_id, frame_jpeg))
                except asyncio.QueueFull:
                    self.stats["frames_dropped"] += 1
                    logger.warning(
                        f"发送队列已满，丢帧 [{camera_id}], "
                        f"总丢帧: {self.stats['frames_dropped']}"
                    )

        except Exception as e:
            logger.error(f"更新帧失败 [{camera_id}]: {e}")

    async def _sender_loop(self) -> None:
        """后台发送循环（异步发送，不阻塞检测）"""
        logger.info("视频流发送循环已启动")

        while True:
            try:
                # 从队列获取待发送的帧
                camera_id, frame_data = await self.send_queue.get()

                # 广播给所有连接的客户端
                disconnected = set()
                clients = self.active_connections.get(camera_id, set())

                for websocket in clients:
                    try:
                        await websocket.send_bytes(frame_data)
                        self.stats["frames_sent"] += 1
                    except Exception as e:
                        logger.debug(f"发送失败，标记断开: {e}")
                        disconnected.add(websocket)

                # 清理断开的连接
                for ws in disconnected:
                    await self.disconnect(ws, camera_id)

            except asyncio.CancelledError:
                logger.info("视频流发送循环已停止")
                break
            except Exception as e:
                logger.error(f"发送循环错误: {e}")
                await asyncio.sleep(0.1)

    async def _redis_subscribe_loop(self) -> None:  # noqa: C901
        """订阅 Redis Pub/Sub 的视频帧并转发到本地发送队列.

        订阅通配频道: video:* ，消息负载为JPEG字节。
        通道名格式: video:{camera_id}
        """
        if aioredis is None:
            logger.warning("未安装 redis，跳过视频流Redis订阅")
            return

        # 构建 Redis 连接串（优先 REDIS_URL，其次三段式变量）
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            host = os.getenv("REDIS_HOST", "localhost")
            port = os.getenv("REDIS_PORT", "6379")
            db = os.getenv("REDIS_DB", "0")
            password = os.getenv("REDIS_PASSWORD")
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                redis_url = f"redis://{host}:{port}/{db}"
        else:
            # 若提供了 REDIS_URL 但未包含密码，同时存在 REDIS_PASSWORD，则自动注入密码
            try:
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(redis_url)
                has_credentials = (parsed.username is not None) or (
                    parsed.password is not None
                )
                password_env = os.getenv("REDIS_PASSWORD")
                if not has_credentials and password_env:
                    username = parsed.username or ""
                    hostname = parsed.hostname or "localhost"
                    netloc = f"{username}:{password_env}@{hostname}"
                    if parsed.port:
                        netloc += f":{parsed.port}"
                    parsed = parsed._replace(netloc=netloc)
                    redis_url = urlunparse(parsed)
            except Exception:
                # 忽略解析失败，沿用原始 REDIS_URL
                pass
        try:
            # 记录脱敏后的 URL 以便诊断（不输出密码）
            try:
                from urllib.parse import urlparse, urlunparse

                p = urlparse(redis_url)
                masked_netloc = p.netloc
                if "@" in p.netloc:
                    masked_netloc = f"***@{p.hostname}"
                    if p.port:
                        masked_netloc = f"***@{p.hostname}:{p.port}"
                masked_url = urlunparse(
                    (p.scheme, masked_netloc, p.path, p.params, p.query, p.fragment)
                )
            except Exception:
                masked_url = redis_url  # 如果解析失败，使用原始URL

            logger.info(f"视频流Redis订阅使用连接: {masked_url}")

            # 创建Redis连接
            self._redis = aioredis.from_url(redis_url, decode_responses=False)

            # 测试连接
            try:
                await self._redis.ping()
                logger.info(f"Redis连接测试成功: {masked_url}")
            except Exception as e:
                logger.error(f"Redis连接测试失败: {e}, url={masked_url}")
                raise

            # 创建pubsub并订阅
            pubsub = self._redis.pubsub()
            await pubsub.psubscribe("video:*")
            logger.info(f"视频流Redis订阅已启动: {masked_url} (pattern=video:*)")

            async for msg in pubsub.listen():
                try:
                    if msg is None:
                        continue
                    if msg.get("type") not in ("pmessage", "message"):
                        continue
                    channel: bytes = msg.get("channel")  # type: ignore
                    data: bytes = msg.get("data")  # type: ignore
                    if not isinstance(channel, (bytes, bytearray)):
                        # pmessage uses separate fields
                        channel = msg.get("pattern") or b""

                    ch = (
                        channel.decode()
                        if isinstance(channel, (bytes, bytearray))
                        else str(channel)
                    )
                    # Extract camera_id from channel name
                    camera_id = ch.split(":", 1)[-1]
                    if not camera_id:
                        continue

                    # 更新帧缓存并加入本地发送队列（不检查客户端，交由sender判断）
                    # 直接调用内部方法，避免重复编码
                    self.frame_cache[camera_id] = data
                    self.stats["frames_received"] += 1

                    # 每30帧记录一次，第一次和每100帧也记录
                    if (
                        self.stats["frames_received"] == 1
                        or self.stats["frames_received"] % 30 == 0
                        or self.stats["frames_received"] % 100 == 0
                    ):
                        logger.info(
                            f"Redis已接收帧: {self.stats['frames_received']} (camera={camera_id}, "
                            f"size={len(data)}, clients={len(self.active_connections.get(camera_id, set()))})"
                        )

                    # 检查是否有客户端连接
                    has_clients = self.has_clients(camera_id)

                    if has_clients:
                        try:
                            # 如果队列快满了，尝试丢弃旧帧，只保留最新帧
                            if self.send_queue.qsize() > 150:
                                try:
                                    # 尝试丢弃一个旧帧
                                    self.send_queue.get_nowait()
                                    self.stats["frames_dropped"] += 1
                                except asyncio.QueueEmpty:
                                    pass
                            self.send_queue.put_nowait((camera_id, data))
                            # 每100帧记录一次队列日志（减少日志输出）
                            if self.stats["frames_received"] % 100 == 0:
                                logger.debug(
                                    f"帧已加入发送队列: camera={camera_id}, queue_size={self.send_queue.qsize()}"
                                )
                        except asyncio.QueueFull:
                            self.stats["frames_dropped"] += 1
                            logger.warning(f"发送队列已满，丢弃帧: camera={camera_id}")
                    else:
                        # 只在第一次或每100帧记录一次（减少日志输出）
                        if (
                            self.stats["frames_received"] == 1
                            or self.stats["frames_received"] % 100 == 0
                        ):
                            logger.debug(
                                f"无客户端连接，跳过发送队列: camera={camera_id} (已接收{self.stats['frames_received']}帧)"
                            )
                except Exception as ie:
                    logger.debug(f"Redis订阅消息处理失败: {ie}")
        except asyncio.CancelledError:
            logger.info("视频流Redis订阅已停止")
        except Exception as e:
            # 失败时也输出脱敏后的 URL，便于排查是否为密码或地址问题
            try:
                from urllib.parse import urlparse, urlunparse

                p = urlparse(redis_url or "redis://localhost:6379/0")
                masked_netloc = p.netloc
                if "@" in p.netloc:
                    masked_netloc = f"***@{p.hostname}"
                    if p.port:
                        masked_netloc = f"***@{p.hostname}:{p.port}"
                masked_url = urlunparse(
                    (p.scheme, masked_netloc, p.path, p.params, p.query, p.fragment)
                )
                logger.warning(f"视频流Redis订阅启动失败: {e} (url={masked_url})")
            except Exception:
                logger.warning(f"视频流Redis订阅启动失败: {e}")

    async def start(self) -> None:
        """启动后台发送任务"""
        if self._sender_task is None or self._sender_task.done():
            self._sender_task = asyncio.create_task(self._sender_loop())
            logger.info("视频流发送循环任务已启动")

        # 启动Redis订阅（可选）
        enable_redis = os.getenv("VIDEO_STREAM_USE_REDIS", "1").strip() not in (
            "0",
            "false",
            "False",
        )

        logger.info(
            f"视频流Redis订阅配置: enable_redis={enable_redis}, task_exists={self._redis_task is not None}, task_done={self._redis_task.done() if self._redis_task else 'N/A'}"
        )

        if enable_redis:
            if self._redis_task is None or self._redis_task.done():
                try:
                    logger.info("正在启动Redis订阅任务...")
                    self._redis_task = asyncio.create_task(self._redis_subscribe_loop())
                    logger.info("视频流Redis订阅任务已创建")
                    # 等待一小段时间，让任务启动
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"启动Redis订阅任务失败: {e}", exc_info=True)
            else:
                logger.info("Redis订阅任务已在运行")
        else:
            logger.info("视频流Redis订阅已禁用（VIDEO_STREAM_USE_REDIS=0）")

    async def stop(self) -> None:
        """停止后台任务"""
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
            logger.info("视频流管理器已停止")
        if self._redis_task and not self._redis_task.done():
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "active_cameras_detail": {
                cam_id: len(clients)
                for cam_id, clients in self.active_connections.items()
                if clients
            },
        }


# 全局实例
_stream_manager: Optional[VideoStreamManager] = None


def get_stream_manager() -> VideoStreamManager:
    """获取视频流管理器单例"""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = VideoStreamManager()
    return _stream_manager


async def init_stream_manager() -> None:
    """初始化视频流管理器"""
    manager = get_stream_manager()
    await manager.start()


async def shutdown_stream_manager() -> None:
    """关闭视频流管理器"""
    global _stream_manager
    if _stream_manager:
        await _stream_manager.stop()
        _stream_manager = None
