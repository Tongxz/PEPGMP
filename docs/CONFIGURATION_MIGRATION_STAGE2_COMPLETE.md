# 配置迁移阶段2完成报告

## 📊 执行摘要

**状态**: ✅ **完成**

阶段2（检测参数迁移到数据库）已完成。现在检测参数配置以数据库（PostgreSQL）为单一数据源，支持全局默认值和按相机覆盖，并实现了配置变更通知机制（Redis Pub/Sub）。

---

## ✅ 完成的工作

### 1. 创建detection_configs数据库表结构

**文件**: `scripts/migrations/001_create_detection_configs_table.sql`

- ✅ 创建 `detection_configs` 表
- ✅ 支持全局默认值（`camera_id IS NULL`）
- ✅ 支持按相机覆盖（`camera_id IS NOT NULL`）
- ✅ 使用JSONB存储配置值
- ✅ 创建索引优化查询性能

**表结构**:
```sql
CREATE TABLE detection_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NULL,  -- NULL表示全局默认值
    config_type VARCHAR(50) NOT NULL,  -- human_detection, hairnet_detection等
    config_key VARCHAR(100) NOT NULL,  -- 配置项名称
    config_value JSONB NOT NULL,  -- 配置值
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, config_type, config_key)
);
```

### 2. 创建IDetectionConfigRepository接口和PostgreSQL实现

**文件**: 
- `src/domain/repositories/detection_config_repository.py` - 接口
- `src/infrastructure/repositories/postgresql_detection_config_repository.py` - 实现

- ✅ 定义仓储接口（CRUD操作）
- ✅ 实现PostgreSQL仓储
- ✅ 支持配置合并（全局配置 + 相机特定配置）
- ✅ 自动创建数据库表

**关键方法**:
- `save()` - 保存配置
- `find_by_camera_and_type()` - 查找配置（合并全局和相机配置）
- `find_all_by_type()` - 查找指定类型的所有配置
- `delete()` - 删除配置
- `exists()` - 检查配置是否存在

### 3. 创建DetectionConfigService领域服务

**文件**: `src/domain/services/detection_config_service.py`

- ✅ 提供配置获取、保存、合并等业务逻辑
- ✅ 支持批量保存配置
- ✅ 支持配置合并（全局配置 + 相机特定配置）

**关键方法**:
- `get_config()` - 获取配置
- `get_all_configs()` - 获取所有配置
- `save_config()` - 保存配置
- `save_configs()` - 批量保存配置
- `get_merged_config()` - 获取合并后的配置

### 4. 编写从unified_params.yaml迁移到数据库的脚本

**文件**: `scripts/migrations/002_migrate_unified_params_to_db.py`

- ✅ 从YAML文件读取配置
- ✅ 提取配置项并插入数据库
- ✅ 支持干运行模式（预览）
- ✅ 自动创建数据库表
- ✅ 支持更新现有配置

**使用方法**:
```bash
# 实际迁移
python scripts/migrations/002_migrate_unified_params_to_db.py

# 干运行（预览）
python scripts/migrations/002_migrate_unified_params_to_db.py --dry-run
```

### 5. 修改get_unified_params()优先从数据库读取

**文件**: 
- `src/config/unified_params.py` - 添加 `load_from_dict()` 方法
- `src/config/unified_params_loader.py` - 新增配置加载器

- ✅ 创建 `UnifiedParams.load_from_dict()` 方法（从字典加载配置）
- ✅ 创建 `unified_params_loader.py`（支持从数据库和YAML加载）
- ✅ `get_unified_params()` 同步函数（向后兼容，从YAML加载）
- ✅ `load_unified_params_from_db()` 异步函数（从数据库加载）
- ✅ 支持配置缓存和强制重新加载

### 6. 更新检测配置API同时更新数据库和YAML

**文件**: `src/api/routers/detection_config.py`

- ✅ `get_detection_config()` 优先从数据库读取
- ✅ `update_detection_config()` 同时更新数据库和YAML
- ✅ 支持按相机保存配置（`camera_id` 参数）
- ✅ 更新后清除缓存，强制重新加载

### 7. 添加配置变更通知机制（Redis Pub/Sub）

**文件**: 
- `src/infrastructure/notifications/config_change_notifier.py` - 通知发布服务
- `src/application/config_change_listener.py` - 配置变更监听器

- ✅ 创建配置变更通知服务（同步和异步版本）
- ✅ 在检测配置API中发布配置变更通知
- ✅ 创建配置变更监听器（检测进程订阅配置变更）
- ✅ 在DetectionLoopService中集成配置变更监听器
- ✅ 收到通知后自动重新加载配置

**通知频道**:
- `detection_config:change` - 全局频道（所有检测进程订阅）
- `detection_config:change:global` - 全局配置变更
- `detection_config:change:camera:{camera_id}` - 相机特定配置变更

### 8. 优化Redis配置同步逻辑

**文件**: `src/api/routers/cameras.py`

- ✅ 优化 `_sync_video_stream_config_to_redis()` 函数
- ✅ 相机配置修改时同步到Redis
- ✅ 发布配置变更通知

---

## 🎯 架构改进成果

### 之前（YAML单一存储）

