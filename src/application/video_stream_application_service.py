"""
视频流应用服务

负责处理视频流的编码、调整大小和推送，
将检测循环与视频流基础设施解耦。
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoStreamApplicationService:
    """
    视频流应用服务

    职责：
    1. 调整帧大小
    2. 编码为JPEG
    3. 通过视频流管理器推送

    不包含：
    - WebSocket连接管理（由 VideoStreamManager 处理）
    - Redis发布/订阅（由 VideoStreamManager 处理）
    """

    def __init__(self, stream_manager=None):
        """
        初始化视频流应用服务

        Args:
            stream_manager: 视频流管理器（可选，延迟初始化）
        """
        self._stream_manager = stream_manager
        logger.info("视频流应用服务已初始化")

    @property
    def stream_manager(self):
        """懒加载视频流管理器"""
        if self._stream_manager is None:
            try:
                from src.services.video_stream_manager import get_stream_manager

                self._stream_manager = get_stream_manager()
                logger.info("视频流管理器已加载")
            except Exception as e:
                logger.warning(f"无法加载视频流管理器: {e}")
                return None
        return self._stream_manager

    def _resize_frame(
        self,
        frame: np.ndarray,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
    ) -> np.ndarray:
        """
        调整帧大小

        Args:
            frame: 原始帧
            target_width: 目标宽度（None表示不调整）
            target_height: 目标高度（None表示不调整）

        Returns:
            调整后的帧
        """
        if target_width is None or target_height is None:
            return frame

        height, width = frame.shape[:2]

        # 如果尺寸相同，不需要调整
        if width == target_width and height == target_height:
            return frame

        # 调整大小
        resized = cv2.resize(
            frame,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,  # 缩小时使用INTER_AREA效果更好
        )

        logger.debug(f"帧大小已调整: {width}x{height} -> {target_width}x{target_height}")
        return resized

    def _encode_jpeg(self, frame: np.ndarray, quality: int = 60) -> bytes:
        """
        编码帧为JPEG格式

        Args:
            frame: 视频帧
            quality: JPEG质量（1-100）

        Returns:
            JPEG字节数据

        Raises:
            RuntimeError: 编码失败
        """
        # 确保质量在有效范围内
        quality = max(1, min(100, quality))

        # 编码为JPEG
        success, encoded = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )

        if not success:
            raise RuntimeError("JPEG编码失败")

        jpeg_data = encoded.tobytes()
        logger.debug(f"帧已编码: 质量={quality}, 大小={len(jpeg_data)} bytes")

        return jpeg_data

    async def _push_via_redis(self, camera_id: str, jpeg_data: bytes) -> bool:
        """
        通过Redis发布视频帧（用于跨进程通信）

        Args:
            camera_id: 摄像头ID
            jpeg_data: JPEG编码的帧数据

        Returns:
            是否成功发布
        """
        try:
            import os

            # 检查是否启用Redis
            enable_redis = os.getenv("VIDEO_STREAM_USE_REDIS", "1").strip() not in (
                "0",
                "false",
                "False",
            )
            if not enable_redis:
                return False

            # 尝试导入redis
            try:
                import redis.asyncio as aioredis
            except ImportError:
                logger.debug("未安装 redis，跳过Redis推送")
                return False

            # 构建 Redis 连接串
            # 优先使用REDIS_URL，如果没有则从单独的环境变量构建
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                host = os.getenv("REDIS_HOST", "localhost")
                port = os.getenv("REDIS_PORT", "6379")
                db = os.getenv("REDIS_DB", "0")
                password = os.getenv("REDIS_PASSWORD")

                # 构建Redis URL
                if password:
                    redis_url = f"redis://:{password}@{host}:{port}/{db}"
                else:
                    redis_url = f"redis://{host}:{port}/{db}"

                masked_url = (
                    redis_url.replace(password or "", "***") if password else redis_url
                )
                logger.info(f"使用环境变量构建Redis URL: {masked_url}")

            # 连接到Redis并发布
            redis_client = aioredis.from_url(redis_url, decode_responses=False)
            try:
                channel = f"video:{camera_id}"
                subscribers = await redis_client.publish(channel, jpeg_data)
                logger.info(
                    f"Redis发布成功: channel={channel}, "
                    f"size={len(jpeg_data)} bytes, subscribers={subscribers}"
                )
                # 如果subscribers为0，说明没有订阅者，但发布仍然成功
                return True
            finally:
                await redis_client.close()

        except Exception as e:
            logger.warning(f"通过Redis推送失败: camera={camera_id}, error={e}")
            return False

    async def push_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        quality: int = 60,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
    ) -> bool:
        """
        推送视频帧

        处理流程：
        1. 调整帧大小（如果指定）
        2. 编码为JPEG
        3. 通过Redis发布（检测进程环境）或直接推送（API服务器环境）

        Args:
            camera_id: 摄像头ID
            frame: 视频帧（numpy数组）
            quality: JPEG质量（1-100，默认60）
            target_width: 目标宽度（None表示不调整）
            target_height: 目标高度（None表示不调整）

        Returns:
            是否成功推送
        """
        try:
            # 1. 调整大小
            if target_width and target_height:
                frame = self._resize_frame(frame, target_width, target_height)

            # 2. 编码为JPEG
            jpeg_data = self._encode_jpeg(frame, quality)

            # 3. 推送方式选择：
            #    - 如果可以使用Redis，优先使用Redis发布（跨进程通信）
            #    - 否则使用本地VideoStreamManager（同进程）
            redis_success = await self._push_via_redis(camera_id, jpeg_data)
            if redis_success:
                logger.info(
                    f"视频帧已通过Redis推送: camera={camera_id}, size={len(jpeg_data)} bytes"
                )
                return True

            # 回退到本地VideoStreamManager（如果可用）
            if self.stream_manager is not None:
                await self.stream_manager.update_frame(camera_id, jpeg_data)
                logger.info(
                    f"视频帧已通过本地管理器推送: camera={camera_id}, size={len(jpeg_data)} bytes"
                )
                return True

            logger.debug("视频流管理器不可用，跳过推送")
            return False

        except Exception as e:
            logger.error(f"推送视频帧失败: camera={camera_id}, error={e}")
            return False

    async def push_frame_from_file(
        self,
        camera_id: str,
        image_path: str,
        quality: int = 60,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
    ) -> bool:
        """
        从文件推送视频帧

        Args:
            camera_id: 摄像头ID
            image_path: 图像文件路径
            quality: JPEG质量
            target_width: 目标宽度
            target_height: 目标高度

        Returns:
            是否成功推送
        """
        try:
            # 读取图像
            frame = cv2.imread(image_path)
            if frame is None:
                raise ValueError(f"无法读取图像: {image_path}")

            # 推送
            return await self.push_frame(
                camera_id, frame, quality, target_width, target_height
            )

        except Exception as e:
            logger.error(f"从文件推送视频帧失败: {e}")
            return False

    def get_stream_status(self, camera_id: str) -> dict:
        """
        获取视频流状态

        Args:
            camera_id: 摄像头ID

        Returns:
            状态字典
        """
        if self.stream_manager is None:
            return {
                "available": False,
                "message": "视频流管理器不可用",
            }

        try:
            client_count = self.stream_manager.get_client_count(camera_id)
            has_frame = self.stream_manager.has_frame(camera_id)

            return {
                "available": True,
                "camera_id": camera_id,
                "client_count": client_count,
                "has_frame": has_frame,
            }
        except Exception as e:
            logger.error(f"获取视频流状态失败: {e}")
            return {
                "available": False,
                "error": str(e),
            }


# 单例实例
_video_stream_service: Optional[VideoStreamApplicationService] = None


def get_video_stream_service() -> VideoStreamApplicationService:
    """
    获取视频流应用服务的单例实例

    Returns:
        VideoStreamApplicationService实例
    """
    global _video_stream_service

    if _video_stream_service is None:
        _video_stream_service = VideoStreamApplicationService()

    return _video_stream_service
