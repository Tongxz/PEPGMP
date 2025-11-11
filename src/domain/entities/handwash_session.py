"""
洗手会话领域实体。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.value_objects.handwash_step import HandwashStepLabel


@dataclass
class HandwashSession:
    """
    洗手会话实体，表示一次连续的洗手行为片段。
    """

    session_id: str
    camera_id: str
    video_path: Path
    started_at: datetime
    ended_at: datetime
    step_labels: List[HandwashStepLabel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def duration(self) -> float:
        """会话持续时长（秒）。"""
        return max(0.0, (self.ended_at - self.started_at).total_seconds())

    def is_compliant(self) -> bool:
        """判断整个流程是否合规。"""
        return all(label.compliant for label in self.step_labels)
