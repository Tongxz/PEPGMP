# 监控配置指南

## 日期
2025-10-31

## 📊 监控端点

### 健康检查端点

**端点**: `GET /api/v1/monitoring/health`

**功能**: 检查服务健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-31T10:00:00",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "domain_services": "ok"
  }
}
```

**使用方法**:
```bash
curl http://localhost:8000/api/v1/monitoring/health | jq
```

### 监控指标端点

**端点**: `GET /api/v1/monitoring/metrics`

**功能**: 获取监控指标数据

**响应示例**:
```json
{
  "timestamp": "2025-10-31T10:00:00",
  "requests": {
    "total": 1000,
    "success": 995,
    "error": 5,
    "success_rate": 99.5,
    "error_rate": 0.5,
    "by_status": {
      "200": 995,
      "400": 3,
      "500": 2
    }
  },
  "domain_service": {
    "usage_count": 500,
    "old_count": 500,
    "usage_rate": 50.0
  },
  "response_time": {
    "p50_ms": 50.0,
    "p95_ms": 100.0,
    "p99_ms": 150.0,
    "max_ms": 200.0,
    "avg_ms": 75.0
  },
  "errors": {
    "total": 5,
    "recent": [...]
  }
}
```

**使用方法**:
```bash
curl http://localhost:8000/api/v1/monitoring/metrics | jq
```

## 🎯 监控指标

### 关键指标

1. **错误率**
   - **目标**: < 1%
   - **阈值**: > 5% 立即告警
   - **计算**: `error_rate = (error_requests / total_requests) * 100`

2. **响应时间**
   - **目标**: P95延迟无明显增加
   - **阈值**: P95延迟增加 > 50% 需要检查
   - **指标**: P50/P95/P99/最大值/平均值

3. **成功率**
   - **目标**: > 99%
   - **阈值**: < 95% 立即告警
   - **计算**: `success_rate = (success_requests / total_requests) * 100`

4. **领域服务使用率**
   - **目的**: 跟踪灰度发布进度
   - **计算**: `usage_rate = (domain_service_count / total_requests) * 100`

## 📋 告警规则配置

### 告警规则1: 错误率告警

**条件**: 错误率 > 5%

**动作**: 
- 立即告警
- 记录错误日志
- 通知相关人员

**优先级**: 高

**配置示例**:
```yaml
alert_rules:
  - name: "high_error_rate"
    condition: "error_rate > 5"
    action: "alert_and_log"
    priority: "high"
```

### 告警规则2: 响应时间告警

**条件**: P95延迟增加 > 50%

**动作**:
- 记录性能日志
- 检查性能瓶颈
- 通知相关人员

**优先级**: 中

**配置示例**:
```yaml
alert_rules:
  - name: "high_response_time"
    condition: "p95_increase > 50"
    action: "log_and_check"
    priority: "medium"
```

### 告警规则3: 成功率告警

**条件**: 成功率 < 95%

**动作**:
- 立即告警
- 记录错误日志
- 通知相关人员

**优先级**: 高

**配置示例**:
```yaml
alert_rules:
  - name: "low_success_rate"
    condition: "success_rate < 95"
    action: "alert_and_log"
    priority: "high"
```

### 告警规则4: 领域服务使用率监控

**条件**: 跟踪使用率变化

**动作**:
- 记录使用率日志
- 监控灰度发布进度

**优先级**: 低

**配置示例**:
```yaml
alert_rules:
  - name: "domain_service_usage"
    condition: "monitor_usage_rate"
    action: "log"
    priority: "low"
```

## 📊 监控仪表板配置（可选）

### 仪表板1: 错误率趋势图

**配置**:
- X轴: 时间（分钟/小时）
- Y轴: 错误率 (%)
- 数据源: `/api/v1/monitoring/metrics`
- 更新频率: 实时

**图表类型**: 折线图

### 仪表板2: 响应时间分布图

**配置**:
- X轴: 时间（分钟/小时）
- Y轴: 响应时间 (ms)
- 指标: P50/P95/P99/最大值/平均值
- 数据源: `/api/v1/monitoring/metrics`
- 更新频率: 实时

**图表类型**: 折线图（多条线）

### 仪表板3: 领域服务使用率图

**配置**:
- X轴: 时间（分钟/小时）
- Y轴: 使用率 (%)
- 数据源: `/api/v1/monitoring/metrics`
- 更新频率: 实时

**图表类型**: 折线图

### 仪表板4: 请求分布图

**配置**:
- X轴: 状态码（200/400/500等）
- Y轴: 请求数量
- 数据源: `/api/v1/monitoring/metrics`
- 更新频率: 实时

**图表类型**: 柱状图

## 🛠️ 监控工具

### 监控脚本

**脚本**: `tools/monitoring_config.sh`

**功能**:
- 验证监控端点可用性
- 显示监控指标配置
- 显示告警规则配置
- 显示监控仪表板配置

**使用方法**:
```bash
./tools/monitoring_config.sh
```

### 监控API

**健康检查**:
```bash
curl http://localhost:8000/api/v1/monitoring/health | jq
```

**监控指标**:
```bash
curl http://localhost:8000/api/v1/monitoring/metrics | jq
```

## 📋 监控检查清单

### 监控端点检查

- [ ] 健康检查端点可用
- [ ] 监控指标端点可用
- [ ] 监控指标正常收集

### 告警规则检查

- [ ] 错误率告警配置完成
- [ ] 响应时间告警配置完成
- [ ] 成功率告警配置完成
- [ ] 领域服务使用率监控配置完成

### 监控仪表板检查（可选）

- [ ] 错误率趋势图配置完成
- [ ] 响应时间分布图配置完成
- [ ] 领域服务使用率图配置完成
- [ ] 请求分布图配置完成

## 🚨 告警触发条件

### 立即告警（高优先级）

1. **错误率 > 5%**
   - 触发: 立即
   - 通知: 相关人员
   - 操作: 检查错误日志

2. **成功率 < 95%**
   - 触发: 立即
   - 通知: 相关人员
   - 操作: 检查服务状态

### 记录告警（中优先级）

1. **P95延迟增加 > 50%**
   - 触发: 记录
   - 通知: 可选
   - 操作: 检查性能瓶颈

### 监控告警（低优先级）

1. **领域服务使用率变化**
   - 触发: 记录
   - 通知: 不需要
   - 操作: 监控灰度发布进度

## 💡 监控最佳实践

### 1. 监控频率

- **实时监控**: 关键指标（错误率、成功率）
- **定期监控**: 性能指标（响应时间）
- **按需监控**: 业务指标（领域服务使用率）

### 2. 告警策略

- **高优先级**: 立即告警并处理
- **中优先级**: 记录并检查
- **低优先级**: 仅记录

### 3. 监控数据保留

- **实时数据**: 保留最近1小时
- **历史数据**: 保留最近7天
- **聚合数据**: 保留最近30天

### 4. 监控指标优化

- **关键指标**: 优先监控
- **非关键指标**: 定期检查
- **冗余指标**: 可以移除

## ✅ 总结

### 已完成

- ✅ 监控端点已创建
- ✅ 监控指标已定义
- ✅ 告警规则已说明
- ✅ 监控仪表板已说明
- ✅ 监控工具已创建

### 待完成

- ⏳ 监控端点验证（需重启服务）
- ⏳ 告警规则实际配置（如需要）
- ⏳ 监控仪表板实际配置（可选）

---

**状态**: ✅ **监控配置指南已完成**  
**下一步**: 重启服务验证监控端点，配置告警规则  
**详细计划**: 请查看 `docs/rollout_preparation_guide.md`

