-- 告警历史数据检查脚本
-- 用于诊断历史告警列表没有数据的原因

-- 1. 检查告警历史表数据总数
SELECT COUNT(*) as total_alerts FROM alert_history;

-- 2. 查看最近10条告警（如果有数据）
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

-- 3. 检查告警规则总数
SELECT COUNT(*) as total_rules FROM alert_rules;

-- 4. 查看告警规则详情
SELECT
    id,
    name,
    enabled,
    rule_type,
    camera_id,
    priority
FROM alert_rules
ORDER BY id;

-- 5. 查看启用的告警规则
SELECT
    id,
    name,
    enabled,
    rule_type,
    camera_id
FROM alert_rules
WHERE enabled = true
ORDER BY id;

-- 6. 按告警类型统计
SELECT
    alert_type,
    COUNT(*) as count
FROM alert_history
GROUP BY alert_type
ORDER BY count DESC;

-- 7. 按摄像头统计
SELECT
    camera_id,
    COUNT(*) as count
FROM alert_history
GROUP BY camera_id
ORDER BY count DESC;

-- 8. 查看最近7天的告警数量
SELECT
    DATE(timestamp) as date,
    COUNT(*) as count
FROM alert_history
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
