# Scripts 目录分析与修复报告

## 📊 脚本分类概览

### 核心部署脚本（必须保留）

| 脚本 | 用途 | 状态 |
|------|------|------|
| `start.sh` | 统一启动脚本 | ✅ 正常 |
| `start_dev.sh` | 开发环境启动（快捷方式） | ✅ 正常 |
| `start_prod.sh` | 生产环境启动（快捷方式） | ✅ 正常 |
| `start_prod_wsl.sh` | WSL 容器化模式启动 | ⚠️ 编码问题 |
| `build_prod_only.sh` | 仅构建生产镜像（本地） | ✅ 正常 |
| `build_prod_images.sh` | 构建+推送+导出镜像 | ⚠️ 镜像名/Dockerfile 不一致 |
| `deploy_prod.sh` | 生产环境部署 | ⚠️ Dockerfile 引用错误 |
| `quick_deploy.sh` | 一键部署 | ✅ 正常 |
| `generate_production_config.sh` | 生成生产配置 | ✅ 正常 |
| `prepare_minimal_deploy.sh` | 准备最小部署包 | ⚠️ 目录比较逻辑可改进 |

### 配置同步脚本（1Panel 部署相关）

| 脚本 | 用途 | 状态 |
|------|------|------|
| `import_images_from_windows.sh` | 从 Windows 导入镜像 | ✅ 正常 |
| `export_images_to_wsl.ps1` | 导出镜像到 WSL（PowerShell） | ✅ 正常 |
| `update_image_version.sh` | 更新镜像版本号 | ✅ 正常 |
| `update_image_version.ps1` | 更新镜像版本号（PowerShell） | ✅ 正常 |

### Registry 和远程部署脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `push_to_registry.sh` | 推送镜像到私有 Registry | ✅ 正常 |
| `deploy_from_registry.sh` | 从 Registry 部署 | ✅ 正常 |
| `check_deployment_readiness.sh` | 检查部署就绪状态 | ✅ 正常 |
| `check_images.sh` | 检查镜像状态 | ✅ 正常 |

### 数据库脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `init_db.sql` | 数据库初始化 SQL | ✅ 正常 |
| `init_database.py` | Python 数据库初始化 | ✅ 正常 |
| `backup_db.sh` | 备份数据库 | ✅ 正常 |
| `restore_db.sh` | 恢复数据库 | ✅ 正常 |
| `check_database_health.sh` | 检查数据库健康 | ✅ 正常 |
| `check_database_init.sh` | 检查数据库初始化 | ✅ 正常 |
| `fix_database_user.sh` | 修复数据库用户 | ✅ 正常 |

### Nginx 修复脚本（可考虑合并/清理）

| 脚本 | 用途 | 建议 |
|------|------|------|
| `fix_nginx_mount.sh` | 修复 nginx 挂载 | 🔄 可合并 |
| `fix_nginx_mount_issue.sh` | 修复 nginx 挂载问题 | 🔄 可合并 |
| `fix_nginx_no_frontend.sh` | 无前端时的 nginx 配置 | 🔄 可合并 |
| `fix_nginx_permissions.sh` | 修复 nginx 权限 | 🔄 可合并 |
| `fix_nginx_structure.sh` | 修复 nginx 目录结构 | 🔄 可合并 |
| `update_nginx_for_frontend.sh` | 更新 nginx 前端配置 | 🔄 可合并 |

### 开发/测试脚本（子目录）

- `scripts/lib/` - 公共函数库
- `scripts/tests/` - 测试脚本
- `scripts/diagnostics/` - 诊断脚本
- `scripts/tools/` - 工具脚本
- `scripts/migrations/` - 数据库迁移
- `scripts/development/` - 开发脚本
- `scripts/evaluation/` - 评估脚本
- `scripts/optimization/` - 优化脚本
- `scripts/training/` - 训练脚本
- `scripts/mlops/` - MLOps 脚本
- `scripts/maintenance/` - 维护脚本
- `scripts/performance/` - 性能脚本
- `scripts/verification/` - 验证脚本
- `scripts/ci/` - CI 脚本
- `scripts/data/` - 数据脚本
- `scripts/frontend/` - 前端脚本

---

## 🔴 发现的问题

### 问题 1: 镜像名称不一致

**影响**: 高 - 导致镜像无法被 Docker Compose 找到

| 文件 | 后端镜像名 | 前端镜像名 |
|------|----------|-----------|
| `docker-compose.prod.yml` | `pepgmp-backend` | `pepgmp-frontend` |
| `docker-compose.prod.1panel.yml` | `pepgmp-backend` | `pepgmp-frontend` |
| `build_prod_images.sh` | ❌ `pyt-api` | ❌ `pyt-frontend` |
| `build_prod_only.sh` | ✅ `pepgmp-backend` | ✅ `pepgmp-frontend` |

### 问题 2: Dockerfile 引用不一致

**影响**: 高 - 可能构建错误的镜像

| 脚本 | 使用的 Dockerfile |
|------|------------------|
| `build_prod_images.sh` | ❌ `Dockerfile` |
| `deploy_prod.sh` | ❌ `Dockerfile.prod.new` |
| `build_prod_only.sh` | ✅ `Dockerfile.prod` |
| `docker-compose.prod.yml` | ✅ `Dockerfile.prod` |

### 问题 3: start_prod_wsl.sh 编码问题

文件内容显示为乱码，需要重新生成。

### 问题 4: Redis 健康检查（已修复）

`docker-compose.prod.1panel.yml` 中的 Redis 健康检查不支持密码认证。

### 问题 5: 数据库初始化脚本未挂载

Docker Compose 配置中没有挂载 `init_db.sql`。

---

## ✅ 修复方案

详见本次提交的代码修改。

### 统一配置变量

创建 `scripts/lib/deploy_config.sh` 统一管理：
- 镜像名称
- Registry 地址
- Dockerfile 路径
- 版本标签

### 跨平台兼容性

所有脚本支持：
- macOS (开发环境)
- WSL2 Ubuntu (测试环境)
- 原生 Ubuntu (生产环境)

关键兼容性处理：
- `stat` 命令格式差异
- `sed -i` 参数差异
- 路径分隔符处理

---

## 📁 推荐的目录结构

```
scripts/
├── lib/                    # 公共函数库
│   ├── common.sh          # 通用函数
│   ├── deploy_config.sh   # 部署配置（新增）
│   ├── docker_utils.sh    # Docker 工具函数
│   ├── env_detection.sh   # 环境检测
│   ├── config_validation.sh # 配置验证
│   └── service_manager.sh # 服务管理
├── start.sh               # 统一启动脚本
├── start_dev.sh           # 开发环境快捷方式
├── start_prod.sh          # 生产环境快捷方式
├── start_prod_wsl.sh      # WSL 容器化模式
├── build_prod_only.sh     # 本地构建镜像
├── build_prod_images.sh   # 构建+推送镜像
├── deploy_prod.sh         # 生产部署
├── quick_deploy.sh        # 一键部署
├── prepare_minimal_deploy.sh # 准备部署包
├── generate_production_config.sh # 生成配置
├── init_db.sql            # 数据库初始化
└── README.md              # 脚本说明
```

---

## 🧹 建议清理的脚本

以下脚本功能重复或已过时，建议合并或删除：

1. **Nginx 修复脚本** - 合并为 `fix_nginx.sh`
2. **行尾修复脚本** - 合并为 `fix_line_endings.sh`
3. **重复的编码修复脚本** - 可删除

---

*文档生成时间: 2025-12-02*
