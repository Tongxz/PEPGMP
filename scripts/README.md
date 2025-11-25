# Scripts 目录说明

## 📋 目录结构

```
scripts/
├── README.md                    # 本文件
├── SCRIPTS_CLEANUP_PLAN.md     # 清理计划文档
│
├── 开发环境脚本/
│   ├── setup_dev.sh            # 开发环境设置
│   ├── start_dev.sh             # 启动开发环境
│   ├── backup_dev_data.sh      # 开发环境数据备份
│   ├── restore_dev_data.sh     # 开发环境数据恢复
│   ├── rebuild_dev_environment.sh  # 重建开发环境
│   ├── check_database_init.sh  # 检查数据库初始化
│   └── fix_database_user.sh    # 修复数据库用户
│
├── 生产环境脚本/
│   ├── build_prod_images.sh    # 构建生产镜像
│   ├── generate_production_config.sh  # 生成生产配置
│   ├── generate_production_secrets.py # 生成生产密钥
│   ├── deploy_prod.sh           # 生产部署
│   ├── deploy_from_registry.sh  # 从Registry部署
│   ├── push_to_registry.sh      # 推送到Registry
│   ├── quick_deploy.sh          # 一键部署
│   ├── check_deployment_readiness.sh  # 检查部署就绪
│   ├── backup_db.sh             # 生产数据库备份
│   ├── restore_db.sh            # 生产数据库恢复
│   ├── start_prod.sh            # 启动生产环境
│   └── start_prod_wsl.sh         # WSL环境启动生产
│
├── 数据库脚本/
│   ├── init_db.sql              # 数据库初始化SQL（Docker容器自动执行）
│   ├── init_database.py         # 数据库初始化Python
│   └── validate_config.py       # 配置验证
│
├── 迁移/导出脚本/
│   ├── export_cameras_to_yaml.py  # 导出相机配置
│   └── export_regions_to_json.py  # 导出区域配置
│
├── tests/                        # 测试脚本
├── diagnostics/                  # 诊断脚本
├── tools/                        # 工具脚本
├── sql/                          # SQL脚本（非初始化）
│
└── 子目录/
    ├── ci/                       # CI/CD工具
    ├── development/              # 开发工具
    ├── data/                     # 数据处理
    ├── frontend/                 # 前端工具
    ├── maintenance/              # 维护工具
    ├── optimization/             # 优化工具
    ├── performance/              # 性能测试
    ├── training/                 # 训练脚本
    ├── migrations/               # 数据库迁移
    ├── mlops/                    # MLOps工具
    ├── evaluation/               # 评估脚本
    └── verification/             # 验证脚本
```

---

## 🚀 快速开始

### 开发环境

```bash
# 设置开发环境
bash scripts/setup_dev.sh

# 启动开发环境
bash scripts/start_dev.sh

# 备份开发数据
bash scripts/backup_dev_data.sh

# 恢复开发数据
bash scripts/restore_dev_data.sh <备份目录> <时间戳>
```

### 生产环境

```bash
# 生成生产配置
bash scripts/generate_production_config.sh

# 检查部署就绪
bash scripts/check_deployment_readiness.sh

# 一键部署
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu

# 或分步部署
bash scripts/build_prod_images.sh
bash scripts/push_to_registry.sh
bash scripts/deploy_from_registry.sh <SERVER_IP> ubuntu
```

### 数据库管理

```bash
# 检查数据库初始化
bash scripts/check_database_init.sh [容器名] [用户名] [数据库名]

# 修复数据库用户（如需要）
bash scripts/fix_database_user.sh

# 备份数据库
bash scripts/backup_db.sh [备份目录] [保留天数]

# 恢复数据库
bash scripts/restore_db.sh <备份文件路径>
```

---

## 📝 脚本分类说明

### 开发环境脚本

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| `setup_dev.sh` | 开发环境设置 | 首次设置开发环境 |
| `start_dev.sh` | 启动开发环境 | 日常开发启动 |
| `backup_dev_data.sh` | 数据备份 | 重建环境前备份 |
| `restore_dev_data.sh` | 数据恢复 | 重建环境后恢复 |
| `rebuild_dev_environment.sh` | 重建环境 | 完全重建Docker环境 |
| `check_database_init.sh` | 检查数据库初始化 | 验证数据库状态 |
| `fix_database_user.sh` | 修复数据库用户 | 用户创建失败时 |

### 生产环境脚本

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| `build_prod_images.sh` | 构建生产镜像 | 构建Docker镜像 |
| `generate_production_config.sh` | 生成生产配置 | 首次部署前 |
| `generate_production_secrets.py` | 生成生产密钥 | 生成强密码和密钥 |
| `deploy_prod.sh` | 生产部署 | 传统部署方式 |
| `deploy_from_registry.sh` | 从Registry部署 | 从私有Registry部署 |
| `push_to_registry.sh` | 推送到Registry | 推送镜像到Registry |
| `quick_deploy.sh` | 一键部署 | **推荐**，完整部署流程 |
| `check_deployment_readiness.sh` | 检查部署就绪 | 部署前检查 |
| `backup_db.sh` | 数据库备份 | 定期备份 |
| `restore_db.sh` | 数据库恢复 | 从备份恢复 |
| `start_prod.sh` | 启动生产环境 | 启动生产服务 |
| `start_prod_wsl.sh` | WSL启动生产 | WSL环境启动 |

### 数据库脚本

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| `init_db.sql` | 数据库初始化SQL | Docker容器首次启动时自动执行 |
| `init_database.py` | 数据库初始化Python | 手动初始化数据库 |
| `validate_config.py` | 配置验证 | 验证配置文件正确性 |

### 迁移/导出脚本

| 脚本 | 用途 | 使用场景 |
|------|------|---------|
| `export_cameras_to_yaml.py` | 导出相机配置 | 备份相机配置 |
| `export_regions_to_json.py` | 导出区域配置 | 备份区域配置 |

---

## 📂 归类目录说明

### `tests/` - 测试脚本
包含各种测试脚本，用于验证功能：
- `test_database.py` - 数据库测试
- `test_dataset_validation.py` - 数据集验证测试
- `test_frontend_improvements.py` - 前端改进测试
- `verify_mlops_workflow.py` - MLOps工作流验证
- 等等...

### `diagnostics/` - 诊断脚本
包含诊断和调试脚本：
- `diagnose_cuda.py` - CUDA诊断
- `diagnose_hairnet_detection.py` - 发网检测诊断
- `debug_stats.py` - 统计调试
- 等等...

### `tools/` - 工具脚本
包含各种工具脚本：
- `check_camera_table_structure.py` - 检查相机表结构
- `check_db_structure.py` - 检查数据库结构
- `download_models.sh` - 下载模型
- 等等...

### `sql/` - SQL脚本
包含SQL脚本（非初始化）：
- `check_alert_data.sql` - 检查告警数据
- `create_test_alert_data.sql` - 创建测试告警数据

---

## 🔗 相关文档

- [部署流程指南](../docs/DEPLOYMENT_PROCESS_GUIDE.md)
- [部署前准备工作清单](../docs/DEPLOYMENT_PREPARATION_CHECKLIST.md)
- [数据库用户初始化问题分析](../docs/DATABASE_USER_INITIALIZATION_ANALYSIS.md)
- [MLOps连接问题修复](../docs/MLOPS_CONNECTION_FIX.md)

---

**最后更新**: 2025-11-25

