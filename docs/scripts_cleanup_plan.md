# 脚本和配置文件清理计划

## 日期
2025-11-03

## 概述
清理scripts目录下的弃用脚本和根目录下的重复.env配置文件，保留关键脚本。

---

## 📁 脚本清理分析

### ✅ 必须保留的关键脚本

#### 开发和启动脚本（核心）
- `scripts/start_dev.sh` - 开发环境启动脚本 ✅ **关键**
- `scripts/start_prod.sh` - 生产环境启动脚本 ✅ **关键**
- `scripts/setup_dev.sh` - 开发环境设置脚本 ✅
- `scripts/validate_config.py` - 配置验证脚本 ✅

#### 数据迁移脚本（仍在使用的工具）
- `scripts/migrate_cameras_from_yaml.py` - 相机配置迁移 ✅
- `scripts/migrate_regions_from_json.py` - 区域配置迁移 ✅
- `scripts/export_cameras_to_yaml.py` - 相机导出（备份/恢复）✅
- `scripts/export_regions_to_json.py` - 区域导出（备份/恢复）✅

#### 数据库脚本
- `scripts/init_db.sql` - 数据库初始化SQL ✅
- `scripts/init_database.py` - 数据库初始化Python脚本 ✅
- `scripts/test_database.py` - 数据库测试脚本 ✅
- `scripts/migrations/001_create_core_tables.sql` - 数据库迁移 ✅

#### 生产部署脚本（评估后保留）
- `scripts/build_prod_images.sh` - 构建生产镜像 ✅
- `scripts/generate_production_config.sh` - 生成生产配置 ✅
- `scripts/generate_production_secrets.py` - 生成生产密钥 ✅
- `scripts/deploy_prod.sh` - 生产部署脚本 ✅（作为主要部署脚本）
- `scripts/check_deployment_readiness.sh` - 部署就绪检查 ✅
- `scripts/push_to_registry.sh` - 推送到Registry ✅
- `scripts/deploy_from_registry.sh` - 从Registry部署 ✅

### ⚠️ 重复的部署脚本（保留一个，删除其他）

以下脚本功能重复，建议只保留 `deploy_prod.sh`：
- `scripts/deploy_prod.sh` ✅ **保留**（主部署脚本）
- `scripts/deploy_to_production.sh` ❌ **删除**（功能重复）
- `scripts/quick_deploy.sh` ❌ **删除**（功能重复）

### ❌ 可以删除的脚本

#### 一次性执行的清理脚本（已执行过）
- `scripts/cleanup_project.sh` ❌ **删除**（已执行过，有Git历史）
- `scripts/deep_cleanup.sh` ❌ **删除**（已执行过，有Git历史）

#### 一次性迁移脚本（已被新脚本替代）
- `scripts/migrate_camera_config.py` ❌ **删除**（已被migrate_cameras_from_yaml.py替代）

#### 一次性修复脚本
- `scripts/fix_xgboost_model.py` ❌ **删除**（一次性修复，已完成）

#### 开发工具脚本（可在需要时重新创建）
- `scripts/improved_head_roi.py` ❌ **删除**（开发工具，已完成）
- `scripts/update_dependencies.py` ❌ **删除**（可直接用pip）

#### Windows特定脚本（可保留在子目录，但项目主要在Linux/Mac）
- `scripts/activate_env.ps1` ❌ **删除**（Windows特定，很少使用）
- `scripts/quick_env.ps1` ❌ **删除**（Windows特定，很少使用）

#### 一次性设置脚本
- `scripts/setup_macos_arm64.sh` ❌ **删除**（一次性设置，已完成）

#### 镜像准备脚本（生产脚本已包含此功能）
- `scripts/prepare_base_images.sh` ❌ **删除**（build_prod_images.sh已包含）
- `scripts/load_offline_images.sh` ❌ **删除**（build_prod_images.sh已包含）

### 📂 子目录脚本（保留，但整理）

以下子目录脚本保留，它们是开发工具：

#### CI/CD脚本
- `scripts/ci/check_dev_env.py` ✅ 保留
- `scripts/ci/check_gpu.py` ✅ 保留
- `scripts/ci/check_ultralytics.py` ✅ 保留

#### 开发工具脚本
- `scripts/development/` ✅ 全部保留（开发时有用）

#### 数据脚本
- `scripts/data/add_dataset.py` ✅ 保留
- `scripts/data/prepare_roboflow_dataset.py` ✅ 保留

#### 前端脚本
- `scripts/frontend/build_optimizer.py` ✅ 保留
- `scripts/frontend/performance_analyzer.py` ✅ 保留

