# Scripts 目录说明

## 📋 目录结构

```
scripts/
├── README.md                    # 本文件
├── SCRIPTS_CLEANUP_PLAN.md     # 清理计划文档
│
├── lib/                         # 公共函数库（新增）
│   ├── common.sh               # 通用函数
│   ├── deploy_config.sh        # 统一部署配置 ⭐
│   ├── docker_utils.sh         # Docker 工具函数
│   ├── env_detection.sh        # 环境检测
│   ├── config_validation.sh    # 配置验证
│   └── service_manager.sh      # 服务管理
│
├── 统一启动脚本/
│   ├── start.sh                # 统一启动脚本（核心）
│   ├── start_dev.sh            # 开发环境启动（快捷方式）
│   ├── start_prod.sh           # 生产环境启动（快捷方式）
│   └── start_prod_wsl.sh       # WSL 容器化模式启动
│
├── 构建与部署脚本/
│   ├── build_prod_only.sh      # 仅构建镜像（本地）
│   ├── build_prod_images.sh    # 构建+推送+导出镜像
│   ├── deploy_prod.sh          # 生产部署
│   ├── quick_deploy.sh         # 一键部署
│   ├── prepare_minimal_deploy.sh # 准备最小部署包（1Panel）
│   ├── push_to_registry.sh     # 推送到 Registry
│   └── deploy_from_registry.sh # 从 Registry 部署
│
├── 配置脚本/
│   ├── generate_production_config.sh  # 生成生产配置
│   ├── generate_production_secrets.py # 生成生产密钥
│   ├── check_deployment_readiness.sh  # 检查部署就绪
│   ├── update_image_version.sh        # 更新镜像版本
│   └── import_images_from_windows.sh  # 从 Windows 导入镜像
│
├── 数据库脚本/
│   ├── init_db.sql             # 数据库初始化 SQL（Docker 自动执行）
│   ├── init_database.py        # 数据库初始化 Python
│   ├── backup_db.sh            # 数据库备份
│   ├── restore_db.sh           # 数据库恢复
│   ├── check_database_health.sh # 检查数据库健康
│   ├── check_database_init.sh  # 检查数据库初始化
│   └── fix_database_user.sh    # 修复数据库用户
│
├── 开发环境脚本/
│   ├── setup_dev.sh            # 开发环境设置
│   ├── backup_dev_data.sh      # 开发数据备份
│   ├── restore_dev_data.sh     # 开发数据恢复
│   └── rebuild_dev_environment.sh # 重建开发环境
│
└── 子目录/
    ├── tests/                  # 测试脚本
    ├── diagnostics/            # 诊断脚本
    ├── tools/                  # 工具脚本
    ├── sql/                    # SQL 脚本
    ├── migrations/             # 数据库迁移
    ├── ci/                     # CI/CD 工具
    ├── development/            # 开发工具
    ├── data/                   # 数据处理
    ├── frontend/               # 前端工具
    ├── maintenance/            # 维护工具
    ├── optimization/           # 优化工具
    ├── performance/            # 性能测试
    ├── training/               # 训练脚本
    ├── mlops/                  # MLOps 工具
    ├── evaluation/             # 评估脚本
    └── verification/           # 验证脚本
```

---

## ⭐ 统一配置（重要）

所有部署脚本共享统一配置文件 `scripts/lib/deploy_config.sh`：

```bash
# 镜像名称（统一使用）
BACKEND_IMAGE_NAME=pepgmp-backend
FRONTEND_IMAGE_NAME=pepgmp-frontend

# Dockerfile 路径
BACKEND_DOCKERFILE=Dockerfile.prod
FRONTEND_DOCKERFILE=Dockerfile.frontend

# Registry 地址
REGISTRY_URL=192.168.30.83:5433
```

**好处**：
- 所有脚本使用相同的镜像名称
- 修改配置只需改一处
- 避免镜像名称不一致导致的部署问题

---

## 🚀 快速开始

### 开发环境

```bash
# 设置开发环境
bash scripts/setup_dev.sh

# 启动开发环境
bash scripts/start_dev.sh

# 或使用统一启动脚本
bash scripts/start.sh --env dev
```

### 生产环境部署

#### 方式 1：本地构建 + Docker Compose（推荐新手）

