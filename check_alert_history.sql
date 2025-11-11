-- 检查告警历史表数据
SELECT COUNT(*) as total_alerts FROM alert_history;

-- 查看最近10条告警
SELECT id, camera_id, alert_type, message, timestamp
FROM alert_history
ORDER BY timestamp DESC
LIMIT 10;

-- 检查告警规则
SELECT COUNT(*) as total_rules FROM alert_rules;
SELECT id, name, enabled, rule_type, camera_id FROM alert_rules ORDER BY id;

-- 按告警类型统计
SELECT alert_type, COUNT(*) as count
FROM alert_history
GROUP BY alert_type
ORDER BY count DESC;

-- 按摄像头统计
SELECT camera_id, COUNT(*) as count
FROM alert_history
GROUP BY camera_id
ORDER BY count DESC;
