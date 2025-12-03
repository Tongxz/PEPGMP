# Scripts 目录清理执行计划

## 📋 清理原则

1. **保留核心脚本**：开发环境、生产部署、数据库管理必需脚本
2. **删除临时修复脚本**：一次性修复脚本，问题已解决
3. **删除临时诊断脚本**：一次性诊断脚本，问题已解决
4. **保留 Windows 脚本**：跨平台支持需要（但仅保留必要的）
5. **移动工具脚本**：非核心工具脚本移动到对应子目录

## 🗑️ 删除列表（临时修复脚本）

### Nginx 修复脚本（问题已解决，不再需要）
- ❌ `fix_nginx_mount.sh`
- ❌ `fix_nginx_mount_issue.sh`
- ❌ `fix_nginx_no_frontend.sh`
- ❌ `fix_nginx_permissions.sh`
- ❌ `fix_nginx_structure.sh`
- ❌ `update_nginx_for_frontend.sh`

### 行尾修复脚本（已通过 .gitattributes 解决）
- ❌ `fix_line_endings.sh`
- ❌ `fix_line_endings.ps1`
- ❌ `fix_line_endings_wsl.sh`
- ❌ `fix_file_endings.py`

### 其他临时修复脚本
- ❌ `fix_prepare_deploy_encoding.py`
- ❌ `fix_prompts.py`
- ❌ `fix_syntax_errors.py`
- ❌ `fix_generate_config.py`

### 临时诊断脚本（问题已解决）
- ❌ `diagnose_scheme_b.sh` - Scheme B 诊断（已修复）
- ❌ `diagnose_frontend_whitescreen.sh` - 前端白屏诊断（已修复）
- ❌ `test_scheme_b.sh` - Scheme B 测试（已修复）
- ❌ `test_unified_script.sh` - 统一脚本测试（一次性）
- ❌ `verify_frontend_fix.sh` - 前端修复验证（一次性）
- ❌ `check_frontend_detailed.sh` - 前端详细检查（一次性）
- ❌ `check_frontend_status.sh` - 前端状态检查（一次性）
- ❌ `cleanup_old_frontend.sh` - 旧前端清理（一次性）
- ❌ `redeploy_scheme_b.sh` - Scheme B 重新部署（一次性）
- ❌ `force_rebuild_frontend.ps1` - 强制重建前端（一次性）

### 其他临时脚本
- ❌ `convert_to_english.py` - 转换脚本（一次性）
- ❌ `find_env_file.sh` - 查找环境文件（工具脚本，可删除）

## ✅ 保留列表（核心脚本）

### 启动脚本
- ✅ `start.sh` - 统一启动脚本（核心）
- ✅ `start_dev.sh` - 开发环境启动
- ✅ `start_prod.sh` - 生产环境启动
- ✅ `start_prod_wsl.sh` - WSL 生产启动

### 构建和部署脚本
- ✅ `build_prod_only.sh` - 构建生产镜像
- ✅ `build_prod_images.sh` - 构建+推送+导出镜像
- ✅ `deploy_prod.sh` - 生产部署
- ✅ `deploy_from_registry.sh` - 从 Registry 部署
- ✅ `quick_deploy.sh` - 一键部署
- ✅ `prepare_minimal_deploy.sh` - 准备最小部署包
- ✅ `push_to_registry.sh` - 推送到 Registry

### 配置脚本
- ✅ `generate_production_config.sh` - 生成生产配置
- ✅ `generate_production_secrets.py` - 生成生产密钥
- ✅ `update_image_version.sh` - 更新镜像版本
- ✅ `validate_config.py` - 配置验证
- ✅ `check_deployment_readiness.sh` - 检查部署就绪

### 数据库脚本
- ✅ `init_db.sql` - 数据库初始化 SQL
- ✅ `init_database.py` - 数据库初始化 Python
- ✅ `backup_db.sh` - 数据库备份
- ✅ `restore_db.sh` - 数据库恢复
- ✅ `check_database_health.sh` - 数据库健康检查
- ✅ `check_database_init.sh` - 检查数据库初始化
- ✅ `fix_database_user.sh` - 修复数据库用户（可能需要）

### 开发环境脚本
- ✅ `setup_dev.sh` - 开发环境设置
- ✅ `backup_dev_data.sh` - 开发数据备份
- ✅ `restore_dev_data.sh` - 开发数据恢复
- ✅ `rebuild_dev_environment.sh` - 重建开发环境

### Docker 相关
- ✅ `docker-entrypoint.sh` - Docker 入口脚本（核心）

### 数据导出/迁移脚本
- ✅ `export_cameras_to_yaml.py` - 导出相机配置（备份用）
- ✅ `export_regions_to_json.py` - 导出区域配置（备份用）

### Windows 脚本（保留必要的）
- ✅ `build_prod_only.ps1` - Windows 构建脚本
- ✅ `update_image_version.ps1` - Windows 更新镜像版本
- ✅ `export_images_to_wsl.ps1` - Windows 导出镜像到 WSL
- ✅ `import_images_from_windows.sh` - 从 Windows 导入镜像

### 工具脚本（保留）
- ✅ `check_images.sh` - 检查镜像（部署验证用）

## 📂 移动列表（移动到子目录）

### 移动到 `scripts/diagnostics/`
- 📁 `check_frontend_detailed.sh` → 如果保留，移动到 diagnostics/
- 📁 `check_frontend_status.sh` → 如果保留，移动到 diagnostics/

## 📊 统计

### 删除数量
- 临时修复脚本: 18 个
- 临时诊断脚本: 10 个
- 其他临时脚本: 2 个
- **总计删除: 30 个脚本**

### 保留数量
- 启动脚本: 4 个
- 构建和部署脚本: 7 个
- 配置脚本: 5 个
- 数据库脚本: 7 个
- 开发环境脚本: 4 个
- Docker 相关: 1 个
- 数据导出/迁移: 2 个
- Windows 脚本: 4 个
- 工具脚本: 1 个
- **总计保留: 35 个核心脚本**

## 🚀 执行步骤

1. 备份当前 scripts 目录（可选）
2. 删除临时修复脚本
3. 删除临时诊断脚本
4. 删除其他临时脚本
5. 更新 README.md 文档
6. 验证核心脚本功能
