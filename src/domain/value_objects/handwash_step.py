"""
洗手步骤值对象定义。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class HandwashStepType(str, Enum):
    """洗手流程中的标准步骤类型。"""

    WET = "wet"
    SOAP = "soap"
    SCRUB = "scrub"
    RINSE = "rinse"
    DRY = "dry"
    TURN_OFF = "turn_off"
    OTHER = "other"


@dataclass(frozen=True)
class HandwashStepLabel:
    """洗手步骤标注信息。"""

    step: HandwashStepType
    start_offset: float
    end_offset: float
    compliant: bool = True
    metadata: Optional[Dict[str, Any]] = None

    def duration(self) -> float:
        """步骤持续时长（秒）。"""
        return max(0.0, self.end_offset - self.start_offset)
