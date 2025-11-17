# 日志轮转机制分析

## 当前状态

### ⚠️ 问题
- **日志文件大小**：`detect_vid1.log` 已达到 **138MB**，**1,752,940行**
- **没有日志轮转**：当前使用的是 `logging.FileHandler`，没有大小限制和轮转功能
- **日志持续增长**：日志会一直追加到同一个文件中，无限增长

### 当前日志配置

**文件**：`src/utils/logger.py`

**当前实现**：
```python
# 第77行
file_handler = logging.FileHandler(log_path, encoding="utf-8")
```

**问题**：
- `FileHandler` 是简单的文件处理器，**没有轮转功能**
- 日志会一直追加，没有大小限制
- 没有自动压缩和清理机制

## 文档建议的配置

### 推荐的日志轮转配置

根据 `docs/LOGGING_STRATEGY.md` 和 `docs/ARCHITECTURE_LOGGING_SPECIFICATION.md`：

- **单个文件最大**：100MB
- **保留文件数**：10个
- **自动压缩**：旧日志文件自动压缩

### 已有实现（未使用）

**文件**：`src/monitoring/structured_logging.py`

**实现**：
```python
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=self.max_file_size,  # 100MB
    backupCount=self.backup_count,  # 5个
    encoding="utf-8",
)
```

**说明**：
- 使用 `RotatingFileHandler` 实现日志轮转
- 但这部分代码似乎没有被主程序使用

## 修复方案

### 方案1：修改 `src/utils/logger.py`（推荐）

**修改内容**：
```python
import logging.handlers

# 修改前
file_handler = logging.FileHandler(log_path, encoding="utf-8")

# 修改后
file_handler = logging.handlers.RotatingFileHandler(
    log_path,
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=10,  # 保留10个备份文件
    encoding="utf-8",
)
```

**优点**：
- 简单直接
- 不影响现有代码
- 所有使用 `get_logger()` 的地方自动获得轮转功能

### 方案2：使用 `structured_logging.py`

**说明**：
- 使用 `StructuredLoggingSystem` 类
- 提供更高级的日志管理功能
- 需要修改代码以使用该类

### 方案3：定期清理旧日志（临时方案）

**脚本**：
```bash
# 清理超过7天的日志文件
find logs/ -name "*.log" -mtime +7 -delete

# 压缩超过1天的日志文件
find logs/ -name "*.log" -mtime +1 ! -name "*.gz" -exec gzip {} \;
```

## 建议的完整配置

### 日志轮转参数

```python
# 推荐的日志轮转配置
LOG_ROTATION_MAX_BYTES = 100 * 1024 * 1024  # 100MB
LOG_ROTATION_BACKUP_COUNT = 10  # 保留10个备份文件
LOG_ROTATION_ENABLE_COMPRESSION = True  # 启用压缩（需要额外实现）
```

### 日志级别配置

```python
# 生产环境
LOG_LEVEL = "INFO"  # 关闭DEBUG

# 开发环境
LOG_LEVEL = "DEBUG"  # 开启所有日志
```

### 日志文件命名

```
logs/
├── detect_vid1.log          # 当前日志
├── detect_vid1.log.1        # 备份1
├── detect_vid1.log.2        # 备份2
├── ...
└── detect_vid1.log.10       # 备份10（最旧）
```

## 立即行动

1. **修复日志轮转**：修改 `src/utils/logger.py` 使用 `RotatingFileHandler`
2. **清理当前日志**：可以考虑压缩或删除旧的 `detect_vid1.log`
3. **监控日志大小**：添加日志大小监控和告警

## 影响评估

### 修复后效果

1. **文件大小控制**：单个日志文件不会超过100MB
2. **自动轮转**：达到100MB时自动创建新文件
3. **保留历史**：保留最近10个日志文件
4. **磁盘空间**：最多占用约1GB磁盘空间（10 × 100MB）

### 注意事项

1. **现有日志**：修复后不会影响现有日志文件
2. **日志连续性**：轮转后日志会继续写入新文件
3. **查找日志**：需要查看多个文件才能找到完整的日志历史

