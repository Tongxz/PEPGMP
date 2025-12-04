# WSL2 生产环境部署详细步骤

## 📋 概述

本指南提供从 macOS 开发环境到 WSL2 Ubuntu 生产环境的完整部署流程。

**部署架构**: Scheme B（单 Nginx 架构）

---

## 🎯 部署前准备

### 检查清单

- [ ] WSL2 Ubuntu 已安装并运行
- [ ] Docker 已在 WSL2 中安装并运行
- [ ] 1Panel 已安装（可选，用于可视化管理）
- [ ] 开发机（macOS）已构建好生产镜像
- [ ] 镜像已导出为 tar 文件

---

## 📦 第一阶段：开发机准备（macOS）

### 步骤 1.1：构建生产镜像

```bash
cd /Users/zhou/Code/Pyt

# 使用日期作为版本号构建镜像（推荐）
bash scripts/build_prod_only.sh 20251202

# 或者使用自定义版本号
bash scripts/build_prod_only.sh v1.0.0
```

**构建输出**：
- `pepgmp-backend:20251202`
- `pepgmp-backend:latest`
- `pepgmp-frontend:20251202`
- `pepgmp-frontend:latest`

### 步骤 1.2：导出镜像

```bash
# 创建导出目录（如果不存在）
mkdir -p docker-images

# 导出后端镜像
docker save pepgmp-backend:20251202 -o docker-images/pepgmp-backend-20251202.tar

# 导出前端镜像
docker save pepgmp-frontend:20251202 -o docker-images/pepgmp-frontend-20251202.tar

# 验证导出文件
ls -lh docker-images/
```

**预期输出**：
```
pepgmp-backend-20251202.tar    (约 2-3 GB)
pepgmp-frontend-20251202.tar   (约 100-200 MB)
```

---

## 🚀 第二阶段：WSL2 环境准备

### 步骤 2.1：进入 WSL2 Ubuntu

在 Windows 中打开 WSL2：

```bash
# 方式1: 从 Windows 终端
wsl

# 方式2: 从 PowerShell
wsl -d Ubuntu-22.04
```

### 步骤 2.2：验证 Docker 环境

```bash
# 检查 Docker 是否运行
docker --version
docker ps

# 检查 Docker Compose
docker compose version
```

