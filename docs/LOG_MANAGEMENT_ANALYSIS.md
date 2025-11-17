# 日志管理机制分析

## 1. 日志文件命名规则

### ✅ 按相机区分

**实现位置**：`src/services/executors/local.py` 第63-65行

**命名规则**：
```python
def _log_file(camera_id: str) -> str:
    os.makedirs(_logs_dir(), exist_ok=True)
    return os.path.join(_logs_dir(), f"detect_{camera_id}.log")
```

**示例**：
- `detect_vid1.log` - 相机 vid1 的日志
- `detect_cam0.log` - 相机 cam0 的日志
- `detect_mps.log` - 相机 mps 的日志

**结论**：✅ **日志按相机ID区分**

### ❌ 不按日期区分

**当前实现**：
- 日志文件命名格式：`detect_{camera_id}.log`
- **不包含日期信息**

**日志轮转机制**：
- 使用 `RotatingFileHandler`（已修复）
- 达到100MB时自动轮转
- 备份文件命名：`detect_{camera_id}.log.1`, `detect_{camera_id}.log.2`, ... `detect_{camera_id}.log.10`
- **备份文件不包含日期信息**

**结论**：❌ **日志不按日期区分**（只有轮转编号）

## 2. 日志清理机制

### ⚠️ 没有自动清理机制

**当前状态**：
- ❌ **没有定时任务**自动清理旧日志
- ❌ **没有按日期自动删除**机制
- ✅ **有手动清理脚本**：`scripts/maintenance/cleanup_output.py`

### 手动清理工具

#### 工具1：`scripts/maintenance/cleanup_output.py`

**功能**：清理指定路径下超过指定天数的文件

**用法**：
```bash
# 预览模式（不实际删除）
python scripts/maintenance/cleanup_output.py --days 30 --paths logs --dry-run

# 实际删除超过30天的日志文件
python scripts/maintenance/cleanup_output.py --days 30 --paths logs --yes
```

**参数**：
- `--days`: 保留天数（默认30天）
- `--paths`: 要清理的路径列表（默认：`output/captures`, `logs`）
- `--dry-run`: 预览模式，不实际删除
- `--yes`: 确认执行删除操作

#### 工具2：`src/services/retention.py`

**功能**：通用的文件清理函数

**函数**：
```python
def cleanup_old_files(
    base_paths: Iterable[str],
    days: int = 30,
    patterns: Optional[List[str]] = None,
) -> int:
    """删除 base_paths 下早于 days 天的文件"""
```

**用法**：
```python
from src.services.retention import cleanup_old_files

# 清理logs目录下超过30天的.log文件
deleted_count = cleanup_old_files(
    base_paths=["logs"],
    days=30,
    patterns=[".log"]
)
```

### 数据库记录清理

**位置**：`src/core/data_manager.py` 第328行

**功能**：清理数据库中的旧检测记录

**方法**：
```python
def cleanup_old_records(self, days: int = 30) -> int:
    """清理旧记录，保留指定天数"""
```

**说明**：
- 只清理数据库记录，**不清理日志文件**
- 默认保留30天

## 3. 当前日志管理问题

### 问题1：日志文件无限增长

**现状**：
- 单个日志文件可能非常大（如 `detect_vid1.log` 已达到146MB）
- 虽然有轮转机制（100MB），但**没有自动删除旧备份**

**影响**：
- 磁盘空间可能被耗尽
- 日志文件过多，难以管理

### 问题2：没有按日期区分

**现状**：
- 日志文件命名不包含日期
- 轮转备份文件只有编号（`.1`, `.2`, ...）
- 无法快速识别日志的日期范围

**影响**：
- 难以按日期查找日志
- 清理旧日志时需要检查文件修改时间

### 问题3：没有自动清理机制

**现状**：
- 需要手动执行清理脚本
- 没有定时任务自动清理

**影响**：
- 可能忘记清理，导致磁盘空间问题
- 需要人工维护

## 4. 建议的改进方案

### 方案1：添加按日期命名的日志文件（推荐）

**实现**：
```python
def _log_file(camera_id: str) -> str:
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    return os.path.join(_logs_dir(), f"detect_{camera_id}_{date_str}.log")
```

**优点**：
- 按日期区分日志文件
- 便于按日期查找和管理
- 便于清理旧日志

**缺点**：
- 需要修改现有代码
- 可能影响日志查看逻辑

### 方案2：添加自动清理机制（推荐）

**实现方式1：定时任务（cron）**

**脚本**：`scripts/maintenance/cleanup_logs.sh`
```bash
#!/bin/bash
# 清理超过30天的日志文件
find logs/ -name "detect_*.log*" -mtime +30 -delete
```

**cron配置**：
```bash
# 每天凌晨2点执行清理
0 2 * * * /path/to/scripts/maintenance/cleanup_logs.sh
```

**实现方式2：Python定时任务**

**使用APScheduler**：
```python
from apscheduler.schedulers.background import BackgroundScheduler
from src.services.retention import cleanup_old_files

scheduler = BackgroundScheduler()
scheduler.add_job(
    cleanup_old_files,
    'cron',
    hour=2,
    minute=0,
    args=[["logs"], 30, [".log"]]
)
scheduler.start()
```

### 方案3：增强日志轮转配置

**当前配置**：
- maxBytes: 100MB
- backupCount: 10

**建议增强**：
- 添加日志压缩（`.gz`）
- 添加按日期轮转（`TimedRotatingFileHandler`）
- 添加自动清理旧备份

**示例**：
```python
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    log_path,
    when='midnight',  # 每天午夜轮转
    interval=1,
    backupCount=30,  # 保留30天
    encoding="utf-8",
)
```

## 5. 立即行动建议

### 短期（立即执行）

1. **手动清理现有大日志文件**：
   ```bash
   # 压缩现有日志
   gzip logs/detect_vid1.log
   
   # 或删除超过30天的日志
   find logs/ -name "detect_*.log*" -mtime +30 -delete
   ```

2. **设置定期清理任务**：
   - 创建清理脚本
   - 添加到cron或系统定时任务

### 中期（1-2周内）

1. **实现按日期命名的日志文件**
2. **添加自动清理机制**
3. **添加日志压缩功能**

### 长期（1个月内）

1. **实现完整的日志管理系统**
2. **添加日志监控和告警**
3. **实现日志查询和分析功能**

## 6. 总结

### 当前状态

| 特性 | 状态 | 说明 |
|------|------|------|
| 按相机区分 | ✅ 是 | `detect_{camera_id}.log` |
| 按日期区分 | ❌ 否 | 不包含日期信息 |
| 自动清理 | ❌ 否 | 需要手动执行 |
| 日志轮转 | ✅ 是 | 100MB，保留10个备份 |
| 日志压缩 | ❌ 否 | 不支持自动压缩 |

### 建议优先级

1. **高优先级**：添加自动清理机制（防止磁盘空间耗尽）
2. **中优先级**：实现按日期命名（便于管理）
3. **低优先级**：添加日志压缩（节省空间）

