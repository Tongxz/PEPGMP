-- 核心表创建脚本
-- 版本: 001
-- 创建时间: 2025-10-14
-- 说明: 创建检测记录、违规事件、统计汇总、告警规则表

-- ============================================
-- 1. 检测记录表
-- ============================================
CREATE TABLE IF NOT EXISTS detection_records (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    frame_number INTEGER,

    -- 检测数量统计
    person_count INTEGER DEFAULT 0,
    hairnet_violations INTEGER DEFAULT 0,
    handwash_events INTEGER DEFAULT 0,
    sanitize_events INTEGER DEFAULT 0,

    -- 详细检测结果 (JSON格式)
    person_detections JSONB,
    hairnet_results JSONB,
    handwash_results JSONB,
    sanitize_results JSONB,

    -- 性能指标
    processing_time FLOAT,
    fps FLOAT,

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_detection_camera_timestamp ON detection_records(camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detection_timestamp ON detection_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detection_camera_id ON detection_records(camera_id);

-- 注释
COMMENT ON TABLE detection_records IS '检测记录表 - 存储每次检测的详细结果';
COMMENT ON COLUMN detection_records.camera_id IS '摄像头ID';
COMMENT ON COLUMN detection_records.frame_number IS '帧编号';
COMMENT ON COLUMN detection_records.person_count IS '检测到的人数';
COMMENT ON COLUMN detection_records.hairnet_violations IS '未佩戴发网的人数';
COMMENT ON COLUMN detection_records.processing_time IS '处理耗时(秒)';

-- ============================================
-- 2. 违规事件表
-- ============================================
CREATE TABLE IF NOT EXISTS violation_events (
    id BIGSERIAL PRIMARY KEY,
    detection_id BIGINT REFERENCES detection_records(id) ON DELETE CASCADE,
    camera_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 违规信息
    violation_type VARCHAR(50) NOT NULL,  -- 'no_hairnet', 'no_handwash', 'no_sanitize'
    track_id INTEGER,
    confidence FLOAT,

    -- 截图和位置
    snapshot_path VARCHAR(500),
    bbox JSONB,  -- {"x": 0, "y": 0, "width": 100, "height": 100}

    -- 处理状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending, confirmed, false_positive, resolved
    handled_at TIMESTAMP,
    handled_by VARCHAR(100),
    notes TEXT,

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_violation_camera_timestamp ON violation_events(camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_violation_type ON violation_events(violation_type);
CREATE INDEX IF NOT EXISTS idx_violation_status ON violation_events(status);
CREATE INDEX IF NOT EXISTS idx_violation_camera_status ON violation_events(camera_id, status);

-- 注释
COMMENT ON TABLE violation_events IS '违规事件表 - 记录所有违规行为';
COMMENT ON COLUMN violation_events.violation_type IS '违规类型: no_hairnet(未戴发网), no_handwash(未洗手), no_sanitize(未消毒)';
COMMENT ON COLUMN violation_events.status IS '处理状态: pending(待处理), confirmed(已确认), false_positive(误报), resolved(已解决)';

-- ============================================
-- 3. 统计汇总表 (按小时)
-- ============================================
CREATE TABLE IF NOT EXISTS statistics_hourly (
    id BIGSERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    hour_start TIMESTAMP NOT NULL,

    -- 检测统计
    total_frames INTEGER DEFAULT 0,
    total_persons INTEGER DEFAULT 0,
    total_hairnet_violations INTEGER DEFAULT 0,
    total_handwash_events INTEGER DEFAULT 0,
    total_sanitize_events INTEGER DEFAULT 0,

    -- 性能统计
    avg_fps FLOAT,
    avg_processing_time FLOAT,
    min_processing_time FLOAT,
    max_processing_time FLOAT,

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 唯一约束：每个摄像头每小时一条记录
    CONSTRAINT uq_camera_hour UNIQUE (camera_id, hour_start)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_stats_camera_hour ON statistics_hourly(camera_id, hour_start DESC);
CREATE INDEX IF NOT EXISTS idx_stats_hour ON statistics_hourly(hour_start DESC);

-- 注释
COMMENT ON TABLE statistics_hourly IS '小时统计表 - 按小时汇总检测数据';
COMMENT ON COLUMN statistics_hourly.hour_start IS '小时开始时间 (例: 2025-10-14 14:00:00)';

-- ============================================
-- 4. 告警规则表
-- ============================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    camera_id VARCHAR(50),  -- NULL表示全局规则

    -- 规则配置
    rule_type VARCHAR(50) NOT NULL,  -- 'violation_threshold', 'continuous_violation', 'no_detection'
    conditions JSONB NOT NULL,  -- {"threshold": 10, "duration_seconds": 60}

    -- 通知配置
    notification_channels JSONB,  -- ["email", "websocket", "webhook"]
    recipients JSONB,  -- ["user@example.com", "admin@example.com"]

    -- 状态
    enabled BOOLEAN DEFAULT true,
    priority VARCHAR(20) DEFAULT 'medium',  -- low, medium, high, critical

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_alert_camera ON alert_rules(camera_id) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_rules(rule_type) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_alert_enabled ON alert_rules(enabled);

-- 注释
COMMENT ON TABLE alert_rules IS '告警规则表 - 定义各种告警条件';
COMMENT ON COLUMN alert_rules.rule_type IS '规则类型: violation_threshold(违规阈值), continuous_violation(持续违规), no_detection(无检测)';

-- ============================================
-- 5. 告警历史表
-- ============================================
CREATE TABLE IF NOT EXISTS alert_history (
    id BIGSERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE CASCADE,
    camera_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 告警信息
    alert_type VARCHAR(50) NOT NULL,
    message TEXT,
    details JSONB,

    -- 通知状态
    notification_sent BOOLEAN DEFAULT false,
    notification_channels_used JSONB,

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_alert_history_timestamp ON alert_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_camera ON alert_history(camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_rule ON alert_history(rule_id, timestamp DESC);

-- 注释
COMMENT ON TABLE alert_history IS '告警历史表 - 记录所有触发的告警';

-- ============================================
-- 6. 创建视图 (便于查询)
-- ============================================

-- 最近违规事件视图 (带检测记录信息)
CREATE OR REPLACE VIEW v_recent_violations AS
SELECT
    ve.id,
    ve.camera_id,
    ve.timestamp,
    ve.violation_type,
    ve.track_id,
    ve.confidence,
    ve.status,
    ve.snapshot_path,
    dr.frame_number,
    dr.person_count,
    dr.fps
FROM violation_events ve
LEFT JOIN detection_records dr ON ve.detection_id = dr.id
ORDER BY ve.timestamp DESC;

-- 每日统计视图
CREATE OR REPLACE VIEW v_daily_statistics AS
SELECT
    camera_id,
    DATE(hour_start) as date,
    SUM(total_frames) as total_frames,
    SUM(total_persons) as total_persons,
    SUM(total_hairnet_violations) as total_hairnet_violations,
    SUM(total_handwash_events) as total_handwash_events,
    SUM(total_sanitize_events) as total_sanitize_events,
    AVG(avg_fps) as avg_fps,
    AVG(avg_processing_time) as avg_processing_time
FROM statistics_hourly
GROUP BY camera_id, DATE(hour_start)
ORDER BY date DESC, camera_id;

-- ============================================
-- 7. 创建函数 (自动更新 updated_at)
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表创建触发器
CREATE TRIGGER update_violation_events_updated_at
    BEFORE UPDATE ON violation_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_statistics_hourly_updated_at
    BEFORE UPDATE ON statistics_hourly
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at
    BEFORE UPDATE ON alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 8. 插入默认数据
-- ============================================

-- 默认告警规则
INSERT INTO alert_rules (name, camera_id, rule_type, conditions, notification_channels, enabled) VALUES
('全局-高频违规告警', NULL, 'violation_threshold', '{"threshold": 5, "duration_minutes": 10, "violation_type": "no_hairnet"}', '["websocket"]', true),
('全局-持续未洗手告警', NULL, 'continuous_violation', '{"duration_seconds": 30, "min_detections": 3, "violation_type": "no_handwash"}', '["websocket"]', true)
ON CONFLICT DO NOTHING;

-- ============================================
-- 完成信息
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ 数据库初始化完成！';
    RAISE NOTICE '   - 已创建 6 个核心表';
    RAISE NOTICE '   - 已创建 15 个索引';
    RAISE NOTICE '   - 已创建 2 个视图';
    RAISE NOTICE '   - 已创建 3 个触发器';
    RAISE NOTICE '   - 已插入 2 条默认告警规则';
END $$;