#### 维护脚本
- `scripts/maintenance/` ✅ 全部保留（维护时有用）

#### 优化脚本
- `scripts/optimization/` ✅ 全部保留（性能优化时有用）

#### 性能脚本
- `scripts/performance/` ✅ 全部保留（性能测试时有用）

#### 训练脚本
- `scripts/training/train_hairnet_model.py` ✅ 保留

#### 文档
- `scripts/README_PROD_BUILD.md` ✅ 保留（文档）

---

## 📄 .env配置文件清理分析

### ✅ 必须保留的配置文件

1. **`.env`** - 开发环境配置（当前使用）✅ **关键**
2. **`.env.example`** - 开发配置模板 ✅ **关键**
3. **`.env.production`** - 生产环境配置 ✅ **关键**
4. **`.env.production.example`** - 生产配置模板 ✅ **关键**

### ❌ 可以删除的配置文件

1. **`.env.test`** ❌ **删除**
   - 理由：测试环境可以使用开发环境配置（.env）
   - 项目中没有独立的测试环境，测试通常在开发环境运行

2. **`.env.bak.*`** ❌ **删除**（所有备份文件）
   - 理由：有Git历史记录，不需要本地备份
   - 文件：`.env.bak.20251103_182644`

3. **`.env.test.bak.*`** ❌ **删除**（所有备份文件）
   - 理由：同上
   - 文件：`.env.test.bak.20251103_180208`

---

## 📋 清理执行计划

### 阶段1：备份关键文件
在删除前，确保关键脚本和配置已在Git中。

### 阶段2：删除弃用脚本
删除以下脚本：
1. `scripts/deploy_to_production.sh`
2. `scripts/quick_deploy.sh`
3. `scripts/cleanup_project.sh`
4. `scripts/deep_cleanup.sh`
5. `scripts/migrate_camera_config.py`
6. `scripts/fix_xgboost_model.py`
7. `scripts/improved_head_roi.py`
8. `scripts/update_dependencies.py`
9. `scripts/activate_env.ps1`
10. `scripts/quick_env.ps1`
11. `scripts/setup_macos_arm64.sh`
12. `scripts/prepare_base_images.sh`
13. `scripts/load_offline_images.sh`

### 阶段3：删除重复配置文件
删除以下配置文件：
1. `.env.test`
2. `.env.bak.20251103_182644`
3. `.env.test.bak.20251103_180208`

### 阶段4：验证
验证关键脚本和配置文件仍在，系统可正常启动。

---

## ✅ 清理后保留的关键脚本列表

### 启动和部署脚本（6个）
- `scripts/start_dev.sh`
- `scripts/start_prod.sh`
- `scripts/setup_dev.sh`
- `scripts/deploy_prod.sh`
- `scripts/check_deployment_readiness.sh`
- `scripts/build_prod_images.sh`

### 数据迁移脚本（4个）
- `scripts/migrate_cameras_from_yaml.py`
- `scripts/migrate_regions_from_json.py`
- `scripts/export_cameras_to_yaml.py`
- `scripts/export_regions_to_json.py`

### 数据库脚本（3个）
- `scripts/init_db.sql`
- `scripts/init_database.py`
- `scripts/test_database.py`

### 生产工具脚本（4个）
- `scripts/generate_production_config.sh`
- `scripts/generate_production_secrets.py`
- `scripts/push_to_registry.sh`
- `scripts/deploy_from_registry.sh`

### 工具脚本（1个）
- `scripts/validate_config.py`

### 子目录脚本（全部保留）
- `scripts/ci/` - CI/CD工具
- `scripts/development/` - 开发工具
- `scripts/data/` - 数据处理
- `scripts/frontend/` - 前端工具
- `scripts/maintenance/` - 维护工具
- `scripts/optimization/` - 优化工具
- `scripts/performance/` - 性能测试
- `scripts/training/` - 训练脚本
- `scripts/migrations/` - 数据库迁移

---

## 📊 清理统计

### 删除的脚本数量
- 重复部署脚本：2个
- 一次性清理脚本：2个
- 一次性迁移脚本：1个
- 一次性修复脚本：1个
- 开发工具脚本：2个
- Windows脚本：2个
- 一次性设置脚本：1个
- 镜像准备脚本：2个
- **总计：13个脚本**

### 删除的配置文件数量
- 备份文件：2个
- 测试环境配置：1个
- **总计：3个配置文件**

### 保留的关键脚本
- 启动和部署脚本：6个
- 数据迁移脚本：4个
- 数据库脚本：3个
- 生产工具脚本：4个
- 工具脚本：1个
- 子目录脚本：全部保留
- **总计：18个关键脚本 + 所有子目录脚本**
