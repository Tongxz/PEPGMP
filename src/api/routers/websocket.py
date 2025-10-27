"""WebSocket路由模块.

提供实时图像检测的WebSocket端点.
"""
import asyncio
import base64
import json
import logging
import os

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK

from src.api.redis_listener import CAMERA_STATS_CACHE
from src.services.websocket_service import (
    ConnectionManager,
    WebSocketSession,
    get_connection_manager,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# 状态推送连接管理器
status_connections: set[WebSocket] = set()


@router.websocket("/ws/status")
async def websocket_status_endpoint(websocket: WebSocket):
    """WebSocket状态推送端点."""
    await websocket.accept()
    status_connections.add(websocket)
    logger.info(f"状态推送客户端已连接，当前连接数: {len(status_connections)}")

    try:
        # 发送初始状态
        await send_all_camera_status(websocket)

        # 保持连接并处理心跳
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("状态推送客户端已断开连接")
    finally:
        status_connections.discard(websocket)
        logger.info(f"状态推送客户端已移除，当前连接数: {len(status_connections)}")


async def send_all_camera_status(websocket: WebSocket):
    """发送所有摄像头的状态信息."""
    try:
        # 获取所有摄像头的状态
        all_status = {}
        for camera_id, stats_data in CAMERA_STATS_CACHE.items():
            if isinstance(stats_data, dict) and stats_data.get("type") == "stats":
                all_status[camera_id] = {
                    "camera_id": camera_id,
                    "timestamp": stats_data.get("timestamp"),
                    "data": stats_data.get("data", {}),
                }

        # 发送状态更新
        message = {
            "type": "status_update",
            "data": all_status,
            "timestamp": asyncio.get_event_loop().time(),
        }
        await websocket.send_text(json.dumps(message))
    except Exception as e:
        logger.error(f"发送状态信息失败: {e}")


async def broadcast_status_update(camera_id: str, stats_data: dict):
    """向所有连接的客户端广播状态更新."""
    if not status_connections:
        return

    message = {
        "type": "status_update",
        "camera_id": camera_id,
        "data": stats_data,
        "timestamp": asyncio.get_event_loop().time(),
    }

    message_text = json.dumps(message)
    disconnected = set()

    for websocket in status_connections:
        try:
            await websocket.send_text(message_text)
        except Exception:
            disconnected.add(websocket)

    # 清理断开的连接
    for websocket in disconnected:
        status_connections.discard(websocket)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, manager: ConnectionManager = Depends(get_connection_manager)
):
    """WebSocket检测端点."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "image":
                    session = manager.active_sessions.get(websocket)
                    if session:
                        await process_image_detection(session, message)
                elif message_type == "pong":
                    pass  # Heartbeat response
                else:
                    logger.warning(f"Unknown message type received: {message_type}")

            except json.JSONDecodeError:
                logger.warning("Received invalid JSON message.")
                try:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Invalid JSON format"})
                    )
                except (WebSocketDisconnect, ConnectionClosedOK):
                    pass  # Client likely disconnected
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}", exc_info=True)
                try:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": f"Processing error: {str(e)}"}
                        )
                    )
                except (WebSocketDisconnect, ConnectionClosedOK):
                    pass  # Client likely disconnected

    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    finally:
        manager.disconnect(websocket)


async def process_image_detection(session: WebSocketSession, message: dict):
    """处理图像检测请求."""
    from src.services.detection_service import process_tracked_frame

    try:
        image_data = message.get("data")
        if not image_data:
            return

        if image_data.startswith("data:image"):
            image_data = image_data.split(",")[1]

        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        # 从 app state 获取检测管道
        optimized_pipeline = session.websocket.scope["app"].state.optimized_pipeline

        # 调用新的带跟踪的处理函数
        detection_result = await asyncio.get_event_loop().run_in_executor(
            None, process_tracked_frame, session, frame, optimized_pipeline
        )

        # 发送检测结果
        try:
            await session.websocket.send_text(json.dumps(detection_result))
        except (WebSocketDisconnect, ConnectionClosedOK):
            pass  # Client likely disconnected

    except Exception as e:
        logger.error(f"Image detection processing error: {e}", exc_info=True)
        try:
            await session.websocket.send_text(
                json.dumps({"type": "error", "message": f"Detection failed: {str(e)}"})
            )
        except (WebSocketDisconnect, ConnectionClosedOK):
            pass  # Client likely disconnected


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    try:
        try:
            from urllib.parse import parse_qs

            qs = (
                parse_qs(websocket.url.query or "") if hasattr(websocket, "url") else {}
            )
            etype_filter = None
            if isinstance(qs, dict):
                vals = qs.get("etype")
                if vals and len(vals) > 0:
                    etype_filter = str(vals[0])
        except Exception:
            etype_filter = None

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        events_file = os.path.join(project_root, "logs", "events_record.jsonl")

        last_pos = 0
        while True:
            try:
                if not os.path.exists(events_file):
                    await asyncio.sleep(0.5)
                    continue
                with open(events_file, "r", encoding="utf-8") as f:
                    if last_pos == 0:
                        f.seek(0, os.SEEK_END)
                        last_pos = f.tell()
                    else:
                        f.seek(last_pos)
                    lines = f.readlines()
                    last_pos = f.tell()
                if lines:
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if etype_filter and str(obj.get("type")) != etype_filter:
                                continue
                            await websocket.send_text(
                                json.dumps({"type": "event", "data": obj})
                            )
                        except Exception:
                            continue
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    pass
                await asyncio.sleep(0.5)
            except (WebSocketDisconnect, ConnectionClosedOK):
                break
            except Exception as e:
                logger.debug(f"ws/events tail error: {e}")
                await asyncio.sleep(0.5)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
