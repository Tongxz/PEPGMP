# Scripts 目录完整脚本清单

## 📊 脚本统计

**最后更新**: 2025-12-02
**总脚本数**: 108 个

## 📁 目录结构

### 根目录脚本（35 个）

#### 启动脚本（4 个）
- `start.sh` - 统一启动脚本（核心）
- `start_dev.sh` - 开发环境启动
- `start_prod.sh` - 生产环境启动
- `start_prod_wsl.sh` - WSL 生产启动

#### 构建和部署脚本（7 个）
- `build_prod_only.sh` - 构建生产镜像
- `build_prod_only.ps1` - Windows 构建脚本
- `build_prod_images.sh` - 构建+推送+导出镜像
- `deploy_prod.sh` - 生产部署
- `deploy_from_registry.sh` - 从 Registry 部署
- `quick_deploy.sh` - 一键部署
- `prepare_minimal_deploy.sh` - 准备最小部署包
- `push_to_registry.sh` - 推送到 Registry

#### 配置脚本（5 个）
- `generate_production_config.sh` - 生成生产配置
- `generate_production_secrets.py` - 生成生产密钥
- `update_image_version.sh` - 更新镜像版本
- `update_image_version.ps1` - Windows 更新镜像版本
- `validate_config.py` - 配置验证
- `check_deployment_readiness.sh` - 检查部署就绪

#### 数据库脚本（7 个）
- `init_db.sql` - 数据库初始化 SQL
- `init_database.py` - 数据库初始化 Python
- `backup_db.sh` - 数据库备份
- `restore_db.sh` - 数据库恢复
- `check_database_health.sh` - 数据库健康检查
- `check_database_init.sh` - 检查数据库初始化
- `fix_database_user.sh` - 修复数据库用户

#### 开发环境脚本（4 个）
- `setup_dev.sh` - 开发环境设置
- `backup_dev_data.sh` - 开发数据备份
- `restore_dev_data.sh` - 开发数据恢复
- `rebuild_dev_environment.sh` - 重建开发环境

#### Docker 相关（1 个）
- `docker-entrypoint.sh` - Docker 入口脚本（核心）

#### 数据导出/迁移脚本（3 个）
- `export_cameras_to_yaml.py` - 导出相机配置
- `export_regions_to_json.py` - 导出区域配置
- `export_images_to_wsl.ps1` - Windows 导出镜像到 WSL

#### 工具脚本（2 个）
- `check_images.sh` - 检查镜像
- `import_images_from_windows.sh` - 从 Windows 导入镜像

#### 文档（4 个）
- `README.md` - 脚本目录说明
- `README_PROD_BUILD.md` - 生产构建说明
- `SCRIPTS_CLEANUP_PLAN.md` - 清理计划文档（历史）
- `CLEANUP_EXECUTION_PLAN.md` - 清理执行计划（历史）
- `CLEANUP_SUMMARY.md` - 清理总结报告
- `COMPLETE_SCRIPTS_INVENTORY.md` - 本文件

---

### 子目录脚本（73 个）

#### `lib/` - 公共函数库（6 个）
- `common.sh` - 通用函数
- `config_validation.sh` - 配置验证
- `deploy_config.sh` - 统一部署配置 ⭐
- `docker_utils.sh` - Docker 工具函数
- `env_detection.sh` - 环境检测
- `service_manager.sh` - 服务管理

#### `sql/` - SQL 脚本（2 个）
- `check_alert_data.sql` - 检查告警数据
- `create_test_alert_data.sql` - 创建测试告警数据

#### `migrations/` - 数据库迁移（10 个）
- `001_create_core_tables.sql` - 创建核心表
- `001_create_detection_configs_table.sql` - 创建检测配置表
- `002_add_camera_status_column.sql` - 添加相机状态列
- `002_migrate_unified_params_to_db.py` - 迁移统一参数到数据库
- `003_convert_camera_id_to_varchar.py` - 转换相机 ID 为字符串
- `004_make_stream_url_nullable.py` - 使流 URL 可为空
- `005_revert_camera_id_to_uuid.py` - 恢复相机 ID 为 UUID
- `migrate_cameras_from_yaml.py` - 从 YAML 迁移相机
- `migrate_regions_from_json.py` - 从 JSON 迁移区域
- `run_migration_002.py` - 运行迁移 002

#### `tools/` - 工具脚本（7 个）
- `check_camera_table_structure.py` - 检查相机表结构
- `check_cameras_in_db.py` - 检查数据库中的相机
- `check_db_structure.py` - 检查数据库结构
- `check_saved_records.py` - 检查保存的记录
- `check_video_stream_status.sh` - 检查视频流状态
- `create_resume_training_workflow.py` - 创建恢复训练工作流
- `download_models.sh` - 下载模型

#### `diagnostics/` - 诊断脚本（5 个）
- `debug_stats.py` - 调试统计
- `diagnose_cuda.py` - CUDA 诊断
- `diagnose_hairnet_detection.py` - 安全帽检测诊断
- `diagnose_hairnet_roi.py` - 安全帽 ROI 诊断
- `diagnose_torch_import.py` - Torch 导入诊断

#### `tests/` - 测试脚本（11 个）
- `test_database.py` - 数据库测试
- `test_dataset_validation.py` - 数据集验证测试
- `test_db_insert.py` - 数据库插入测试
- `test_deployment_service.py` - 部署服务测试
- `test_docker_service.py` - Docker 服务测试
- `test_frontend_improvements.py` - 前端改进测试
- `test_roi_without_preprocessing.py` - ROI 无预处理测试
- `test_timezone_fix.py` - 时区修复测试
- `test_xgboost_enabled.py` - XGBoost 启用测试
- `verify_export_functionality.py` - 验证导出功能
- `verify_mlops_workflow.py` - 验证 MLOps 工作流

