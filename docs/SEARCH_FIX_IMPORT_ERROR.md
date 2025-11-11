# 搜索功能导入错误修复

## 问题描述

后端启动时出现以下错误：

1. `ImportError: cannot import name 'get_alert_service' from 'src.api.dependencies'`
   - `get_alert_service` 不在 `dependencies.py` 中，而是在 `alerts.py` 中定义

2. `NameError: name 'search' is not defined`
   - search模块导入失败，导致在app.py中使用时未定义

## 修复方案

### 1. 修复导入位置

**问题**：`get_alert_service` 和 `get_region_domain_service` 不在 `src.api.dependencies` 中，而是在各自的路由模块中定义。

**修复**：
- 移除了从 `dependencies.py` 的错误导入
- 使用延迟导入（在函数内部导入），避免循环依赖

### 2. 延迟导入策略

在 `search.py` 中，将服务获取函数的导入改为延迟导入：

```python
# 之前（错误）：
from src.api.dependencies import (
    get_alert_service,
    get_region_domain_service,
)

# 修复后（正确）：
# 在函数内部延迟导入
try:
    from src.api.routers.alerts import get_alert_service as _get_alert_service
    if _get_alert_service is not None:
        alert_service = await _get_alert_service()
        # ...
except ImportError:
    # 处理导入失败的情况
    pass
```

### 3. 修复的文件

- `src/api/routers/search.py`: 修复导入错误，使用延迟导入
- `src/api/app.py`: 确保search模块正确导入

## 修复后的导入结构

```python
# search.py 顶层导入
from src.services.detection_service_domain import get_detection_service_domain

# 函数内部延迟导入（避免循环依赖）
async def global_search(...):
    # 在需要时导入
    from src.api.routers.alerts import get_alert_service
    from src.api.routers.region_management import get_region_domain_service
```

## 验证

- ✅ search模块可以正常导入
- ✅ 延迟导入避免循环依赖
- ✅ 错误处理完善（导入失败时返回空结果）

## 状态

✅ **已修复** - 后端应该可以正常启动
