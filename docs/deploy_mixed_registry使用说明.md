# deploy_mixed_registry.sh 使用说明

## 📋 脚本概述

**脚本路径**: `scripts/deploy_mixed_registry.sh`

**功能**: 混合部署脚本（网络隔离适配版）
- 构建 Docker 镜像
- 导出为 tar 文件
- 传输到生产服务器
- 远程部署

**适用场景**: 开发机无法同时连接 Registry 和生产网络的情况

---

## 🔧 参数说明

### 命令格式

```bash
bash scripts/deploy_mixed_registry.sh [生产服务器IP] [用户名] [部署目录] [版本标签]
```

### 参数详解

| 位置 | 参数名 | 必填 | 默认值 | 说明 |
|------|--------|------|--------|------|
| `$1` | `PRODUCTION_IP` | ✅ 是 | - | 生产服务器 IP 地址 |
| `$2` | `PRODUCTION_USER` | ❌ 否 | `ubuntu` | SSH 登录用户名 |
| `$3` | `DEPLOY_DIR` | ❌ 否 | `/home/ubuntu/projects/PEPGMP` | 生产服务器上的部署目录 |
| `$4` | `TAG` | ❌ 否 | 当前时间（`YYYYMMDD-HHMM`） | Docker 镜像版本标签 |

### 版本标签说明

版本标签优先级：
1. **命令行参数**（第4个参数）- 最高优先级
2. **环境变量** `VERSION_TAG`
3. **默认值** - 当前时间戳（格式：`YYYYMMDD-HHMM`）

支持的版本标签格式：
- 语义化版本: `v1.0.0`, `1.0.0`, `v2.1.3`
- 日期格式: `20251224`
- 日期时间格式: `20251224-1430`
- 自定义格式: `release-1.0`, `prod-v1`

---

## 📖 使用示例

### 示例 1: 基本使用（只提供 IP）

```bash
bash scripts/deploy_mixed_registry.sh 192.168.1.100
```

**效果**:
- 生产服务器 IP: `192.168.1.100`
- SSH 用户名: `ubuntu`（默认）
- 部署目录: `/home/ubuntu/projects/PEPGMP`（默认）
- 版本标签: 当前时间（如 `20251224-1430`）

---

### 示例 2: 指定用户名

```bash
bash scripts/deploy_mixed_registry.sh 192.168.1.100 admin
```

**效果**:
- 生产服务器 IP: `192.168.1.100`
- SSH 用户名: `admin`
- 部署目录: `/home/ubuntu/projects/PEPGMP`（默认）
- 版本标签: 当前时间（如 `20251224-1430`）

---

### 示例 3: 指定用户名和部署目录

```bash
bash scripts/deploy_mixed_registry.sh 192.168.1.100 admin /opt/pepgmp
```

**效果**:
- 生产服务器 IP: `192.168.1.100`
- SSH 用户名: `admin`
- 部署目录: `/opt/pepgmp`
- 版本标签: 当前时间（如 `20251224-1430`）

---

### 示例 4: 完整参数（推荐）

```bash
bash scripts/deploy_mixed_registry.sh 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP v1.0.0
```

**效果**:
- 生产服务器 IP: `192.168.1.100`
- SSH 用户名: `ubuntu`
- 部署目录: `/home/ubuntu/projects/PEPGMP`
- 版本标签: `v1.0.0`

---

### 示例 5: 使用环境变量指定版本号

```bash
# 方式1: 先设置环境变量
export VERSION_TAG=v1.0.0
bash scripts/deploy_mixed_registry.sh 192.168.1.100

# 方式2: 一行命令
VERSION_TAG=v1.0.0 bash scripts/deploy_mixed_registry.sh 192.168.1.100
```

**效果**:
- 生产服务器 IP: `192.168.1.100`
- SSH 用户名: `ubuntu`（默认）
- 部署目录: `/home/ubuntu/projects/PEPGMP`（默认）
- 版本标签: `v1.0.0`（从环境变量读取）

---

## 🚀 脚本执行流程

### 步骤概览

1. **[1/7] 构建镜像**
   - 检查本地基础镜像
   - 构建后端镜像（`pepgmp-backend`）
   - 构建前端镜像（`pepgmp-frontend`）

2. **[2/7] 推送到 Registry**（可选）
   - 如果 Registry 可访问，推送镜像备份

3. **[3/7] 导出镜像**
   - 导出为 tar.gz 文件
   - 保存到 `/tmp/pepgmp-backend-{TAG}.tar.gz`
   - 保存到 `/tmp/pepgmp-frontend-{TAG}.tar.gz`

4. **[4/7] 网络切换提示**
   - 如果需要，提示切换到生产网络

