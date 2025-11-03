# 持续监控配置方案

## 日期
2025-10-31

## 📊 监控配置概述

### 当前监控状态

- ✅ **监控端点**: `/api/v1/monitoring/health` 和 `/api/v1/monitoring/metrics` 已配置
- ✅ **监控中间件**: `MetricsMiddleware` 已集成
- ✅ **基础指标**: 请求计数、状态码分布、响应时间、领域服务使用率

### 待完善的监控配置

#### 1. 告警规则配置

需要配置以下告警阈值：

**错误率告警**:
- 严重告警: 错误率 > 5%
- 警告告警: 错误率 > 1%

**成功率告警**:
- 严重告警: 成功率 < 95%
- 警告告警: 成功率 < 99%

**响应时间告警**:
- 严重告警: P95延迟增加 > 50%
- 警告告警: P95延迟增加 > 20%

**领域服务使用率**:
- 监控领域服务使用率，确保100%全量发布正常工作

#### 2. 数据一致性监控

**CameraService数据一致性检查**:
- 数据库和YAML配置同步验证
- 定期检查数据一致性（建议每小时）
- 异常情况告警

**检查项**:
- 摄像头ID在数据库和YAML中是否存在
- 摄像头字段值是否一致
- 是否有孤立的记录（数据库有但YAML无，或反之）

## 📋 实施方案

### 方案一：增强现有监控端点（推荐）

#### 1.1 增强健康检查端点

在 `/api/v1/monitoring/health` 中添加数据库和YAML一致性检查：

```python
@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查端点."""
    checks = {
        "database": "ok",
        "redis": "ok",
        "domain_services": "ok",
        "camera_data_consistency": "ok",  # 新增
    }
    
    # 检查CameraService数据一致性
    try:
        consistency_check = await check_camera_data_consistency()
        if not consistency_check["consistent"]:
            checks["camera_data_consistency"] = "inconsistent"
            checks["consistency_issues"] = consistency_check["issues"]
    except Exception as e:
        checks["camera_data_consistency"] = "error"
        checks["consistency_error"] = str(e)
    
    return {
        "status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }
```

#### 1.2 添加数据一致性检查函数

```python
async def check_camera_data_consistency() -> Dict[str, Any]:
    """检查CameraService数据一致性."""
    issues = []
    
    try:
        # 获取CameraService实例
        camera_service = await get_camera_service()
        if not camera_service:
            return {"consistent": True, "issues": []}
        
        # 从数据库获取所有摄像头
        db_cameras = await camera_service.camera_repository.find_all()
        db_camera_ids = {cam.id for cam in db_cameras}
        
        # 从YAML获取所有摄像头
        yaml_config = camera_service._read_yaml_config()
        yaml_cameras = yaml_config.get("cameras", [])
        yaml_camera_ids = {cam.get("id") for cam in yaml_cameras if cam.get("id")}
        
        # 检查不一致
        only_in_db = db_camera_ids - yaml_camera_ids
        only_in_yaml = yaml_camera_ids - db_camera_ids
        
        if only_in_db:
            issues.append(f"数据库中存在但YAML中不存在: {only_in_db}")
        
        if only_in_yaml:
            issues.append(f"YAML中存在但数据库中不存在: {only_in_yaml}")
        
        # 检查字段一致性（对于同时存在的摄像头）
        common_ids = db_camera_ids & yaml_camera_ids
        for camera_id in common_ids:
            db_camera = next((c for c in db_cameras if c.id == camera_id), None)
            yaml_camera = next((c for c in yaml_cameras if c.get("id") == camera_id), None)
            
            if db_camera and yaml_camera:
                # 检查关键字段是否一致
                if db_camera.name != yaml_camera.get("name"):
                    issues.append(f"摄像头 {camera_id} name不一致: DB={db_camera.name}, YAML={yaml_camera.get('name')}")
                
                if db_camera.metadata.get("source") != yaml_camera.get("source"):
                    issues.append(f"摄像头 {camera_id} source不一致")
        
        return {
            "consistent": len(issues) == 0,
            "issues": issues,
            "db_count": len(db_camera_ids),
            "yaml_count": len(yaml_camera_ids),
        }
    except Exception as e:
        logger.error(f"数据一致性检查失败: {e}")
        return {
            "consistent": False,
            "issues": [f"检查失败: {str(e)}"],
        }
```

