# Scripts目录清理计划

## 📋 清理目标

**目标**: 只保留开发部署和生产部署过程中需要的脚本，其他测试文件归类处理

**原则**:
- ✅ 保留所有部署相关脚本
- ✅ 保留数据库初始化和管理脚本
- ✅ 保留配置验证脚本
- ✅ 测试/诊断脚本归类到子目录
- ❌ 删除重复或过时的脚本

---

## 📁 目录结构规划

### 保留在根目录的脚本（部署必需）

#### 开发环境脚本
- ✅ `setup_dev.sh` - 开发环境设置
- ✅ `start_dev.sh` - 启动开发环境
- ✅ `backup_dev_data.sh` - 开发环境数据备份
- ✅ `restore_dev_data.sh` - 开发环境数据恢复
- ✅ `rebuild_dev_environment.sh` - 重建开发环境
- ✅ `check_database_init.sh` - 检查数据库初始化
- ✅ `fix_database_user.sh` - 修复数据库用户

#### 生产环境脚本
- ✅ `build_prod_images.sh` - 构建生产镜像
- ✅ `generate_production_config.sh` - 生成生产配置
- ✅ `generate_production_secrets.py` - 生成生产密钥
- ✅ `deploy_prod.sh` - 生产部署
- ✅ `deploy_from_registry.sh` - 从Registry部署
- ✅ `push_to_registry.sh` - 推送到Registry
- ✅ `quick_deploy.sh` - 一键部署
- ✅ `check_deployment_readiness.sh` - 检查部署就绪
- ✅ `backup_db.sh` - 生产数据库备份
- ✅ `restore_db.sh` - 生产数据库恢复
- ✅ `start_prod.sh` - 启动生产环境
- ✅ `start_prod_wsl.sh` - WSL环境启动生产

#### 数据库脚本
- ✅ `init_db.sql` - 数据库初始化SQL
- ✅ `init_database.py` - 数据库初始化Python
- ✅ `validate_config.py` - 配置验证

#### 迁移脚本（保留，但可考虑归类）
- ⚠️ `migrate_cameras_from_yaml.py` - 相机迁移（一次性，可归类）
- ⚠️ `migrate_regions_from_json.py` - 区域迁移（一次性，可归类）
- ⚠️ `export_cameras_to_yaml.py` - 相机导出（备份用，保留）
- ⚠️ `export_regions_to_json.py` - 区域导出（备份用，保留）

---

## 📂 归类目录结构

### 1. `scripts/tests/` - 测试脚本
移动以下文件：
- `test_database.py`
- `test_dataset_validation.py`
- `test_db_insert.py`
- `test_deployment_service.py`
- `test_docker_service.py`
- `test_frontend_improvements.py`
- `test_roi_without_preprocessing.py`
- `test_timezone_fix.py`
- `test_xgboost_enabled.py`
- `verify_export_functionality.py`
- `verify_mlops_workflow.py`

### 2. `scripts/diagnostics/` - 诊断脚本
移动以下文件：
- `diagnose_cuda.py`
- `diagnose_hairnet_detection.py`
- `diagnose_hairnet_roi.py`
- `diagnose_torch_import.py`
- `debug_stats.py`

### 3. `scripts/tools/` - 工具脚本
移动以下文件：
- `check_camera_table_structure.py`
- `check_cameras_in_db.py`
- `check_db_structure.py`
- `check_saved_records.py`
- `check_video_stream_status.sh`
- `create_resume_training_workflow.py`
- `download_models.sh`

### 4. `scripts/migrations/` - 数据迁移（已存在）
保留现有结构，但考虑移动：
- `migrate_cameras_from_yaml.py` → `scripts/migrations/`
- `migrate_regions_from_json.py` → `scripts/migrations/`

### 5. `scripts/sql/` - SQL脚本（新建）
移动以下文件：
- `check_alert_data.sql` → `scripts/sql/`
- `create_test_alert_data.sql` → `scripts/sql/`
- `init_db.sql` → 保留在根目录（部署必需）

---

## 🗑️ 删除的脚本

### Windows脚本（Linux环境不需要）
- ❌ `start_dev.ps1`
- ❌ `start_prod.ps1`
- ❌ `start_prod_wsl.ps1`
- ❌ `start_frontend.ps1`

### 重复的部署脚本
- ⚠️ 检查是否有重复功能

---

## 📝 保留的子目录

以下子目录已存在且结构合理，保持不变：
- ✅ `scripts/ci/` - CI/CD工具
- ✅ `scripts/development/` - 开发工具
- ✅ `scripts/data/` - 数据处理
- ✅ `scripts/frontend/` - 前端工具
- ✅ `scripts/maintenance/` - 维护工具
- ✅ `scripts/optimization/` - 优化工具
- ✅ `scripts/performance/` - 性能测试
- ✅ `scripts/training/` - 训练脚本
- ✅ `scripts/migrations/` - 数据库迁移
- ✅ `scripts/mlops/` - MLOps工具
- ✅ `scripts/evaluation/` - 评估脚本
- ✅ `scripts/verification/` - 验证脚本

---

## 📊 清理统计

### 保留在根目录的脚本
- 开发环境脚本: 7个
- 生产环境脚本: 12个
- 数据库脚本: 3个
- 迁移/导出脚本: 4个（可选归类）
- **总计: 26个核心脚本**

### 归类到子目录的脚本
- 测试脚本: 11个 → `scripts/tests/`
- 诊断脚本: 5个 → `scripts/diagnostics/`
- 工具脚本: 7个 → `scripts/tools/`
- SQL脚本: 2个 → `scripts/sql/`
- **总计: 25个归类脚本**

### 删除的脚本
- Windows脚本: 4个
- **总计: 4个删除**

---

## ✅ 清理步骤

1. 创建归类目录
2. 移动测试脚本
3. 移动诊断脚本
4. 移动工具脚本
5. 移动SQL脚本
6. 删除Windows脚本
7. 更新文档引用
8. 创建README说明

---

**创建日期**: 2025-11-25  
**状态**: 📋 计划中

