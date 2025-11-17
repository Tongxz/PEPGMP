# 配置迁移进度报告

## 📊 执行摘要

**状态**: ✅ **阶段1完成** | 🔄 **阶段2进行中**

---

## ✅ 阶段1：相机配置统一到数据库（已完成）

### 完成的工作

1. ✅ **修改LocalProcessExecutor支持传入相机配置**
   - `start()` 方法新增 `camera_config` 参数
   - 优先使用传入的配置，避免调用 `list_cameras()`

2. ✅ **修改DetectionScheduler传递相机配置**
   - `start_detection()` 方法新增 `camera_config` 参数
   - 将配置传递给executor

3. ✅ **修改CameraControlService从数据库获取配置**
   - `start_camera()` 方法改为 `async`
   - 从数据库获取相机配置并传递给scheduler

4. ✅ **修改API路由支持传递配置**
   - `start_camera()` 路由从数据库获取配置
   - 传递给scheduler（如果使用领域服务，则自动处理）

5. ✅ **保留YAML回退机制**
   - `list_cameras()` 方法保留YAML回退
   - 添加警告日志，提醒YAML不再是主要配置源
   - 仅在数据库不可用或命令行启动时使用

### 架构改进

**之前**:
- executor运行时依赖YAML文件
- 数据不一致风险
- 前端修改配置后，executor可能读取到旧配置

**现在**:
- 数据库作为单一数据源
- API层从数据库获取配置并传递给executor
- executor不依赖YAML文件（保留回退机制）
- 前端修改配置后，executor立即使用新配置

---

## 🔄 阶段2：检测参数迁移到数据库（进行中）

### 已完成的工作

1. ✅ **创建detection_configs数据库表结构**
   - SQL迁移脚本：`scripts/migrations/001_create_detection_configs_table.sql`
   - 支持全局默认值和按相机覆盖
   - 使用JSONB存储配置值

2. ✅ **创建IDetectionConfigRepository接口和PostgreSQL实现**
   - 接口：`src/domain/repositories/detection_config_repository.py`
   - 实现：`src/infrastructure/repositories/postgresql_detection_config_repository.py`
   - 支持CRUD操作、配置合并（全局配置 + 相机特定配置）

3. ✅ **创建DetectionConfigService领域服务**
   - 服务：`src/domain/services/detection_config_service.py`
   - 提供配置获取、保存、合并等业务逻辑

4. ✅ **编写从unified_params.yaml迁移到数据库的脚本**
   - 迁移脚本：`scripts/migrations/002_migrate_unified_params_to_db.py`
   - 支持干运行模式
   - 自动创建数据库表

5. ✅ **修改get_unified_params()优先从数据库读取**
   - 创建 `unified_params_loader.py`（支持从数据库和YAML加载）
   - 修改 `get_unified_params()` 向后兼容（同步函数，从YAML加载）
   - 创建 `load_unified_params_from_db()` 异步函数（从数据库加载）

6. ✅ **更新检测配置API同时更新数据库和YAML**
   - 修改 `get_detection_config()` 支持从数据库读取
   - 修改 `update_detection_config()` 支持同时更新数据库和YAML
   - 支持按相机保存配置（`camera_id` 参数）

### 待完成的工作

1. ⏳ **添加配置变更通知机制（Redis Pub/Sub）**
   - 配置更新时发布通知
   - 检测进程订阅通知并重新加载配置

2. ⏳ **优化Redis配置同步逻辑（相机配置修改时同步到Redis）**
   - 相机配置修改时同步到Redis
   - 检测进程启动时从数据库读取配置并同步到Redis

---

## 📊 数据库表结构

### detection_configs表

```sql
CREATE TABLE detection_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NULL,  -- NULL表示全局默认值
    config_type VARCHAR(50) NOT NULL,  -- human_detection, hairnet_detection等
    config_key VARCHAR(100) NOT NULL,  -- 配置项名称
    config_value JSONB NOT NULL,  -- 配置值（JSONB格式）
    description TEXT,  -- 配置项描述
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, config_type, config_key)
);
```

### 配置合并逻辑

- **全局配置**（`camera_id IS NULL`）：所有相机的默认配置
- **相机特定配置**（`camera_id IS NOT NULL`）：覆盖全局配置
- **合并顺序**：先加载全局配置，然后加载相机特定配置并覆盖

---

## 🔧 配置加载流程

### FastAPI环境（推荐）

```
1. API层调用 load_unified_params_from_db(camera_id)
2. 从数据库加载配置（全局配置 + 相机特定配置）
3. 转换为UnifiedParams对象
4. 返回配置对象
```

### 同步环境（回退）

```
1. 调用 get_unified_params()
2. 从YAML文件加载配置
3. 返回配置对象
```

---

## 📝 使用示例

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

# 干运行模式（预览）
python scripts/migrations/002_migrate_unified_params_to_db.py --dry-run
```

---

## 🚀 下一步

1. **添加配置变更通知机制（Redis Pub/Sub）**
   - 配置更新时发布通知
   - 检测进程订阅通知并重新加载配置

2. **优化Redis配置同步逻辑**
   - 相机配置修改时同步到Redis
   - 检测进程启动时从数据库读取配置并同步到Redis

3. **测试验证**
   - 测试配置迁移脚本
   - 测试配置加载（数据库优先，YAML回退）
   - 测试配置更新（数据库 + YAML）

---

## 📚 相关文档

- `docs/CONFIGURATION_ANALYSIS.md` - 配置分析文档
- `docs/CONFIGURATION_MIGRATION_PLAN.md` - 配置迁移计划
- `docs/CONFIGURATION_MIGRATION_STAGE1_COMPLETE.md` - 阶段1完成报告

---

**更新日期**: 2025-11-13
**状态**: 阶段1完成，阶段2进行中

