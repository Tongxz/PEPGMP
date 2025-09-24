import time

from src.services.process_engine import ProcessConfig, ProcessEngine


def make_engine(**overrides) -> ProcessEngine:
    cfg = ProcessConfig(
        enable=True,
        min_dwell_seconds_stand=0.5,
        min_dwell_seconds_sink=0.5,
        min_dwell_seconds_dryer=0.5,
        cooldown_seconds=0.0,
        region_entrance="入口线",
        region_stand="洗手站立区域",
        region_sink="洗手水池",
        region_dryer="烘干区域",
        region_work="工作区区域",
        handwash_min_consecutive=overrides.get("handwash_min_consecutive", 2),
    )
    return ProcessEngine(cfg)


def test_no_hairnet_at_sink_immediate():
    pe = make_engine()
    # 进入洗手池且未戴发网
    evs = pe.step(
        [
            {"track_id": 1, "region": "洗手水池", "has_hairnet": False, "ts": time.time()},
        ]
    )
    assert any(e.type == "NO_HAIRNET_AT_SINK" and e.track_id == 1 for e in evs)


def test_skip_drying_from_sink_to_work():
    pe = make_engine()
    # 手动传入区域变更：洗手池 -> 工作区，且未访问过烘干
    evs = pe.step(
        [
            {"track_id": 2, "region": "工作区区域", "has_hairnet": True, "ts": time.time()},
        ],
        region_changes=[(2, "洗手水池", "工作区区域")],
    )
    assert any(e.type == "SKIP_DRYING" and e.track_id == 2 for e in evs)


def test_insufficient_dwell_time_on_exit():
    pe = make_engine()
    # 先进入站立区域，建立 enter_ts
    _ = pe.step(
        [
            {"track_id": 3, "region": "洗手站立区域", "has_hairnet": True, "ts": time.time()},
        ]
    )
    # 人为将进入时间设置为很近（不足阈值）
    st = pe._persons[3]
    st.enter_ts[pe.cfg.region_stand] = time.time() - 0.1  # < 0.5s
    pe._persons[3] = st
    # 离开
    evs = pe.step([], region_changes=[(3, "洗手站立区域", None)])
    assert any(e.type == "INSUFFICIENT_DWELL_TIME" and e.track_id == 3 for e in evs)


def test_handwashing_active_consecutive_frames():
    pe = make_engine(handwash_min_consecutive=2)
    now = time.time()
    # 第1帧：站立且手在水池内（不应立即触发）
    evs1 = pe.step(
        [
            {"track_id": 4, "region": "洗手站立区域", "hand_in_sink": True, "ts": now},
        ]
    )
    assert not any(e.type == "HANDWASHING_ACTIVE" for e in evs1)
    # 第2帧：继续满足条件，应触发
    evs2 = pe.step(
        [
            {"track_id": 4, "region": "洗手站立区域", "hand_in_sink": True, "ts": now + 0.04},
        ]
    )
    assert any(e.type == "HANDWASHING_ACTIVE" and e.track_id == 4 for e in evs2)