5. **[5/7] 传输文件**
   - 使用 rsync（支持断点续传）传输镜像文件
   - 传输配置文件（docker-compose.prod.yml, nginx.conf）

6. **[6/7] 远程部署**
   - 导入镜像
   - 更新 `.env.production` 中的 `IMAGE_TAG`
   - 重启服务

7. **[7/7] 健康检查**
   - 检查 API 服务是否正常启动

---

## ⚙️ 前置条件

### 1. 本地环境

- ✅ Docker 已安装并运行
- ✅ 本地有基础镜像 `nvidia/cuda:12.8.0-runtime-ubuntu22.04`
- ✅ 可以访问 PyTorch 和 PyPI 下载源（构建时需要）
- ✅ 有足够的磁盘空间（镜像文件可能较大）

### 2. 生产服务器

- ✅ 已配置 SSH 免密登录（推荐）或可以输入密码
- ✅ 安装了 Docker 和 Docker Compose
- ✅ 存在 `.env.production` 配置文件
- ✅ 有足够的磁盘空间

### 3. 网络环境

- ✅ 构建阶段：需要能访问 PyTorch 和 PyPI 下载源
- ✅ 传输阶段：需要能连接到生产服务器（SSH）
- ✅ Registry：可选（如果可访问，会推送镜像备份）

---

## 🔍 常见使用场景

### 场景 1: 首次部署

```bash
# 1. 确保生产服务器已配置好（数据库、.env.production 等）
# 2. 执行部署
bash scripts/deploy_mixed_registry.sh 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP v1.0.0
```

### 场景 2: 日常更新（使用语义化版本）

```bash
# 小版本更新
bash scripts/deploy_mixed_registry.sh 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP v1.0.1

# 大版本更新
bash scripts/deploy_mixed_registry.sh 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP v2.0.0
```

### 场景 3: 快速迭代（使用时间戳）

```bash
# 使用默认时间戳，方便快速迭代
bash scripts/deploy_mixed_registry.sh 192.168.1.100
```

### 场景 4: 多服务器部署

```bash
# 部署到服务器1
bash scripts/deploy_mixed_registry.sh 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP v1.0.0

# 部署到服务器2（使用相同的版本标签）
bash scripts/deploy_mixed_registry.sh 192.168.1.101 ubuntu /home/ubuntu/projects/PEPGMP v1.0.0
```

---

## 📝 注意事项

### 1. SSH 连接

- **推荐**: 配置 SSH Key 免密登录
- 如果没有配置，脚本执行时会提示输入密码
- 脚本使用 SSH ControlMaster 复用连接，提升性能

### 2. 网络切换

- 脚本会在传输文件前提示切换网络（如果需要）
- 确保在正确的网络环境下执行相应步骤

### 3. 版本标签建议

- **生产环境**: 使用语义化版本号（`v1.0.0`）
- **测试环境**: 可以使用时间戳或自定义标签
- **重要更新**: 使用有意义的版本号，便于追踪和回滚

### 4. 磁盘空间

- 镜像 tar 文件可能较大（几 GB）
- 确保本地和生产服务器都有足够空间
- 脚本会自动清理临时文件

### 5. 构建缓存

- 首次构建需要下载依赖（可能较慢）
- 后续构建会使用 Docker 缓存（更快）
- 如果修改了依赖版本，会重新下载

---

## 🐛 故障排查

### 问题 1: SSH 连接失败

```bash
# 检查 SSH 连接
ssh ubuntu@192.168.1.100

# 检查网络连通性
ping 192.168.1.100
```

### 问题 2: 构建失败

```bash
# 检查 Docker 是否运行
docker info

# 检查基础镜像是否存在
docker images | grep nvidia/cuda

# 检查网络连接（构建时需要下载依赖）
curl -I https://download.pytorch.org/whl/cu128
```

### 问题 3: 传输失败

```bash
# 检查磁盘空间
df -h

# 检查文件是否存在
ls -lh /tmp/pepgmp-backend-*.tar.gz
```

### 问题 4: 部署后服务未启动

```bash
# SSH 到生产服务器检查
ssh ubuntu@192.168.1.100

# 查看容器状态
cd /home/ubuntu/projects/PEPGMP
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 查看日志
docker logs pepgmp-api-prod
```

---

## 📚 相关脚本

- `scripts/deploy_via_registry.sh` - 通过 Registry 部署（同一网络）
- `scripts/build_prod_only.sh` - 仅构建镜像
- `scripts/update_image_version.sh` - 更新镜像版本

---

## 🔗 相关文档

- [Docker构建缓存失效分析报告.md](./Docker构建缓存失效分析报告.md)
- [系统架构文档](./SYSTEM_ARCHITECTURE.md)