#### `data/` - 数据处理（2 个）
- `add_dataset.py` - 添加数据集
- `prepare_roboflow_dataset.py` - 准备 Roboflow 数据集

#### `performance/` - 性能测试（5 个）
- `gpu_acceleration_optimizer.py` - GPU 加速优化器
- `gpu_optimization_setup.py` - GPU 优化设置
- `gpu_performance_test.py` - GPU 性能测试
- `performance_profiler.py` - 性能分析器
- `windows_gpu_optimizer.py` - Windows GPU 优化器

#### `maintenance/` - 维护工具（9 个）
- `cleanup_output.py` - 清理输出
- `cleanup_root.sh` - 清理根目录
- `cleanup_root_directory.py` - 清理根目录（Python）
- `cleanup_tests.py` - 清理测试
- `organize_model_files.py` - 组织模型文件
- `organize_tests.py` - 组织测试
- `update_model_paths.py` - 更新模型路径
- `update_test_paths.py` - 更新测试路径
- `verify_model_paths.py` - 验证模型路径

#### `evaluation/` - 评估脚本（2 个）
- `evaluate_hairnet_model.py` - 评估安全帽模型
- `evaluate_handwash_model.py` - 评估洗手模型

#### `verification/` - 验证脚本（1 个）
- `verify_optimizations.py` - 验证优化

#### `mlops/` - MLOps 工具（2 个）
- `test_api_connection.py` - 测试 API 连接
- `train_hairnet_workflow.py` - 训练安全帽工作流

#### `training/` - 训练脚本（1 个）
- `train_hairnet_model.py` - 训练安全帽模型

#### `optimization/` - 优化工具（5 个）
- `compare_yolo_models.py` - 比较 YOLO 模型
- `convert_to_coreml.py` - 转换为 CoreML
- `convert_to_tensorrt.py` - 转换为 TensorRT
- `performance_comparison.py` - 性能比较
- `test_hardware_adaptivity.py` - 测试硬件适应性

#### `ci/` - CI/CD 工具（3 个）
- `check_dev_env.py` - 检查开发环境
- `check_gpu.py` - 检查 GPU
- `check_ultralytics.py` - 检查 Ultralytics

#### `development/` - 开发工具（5 个）
- `debug_hardware_detection.py` - 调试硬件检测
- `demo_handwash_detection.py` - 演示洗手检测
- `run_simple_detection.py` - 运行简单检测
- `start_optimized_api.py` - 启动优化 API
- `visualize_roi.py` - 可视化 ROI

#### `frontend/` - 前端工具（2 个）
- `build_optimizer.py` - 构建优化器
- `performance_analyzer.py` - 性能分析器

---

## 📊 分类统计

| 类别 | 数量 | 说明 |
|------|------|------|
| **根目录脚本** | 35 | 核心部署和开发脚本 |
| **公共函数库** | 6 | `lib/` 目录 |
| **数据库相关** | 12 | `sql/` + `migrations/` |
| **工具脚本** | 7 | `tools/` 目录 |
| **诊断脚本** | 5 | `diagnostics/` 目录 |
| **测试脚本** | 11 | `tests/` 目录 |
| **数据处理** | 2 | `data/` 目录 |
| **性能测试** | 5 | `performance/` 目录 |
| **维护工具** | 9 | `maintenance/` 目录 |
| **评估脚本** | 2 | `evaluation/` 目录 |
| **验证脚本** | 1 | `verification/` 目录 |
| **MLOps** | 2 | `mlops/` 目录 |
| **训练脚本** | 1 | `training/` 目录 |
| **优化工具** | 5 | `optimization/` 目录 |
| **CI/CD** | 3 | `ci/` 目录 |
| **开发工具** | 5 | `development/` 目录 |
| **前端工具** | 2 | `frontend/` 目录 |
| **总计** | **108** | |

---

## 🎯 脚本分类说明

### 核心脚本（必须保留）
- ✅ 根目录的所有脚本（35 个）
- ✅ `lib/` 公共函数库（6 个）
- ✅ `sql/` 和 `migrations/` 数据库脚本（12 个）

### 开发工具脚本（建议保留）
- ✅ `tools/` - 工具脚本（7 个）
- ✅ `diagnostics/` - 诊断脚本（5 个）
- ✅ `tests/` - 测试脚本（11 个）
- ✅ `development/` - 开发工具（5 个）

### 专业工具脚本（按需保留）
- ⚠️ `data/` - 数据处理（2 个）
- ⚠️ `performance/` - 性能测试（5 个）
- ⚠️ `maintenance/` - 维护工具（9 个）
- ⚠️ `evaluation/` - 评估脚本（2 个）
- ⚠️ `verification/` - 验证脚本（1 个）
- ⚠️ `mlops/` - MLOps 工具（2 个）
- ⚠️ `training/` - 训练脚本（1 个）
- ⚠️ `optimization/` - 优化工具（5 个）
- ⚠️ `ci/` - CI/CD 工具（3 个）
- ⚠️ `frontend/` - 前端工具（2 个）

---

## 📝 说明

1. **根目录脚本**：这些是核心脚本，用于开发和生产部署，必须保留。
2. **子目录脚本**：按功能分类组织，便于管理和维护。
3. **清理原则**：只删除临时修复和诊断脚本，保留所有功能脚本。
4. **文档脚本**：清理计划文档保留作为历史记录。

---

**最后更新**: 2025-12-02
