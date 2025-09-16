from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import time
import logging


@dataclass
class PersonState:
    track_id: int
    has_hairnet: bool = False
    current_region: Optional[str] = None
    visited_regions: Set[str] = field(default_factory=set)
    enter_ts: Dict[str, float] = field(default_factory=dict)  # region -> enter timestamp
    status: str = "IN_PROGRESS"  # COMPLIANT / VIOLATION
    # 连续性计数：用于平滑 HANDWASHING_ACTIVE
    hand_in_sink_consec: int = 0


@dataclass
class ProcessConfig:
    enable: bool = False
    min_dwell_seconds_stand: float = 3.0
    min_dwell_seconds_sink: float = 3.0
    min_dwell_seconds_dryer: float = 3.0
    cooldown_seconds: float = 10.0
    region_entrance: str = "入口线"
    region_stand: str = "洗手站立区域"
    region_sink: str = "洗手池区域"
    region_dryer: str = "烘干区域"
    region_work: str = "工作区区域"
    # 新增：HANDWASHING_ACTIVE 连续帧阈值
    handwash_min_consecutive: int = 3


@dataclass
class Event:
    type: str
    track_id: int
    ts: float
    evidence: Dict[str, Any] = field(default_factory=dict)


class ProcessEngine:
    def __init__(self, cfg: ProcessConfig) -> None:
        self.cfg = cfg
        self._persons: Dict[int, PersonState] = {}
        self._cooldown: Dict[Tuple[int, str], float] = {}
        # 局部日志器
        global logger
        try:
            logger
        except NameError:
            logger = logging.getLogger(__name__)

    def step(
        self,
        uod_persons: List[Dict[str, Any]],  # 轻依赖：内部先用 dict，后续可换 dataclass
        region_changes: Optional[List[Tuple[int, Optional[str], Optional[str]]]] = None,
    ) -> List[Event]:
        """
        输入：
          - uod_persons: [{track_id, has_hairnet, region, ts, bbox, ...}]
          - region_changes: [(track_id, prev_region, new_region)] 可选；若未提供则从 uod 中推断
        输出：
          - 事件列表（仅记录，不做抓拍）
        """
        if not self.cfg.enable:
            return []

        now = time.time()
        events: List[Event] = []

        # 更新状态并计算区域变更
        local_changes: List[Tuple[int, Optional[str], Optional[str]]] = []
        seen_tids: Set[int] = set()
        for p in uod_persons:
            tid = int(p.get("track_id", -1))
            if tid < 0:
                continue
            seen_tids.add(tid)
            st = self._persons.get(tid) or PersonState(track_id=tid)
            st.has_hairnet = bool(p.get("has_hairnet", st.has_hairnet))
            prev_region = st.current_region
            region = p.get("region")
            if isinstance(region, str) and region:
                st.current_region = region
                st.visited_regions.add(region)
                if region not in st.enter_ts:
                    st.enter_ts[region] = now
                if prev_region != region:
                    local_changes.append((tid, prev_region, region))
            else:
                # 当前帧不在任何区域：若之前在某区域，生成离开事件
                if isinstance(prev_region, str) and prev_region:
                    st.current_region = None
                    local_changes.append((tid, prev_region, None))
            self._persons[tid] = st

        # 推断区域变更
        inferred_changes: List[Tuple[int, Optional[str], Optional[str]]] = []
        if region_changes is not None:
            inferred_changes = region_changes
        else:
            inferred_changes = local_changes or []

        # 对本帧未出现的历史目标，若其仍在某区域，推断为离开
        try:
            if self._persons:
                for tid_all, st_all in list(self._persons.items()):
                    if tid_all not in seen_tids and isinstance(st_all.current_region, str) and st_all.current_region:
                        inferred_changes.append((tid_all, st_all.current_region, None))
                        # 清空当前区域，避免重复追加离开
                        st_all.current_region = None
                        self._persons[tid_all] = st_all
        except Exception:
            pass

        # 规则触发（基于区域变更）
        for tid, prev_r, new_r in inferred_changes:
            st = self._persons.get(tid)
            if not st:
                continue

            # 记录进入区域的时间戳
            if new_r and isinstance(new_r, str):
                st.enter_ts[new_r] = now
                logger.info(f"Person {tid} entered region '{new_r}' at {now}")

            # 规则3：停留时长（在离开某区域时计算）
            try:
                if isinstance(prev_r, str) and prev_r:
                    enter_ts = st.enter_ts.get(prev_r)
                    if enter_ts:
                        dwell = now - float(enter_ts)
                        logger.info(f"Person {tid} left region '{prev_r}' after {dwell:.1f} seconds")
                        
                        # stand 区域（站立区域）
                        if prev_r == self.cfg.region_stand:
                            min_dwell = float(self.cfg.min_dwell_seconds_stand)
                            if dwell < min_dwell:
                                logger.warning(f"Person {tid} insufficient dwell time in stand: {dwell:.1f}s < {min_dwell}s")
                                self._maybe_emit(events, tid, "INSUFFICIENT_DWELL_TIME", now, {
                                    "region": prev_r,
                                    "dwell_seconds": round(dwell, 3),
                                    "required_seconds": min_dwell
                                })

                        # sink 区域
                        if prev_r == self.cfg.region_sink:
                            min_dwell = float(self.cfg.min_dwell_seconds_sink)
                            if dwell < min_dwell:
                                logger.warning(f"Person {tid} insufficient dwell time in sink: {dwell:.1f}s < {min_dwell}s")
                                self._maybe_emit(events, tid, "INSUFFICIENT_DWELL_TIME", now, {
                                    "region": prev_r,
                                    "dwell_seconds": round(dwell, 3),
                                    "required_seconds": min_dwell
                                })
                        
                        # dryer 区域
                        if prev_r == self.cfg.region_dryer:
                            min_dwell = float(self.cfg.min_dwell_seconds_dryer)
                            if dwell < min_dwell:
                                logger.warning(f"Person {tid} insufficient dwell time in dryer: {dwell:.1f}s < {min_dwell}s")
                                self._maybe_emit(events, tid, "INSUFFICIENT_DWELL_TIME", now, {
                                    "region": prev_r,
                                    "dwell_seconds": round(dwell, 3),
                                    "required_seconds": min_dwell
                                })
                        
                        # 清理时间戳
                        del st.enter_ts[prev_r]
            except Exception as e:
                logger.error(f"Error checking dwell time: {e}")

            # 规则1：发网准入
            if new_r == self.cfg.region_sink and not st.has_hairnet:
                self._maybe_emit(events, tid, "NO_HAIRNET_AT_SINK", now, {
                    "region": new_r
                })

            # 规则2：流程顺序（洗手→工作区 跳过烘干）
            if prev_r == self.cfg.region_sink and new_r == self.cfg.region_work:
                if self.cfg.region_dryer not in st.visited_regions:
                    self._maybe_emit(events, tid, "SKIP_DRYING", now, {
                        "from": prev_r,
                        "to": new_r
                    })

        # 规则1（补充）：当前帧内在洗手池区域且未戴发网，持续性触发（受冷却控制）
        try:
            for p in uod_persons:
                tid = int(p.get("track_id", -1))
                if tid < 0:
                    continue
                st = self._persons.get(tid)
                rn = p.get("region")
                if st and rn == self.cfg.region_sink and not bool(p.get("has_hairnet", st.has_hairnet)):
                    self._maybe_emit(events, tid, "NO_HAIRNET_AT_SINK", now, {"region": rn})
        except Exception:
            pass

        # 规则4：站立区域内，且“手部关键点”落入洗手池，判定洗手中（连续N帧平滑）
        try:
            for p in uod_persons:
                tid = int(p.get("track_id", -1))
                if tid < 0:
                    continue
                st = self._persons.get(tid)
                rn = p.get("region")
                hand_in_sink = bool(p.get("hand_in_sink", False))
                if st is None:
                    continue
                if rn == self.cfg.region_stand and hand_in_sink:
                    st.hand_in_sink_consec = int(st.hand_in_sink_consec) + 1
                    if st.hand_in_sink_consec >= int(self.cfg.handwash_min_consecutive):
                        self._maybe_emit(events, tid, "HANDWASHING_ACTIVE", now, {
                            "region": rn,
                            "hand_in_sink": True,
                            "consecutive": st.hand_in_sink_consec,
                            "required_consecutive": int(self.cfg.handwash_min_consecutive),
                        })
                else:
                    st.hand_in_sink_consec = 0
                self._persons[tid] = st
        except Exception:
            pass

        return events

        # 注：return 之前已返回；以下逻辑应在返回前运行

    def _maybe_emit(self, events: List[Event], tid: int, etype: str, ts: float, evidence: Dict[str, Any]) -> None:
        key = (tid, etype)
        last = self._cooldown.get(key, 0.0)
        if ts - last < self.cfg.cooldown_seconds:
            return
        self._cooldown[key] = ts
        events.append(Event(type=etype, track_id=tid, ts=ts, evidence=evidence))


