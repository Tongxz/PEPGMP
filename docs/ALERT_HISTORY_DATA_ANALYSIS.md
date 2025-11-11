# 告警历史数据问题分析

## 问题描述

前端历史告警列表没有数据显示，需要确认是数据库为空还是其他原因。

## 告警数据来源分析

### 1. 告警数据写入逻辑

根据代码分析，告警数据有以下写入路径：

#### 路径1：检测违规时自动生成告警
- **位置**：`src/utils/error_monitor.py` 的 `_trigger_alert()` 方法
- **触发条件**：当检测到违规时，如果配置了告警规则
- **数据写入**：调用 `db.save_alert_history()` 保存到 `alert_history` 表

#### 路径2：系统错误监控告警
- **位置**：`src/utils/error_monitor.py` 的 `_trigger_alert()` 方法
- **触发条件**：系统错误、性能问题等触发告警规则
- **数据写入**：保存到 `alert_history` 表，`camera_id` 为 "system"

#### 路径3：手动创建告警（如果有API）
- **位置**：告警规则服务（如果有手动触发功能）
- **数据写入**：通过 `AlertService` 或 `DatabaseService.save_alert_history()` 保存

### 2. 告警数据查询逻辑

#### API接口
- **路径**：`GET /alerts/history-db`
- **实现**：`src/api/routers/alerts.py` 的 `get_alert_history_db()` 方法
- **服务层**：`src/domain/services/alert_service.py` 的 `get_alert_history()` 方法
- **仓储层**：`src/infrastructure/repositories/postgresql_alert_repository.py` 的 `find_all()` 方法

#### 查询逻辑
```sql
SELECT id, rule_id, camera_id, alert_type, message, details,
       notification_sent, notification_channels_used, timestamp
FROM alert_history
WHERE ($1::VARCHAR IS NULL OR camera_id = $1)
  AND ($2::VARCHAR IS NULL OR alert_type = $2)
ORDER BY timestamp DESC
LIMIT $3
```

## 可能的原因

### 1. 数据库确实为空 ✅（最可能）

**原因**：
- 系统刚部署，还没有触发过告警
- 没有配置告警规则，所以没有告警生成
- 检测系统没有检测到违规，所以没有告警

**检查方法**：
```sql
-- 检查告警历史表数据
SELECT COUNT(*) FROM alert_history;

-- 检查告警规则表数据
SELECT COUNT(*) FROM alert_rules;

-- 查看最近10条告警
SELECT * FROM alert_history ORDER BY timestamp DESC LIMIT 10;
```

### 2. 告警规则未配置或未启用

**原因**：
- 没有创建告警规则
- 告警规则已创建但未启用（`enabled = false`）

**检查方法**：
```sql
-- 检查告警规则
SELECT id, name, rule_type, enabled, camera_id FROM alert_rules;

-- 检查启用的告警规则
SELECT id, name, rule_type, enabled, camera_id FROM alert_rules WHERE enabled = true;
```

### 3. 告警触发逻辑未执行

**原因**：
- 检测系统没有检测到违规
- 告警触发逻辑有问题
- 告警保存失败（但应该有错误日志）

**检查方法**：
- 查看后端日志，是否有告警相关的错误
- 检查检测系统是否正常运行
- 检查是否有违规检测记录

### 4. API返回格式问题

**原因**：
- API返回格式与前端期望不一致
- 数据转换有问题

**检查方法**：
- 直接调用API：`GET /alerts/history-db`
- 查看返回的数据格式

## 诊断步骤

### 步骤1：检查数据库是否有数据

```sql
-- 连接到数据库
psql $DATABASE_URL

-- 检查告警历史表
SELECT COUNT(*) as total FROM alert_history;

-- 如果有数据，查看最近的数据
SELECT id, camera_id, alert_type, message, timestamp
FROM alert_history
ORDER BY timestamp DESC
LIMIT 10;

-- 检查告警规则表
SELECT COUNT(*) as total FROM alert_rules;
SELECT id, name, enabled, rule_type FROM alert_rules;
```

### 步骤2：检查API是否正常返回

