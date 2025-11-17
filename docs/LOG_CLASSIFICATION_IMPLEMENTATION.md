# 日志分类体系实施总结

## 📋 概述

本文档总结了日志分类体系的实施情况，包括已完成的修改和目录结构。

**更新日期**: 2025-11-14
**实施状态**: ✅ **已完成**

---

## 1. 实施内容

### 1.1 日志目录结构

实施后的日志目录结构：

```
logs/
├── detection/           # 检测日志（按相机）
│   ├── detect_vid1.log
│   ├── detect_cam0.log
│   └── ...
├── api/                 # API服务日志
│   ├── api.log
│   └── api_error.log
├── errors/              # 统一错误日志（所有模块）
│   └── error.log
└── events/              # 事件日志
    └── events_record.jsonl
```

### 1.2 已修改的文件

#### ✅ `src/utils/logger.py`

**修改内容**：
1. 添加 `log_category` 参数到 `get_logger()` 函数
2. 支持自动构建分类日志路径：
   - `detection`: `logs/detection/detect_{camera_id}.log`
   - `api`: `logs/api/api.log`
   - `application`: `logs/application/application.log`
   - `error`: `logs/errors/error.log`
   - `event`: `logs/events/events_record.jsonl`
3. 根据分类设置不同的日志轮转参数：
   - **API日志**: 50MB，5个备份
   - **错误日志**: 50MB，20个备份（保留更长时间）
   - **检测日志**: 100MB，10个备份
   - **默认**: 100MB，10个备份
4. 添加统一错误日志支持：`setup_error_logger()` 和 `log_error()`
5. 自动将ERROR级别日志同时写入统一错误日志

#### ✅ `src/services/executors/local.py`

**修改内容**：
1. 修改 `_log_file()` 函数，将检测日志放入 `logs/detection/` 目录
2. 日志文件路径：`logs/detection/detect_{camera_id}.log`

#### ✅ `src/api/app.py`

**修改内容**：
1. 配置API日志文件处理器，将API日志写入 `logs/api/api.log`
2. 配置API错误日志文件处理器，将API错误日志写入 `logs/api/api_error.log`
3. 使用 `RotatingFileHandler` 实现日志轮转：
   - API日志：50MB，5个备份
   - API错误日志：50MB，5个备份

#### ✅ `src/api/routers/events.py`

**修改内容**：
1. 更新 `_read_events()` 函数中的事件日志路径
2. 事件日志路径从 `logs/events_record.jsonl` 更新为 `logs/events/events_record.jsonl`

#### ✅ `src/api/routers/metrics.py`

**修改内容**：
1. 更新 `_read_event_counts()` 函数中的事件日志路径
2. 事件日志路径从 `logs/events_record.jsonl` 更新为 `logs/events/events_record.jsonl`

#### ✅ `src/api/routers/websocket.py`

**修改内容**：
1. 更新 `websocket_events()` 函数中的事件日志路径
2. 事件日志路径从 `logs/events_record.jsonl` 更新为 `logs/events/events_record.jsonl`

---

## 2. 日志分类说明

### 2.1 检测日志 (`logs/detection/`)

**用途**：
- 检测流程日志
- 检测结果日志
- 违规检测日志
- 统计信息日志

**文件命名**：
- `detect_{camera_id}.log`
- 示例：`detect_vid1.log`, `detect_cam0.log`

**轮转策略**：
- 单个文件最大：100MB
- 保留备份数：10个
- 保留时间：30天（通过清理脚本）

### 2.2 API日志 (`logs/api/`)

**用途**：
- API请求日志
- API响应日志
- API错误日志

**文件命名**：
- `api.log` - 所有API日志
- `api_error.log` - 仅ERROR级别日志

**轮转策略**：
- 单个文件最大：50MB
- 保留备份数：5个
- 保留时间：7天（通过清理脚本）

### 2.3 错误日志 (`logs/errors/`)

**用途**：
- 所有模块的错误日志汇总
- 便于集中监控和分析

**文件命名**：
- `error.log` - 统一错误日志

**轮转策略**：
- 单个文件最大：50MB
- 保留备份数：20个（保留更长时间）
- 保留时间：90天（通过清理脚本）

