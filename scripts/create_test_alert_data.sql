-- 创建测试告警数据脚本
-- 用于测试告警历史列表功能

-- 插入测试告警数据
INSERT INTO alert_history (
    rule_id,
    camera_id,
    alert_type,
    message,
    details,
    notification_sent,
    notification_channels_used,
    timestamp
) VALUES
    -- 测试告警1：违规告警（未戴发网）
    (
        NULL,
        'cam0',
        'violation',
        '检测到违规：未戴发网',
        '{"violation_type": "no_hairnet", "track_id": 123, "confidence": 0.95}'::jsonb,
        false,
        '[]'::jsonb,
        NOW() - INTERVAL '1 hour'
    ),
    -- 测试告警2：违规告警（未洗手）
    (
        NULL,
        'vid1',
        'violation',
        '检测到违规：未洗手',
        '{"violation_type": "no_handwash", "track_id": 456, "confidence": 0.88}'::jsonb,
        false,
        '[]'::jsonb,
        NOW() - INTERVAL '2 hours'
    ),
    -- 测试告警3：性能警告
    (
        NULL,
        'cam0',
        'warning',
        '性能警告：FPS下降到15',
        '{"fps": 15, "threshold": 20}'::jsonb,
        false,
        '[]'::jsonb,
        NOW() - INTERVAL '3 hours'
    ),
    -- 测试告警4：系统告警
    (
        NULL,
        'system',
        'system',
        '系统告警：内存使用率过高',
        '{"memory_usage": 85, "threshold": 80}'::jsonb,
        true,
        '["email", "webhook"]'::jsonb,
        NOW() - INTERVAL '4 hours'
    ),
    -- 测试告警5：违规告警（未消毒）
    (
        NULL,
        'cam0',
        'violation',
        '检测到违规：未消毒',
        '{"violation_type": "no_sanitize", "track_id": 789, "confidence": 0.92}'::jsonb,
        false,
        '[]'::jsonb,
        NOW() - INTERVAL '5 hours'
    ),
    -- 测试告警6：已通知的告警
    (
        NULL,
        'vid1',
        'violation',
        '检测到违规：未戴发网（已通知）',
        '{"violation_type": "no_hairnet", "track_id": 321, "confidence": 0.98}'::jsonb,
        true,
        '["email"]'::jsonb,
        NOW() - INTERVAL '6 hours'
    );

-- 查看插入的数据
SELECT
    id,
    camera_id,
    alert_type,
    message,
    timestamp,
    notification_sent
FROM alert_history
ORDER BY timestamp DESC
LIMIT 10;
