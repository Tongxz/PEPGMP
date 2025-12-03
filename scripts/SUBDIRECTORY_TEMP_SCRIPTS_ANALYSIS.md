# 子目录临时脚本分析

## 📋 分析目标

识别子目录中不再使用的临时脚本、一次性脚本和调试脚本。

## 🔍 分析结果

### ⚠️ 可能的临时脚本（建议删除或归档）

#### 1. `tests/` - 测试脚本（4 个临时测试）

**临时测试脚本**（问题已解决，不再需要）：
- ❌ `test_timezone_fix.py` - 时区修复测试（一次性测试，问题已解决）
- ❌ `test_xgboost_enabled.py` - XGBoost 启用测试（一次性测试，功能已启用）
- ❌ `test_frontend_improvements.py` - 前端改进测试（一次性测试，改进已完成）
- ❌ `test_roi_without_preprocessing.py` - ROI 无预处理测试（一次性测试）

**保留的测试脚本**（常规测试）：
- ✅ `test_database.py` - 数据库测试（常规测试）
- ✅ `test_dataset_validation.py` - 数据集验证测试（常规测试）
- ✅ `test_db_insert.py` - 数据库插入测试（常规测试）
- ✅ `test_deployment_service.py` - 部署服务测试（常规测试）
- ✅ `test_docker_service.py` - Docker 服务测试（常规测试）
- ✅ `verify_export_functionality.py` - 验证导出功能（常规测试）
- ✅ `verify_mlops_workflow.py` - 验证 MLOps 工作流（常规测试）

#### 2. `maintenance/` - 维护脚本（9 个临时清理脚本）

**临时清理脚本**（一次性清理，已完成）：
- ❌ `cleanup_output.py` - 清理输出（一次性清理）
- ❌ `cleanup_root.sh` - 清理根目录（一次性清理）
- ❌ `cleanup_root_directory.py` - 清理根目录（一次性清理）
- ❌ `cleanup_tests.py` - 清理测试（一次性清理）
- ❌ `organize_model_files.py` - 组织模型文件（一次性组织）
- ❌ `organize_tests.py` - 组织测试（一次性组织）
- ❌ `update_model_paths.py` - 更新模型路径（一次性更新）
- ❌ `update_test_paths.py` - 更新测试路径（一次性更新）
- ❌ `verify_model_paths.py` - 验证模型路径（一次性验证）

**说明**：这些脚本看起来是项目重构时使用的临时脚本，用于清理和组织文件。如果重构已完成，这些脚本可以删除。

#### 3. `migrations/` - 数据库迁移（3 个一次性迁移）

**一次性迁移脚本**（迁移已完成，可归档）：
- ⚠️ `migrate_cameras_from_yaml.py` - 从 YAML 迁移相机（一次性迁移，已完成）
- ⚠️ `migrate_regions_from_json.py` - 从 JSON 迁移区域（一次性迁移，已完成）
- ⚠️ `run_migration_002.py` - 运行迁移 002（一次性迁移，已完成）

**保留的迁移脚本**（标准迁移）：
- ✅ `001_create_core_tables.sql` - 创建核心表（标准迁移）
- ✅ `001_create_detection_configs_table.sql` - 创建检测配置表（标准迁移）
- ✅ `002_add_camera_status_column.sql` - 添加相机状态列（标准迁移）
- ✅ `002_migrate_unified_params_to_db.py` - 迁移统一参数到数据库（标准迁移）
- ✅ `003_convert_camera_id_to_varchar.py` - 转换相机 ID 为字符串（标准迁移）
- ✅ `004_make_stream_url_nullable.py` - 使流 URL 可为空（标准迁移）
- ✅ `005_revert_camera_id_to_uuid.py` - 恢复相机 ID 为 UUID（标准迁移）

**建议**：一次性迁移脚本可以移动到 `migrations/archive/` 目录归档，而不是删除。

#### 4. `development/` - 开发工具（1 个临时调试）

**临时调试脚本**：
- ❌ `debug_hardware_detection.py` - 调试硬件检测（临时调试脚本）

**保留的开发工具**：
- ✅ `demo_handwash_detection.py` - 演示洗手检测（演示工具）
- ✅ `run_simple_detection.py` - 运行简单检测（开发工具）
- ✅ `start_optimized_api.py` - 启动优化 API（开发工具）
- ✅ `visualize_roi.py` - 可视化 ROI（开发工具）

#### 5. `tools/` - 工具脚本（4 个临时检查）

**临时检查脚本**（一次性检查，已完成）：
- ❌ `check_camera_table_structure.py` - 检查相机表结构（一次性检查）
- ❌ `check_cameras_in_db.py` - 检查数据库中的相机（一次性检查）
- ❌ `check_db_structure.py` - 检查数据库结构（一次性检查）
- ❌ `check_saved_records.py` - 检查保存的记录（一次性检查）

**保留的工具脚本**：
- ✅ `check_video_stream_status.sh` - 检查视频流状态（常规工具）
- ✅ `create_resume_training_workflow.py` - 创建恢复训练工作流（常规工具）
- ✅ `download_models.sh` - 下载模型（常规工具）

#### 6. `diagnostics/` - 诊断脚本（保留）

**所有诊断脚本保留**（用于问题诊断）：
- ✅ `debug_stats.py` - 调试统计（诊断工具）
- ✅ `diagnose_cuda.py` - CUDA 诊断（诊断工具）
- ✅ `diagnose_hairnet_detection.py` - 安全帽检测诊断（诊断工具）
- ✅ `diagnose_hairnet_roi.py` - 安全帽 ROI 诊断（诊断工具）
- ✅ `diagnose_torch_import.py` - Torch 导入诊断（诊断工具）

**说明**：诊断脚本用于问题排查，应该保留。

#### 7. 其他目录（保留）

以下目录的脚本都是常规工具，应该保留：
- ✅ `data/` - 数据处理脚本（2 个）
- ✅ `performance/` - 性能测试脚本（5 个）
- ✅ `evaluation/` - 评估脚本（2 个）
- ✅ `verification/` - 验证脚本（1 个）
- ✅ `mlops/` - MLOps 工具（2 个）
- ✅ `training/` - 训练脚本（1 个）
- ✅ `optimization/` - 优化工具（5 个）
- ✅ `ci/` - CI/CD 工具（3 个）
- ✅ `frontend/` - 前端工具（2 个）

---

## 📊 统计汇总

| 类别 | 临时脚本数量 | 建议操作 |
|------|------------|---------|
| `tests/` | 4 个 | 删除 |
| `maintenance/` | 9 个 | 删除 |
| `migrations/` | 3 个 | 归档到 `migrations/archive/` |
| `development/` | 1 个 | 删除 |
| `tools/` | 4 个 | 删除 |
| **总计** | **21 个** | |

---

## 🎯 清理建议

### 立即删除（18 个）
- `tests/` 中的 4 个临时测试脚本
- `maintenance/` 中的 9 个临时清理脚本
- `development/` 中的 1 个临时调试脚本
- `tools/` 中的 4 个临时检查脚本

### 归档（3 个）
- `migrations/` 中的 3 个一次性迁移脚本移动到 `migrations/archive/`

### 保留
- 所有常规测试脚本
- 所有诊断脚本
- 所有常规工具脚本
- 所有标准迁移脚本

---

## 📝 执行步骤

1. **删除临时测试脚本**（4 个）
2. **删除临时维护脚本**（9 个）
3. **删除临时调试脚本**（1 个）
4. **删除临时检查脚本**（4 个）
5. **归档一次性迁移脚本**（3 个）
6. **更新文档**

---

**分析日期**: 2025-12-02
