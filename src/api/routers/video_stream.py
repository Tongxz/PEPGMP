"""
视频流WebSocket API

提供实时视频流推送的WebSocket端点
"""

from typing import Optional

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from loguru import logger

from src.services.video_stream_manager import get_stream_manager

router = APIRouter(prefix="/video-stream", tags=["视频流"])


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
            raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    sm = get_stream_manager()
    await sm.update_frame(camera_id, body)
    return {"ok": True, "camera_id": camera_id, "size": len(body)}
