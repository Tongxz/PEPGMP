# 日志分类优化建议

## 当前日志分类情况

### ✅ 已实现的分类

1. **按相机区分**：
   - 格式：`detect_{camera_id}.log`
   - 示例：`detect_vid1.log`, `detect_cam0.log`
   - 状态：✅ 已实现

2. **部分功能区分**：
   - API日志：`api*.log`, `uvicorn_run.log`
   - 前端日志：`frontend*.log`
   - 检测日志：`detect_*.log`
   - 事件日志：`record_events*.log`, `events_record.jsonl`
   - 状态：⚠️ **部分实现，不完整**

### ❌ 缺失的分类

1. **不按日期区分**：日志文件命名不包含日期
2. **没有统一的应用日志**：缺少 `application.log`（系统级日志）
3. **没有统一的错误日志**：缺少 `error.log`（所有错误汇总）
4. **没有自动清理机制**：需要手动清理

## 建议的日志分类体系

### 方案1：按功能模块分类（推荐）

**目录结构**：
```
logs/
├── detection/           # 检测相关日志
│   ├── detect_vid1.log
│   ├── detect_cam0.log
│   └── ...
├── api/                 # API服务日志
│   ├── api.log
│   ├── api_error.log
│   └── ...
├── application/         # 应用级日志
│   ├── application.log
│   ├── application_error.log
│   └── ...
├── frontend/            # 前端日志
│   ├── frontend.log
│   └── ...
├── events/              # 事件日志
│   ├── events_record.jsonl
│   └── ...
└── system/              # 系统级日志
    ├── system.log
    └── system_error.log
```

**优点**：
- 清晰的功能划分
- 便于按模块查找日志
- 便于设置不同的清理策略

**缺点**：
- 需要修改现有代码
- 可能影响日志查看逻辑

### 方案2：按日志类型分类（推荐）

**目录结构**：
```
logs/
├── detection/           # 检测日志（按相机）
│   ├── detect_vid1.log
│   ├── detect_cam0.log
│   └── ...
├── api/                 # API日志
│   ├── api.log
│   └── api_error.log
├── application/         # 应用日志
│   ├── application.log
│   └── application_error.log
└── errors/              # 统一错误日志（所有模块）
    └── error.log
```

**优点**：
- 功能清晰
- 错误日志集中管理
- 便于错误监控和分析

### 方案3：按日期+功能分类（最推荐）

**目录结构**：
```
logs/
├── detection/           # 检测日志
│   ├── 2025/11/14/      # 按日期分目录
│   │   ├── detect_vid1_20251114.log
│   │   └── detect_cam0_20251114.log
│   └── ...
├── api/                 # API日志
│   ├── 2025/11/14/
│   │   ├── api_20251114.log
│   │   └── api_error_20251114.log
│   └── ...
├── application/         # 应用日志
│   ├── 2025/11/14/
│   │   ├── application_20251114.log
│   │   └── application_error_20251114.log
│   └── ...
└── errors/              # 统一错误日志
    ├── 2025/11/14/
    │   └── error_20251114.log
    └── ...
```

**优点**：
- 功能清晰
- 按日期查找方便
- 便于自动清理（删除整个日期目录）
- 符合日志管理最佳实践

**缺点**：
- 实现复杂度较高
- 需要修改现有代码较多

## 建议的日志分类

### 1. 检测日志（Detection Logs）

**用途**：
- 检测流程日志
- 检测结果日志
- 违规检测日志
- 统计信息日志

**文件命名**：
- 当前：`detect_{camera_id}.log`
- 建议：`detection/detect_{camera_id}.log` 或 `detection/{date}/detect_{camera_id}.log`

**清理策略**：
- 保留30天
- 单个文件最大100MB

### 2. API日志（API Logs）

**用途**：
- API请求日志
- API响应日志
- API错误日志

**文件命名**：
- 建议：`api/api.log`, `api/api_error.log`
- 或：`api/{date}/api_{date}.log`, `api/{date}/api_error_{date}.log`

**清理策略**：
- 保留7天（API日志通常不需要保留太长时间）
- 单个文件最大50MB

### 3. 应用日志（Application Logs）

**用途**：
- 应用启动/停止日志
- 服务初始化日志
- 系统状态日志
- 业务逻辑日志

**文件命名**：
- 建议：`application/application.log`, `application/application_error.log`

**清理策略**：
- 保留30天
- 单个文件最大100MB

### 4. 错误日志（Error Logs）

**用途**：
- 所有模块的错误日志汇总
- 便于集中监控和分析

**文件命名**：
- 建议：`errors/error.log` 或 `errors/{date}/error_{date}.log`

**清理策略**：
- 保留90天（错误日志需要保留更长时间）
- 单个文件最大50MB

