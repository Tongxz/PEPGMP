# Scripts 目录说明

## 📋 目录结构（已收敛）

```
scripts/
├── README.md                    # 本文件
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
│   └── start_prod.sh           # 生产环境启动（快捷方式）
│
├── 构建与部署脚本/
│   ├── build_prod_only.sh      # 仅构建镜像（本地）
│   ├── build_prod_images.sh    # 构建+推送+导出镜像
│   ├── prepare_minimal_deploy.sh # 准备最小部署包（1Panel）
│   ├── deploy_mixed_registry.sh # 混合部署（网络隔离：导出/传输 tar）
│   └── deploy_via_registry.sh   # Registry 部署（同网：生产机可访问 Registry）
│
├── 配置脚本/
│   ├── generate_production_config.sh  # 生成生产配置
│   ├── generate_production_secrets.py # 生成生产密钥
│   ├── check_deployment_readiness.sh  # 检查部署就绪
│   ├── update_image_version.sh        # 更新镜像版本
│   └── （已清理 Windows/PowerShell 相关脚本）
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
    ├── sql/                    # SQL 脚本
    ├── migrations/             # 数据库迁移
    └── maintenance/            # 维护工具（预留）
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
REGISTRY_URL=11.25.125.115:5433
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

### 生产环境部署（仅保留两条主线）

#### 方式 1：混合部署（网络隔离：构建 → 导出 tar → 传输 → 远程部署，现状推荐）

```bash
bash scripts/deploy_mixed_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP
```

#### 方式 2：Registry 部署（同一网络：构建 → 推送 Registry → 生产机拉取 → 部署）

```bash
bash scripts/deploy_via_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP
```

#### 本机仅构建（可选）

```bash
bash scripts/build_prod_only.sh 20251218
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

### 构建脚本

| 脚本 | 用途 | 输出 |
|------|------|------|
| `build_prod_only.sh` | 仅构建本地镜像 | `pepgmp-backend:版本号`, `pepgmp-frontend:版本号` |
| `build_prod_images.sh` | 构建+推送+导出 | 本地镜像 + Registry 镜像 + tar 包 |

### 部署脚本

| 脚本 | 适用场景 | 说明 |
|------|----------|------|
| `deploy_mixed_registry.sh` | 网络隔离（现状） | 构建 →（可选推送）→ 导出 tar → 传输 → 远程部署 |
| `deploy_via_registry.sh` | 同一网络 | 构建 → 推送 Registry → 生产机拉取 → 部署 |
| `prepare_minimal_deploy.sh` | 1Panel/手动辅助 | 准备最小部署包（配置/compose 等） |

---

## 🔧 跨平台支持

所有脚本支持以下环境：
- **macOS** (开发环境)
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
| `sql/` | SQL 脚本 | 非初始化 SQL |
| `migrations/` | 数据库迁移 | 迁移脚本 |

---

## 🔗 相关文档

- [数据库连接架构分析](../docs/DATABASE_CONNECTION_ARCHITECTURE_ANALYSIS.md)
- [生产部署指南](../docs/PRODUCTION_DEPLOYMENT_GUIDE.md)

---

---

## 📊 脚本统计

本目录已按“生产仅保留两条主线”做过收敛；如需新增脚本，请先更新本 README，避免出现无效入口或误用旧流程。
