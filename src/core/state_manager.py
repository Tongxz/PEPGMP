"""
状态管理器

负责：
1. 时间窗状态稳定判定
2. 事件边界检测
3. 状态转换管理
4. 与FrameMetadataManager集成
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.frame_metadata import FrameMetadata
from src.core.frame_metadata_manager import FrameMetadataManager

logger = logging.getLogger(__name__)


@dataclass
class DetectionState:
    """检测状态"""
    state_type: str  # 'normal', 'violation', 'transition'
    confidence: float
    frame_count: int
    start_frame_id: str  # 使用frame_id而不是frame编号
    last_update_frame_id: str
    stability_frames: int = 5
    confidence_threshold: float = 0.7
    history: deque = field(default_factory=lambda: deque(maxlen=10))  # 最近10帧的置信度历史


class StateManager:
    """状态管理器 - 使用FrameMetadata作为数据载体
    
    功能：
    1. 时间窗状态稳定判定：连续N帧置信度>阈值才输出稳定状态
    2. 事件边界检测：检测状态转换（normal -> violation 或 violation -> normal）
    3. 状态转换管理：管理状态转换历史
    """
    
    def __init__(
        self,
        stability_frames: int = 5,
        confidence_threshold: float = 0.7,
        transition_threshold: float = 0.3,  # 状态转换阈值
        frame_metadata_manager: Optional[FrameMetadataManager] = None,
    ):
        """
        初始化状态管理器
        
        Args:
            stability_frames: 稳定帧数阈值（连续N帧才判定为稳定）
            confidence_threshold: 置信度阈值
            transition_threshold: 状态转换阈值（置信度变化超过此值才判定为转换）
            frame_metadata_manager: 帧元数据管理器（可选）
        """
        self.stability_frames = stability_frames
        self.confidence_threshold = confidence_threshold
        self.transition_threshold = transition_threshold
        self.frame_metadata_manager = frame_metadata_manager
        
        # 状态索引：track_id -> DetectionState
        self.states: Dict[str, DetectionState] = {}
        
        logger.info(
            f"StateManager initialized: stability_frames={stability_frames}, "
            f"confidence_threshold={confidence_threshold}"
        )
    
    def update_state(
        self,
        frame_meta: FrameMetadata,
        current_confidence: float,
    ) -> Tuple[str, float]:
        """
        更新状态并返回稳定状态
        
        Args:
            frame_meta: 帧元数据（包含frame_id, timestamp等）
            current_confidence: 当前置信度
        
        Returns:
            (stable_state_type, stable_confidence)
        """
        # 获取track_id（从metadata或使用frame_id）
        track_id = frame_meta.metadata.get("track_id") or frame_meta.frame_id
        
        # 获取或创建状态
        if track_id not in self.states:
            self.states[track_id] = DetectionState(
                state_type="normal",
                confidence=0.0,
                frame_count=0,
                start_frame_id=frame_meta.frame_id,
                last_update_frame_id=frame_meta.frame_id,
                stability_frames=self.stability_frames,
                confidence_threshold=self.confidence_threshold,
            )
        
        state = self.states[track_id]
        
        # 更新状态历史
        state.history.append(current_confidence)
        state.frame_count += 1
        state.last_update_frame_id = frame_meta.frame_id
        
        # 判定当前状态类型
        current_state_type = self._determine_state_type(current_confidence)
        
        # 检测事件边界（状态转换）
        has_transition = self._detect_event_boundary(
            state,
            current_state_type,
            current_confidence
        )
        
        if has_transition:
            # 状态转换：重置稳定计数
            state.state_type = current_state_type
            state.start_frame_id = frame_meta.frame_id
            state.frame_count = 1
            logger.debug(
                f"State transition detected: track_id={track_id}, "
                f"new_state={current_state_type}, confidence={current_confidence:.3f}"
            )
        else:
            # 状态保持：更新状态类型（如果置信度足够高）
            if current_confidence >= self.confidence_threshold:
                state.state_type = current_state_type
        
        # 时间窗稳定判定
        stable_state, stable_confidence = self._check_stability(state)
        
        # 更新FrameMetadata的状态信息
        if self.frame_metadata_manager:
            self.frame_metadata_manager.update_state(
                frame_meta.frame_id,
                stable_state,
                stable_confidence
            )
        
        return stable_state, stable_confidence
    
    def _determine_state_type(self, confidence: float) -> str:
        """根据置信度判定状态类型"""
        if confidence >= self.confidence_threshold:
            return "violation"
        elif confidence < self.confidence_threshold * 0.5:
            return "normal"
        else:
            return "transition"
    
    def _detect_event_boundary(
        self,
        state: DetectionState,
        current_state_type: str,
        current_confidence: float,
    ) -> bool:
        """检测事件边界（状态转换）"""
        # 如果状态类型改变，判定为转换
        if state.state_type != current_state_type:
            # 检查置信度变化是否超过阈值
            if len(state.history) >= 2:
                prev_confidence = state.history[-2]
                confidence_change = abs(current_confidence - prev_confidence)
                if confidence_change >= self.transition_threshold:
                    return True
            else:
                # 历史不足，直接判定为转换
                return True
        
        return False
    
    def _check_stability(
        self,
        state: DetectionState,
    ) -> Tuple[str, float]:
        """
        检查状态稳定性
        
        返回：
            (stable_state_type, stable_confidence)
        """
        if not state.history:
            return state.state_type, 0.0
        
        # 计算平均置信度
        avg_confidence = sum(state.history) / len(state.history)
        
        if len(state.history) < self.stability_frames:
            # 历史不足，返回当前状态但置信度降低（表示不稳定）
            return state.state_type, avg_confidence * 0.5  # 降低置信度表示不稳定
        
        # 历史足够，检查最近N帧的稳定性
        recent_confidences = list(state.history)[-self.stability_frames:]
        avg_confidence = sum(recent_confidences) / len(recent_confidences)
        
        # 如果平均置信度超过阈值，判定为稳定
        if avg_confidence >= self.confidence_threshold:
            stable_state = "violation"
        elif avg_confidence < self.confidence_threshold * 0.5:
            stable_state = "normal"
        else:
            stable_state = "transition"
        
        return stable_state, avg_confidence
    
    def get_state(self, track_id: str) -> Optional[DetectionState]:
        """获取指定track的状态"""
        return self.states.get(track_id)
    
    def clear_state(self, track_id: str):
        """清除指定track的状态"""
        if track_id in self.states:
            del self.states[track_id]
            logger.debug(f"Cleared state for track_id={track_id}")
    
    def clear_all_states(self):
        """清除所有状态"""
        self.states.clear()
        logger.info("Cleared all states")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tracks": len(self.states),
            "stability_frames": self.stability_frames,
            "confidence_threshold": self.confidence_threshold,
            "states": {
                track_id: {
                    "state_type": state.state_type,
                    "confidence": state.confidence,
                    "frame_count": state.frame_count,
                }
                for track_id, state in self.states.items()
            },
        }

