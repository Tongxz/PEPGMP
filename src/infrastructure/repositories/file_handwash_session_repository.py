"""
基于文件的洗手会话仓储实现。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from src.domain.entities.handwash_session import HandwashSession
from src.domain.repositories.handwash_session_repository import (
    IHandwashSessionRepository,
)
from src.domain.value_objects.handwash_step import HandwashStepLabel, HandwashStepType


class FileHandwashSessionRepository(IHandwashSessionRepository):
    """从本地目录读取洗手会话元数据。"""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir.expanduser()

    async def list_sessions(
        self,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        camera_ids: Optional[Sequence[str]] = None,
        limit: int = 100,
    ) -> List[HandwashSession]:
        sessions: List[HandwashSession] = []
        if not self._base_dir.exists():
            return sessions

        for metadata_file in self._base_dir.glob("*/session.json"):
            if len(sessions) >= limit:
                break
            session = self._load_session(metadata_file)
            if session is None:
                continue
            if start_time and session.started_at < start_time:
                continue
            if end_time and session.ended_at > end_time:
                continue
            if camera_ids and session.camera_id not in camera_ids:
                continue
            sessions.append(session)

        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions[:limit]

    async def get_session(self, session_id: str) -> Optional[HandwashSession]:
        metadata_file = self._base_dir / session_id / "session.json"
        return self._load_session(metadata_file)

    async def save_session(self, session: HandwashSession) -> str:
        session_dir = self._base_dir / session.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "session_id": session.session_id,
            "camera_id": session.camera_id,
            "video_path": str(session.video_path),
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "step_labels": [
                {
                    "step": label.step.value,
                    "start_offset": label.start_offset,
                    "end_offset": label.end_offset,
                    "compliant": label.compliant,
                    "metadata": label.metadata,
                }
                for label in session.step_labels
            ],
            "metadata": session.metadata,
        }
        (session_dir / "session.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False)
        )
        return session.session_id

    def _load_session(self, metadata_file: Path) -> Optional[HandwashSession]:
        try:
            data = json.loads(metadata_file.read_text())
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None

        video_path = Path(data.get("video_path", ""))
        if not video_path.exists():
            return None

        try:
            started_at = datetime.fromisoformat(data["started_at"])
            ended_at = datetime.fromisoformat(data["ended_at"])
        except (KeyError, ValueError):
            return None

        step_labels = []
        for raw_label in data.get("step_labels", []):
            try:
                step_type = HandwashStepType(raw_label["step"])
            except (KeyError, ValueError):
                step_type = HandwashStepType.OTHER
            label = HandwashStepLabel(
                step=step_type,
                start_offset=float(raw_label.get("start_offset", 0.0)),
                end_offset=float(raw_label.get("end_offset", 0.0)),
                compliant=bool(raw_label.get("compliant", True)),
                metadata=raw_label.get("metadata"),
            )
            step_labels.append(label)

        return HandwashSession(
            session_id=data.get("session_id", metadata_file.parent.name),
            camera_id=data.get("camera_id", "unknown"),
            video_path=video_path,
            started_at=started_at,
            ended_at=ended_at,
            step_labels=step_labels,
            metadata=data.get("metadata", {}),
        )
