"""
视频流WebSocket API

提供实时视频流推送的WebSocket端点
"""

from typing import Optional

from fastapi import APIRouter, Body, Header, Request, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel, Field

from src.services.video_stream_manager import get_stream_manager

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

router = APIRouter(prefix="/video-stream", tags=["视频流"])


class VideoStreamConfigRequest(BaseModel):
    """视频流配置请求"""

    stream_interval: Optional[int] = Field(
        None, ge=1, le=30, description="视频流推送间隔（帧数），1表示逐帧", example=3
    )
    log_interval: Optional[int] = Field(None, ge=1, description="检测间隔（帧数）", example=120)
    frame_by_frame: Optional[bool] = Field(
        None, description="是否逐帧模式（stream_interval=1）", example=False
    )


class VideoStreamConfigResponse(BaseModel):
    """视频流配置响应"""

    camera_id: str
    stream_interval: int
    log_interval: int
    frame_by_frame: bool
    message: str


@router.websocket("/ws/{camera_id}")
async def video_stream_websocket(
    websocket: WebSocket,
    camera_id: str,
):
    """
    视频流WebSocket端点

    Args:
        websocket: WebSocket连接
        camera_id: 摄像头ID

    WebSocket协议:
        - 客户端连接后，服务器自动推送视频帧（JPEG格式）
        - 客户端可以发送 "ping" 进行心跳检测，服务器回复 "pong"
        - 服务器推送格式: 二进制JPEG数据
    """
    stream_manager = get_stream_manager()

    try:
        # 建立连接
        await stream_manager.connect(websocket, camera_id)
        logger.info(f"WebSocket已连接: camera={camera_id}")

        # 保持连接，接收客户端消息
        while True:
            try:
                # 接收客户端消息（主要用于心跳）
                data = await websocket.receive_text()

                # 处理心跳
                if data == "ping":
                    await websocket.send_text("pong")
                    logger.debug(f"心跳响应: camera={camera_id}")

            except WebSocketDisconnect:
                logger.info(f"客户端主动断开: camera={camera_id}")
                break
            except Exception as e:
                logger.warning(f"接收消息错误: {e}, camera={camera_id}")
                break

    except Exception as e:
        logger.error(f"WebSocket错误: {e}, camera={camera_id}")

    finally:
        # 清理连接
        await stream_manager.disconnect(websocket, camera_id)
        logger.info(f"WebSocket已清理: camera={camera_id}")


@router.get("/stats", summary="获取视频流统计")
async def get_video_stream_stats():
    """
    获取视频流统计信息

    Returns:
        - total_connections: 总连接数
        - active_cameras: 活跃摄像头数
        - frames_sent: 已发送帧数
        - frames_dropped: 丢弃帧数
        - active_cameras_detail: 每个摄像头的客户端数
    """
    stream_manager = get_stream_manager()
    return stream_manager.get_stats()


@router.get("/status/{camera_id}", summary="获取摄像头视频流状态")
async def get_camera_stream_status(camera_id: str):
    """
    获取某个摄像头的视频流状态

    Args:
        camera_id: 摄像头ID

    Returns:
        - has_clients: 是否有客户端连接
        - client_count: 客户端数量
    """
    stream_manager = get_stream_manager()
    return {
        "camera_id": camera_id,
        "has_clients": stream_manager.has_clients(camera_id),
        "client_count": stream_manager.get_client_count(camera_id),
    }


@router.post("/frame/{camera_id}", summary="接收视频帧(HTTP推送)")
async def receive_frame(
    camera_id: str,
    request: Request,
    x_video_token: Optional[str] = Header(None, convert_underscores=False),
):
    """
    HTTP方式接收摄像头帧数据（JPEG二进制）并广播给所有连接的客户端。

    安全：若设置环境变量 VIDEO_PUSH_TOKEN，将校验请求头 X-Video-Token。
    """
    import os

    expected = os.getenv("VIDEO_PUSH_TOKEN")
    if expected:
        if not x_video_token or x_video_token != expected:
            raise raise_http_exception(
                status_code=401,
                message="Unauthorized",
                error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            )

    body = await request.body()
    if not body:
        raise raise_http_exception(
            status_code=400,
            message="Empty body",
            error_code=ErrorCode.VALIDATION_ERROR,
        )

    sm = get_stream_manager()
    await sm.update_frame(camera_id, body)
    return {"ok": True, "camera_id": camera_id, "size": len(body)}


@router.post("/config/{camera_id}", summary="配置视频流参数")
async def update_video_stream_config(
    camera_id: str,
    config: VideoStreamConfigRequest = Body(...),
):
    """
    更新视频流配置

    Args:
        camera_id: 摄像头ID
        config: 视频流配置

    Returns:
        配置响应
    """
    import os

    import redis

    try:
        # 处理逐帧模式
        if config.frame_by_frame is not None:
            if config.frame_by_frame:
                stream_interval = 1
            else:
                stream_interval = config.stream_interval or 3
        else:
            stream_interval = config.stream_interval or 3

        # 保存配置到Redis（用于检测进程读取）
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                r = redis.from_url(redis_url)
                config_key = f"video_stream:config:{camera_id}"
                config_data = {
                    "stream_interval": stream_interval,
                    "log_interval": config.log_interval,
                    "frame_by_frame": stream_interval == 1,
                }
                # 只保存非None的配置
                config_data = {k: v for k, v in config_data.items() if v is not None}
                r.hset(config_key, mapping=config_data)
                r.expire(config_key, 3600)  # 1小时过期
                logger.info(f"视频流配置已保存到Redis: camera={camera_id}, config={config_data}")
            except Exception as e:
                logger.warning(f"保存配置到Redis失败: {e}，将仅返回配置信息")

        return VideoStreamConfigResponse(
            camera_id=camera_id,
            stream_interval=stream_interval,
            log_interval=config.log_interval or 120,
            frame_by_frame=stream_interval == 1,
            message="配置已更新，检测进程将在下次读取时应用新配置",
        )
    except Exception as e:
        logger.error(f"更新视频流配置失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="更新配置失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )


@router.get("/config/{camera_id}", summary="获取视频流配置")
async def get_video_stream_config(camera_id: str):
    """
    获取当前视频流配置

    Args:
        camera_id: 摄像头ID

    Returns:
        当前配置
    """
    import os

    import redis

    try:
        # 从Redis读取配置
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                r = redis.from_url(redis_url)
                config_key = f"video_stream:config:{camera_id}"
                config_data = r.hgetall(config_key)
                if config_data:
                    # 解码bytes为字符串
                    config_data = {
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in config_data.items()
                    }
                    return {
                        "camera_id": camera_id,
                        "stream_interval": int(config_data.get("stream_interval", 3)),
                        "log_interval": int(config_data.get("log_interval", 120)),
                        "frame_by_frame": config_data.get(
                            "frame_by_frame", "False"
                        ).lower()
                        == "true",
                    }
            except Exception as e:
                logger.warning(f"从Redis读取配置失败: {e}")

        # 返回默认配置
        return {
            "camera_id": camera_id,
            "stream_interval": int(os.getenv("VIDEO_STREAM_INTERVAL", "3")),
            "log_interval": 120,
            "frame_by_frame": False,
        }
    except Exception as e:
        logger.error(f"获取视频流配置失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取配置失败",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details=str(e),
        )