```bash
# 1. 生成生产配置
bash scripts/generate_production_config.sh

# 2. 构建镜像
bash scripts/build_prod_only.sh

# 3. 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

#### 方式 2：1Panel 部署（WSL2/Ubuntu）

```bash
# 1. 在开发机构建镜像
bash scripts/build_prod_only.sh 20251202

# 2. 导出镜像
docker save pepgmp-backend:20251202 > docker-images/pepgmp-backend-20251202.tar
docker save pepgmp-frontend:20251202 > docker-images/pepgmp-frontend-20251202.tar

# 3. 同步配置到部署目录
bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt

# 4. 在生产服务器导入镜像
docker load -i pepgmp-backend-20251202.tar
docker load -i pepgmp-frontend-20251202.tar

# 5. 通过 1Panel 创建 Compose 项目
```

#### 方式 3：Registry 部署（有私有 Registry）

```bash
# 1. 构建并推送到 Registry
bash scripts/build_prod_images.sh

# 2. 在生产服务器拉取并部署
bash scripts/deploy_from_registry.sh <SERVER_IP> ubuntu
```

### 数据库管理

```bash
# 检查数据库健康
bash scripts/check_database_health.sh

# 备份数据库
bash scripts/backup_db.sh

# 恢复数据库
bash scripts/restore_db.sh <备份文件路径>
```

---

## 📝 核心脚本说明

### 统一启动脚本

| 脚本 | 用途 | 示例 |
|------|------|------|
| `start.sh` | 统一启动脚本（支持多种模式） | `bash scripts/start.sh --env prod --mode containerized` |
| `start_dev.sh` | 开发环境快捷方式 | `bash scripts/start_dev.sh` |
| `start_prod.sh` | 生产环境快捷方式（宿主机模式） | `bash scripts/start_prod.sh` |
| `start_prod_wsl.sh` | WSL 容器化模式 | `bash scripts/start_prod_wsl.sh` |

### 构建脚本

| 脚本 | 用途 | 输出 |
|------|------|------|
| `build_prod_only.sh` | 仅构建本地镜像 | `pepgmp-backend:版本号`, `pepgmp-frontend:版本号` |
| `build_prod_images.sh` | 构建+推送+导出 | 本地镜像 + Registry 镜像 + tar 包 |

### 部署脚本

| 脚本 | 适用场景 | 说明 |
|------|----------|------|
| `quick_deploy.sh` | 有 SSH 访问的远程服务器 | 一键完成构建、推送、部署 |
| `prepare_minimal_deploy.sh` | 1Panel/手动部署 | 准备最小部署包（配置+脚本） |
| `deploy_from_registry.sh` | 有私有 Registry | 从 Registry 拉取并部署 |

---

## 🔧 跨平台支持

所有脚本支持以下环境：
- **macOS** (开发环境)
- **WSL2 Ubuntu** (测试/生产环境)
- **原生 Ubuntu/Linux** (生产环境)

关键兼容性处理：
- `stat` 命令格式差异
- `sed -i` 参数差异
- 路径分隔符处理
- 哈希命令差异（`md5sum` vs `md5`）

---

## 📂 子目录说明

| 目录 | 用途 | 主要文件 |
|------|------|----------|
| `lib/` | 公共函数库 | `deploy_config.sh`, `common.sh` |
| `tests/` | 测试脚本 | 各种测试脚本 |
| `diagnostics/` | 诊断脚本 | CUDA 诊断、检测诊断 |
| `tools/` | 工具脚本 | 数据库结构检查等 |
| `sql/` | SQL 脚本 | 非初始化 SQL |
| `migrations/` | 数据库迁移 | 迁移脚本 |
| `development/` | 开发工具 | 调试、演示脚本 |
| `mlops/` | MLOps 工具 | 训练工作流 |

---

## 🔗 相关文档

- [部署流程指南](../docs/DEPLOYMENT_PROCESS_GUIDE.md)
- [脚本分析与修复报告](../docs/SCRIPTS_ANALYSIS_AND_FIX.md)
- [数据库连接架构分析](../docs/DATABASE_CONNECTION_ARCHITECTURE_ANALYSIS.md)
- [开发环境到生产环境部署步骤](../docs/DEV_TO_PROD_DEPLOYMENT_STEPS.md)

---

**最后更新**: 2025-12-02