### 2.4 事件日志 (`logs/events/`)

**用途**：
- 检测事件日志
- 违规事件日志
- 行为事件日志

**文件命名**：
- `events_record.jsonl` - JSONL格式事件日志

**轮转策略**：
- 单个文件最大：200MB（待实现）
- 保留备份数：5个（待实现）
- 保留时间：90天（通过清理脚本）

---

## 3. 使用方法

### 3.1 使用分类日志

```python
from src.utils.logger import get_logger

# 检测日志（自动从name中提取camera_id）
logger = get_logger(name="detection:vid1", log_category="detection")

# API日志
logger = get_logger(name="api", log_category="api")

# 应用日志
logger = get_logger(name="application", log_category="application")

# 错误日志（手动记录）
from src.utils.logger import log_error
log_error("发生了错误", exc_info=True, extra_context={"user_id": "123"})
```

### 3.2 统一错误日志

所有使用 `get_logger()` 创建的日志记录器，如果日志级别设置为ERROR或以下，会自动将ERROR级别日志同时写入统一错误日志 `logs/errors/error.log`。

**注意**：统一错误日志写入是通过根日志记录器实现的，避免重复添加处理器。

---

## 4. 架构合规性

### ✅ 符合DDD架构要求

1. **日志文件位置**：
   - ✅ 所有日志文件仍在 `logs/` 目录下（符合规范）

2. **日志内容**：
   - ✅ 日志内容仍然符合分层架构规范（各层记录的内容不变）

3. **日志组织**：
   - ✅ 日志文件组织方式与架构层次正交（互相独立）

4. **架构映射**：
   - `logs/api/` → API层（`src/api/`）
   - `logs/application/` → 应用层（`src/application/`）
   - `logs/detection/` → 检测功能日志（应用层用例 + 基础设施层检测管道）
   - `logs/errors/` → 所有层的错误汇总
   - `logs/events/` → 领域事件日志

---

## 5. 后续工作

### 5.1 待完成

1. **事件日志轮转**：
   - ⏳ 实现 `events_record.jsonl` 的日志轮转（目前是JSONL格式，需要特殊处理）

2. **清理脚本更新**：
   - ⏳ 更新 `scripts/maintenance/cleanup_output.py`，支持按分类清理日志

3. **监控和告警**：
   - ⏳ 可以针对不同类型的日志进行监控和告警

### 5.2 可选优化

1. **按日期分目录**：
   - 可以考虑按日期进一步组织日志文件（如 `logs/detection/2025/11/14/detect_vid1.log`）

2. **日志压缩**：
   - 可以实现旧日志文件的自动压缩

3. **结构化日志**：
   - 可以支持JSON格式的结构化日志（便于日志聚合和分析）

---

## 6. 测试验证

### 6.1 验证步骤

1. **验证检测日志**：
   - 启动检测进程，检查 `logs/detection/` 目录是否创建
   - 检查日志文件是否正确生成（如 `detect_vid1.log`）

2. **验证API日志**：
   - 启动API服务，检查 `logs/api/` 目录是否创建
   - 检查 `api.log` 和 `api_error.log` 是否正确生成

3. **验证错误日志**：
   - 触发一个错误，检查 `logs/errors/error.log` 是否正确记录

4. **验证事件日志**：
   - 检查 `logs/events/events_record.jsonl` 路径是否正确
   - 验证事件读取功能是否正常

### 6.2 验证命令

```bash
# 检查日志目录结构
ls -la logs/

# 检查检测日志
ls -la logs/detection/

# 检查API日志
ls -la logs/api/

# 检查错误日志
ls -la logs/errors/

# 检查事件日志
ls -la logs/events/
```

---

## 7. 总结

✅ **实施完成**：
- 日志分类体系已成功实施
- 符合DDD架构要求
- 支持日志轮转
- 提供统一错误日志

📋 **主要改进**：
1. 日志按功能模块分类，便于管理
2. 不同日志类型设置不同的清理策略
3. 统一错误日志便于错误监控和分析
4. 符合架构规范，不影响现有功能

🔄 **后续优化**：
- 实现事件日志轮转
- 更新清理脚本支持分类清理
- 考虑按日期进一步组织日志

