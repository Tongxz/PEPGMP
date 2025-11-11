"""
洗手会话仓储接口定义。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Protocol, Sequence

from src.domain.entities.handwash_session import HandwashSession


class IHandwashSessionRepository(Protocol):
    """洗手会话仓储接口。"""

    async def list_sessions(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        camera_ids: Optional[Sequence[str]] = None,
        limit: int = 100,
    ) -> List[HandwashSession]:
        """根据时间范围和摄像头筛选洗手会话列表。"""

    async def get_session(self, session_id: str) -> Optional[HandwashSession]:
        """根据ID获取单个洗手会话。"""

    async def save_session(self, session: HandwashSession) -> str:
        """保存或更新洗手会话，返回会话ID。"""
