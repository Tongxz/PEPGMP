"""WebSocket路由模块.

提供实时图像检测的WebSocket端点.
"""
import asyncio
import base64
import json
import logging
from io import BytesIO
import os

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from PIL import Image
from websockets.exceptions import ConnectionClosedOK

from src.services.websocket_service import (
    ConnectionManager,
    WebSocketSession,
    get_connection_manager,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
                    pass # Client likely disconnected
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}", exc_info=True)
                try:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": f"Processing error: {str(e)}"})
                    )
                except (WebSocketDisconnect, ConnectionClosedOK):
                    pass # Client likely disconnected

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
            pass # Client likely disconnected

    except Exception as e:
        logger.error(f"Image detection processing error: {e}", exc_info=True)
        try:
            await session.websocket.send_text(
                json.dumps({"type": "error", "message": f"Detection failed: {str(e)}"})
            )
        except (WebSocketDisconnect, ConnectionClosedOK):
            pass # Client likely disconnected


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    try:
        try:
            from urllib.parse import parse_qs

            qs = parse_qs(websocket.url.query or "") if hasattr(websocket, "url") else {}
            etype_filter = None
            if isinstance(qs, dict):
                vals = qs.get("etype")
                if vals and len(vals) > 0:
                    etype_filter = str(vals[0])
        except Exception:
            etype_filter = None

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
                            await websocket.send_text(json.dumps({"type": "event", "data": obj}))
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