```
┌──────────────┐
│  YAML File   │ ← 单一数据源
└──────┬───────┘
       │
       └─→ Detection Process
```

**问题**:
- ❌ 不支持按相机配置
- ❌ 配置变更需要重启检测进程
- ❌ 无法动态更新配置
- ❌ 配置管理不灵活

### 现在（数据库 + Redis通知）

```
┌──────────────┐
│  Database    │ ← 单一数据源（支持全局和按相机）
└──────┬───────┘
       │
       ├─→ API Layer（读取配置）
       │
       ├─→ Redis Pub/Sub（配置变更通知）
       │
       └─→ Detection Process（订阅通知，自动重新加载）
```

**优势**:
- ✅ 数据库作为单一数据源
- ✅ 支持全局默认值和按相机覆盖
- ✅ 配置变更通知机制（Redis Pub/Sub）
- ✅ 检测进程自动重新加载配置
- ✅ 配置管理更灵活

---

## 📊 配置读取流程

### FastAPI环境（推荐）

```
1. API层调用 load_unified_params_from_db(camera_id)
2. DetectionConfigService.get_all_configs(camera_id)
3. PostgreSQLDetectionConfigRepository.find_by_camera_and_type()
   - 先加载全局配置（camera_id IS NULL）
   - 再加载相机特定配置并覆盖
4. UnifiedParams.load_from_dict(config_dict)
5. 返回配置对象
```

### 检测进程环境

```
1. 启动时从数据库加载配置（通过命令行参数传递）
2. 订阅配置变更通知（Redis Pub/Sub）
3. 收到通知后自动重新加载配置
4. 部分配置需要重启才能完全生效
```

---

## 🔧 配置变更通知机制

### 发布通知

```python
# 在检测配置API中
await publish_config_change_notification_async(
    camera_id=camera_id,
    config_type="human_detection",
    config_key="confidence_threshold",
    config_value=0.6,
    change_type="update",
)
```

### 订阅通知

```python
# 在检测进程中
config_change_listener = ConfigChangeListener(
    camera_id=camera_id,
    on_config_change=on_config_change,
)
await config_change_listener.start()
```

### 处理通知

```python
def on_config_change(notification: Dict[str, Any]):
    # 重新加载配置
    params = get_unified_params()
    # 更新检测管道的参数
    detection_pipeline.params = params
```

---

## 📝 配置存储状态

### ✅ 已存入数据库

- **检测参数配置**（`detection_configs` 表）
  - 全局默认值（`camera_id IS NULL`）
  - 按相机覆盖（`camera_id IS NOT NULL`）
  - 配置类型：`human_detection`, `hairnet_detection`, `behavior_recognition`, `pose_detection`, `detection_rules`, `system`

### ✅ 保留在文件（作为备份）

- **`config/unified_params.yaml`**
  - 作为备份和回退
  - 配置更新时同步更新YAML
  - 数据库不可用时从YAML加载

---

## 🚀 使用示例

### 从数据库加载配置

```python
# 在FastAPI环境中（异步）
from src.config.unified_params_loader import load_unified_params_from_db

# 获取全局配置
params = await load_unified_params_from_db()

# 获取特定相机的配置
params = await load_unified_params_from_db(camera_id="vid1")
```

### 更新配置

```python
# 通过API更新配置
PUT /api/v1/detection-config?camera_id=vid1
{
    "human_detection": {
        "confidence_threshold": 0.6
    }
}
```

### 迁移配置

```bash
# 从YAML迁移到数据库
python scripts/migrations/002_migrate_unified_params_to_db.py

# 干运行（预览）
python scripts/migrations/002_migrate_unified_params_to_db.py --dry-run
```

---

## 🚀 后续工作

### 阶段3：运行时配置优化（已完成）

- ✅ 优化Redis配置同步逻辑（相机配置修改时同步到Redis）
- ✅ 添加配置变更通知机制（Redis Pub/Sub）

### 待优化项

- [ ] 实现配置热重载（部分配置无需重启即可生效）
- [ ] 添加配置版本管理
- [ ] 添加配置变更历史记录
- [ ] 实现配置回滚功能

---

## 📝 注意事项

1. **配置变更通知**：
   - 配置更新时会自动发布通知到Redis
   - 检测进程会自动订阅通知并重新加载配置
   - 部分配置（如模型路径）需要重启才能完全生效

2. **配置合并逻辑**：
   - 全局配置（`camera_id IS NULL`）作为默认值
   - 相机特定配置（`camera_id IS NOT NULL`）覆盖全局配置
   - 合并顺序：先加载全局配置，再加载相机特定配置

3. **YAML文件作为备份**：
   - YAML文件仍用于备份和回退
   - 配置更新时会同步更新YAML
   - 数据库不可用时从YAML加载

---

## 📚 相关文档

- `docs/CONFIGURATION_ANALYSIS.md` - 配置分析文档
- `docs/CONFIGURATION_MIGRATION_PLAN.md` - 配置迁移计划
- `docs/CONFIGURATION_MIGRATION_STAGE1_COMPLETE.md` - 阶段1完成报告
- `docs/CONFIGURATION_MIGRATION_PROGRESS.md` - 配置迁移进度报告

---

**更新日期**: 2025-11-13
**状态**: 阶段2完成