### 5. 事件日志（Event Logs）

**用途**：
- 检测事件日志
- 违规事件日志
- 行为事件日志

**文件命名**：
- 当前：`events_record.jsonl`
- 建议：`events/{date}/events_{date}.jsonl`

**清理策略**：
- 保留90天
- 单个文件最大200MB

## 实现方案

### 方案A：简单分类（推荐，易于实现）

**修改 `src/utils/logger.py`**：
```python
def get_logger(
    name: str = "HumanBehaviorDetection",
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_category: Optional[str] = None,  # 新增：日志分类
    console_output: bool = True,
) -> logging.Logger:
    """
    获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径（如果为None则不写入文件）
        log_category: 日志分类（detection, api, application, error）
        console_output: 是否输出到控制台
    """
    # 如果指定了分类，自动构建日志路径
    if log_category and log_file is None:
        log_dir = Path("logs") / log_category
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / f"{log_category}.log")
    
    # ... 其余代码保持不变
```

**修改 `src/services/executors/local.py`**：
```python
def _log_file(camera_id: str) -> str:
    os.makedirs(_logs_dir(), exist_ok=True)
    detection_log_dir = os.path.join(_logs_dir(), "detection")
    os.makedirs(detection_log_dir, exist_ok=True)
    return os.path.join(detection_log_dir, f"detect_{camera_id}.log")
```

### 方案B：完整分类（推荐，功能完整）

**创建日志分类工具** `src/utils/log_manager.py`：
```python
from enum import Enum
from pathlib import Path
from datetime import datetime

class LogCategory(Enum):
    """日志分类"""
    DETECTION = "detection"      # 检测日志
    API = "api"                  # API日志
    APPLICATION = "application"  # 应用日志
    ERROR = "error"              # 错误日志
    EVENT = "event"              # 事件日志

def get_log_file(category: LogCategory, identifier: Optional[str] = None) -> str:
    """
    获取日志文件路径
    
    Args:
        category: 日志分类
        identifier: 标识符（如camera_id）
    
    Returns:
        日志文件路径
    """
    log_dir = Path("logs") / category.value
    log_dir.mkdir(parents=True, exist_ok=True)
    
    if identifier:
        return str(log_dir / f"{category.value}_{identifier}.log")
    else:
        return str(log_dir / f"{category.value}.log")
```

## 清理策略建议

### 按分类设置不同的清理策略

| 日志类型 | 保留天数 | 文件大小限制 | 备份数量 |
|---------|---------|-------------|---------|
| 检测日志 | 30天 | 100MB | 10个 |
| API日志 | 7天 | 50MB | 5个 |
| 应用日志 | 30天 | 100MB | 10个 |
| 错误日志 | 90天 | 50MB | 20个 |
| 事件日志 | 90天 | 200MB | 5个 |

## 建议的实施步骤

### 阶段1：实现基础分类（1-2天）

1. **修改 `src/utils/logger.py`**：
   - 添加 `log_category` 参数
   - 支持按分类创建日志目录

2. **修改 `src/services/executors/local.py`**：
   - 检测日志放入 `logs/detection/` 目录

3. **修改 API日志配置**：
   - API日志放入 `logs/api/` 目录

### 阶段2：完善分类体系（3-5天）

1. **创建日志管理器**：`src/utils/log_manager.py`
2. **统一日志路径获取**：所有模块使用统一的日志路径获取方法
3. **添加错误日志汇总**：所有ERROR级别日志写入 `logs/error/error.log`

### 阶段3：添加自动清理（5-7天）

1. **实现分类清理脚本**：`scripts/maintenance/cleanup_logs.py`
2. **添加定时任务**：使用cron或APScheduler
3. **添加监控告警**：日志大小和磁盘空间监控

## 影响评估

### 优点

1. **便于管理**：按功能分类，便于查找和管理
2. **便于清理**：可以针对不同日志类型设置不同的清理策略
3. **便于监控**：可以针对不同类型的日志进行监控和分析
4. **符合最佳实践**：符合日志管理的最佳实践

### 缺点

1. **需要修改代码**：需要修改所有使用日志的地方
2. **可能影响现有功能**：日志路径变化可能影响日志查看功能
3. **需要测试**：需要充分测试确保不影响现有功能

## 总结

**建议实施**：
1. ✅ **实施方案A（简单分类）**：易于实现，影响范围小
2. ✅ **按功能分类**：检测日志、API日志、应用日志、错误日志
3. ✅ **添加错误日志汇总**：便于错误监控
4. ✅ **实现自动清理机制**：防止磁盘空间耗尽

**优先级**：
1. **高优先级**：检测日志分类（已有基础，只需调整目录）
2. **中优先级**：API日志和应用日志分类
3. **低优先级**：按日期分目录（可以后续优化）

