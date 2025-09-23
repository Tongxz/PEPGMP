from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class UODPerson:
    track_id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float
    has_hairnet: bool = False
    hairnet_confidence: float = 0.0
    hand_regions: Optional[List[Dict[str, Any]]] = None
    region: Optional[str] = None
    ts: Optional[float] = None
    hand_in_sink: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
