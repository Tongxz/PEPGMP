import asyncio
import json
import logging
import time
from typing import Dict, List

from fastapi import WebSocket

from src.core.tracker import MultiObjectTracker

logger = logging.getLogger(__name__)


class WebSocketSession:
    """管理单个WebSocket会话的状态."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.tracker = MultiObjectTracker()
        self.last_frame_time = time.time()
        self.violation_cooldowns: Dict[Tuple[int, str], float] = {}

    def reset_tracker(self):
        """重置跟踪器."""
        self.tracker = MultiObjectTracker()


class ConnectionManager:
    def __init__(self):
        self.active_sessions: Dict[WebSocket, WebSocketSession] = {}
        self.heartbeat_interval = 30  # Heartbeat interval (seconds)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        session = WebSocketSession(websocket)
        self.active_sessions[websocket] = session
        logger.info(
            f"WebSocket connection established, current sessions: {len(self.active_sessions)}"
        )
        # Start heartbeat task
        asyncio.create_task(self._heartbeat(websocket))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_sessions:
            del self.active_sessions[websocket]
        logger.info(
            f"WebSocket connection disconnected, current sessions: {len(self.active_sessions)}"
        )

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if self.active_sessions:
            for session in list(self.active_sessions.values()):
                try:
                    await session.websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to broadcast message: {e}")
                    self.disconnect(session.websocket)

    async def _heartbeat(self, websocket: WebSocket):
        """Heartbeat task to keep connection alive."""
        try:
            while websocket in self.active_sessions:
                await asyncio.sleep(self.heartbeat_interval)
                if websocket in self.active_sessions:
                    await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception as e:
            logger.info(f"Heartbeat ended: {e}")
            self.disconnect(websocket)


# Singleton instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return manager