**如果 Docker 未安装**，参考 [Docker 安装指南](https://docs.docker.com/engine/install/ubuntu/)

### 步骤 2.3：导入镜像

```bash
# 从 Windows 文件系统导入镜像
# 注意：路径需要根据实际情况调整

# 导入后端镜像
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-backend-20251202.tar

# 导入前端镜像
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-frontend-20251202.tar

# 验证镜像已导入
docker images | grep pepgmp
```

**预期输出**：
```
pepgmp-backend    20251202    abc123def456   2 hours ago    2.5GB
pepgmp-backend    latest      abc123def456   2 hours ago    2.5GB
pepgmp-frontend   20251202    def456ghi789   1 hour ago     150MB
pepgmp-frontend   latest      def456ghi789   1 hour ago     150MB
```

---

## 📁 第三阶段：准备部署包

### 步骤 3.1：运行准备脚本

```bash
# 从 Windows 项目目录运行准备脚本
bash /mnt/c/Users/YourName/Code/PEPGMP/scripts/prepare_minimal_deploy.sh ~/projects/Pyt
```

**脚本会自动**：
1. 创建 `~/projects/PEPGMP 目录
2. 复制 `docker-compose.prod.1panel.yml` → `docker-compose.prod.yml`
3. 复制 `config/` 目录
4. 复制 `models/` 目录（如果存在）
5. 复制 `nginx/nginx.conf`
6. 复制 `scripts/init_db.sql`
7. 复制 `scripts/docker-entrypoint.sh`
8. 复制 `scripts/generate_production_config.sh`

### 步骤 3.2：验证部署包

```bash
cd ~/projects/Pyt

# 检查目录结构
ls -la

# 应该看到：
# - docker-compose.prod.yml
# - config/
# - models/ (可选)
# - nginx/
# - scripts/
```

---

## ⚙️ 第四阶段：生成配置文件

### 步骤 4.1：运行配置生成脚本

```bash
cd ~/projects/Pyt

# 运行配置生成脚本
bash scripts/generate_production_config.sh
```

**交互式输入**（直接回车使用默认值）：
```
API Port [8000]:
Admin Username [admin]:
CORS Origins [*]:
Image Tag [latest]: 20251202  ← 重要：输入你的镜像版本号
```

**脚本会自动**：
- ✅ 生成强随机密码（数据库、Redis、密钥等）
- ✅ 自动探测当前用户的 UID/GID
- ✅ 创建 `.env.production` 配置文件
- ✅ 创建 `.env.production.credentials` 凭证文件

### 步骤 4.2：保存凭证信息

```bash
# 查看凭证信息
cat .env.production.credentials

# 重要：请将凭证信息保存到安全的地方（密码管理器）
# 包含：
# - Admin 用户名和密码
# - 数据库密码
# - Redis 密码
# - SECRET_KEY
# - JWT_SECRET_KEY
```

**保存凭证后，可以删除凭证文件**（可选）：
```bash
rm .env.production.credentials
```

### 步骤 4.3：验证配置文件

```bash
# 检查配置文件是否存在
ls -la .env.production

# 验证镜像标签
grep IMAGE_TAG .env.production
# 应该显示: IMAGE_TAG=20251202

# 验证 Docker Compose 配置语法
docker compose -f docker-compose.prod.yml config > /dev/null && echo "配置语法正确"
```

---

## 🚀 第五阶段：部署服务

### 方式 A：使用 1Panel 部署（推荐）

#### 步骤 5.1：登录 1Panel

1. 打开浏览器访问 1Panel（通常是 `http://localhost:端口` 或 `http://你的IP:端口`）
2. 使用安装时设置的用户名和密码登录

#### 步骤 5.2：创建 Compose 项目

1. **进入容器管理**
   - 点击左侧菜单 **"容器"** 或 **"Docker"**
   - 选择 **"Compose"** 或 **"编排"** 标签页

2. **创建新项目**
   - 点击 **"创建"** 或 **"新建"** 按钮
   - 项目名称：`pepgmp-production`
   - 工作目录：`/home/你的用户名/projects/Pyt`（例如：`/home/pep/projects/Pyt`）

3. **配置 Compose 文件**
   - 方式1：上传 `docker-compose.prod.yml` 文件
   - 方式2：在编辑器中粘贴文件内容
   - 方式3：选择 **"从文件创建"**，指向 `~/projects/PEPGMPdocker-compose.prod.yml`

#### 步骤 5.3：启动服务

1. 在 1Panel 中点击 **"启动"** 或 **"部署"** 按钮
2. 等待服务启动（首次启动需要 60-90 秒）
3. 查看服务状态，确保所有容器状态为 **"运行中"**

### 方式 B：使用命令行部署

```bash
cd ~/projects/Pyt

# 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

---

## ✅ 第六阶段：验证部署

### 步骤 6.1：检查容器状态

```bash
cd ~/projects/Pyt

# 查看所有容器状态
docker compose -f docker-compose.prod.yml ps

# 应该看到所有容器状态为 "Up"：
# - pepgmp-postgres-prod (database)
# - pepgmp-redis-prod (redis)
# - pepgmp-api-prod (api)
# - pepgmp-frontend-init-prod (frontend-init)
# - pepgmp-nginx-prod (nginx)
```

### 步骤 6.2：健康检查

```bash
# API 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 预期输出: {"status":"healthy"}

# Nginx 健康检查
curl http://localhost/health

# 预期输出: healthy
```

### 步骤 6.3：检查数据库连接

```bash
# 检查数据库是否就绪
docker exec pepgmp-postgres-prod pg_isready -U pepgmp_prod -d pepgmp_production

# 检查数据库版本
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT version();"
```

### 步骤 6.4：检查 Redis 连接

```bash
# 获取 Redis 密码
REDIS_PASSWORD=$(grep REDIS_PASSWORD .env.production | cut -d'=' -f2)

# 测试 Redis 连接
docker exec pepgmp-redis-prod redis-cli -a "$REDIS_PASSWORD" ping

# 预期输出: PONG
```

### 步骤 6.5：检查前端静态文件

```bash
# 检查前端静态文件是否已提取
ls -la frontend/dist/

# 应该看到：
# - index.html
# - assets/
```

### 步骤 6.6：访问应用

1. **在 Windows 浏览器中访问**：
   ```
   http://localhost/
   ```

2. **如果无法访问，检查 WSL2 IP**：
   ```bash
   # 在 WSL2 中查看 IP
   hostname -I

   # 在 Windows 浏览器中访问
   # http://<WSL2-IP>/
   ```

3. **登录应用**：
   - 使用 `.env.production.credentials` 中的 Admin 用户名和密码

---

## 🔍 故障排查

### 问题 1：容器无法启动

**检查步骤**：
```bash
# 查看容器日志
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs nginx

# 检查镜像是否存在
docker images | grep pepgmp

# 检查镜像标签是否匹配
grep IMAGE_TAG .env.production
```

**常见原因**：
- 镜像标签不匹配：检查 `IMAGE_TAG` 是否与导入的镜像标签一致
- 配置文件错误：重新运行 `generate_production_config.sh`
- 端口冲突：检查 80 端口是否被占用

### 问题 2：前端白屏

**检查步骤**：
```bash
# 检查前端静态文件
ls -la frontend/dist/

# 检查 frontend-init 容器日志
docker compose -f docker-compose.prod.yml logs frontend-init

# 检查 Nginx 配置
docker exec pepgmp-nginx-prod nginx -t

# 检查 Nginx 日志
docker compose -f docker-compose.prod.yml logs nginx
```

**解决方案**：
- 确保 `frontend-init` 容器已成功完成
- 检查 `frontend/dist/` 目录权限
- 检查 Nginx 配置是否正确

### 问题 3：数据库连接失败

**检查步骤**：
```bash
# 检查数据库容器状态
docker compose -f docker-compose.prod.yml ps database

# 检查数据库日志
docker compose -f docker-compose.prod.yml logs database

# 检查数据库密码
grep DATABASE_PASSWORD .env.production
```

**解决方案**：
- 确保数据库容器已启动
- 检查数据库密码是否正确
- 检查数据库初始化是否完成

### 问题 4：API 无法访问

**检查步骤**：
```bash
# 检查 API 容器状态
docker compose -f docker-compose.prod.yml ps api

# 检查 API 日志
docker compose -f docker-compose.prod.yml logs api

# 检查 API 健康检查
curl http://localhost:8000/api/v1/monitoring/health
```

**解决方案**：
- 检查 API 容器是否正常运行
- 检查数据库迁移是否成功（查看 `docker-entrypoint.sh` 日志）
- 检查环境变量配置

---

## 🔄 更新部署

### 更新镜像

```bash
# 1. 在 macOS 中构建新镜像
bash scripts/build_prod_only.sh 20251203

# 2. 导出新镜像
docker save pepgmp-backend:20251203 -o docker-images/pepgmp-backend-20251203.tar
docker save pepgmp-frontend:20251203 -o docker-images/pepgmp-frontend-20251203.tar

# 3. 在 WSL2 中导入新镜像
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-backend-20251203.tar
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-frontend-20251203.tar

# 4. 更新配置文件中的 IMAGE_TAG
cd ~/projects/Pyt
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251203/' .env.production

# 5. 重启服务
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### 更新配置

```bash
cd ~/projects/Pyt

# 1. 修改配置文件
nano .env.production

# 2. 重启服务
docker compose -f docker-compose.prod.yml restart api
```

---

## 📋 快速参考命令

```bash
# ========== 准备阶段 ==========
# 构建镜像（macOS）
bash scripts/build_prod_only.sh 20251202

# 导出镜像（macOS）
docker save pepgmp-backend:20251202 -o docker-images/pepgmp-backend-20251202.tar
docker save pepgmp-frontend:20251202 -o docker-images/pepgmp-frontend-20251202.tar

# ========== WSL2 部署阶段 ==========
# 导入镜像（WSL2）
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-backend-20251202.tar
docker load -i /mnt/c/Users/YourName/Code/PEPGMP/docker-images/pepgmp-frontend-20251202.tar

# 准备部署包（WSL2）
bash /mnt/c/Users/YourName/Code/PEPGMP/scripts/prepare_minimal_deploy.sh ~/projects/Pyt

# 生成配置文件（WSL2）
cd ~/projects/PEPGMP&& bash scripts/generate_production_config.sh

# 启动服务（WSL2）
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# ========== 验证阶段 ==========
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 健康检查
curl http://localhost:8000/api/v1/monitoring/health
curl http://localhost/health

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx

# ========== 运维命令 ==========
# 停止服务
docker compose -f docker-compose.prod.yml down

# 重启服务
docker compose -f docker-compose.prod.yml restart

# 查看资源使用
docker stats
```

---

## 📚 相关文档

- [完整部署方案说明](./完整部署方案说明.md) - 架构详细说明
- [生产环境部署指南](./生产环境部署指南.md) - 通用部署指南
- [WSL2 1Panel 部署步骤](./WSL2_1PANEL_DEPLOYMENT_STEPS.md) - 1Panel 专用指南
- [第2天运维问题修复方案](./第2天运维问题修复方案.md) - 运维优化说明

---

**最后更新**: 2025-12-02
**适用环境**: WSL2 Ubuntu 22.04 + Docker + 1Panel（可选）
