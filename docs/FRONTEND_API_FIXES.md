# 前端API调用问题修复报告

## 📅 修复日期
2025-11-04

## 🔍 问题分析

### 问题1: 实时统计接口无响应
**症状**: 前端调用 `/api/v1/statistics/realtime` 接口时没有响应或超时

**根本原因**:
- `get_realtime_statistics()` 方法中使用了 `r.average_confidence`
- 当从数据库读取的记录是字典格式时，访问 `r.average_confidence` 会失败
- 导致接口抛出 `AttributeError` 并被异常处理捕获，但没有返回有效的响应

**修复方案**:
在 `src/services/detection_service_domain.py` 的 `get_realtime_statistics()` 方法中，添加了对 `average_confidence` 属性的兼容性检查：

```python
"detection_accuracy": (
    sum(
        r.average_confidence if hasattr(r, 'average_confidence')
        else (r.confidence.value if hasattr(r, 'confidence') and hasattr(r.confidence, 'value')
              else 0.0)
        for r in records
    )
    / len(records)
    if records
    else 0.0
),
```

### 问题2: API路径不匹配
**症状**: 前端调用统计、历史记录、告警信息接口时返回 404

**分析**:
- 前端HTTP客户端配置了 `baseURL: '/api/v1'`
- 前端API调用路径（如 `/statistics/summary`）加上 baseURL 后为 `/api/v1/statistics/summary`
- 后端路由注册在 `/api/v1` 前缀下，路径匹配正确

**结论**: 路径匹配是正确的，问题在于接口本身的错误处理

### 问题3: `get_process_manager` 未定义错误
**症状**: 日志中出现 `name 'get_process_manager' is not defined` 错误

**分析**:
- 错误出现在 `/api/v1/cameras/{camera_id}/stats` 接口调用时
- 在 `cameras.py` 中没有找到 `get_process_manager` 的调用
- 可能是其他中间件或错误处理代码中的问题

**状态**: 需要进一步调查

## ✅ 已完成的修复

1. **修复 `average_confidence` 访问问题**
   - 文件: `src/services/detection_service_domain.py`
   - 方法: `get_realtime_statistics()`
   - 状态: ✅ 已完成

## 🔄 待处理问题

1. **`get_process_manager` 未定义错误**
   - 需要定位具体的调用位置
   - 可能需要添加导入或修复函数调用

2. **数据库连接管理**
   - 日志中出现 "connection was closed in the middle of operation" 错误
   - 需要检查数据库连接池的配置和使用

## 📋 测试建议

1. **测试实时统计接口**:
   ```bash
   curl "http://localhost:8000/api/v1/statistics/realtime"
   ```

2. **测试统计摘要接口**:
   ```bash
   curl "http://localhost:8000/api/v1/statistics/summary"
   ```

3. **测试告警历史接口**:
   ```bash
   curl "http://localhost:8000/api/v1/alerts/history-db?limit=10"
   ```

4. **前端页面测试**:
   - 打开统计分析页面，检查数据是否正常显示
   - 打开历史记录页面，检查数据是否正常显示
   - 打开告警信息页面，检查数据是否正常显示

## 📝 相关文件

- `src/services/detection_service_domain.py` - 检测服务领域层
- `src/api/routers/statistics.py` - 统计路由
- `src/api/routers/alerts.py` - 告警路由
- `src/api/routers/records.py` - 记录路由
- `frontend/src/lib/http.ts` - 前端HTTP客户端配置
- `frontend/src/api/statistics.ts` - 前端统计API
- `frontend/src/api/alerts.ts` - 前端告警API