```bash
# 测试API
curl http://localhost:8000/api/v1/alerts/history-db?limit=10

# 应该返回格式：
# {
#   "count": 0,
#   "items": []
# }
```

### 步骤3：检查告警规则配置

```bash
# 检查告警规则
curl http://localhost:8000/api/v1/alerts/rules

# 如果没有规则，需要创建告警规则
```

### 步骤4：检查告警触发逻辑

- 查看后端日志，搜索 "告警"、"alert"、"trigger" 等关键词
- 检查是否有告警相关的错误日志

## 解决方案

### 方案1：如果数据库确实为空

这是正常情况，因为：
1. 系统刚部署，还没有告警数据
2. 需要配置告警规则并启用
3. 需要触发告警条件才会生成告警

**解决方法**：
1. **配置告警规则**：
   - 通过前端或API创建告警规则
   - 确保规则已启用（`enabled = true`）

2. **触发告警**：
   - 等待检测系统检测到违规
   - 或者手动触发测试告警（如果有测试功能）

3. **测试告警**：
   - 可以创建一个测试告警规则
   - 手动触发告警验证功能

### 方案2：如果数据库有数据但前端不显示

**可能原因**：
- API返回格式问题
- 前端数据解析问题
- 数据格式不匹配

**解决方法**：
1. 检查API返回的数据格式
2. 检查前端对返回数据的处理
3. 检查数据转换逻辑

### 方案3：创建测试数据（用于验证）

如果需要测试告警功能，可以创建测试告警数据：

```sql
-- 插入测试告警数据
INSERT INTO alert_history (
    rule_id, camera_id, alert_type, message, details,
    notification_sent, notification_channels_used, timestamp
) VALUES (
    NULL,
    'cam0',
    'test_alert',
    '测试告警消息',
    '{"test": true}'::jsonb,
    false,
    '[]'::jsonb,
    NOW()
);

-- 插入更多测试数据
INSERT INTO alert_history (
    rule_id, camera_id, alert_type, message, details,
    notification_sent, notification_channels_used, timestamp
) VALUES
    (NULL, 'cam0', 'violation', '检测到违规：未戴发网', '{"violation_type": "no_hairnet"}'::jsonb, false, '[]'::jsonb, NOW() - INTERVAL '1 hour'),
    (NULL, 'vid1', 'violation', '检测到违规：未洗手', '{"violation_type": "no_handwash"}'::jsonb, false, '[]'::jsonb, NOW() - INTERVAL '2 hours'),
    (NULL, 'cam0', 'warning', '性能警告：FPS下降', '{"fps": 15}'::jsonb, false, '[]'::jsonb, NOW() - INTERVAL '3 hours');
```

## 告警规则配置建议

### 1. 创建违规检测告警规则

```json
{
  "name": "未戴发网告警",
  "rule_type": "violation",
  "camera_id": "cam0",
  "conditions": {
    "violation_type": "no_hairnet",
    "threshold": 1
  },
  "enabled": true,
  "priority": "high"
}
```

### 2. 创建系统性能告警规则

```json
{
  "name": "FPS下降告警",
  "rule_type": "performance",
  "camera_id": null,
  "conditions": {
    "metric": "fps",
    "threshold": 20,
    "operator": "<"
  },
  "enabled": true,
  "priority": "medium"
}
```

## 总结

历史告警列表没有数据，最可能的原因是：

1. ✅ **数据库确实为空**（最可能）
   - 系统刚部署，还没有告警数据
   - 没有配置告警规则
   - 没有触发告警条件

2. ⚠️ **告警规则未配置**
   - 需要创建并启用告警规则

3. ⚠️ **告警触发逻辑未执行**
   - 需要检查检测系统是否正常运行
   - 需要检查是否有违规检测

**建议操作**：
1. 首先检查数据库是否有数据（使用SQL查询）
2. 如果数据库为空，配置告警规则
3. 等待或触发告警条件
4. 如果需要测试，可以插入测试数据

---

**文档版本**: 1.0
**最后更新**: 2024-11-05
**状态**: 📋 分析完成