### 方案二：定时任务监控（可选）

创建定时任务定期检查数据一致性：

```python
import asyncio
from datetime import datetime, timedelta

async def periodic_consistency_check():
    """定期数据一致性检查."""
    while True:
        try:
            result = await check_camera_data_consistency()
            if not result["consistent"]:
                logger.error(f"数据一致性检查失败: {result['issues']}")
                # 发送告警通知（邮件、钉钉、Slack等）
                await send_alert(f"CameraService数据不一致: {result['issues']}")
        except Exception as e:
            logger.error(f"定期一致性检查异常: {e}")
        
        # 每小时检查一次
        await asyncio.sleep(3600)
```

### 方案三：增强监控指标端点

在 `/api/v1/monitoring/metrics` 中添加数据一致性指标：

```python
@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """获取监控指标."""
    # ... 现有代码 ...
    
    # 添加数据一致性指标
    consistency_check = await check_camera_data_consistency()
    
    metrics = {
        # ... 现有指标 ...
        "data_consistency": {
            "consistent": consistency_check["consistent"],
            "issues_count": len(consistency_check.get("issues", [])),
            "last_check": datetime.now().isoformat(),
        },
    }
    
    return metrics
```

## 📊 监控告警配置

### 告警规则示例（Prometheus格式）

```yaml
groups:
  - name: api_monitoring
    rules:
      - alert: HighErrorRate
        expr: api_error_rate > 0.05
        for: 5m
        annotations:
          summary: "API错误率过高"
          description: "错误率超过5%，当前值: {{ $value }}"
      
      - alert: LowSuccessRate
        expr: api_success_rate < 0.95
        for: 5m
        annotations:
          summary: "API成功率过低"
          description: "成功率低于95%，当前值: {{ $value }}"
      
      - alert: HighResponseTime
        expr: increase(api_p95_response_time) > 0.5
        for: 10m
        annotations:
          summary: "API响应时间异常增加"
          description: "P95响应时间增加超过50%"
      
      - alert: DataInconsistency
        expr: camera_data_consistency == 0
        for: 1m
        annotations:
          summary: "CameraService数据不一致"
          description: "数据库和YAML配置文件存在不一致"
```

## 🎯 实施步骤

### 第一步：增强健康检查端点（1小时）

1. 添加 `check_camera_data_consistency()` 函数
2. 在健康检查端点中调用该函数
3. 测试验证

### 第二步：增强监控指标端点（30分钟）

1. 在监控指标端点中添加数据一致性指标
2. 更新指标文档

### 第三步：配置告警规则（30分钟）

1. 定义告警阈值
2. 配置告警通知渠道（邮件、钉钉等）
3. 测试告警触发

### 第四步：文档和验证（30分钟）

1. 更新监控文档
2. 验证所有监控功能
3. 编写监控使用指南

## ✅ 总结

### 已完成 ✅

- ✅ 基础监控端点已配置
- ✅ 监控中间件已集成
- ✅ 基础指标已收集

### 待完成 ⏳

- ⏳ 数据一致性检查函数
- ⏳ 增强健康检查端点
- ⏳ 增强监控指标端点
- ⏳ 告警规则配置
- ⏳ 告警通知渠道配置

### 预计工作量

- **实施时间**: 2-3小时
- **测试时间**: 30分钟
- **文档时间**: 30分钟
- **总计**: 3-4小时

---

**状态**: ⏳ **待实施**  
**优先级**: 高  
**下一步**: 开始实施第一步：增强健康检查端点
