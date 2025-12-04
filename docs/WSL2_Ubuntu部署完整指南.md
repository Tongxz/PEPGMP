# WSL2 / Ubuntu 部署完整指南

## 📋 概述

本指南提供从 **macOS 开发环境** 到 **WSL2/Ubuntu 生产环境** 的完整部署流程。

**部署架构**: Scheme B（单 Nginx 架构）

---

## 🎯 部署前准备

### 检查清单

**macOS 开发机**：
- [ ] 已成功在本地部署并测试通过
- [ ] 已构建好生产镜像（`pepgmp-backend:20251204` 和 `pepgmp-frontend:20251204`）
- [ ] 镜像已导出为 tar 文件（可选，如果使用 Docker Desktop WSL2 集成则不需要）

**WSL2/Ubuntu 目标机**：
- [ ] WSL2 Ubuntu 已安装并运行
- [ ] Docker 已安装并运行
- [ ] Docker Compose 已安装
- [ ] 有足够的磁盘空间（至少 10GB）

---

## 📦 第一阶段：macOS 开发机准备

### 步骤 1.1：构建生产镜像

```bash
cd /Users/zhou/Code/Pyt

# 使用日期作为版本号构建镜像（推荐）
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 例如：20251204
# 构建输出：
# - pepgmp-backend:20251204
# - pepgmp-backend:latest
# - pepgmp-frontend:20251204
# - pepgmp-frontend:latest
```

### 步骤 1.2：验证镜像

```bash
# 检查镜像是否存在
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251204
# pepgmp-frontend:20251204
```

### 步骤 1.3：导出镜像（方法 1：手动导出）

**如果 WSL2 使用独立的 Docker（不是 Docker Desktop WSL2 集成）**，需要导出镜像：

```bash
# 创建导出目录
mkdir -p docker-images

# 导出后端镜像
docker save pepgmp-backend:20251204 -o docker-images/pepgmp-backend-20251204.tar

# 导出前端镜像
docker save pepgmp-frontend:20251204 -o docker-images/pepgmp-frontend-20251204.tar

# 验证导出文件
ls -lh docker-images/

# 预期输出：
# pepgmp-backend-20251204.tar    (约 2-3 GB)
# pepgmp-frontend-20251204.tar   (约 100-200 MB)
```

### 步骤 1.4：准备部署包

```bash
cd /Users/zhou/Code/Pyt

# 使用准备脚本创建最小化部署包
# 目标目录：可以放在共享位置，方便传输到 WSL2
bash scripts/prepare_minimal_deploy.sh ~/deploy-packages/Pyt

# 脚本会复制：
# - docker-compose.prod.yml
# - config/ 目录
# - models/ 目录（可选）
# - scripts/ 目录（包含 generate_production_config.sh）
# - nginx/ 目录
```

---

## 🚀 第二阶段：WSL2/Ubuntu 环境准备

### 步骤 2.1：进入 WSL2 Ubuntu

在 Windows 中打开 WSL2：

```bash
# 方式1: 从 Windows 终端
wsl

# 方式2: 从 PowerShell
wsl -d Ubuntu-22.04

# 方式3: 从 Windows Terminal
# 直接选择 Ubuntu 标签页
```

### 步骤 2.2：验证 Docker 环境

```bash
# 检查 Docker 是否运行
docker --version
docker ps

# 检查 Docker Compose
docker compose version

# 如果 Docker 未安装，参考：
# https://docs.docker.com/engine/install/ubuntu/
```

### 步骤 2.3：导入镜像

#### 方法 A: Docker Desktop WSL2 集成（推荐）

如果使用 Docker Desktop 并启用了 WSL2 集成，镜像会自动共享，**无需手动导入**。

```bash
# 直接检查镜像是否可用
docker images | grep pepgmp

# 如果能看到镜像，说明已自动共享 ✅
```

#### 方法 B: 手动导入镜像

如果 WSL2 使用独立的 Docker，需要手动导入：

```bash
# 从 macOS 传输镜像文件到 Windows，然后从 Windows 文件系统导入

# 导入后端镜像
docker load -i /mnt/c/Users/YourName/Downloads/pepgmp-backend-20251204.tar

# 导入前端镜像
docker load -i /mnt/c/Users/YourName/Downloads/pepgmp-frontend-20251204.tar

# 验证导入
docker images | grep pepgmp
```

**镜像传输方式**：
1. **通过共享文件夹**：将 tar 文件放到 Windows 可访问的位置
2. **通过 SCP**：`scp docker-images/*.tar user@wsl-host:/path/`
3. **通过 USB/网络**：物理传输

---

## 📁 第三阶段：准备部署目录

### 步骤 3.1：创建部署目录

**重要**：将项目放在 WSL2 文件系统中（`~/projects/`），而不是 Windows 文件系统（`/mnt/c/...`），以获得最佳性能。

```bash
# 在 WSL2 Ubuntu 中
mkdir -p ~/projects
cd ~/projects
```

### 步骤 3.2：复制部署包

#### 方式 1: 从 macOS 直接传输（推荐）

```bash
# 在 WSL2 中，从 macOS 通过 SCP 传输
# 需要 macOS 和 WSL2 在同一网络

# 在 macOS 上：
cd ~/deploy-packages
scp -r Pyt user@wsl-ip:~/projects/

# 或使用 rsync（更高效）
rsync -avz --progress Pyt/ user@wsl-ip:~/projects/PEPGMP
```

#### 方式 2: 通过 Windows 文件系统

```bash
# 在 WSL2 中
# 如果部署包在 Windows 文件系统中
cp -r /mnt/c/Users/YourName/Downloads/Pyt ~/projects/
cd ~/projects/Pyt
```

#### 方式 3: 使用 Git（推荐用于代码同步）

```bash
# 在 WSL2 中
cd ~/projects
git clone <your-repo-url> Pyt
cd Pyt

# 只保留必要的文件（不需要 src/, frontend/src/ 等）
# 使用 prepare_minimal_deploy.sh 脚本准备最小化部署包
bash scripts/prepare_minimal_deploy.sh ~/projects/PEPGMP-deploy
cd ~/projects/PEPGMP-deploy
```

### 步骤 3.3：验证部署文件

```bash
cd ~/projects/Pyt

# 检查必要文件是否存在
ls -la docker-compose.prod.yml
ls -la config/
ls -la scripts/generate_production_config.sh

# 应该看到：
# ✅ docker-compose.prod.yml
# ✅ config/ 目录
# ✅ scripts/ 目录
# ✅ nginx/ 目录（如果使用）
```

---

## ⚙️ 第四阶段：配置环境

### 步骤 4.1：生成配置文件

```bash
cd ~/projects/Pyt

# 运行配置生成脚本
bash scripts/generate_production_config.sh

# 按提示输入：
# - API端口 [8000]: 直接回车（或输入自定义端口）
# - 管理员用户名 [admin]: 直接回车（或输入自定义用户名）
# - CORS来源 [*]: 直接回车（或输入特定域名）
# - 镜像标签 [latest]: 20251204  ← 重要！输入你的镜像版本号
# - 数据库密码: 输入强密码（或使用自动生成的）
# - Redis 密码: 输入强密码（或使用自动生成的）
```

**脚本会自动生成**：
- `.env.production` - 完整配置文件
- `.env.production.credentials` - 凭证文件（请保存后删除）

### 步骤 4.2：检查配置文件

```bash
# 检查 .env.production
cat .env.production | grep -E "IMAGE_TAG|DATABASE_PASSWORD|REDIS_PASSWORD"

# 确保 IMAGE_TAG 与构建的镜像版本一致
# 例如：IMAGE_TAG=20251204
```

### 步骤 4.3：设置文件权限

```bash
# 确保脚本有执行权限
chmod +x scripts/*.sh

# 确保配置文件权限正确
chmod 600 .env.production
```

---

## 🚀 第五阶段：启动服务

### 步骤 5.1：启动服务

```bash
cd ~/projects/Pyt

# 使用 Docker Compose 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 或使用简写（如果 docker-compose.prod.yml 是默认文件）
docker compose --env-file .env.production up -d
```

**启动过程**：
1. 启动 PostgreSQL 数据库
2. 启动 Redis 缓存
3. 启动 API 服务（等待数据库就绪）
4. 运行 `frontend-init` 容器（提取静态文件）
5. 启动 Nginx（等待 frontend-init 完成）

### 步骤 5.2：查看启动日志

```bash
# 查看所有服务状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 查看服务日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 查看特定服务日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs api
docker compose -f docker-compose.prod.yml --env-file .env.production logs frontend-init
docker compose -f docker-compose.prod.yml --env-file .env.production logs nginx
```

### 步骤 5.3：等待服务就绪

```bash
# 等待约 60-90 秒让所有服务启动
# 检查健康状态
curl http://localhost:8000/api/v1/monitoring/health

# 应该返回：
# {"status":"healthy",...}
```

---

## ✅ 第六阶段：验证部署

### 步骤 6.1：检查服务状态

```bash
# 检查所有容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 应该看到所有服务都是 "Up" 状态：
# ✅ pepgmp-postgres-prod    Up (healthy)
# ✅ pepgmp-redis-prod       Up (healthy)
# ✅ pepgmp-api-prod         Up (healthy)
# ✅ pepgmp-frontend-init    Exited (0)  ← 正常，任务完成后退出
# ✅ pepgmp-nginx-prod       Up
```

### 步骤 6.2：检查前端文件

```bash
# 检查静态文件是否已提取
ls -la frontend/dist/

# 应该看到：
# ✅ index.html
# ✅ assets/ 目录
# ✅ 50x.html

# 检查 index.html 内容
cat frontend/dist/index.html | head -15

# 应该看到使用简化策略的构建产物
```

### 步骤 6.3：测试 HTTP 访问

```bash
# 测试 API 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 测试前端访问
curl -I http://localhost/

# 应该返回: HTTP/1.1 200 OK
```

### 步骤 6.4：浏览器验证

1. **获取 WSL2 IP 地址**：
   ```bash
   # 在 WSL2 中
   hostname -I
   # 或
   ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
   ```

2. **在 Windows 浏览器中访问**：
   - 前端：`http://<WSL2-IP>/`
   - API：`http://<WSL2-IP>:8000/api/v1/monitoring/health`

3. **检查**：
   - 页面是否正常显示
   - 控制台是否有错误
   - 网络请求是否都返回 200

---

## 🔧 常见问题排查

### 问题 1: 镜像不存在

**症状**：
```
Error: No such image: pepgmp-backend:20251204
```

**解决**：
```bash
# 检查镜像是否存在
docker images | grep pepgmp

# 如果不存在，需要导入
docker load -i /path/to/pepgmp-backend-20251204.tar
docker load -i /path/to/pepgmp-frontend-20251204.tar
```

### 问题 2: 端口被占用

**症状**：
```
Error: bind: address already in use
```

**解决**：
```bash
# 检查端口占用
sudo netstat -tulpn | grep -E "80|8000|5432|6379"

# 或修改 .env.production 中的端口配置
# API_PORT=8001
# 然后更新 docker-compose.prod.yml
```

### 问题 3: 数据库连接失败

**症状**：
```
API 容器日志显示: could not connect to database
```

**解决**：
```bash
# 检查数据库容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps database

# 检查数据库日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs database

# 检查 .env.production 中的数据库密码是否正确
cat .env.production | grep DATABASE_PASSWORD
```

### 问题 4: 前端白屏

**症状**：
- 浏览器显示白屏
- 控制台有错误

**解决**：
```bash
# 1. 检查静态文件是否已提取
ls -la frontend/dist/

# 2. 重新提取静态文件
rm -rf frontend/dist/*
docker compose -f docker-compose.prod.yml --env-file .env.production up frontend-init

# 3. 重启 Nginx
docker compose -f docker-compose.prod.yml --env-file .env.production restart nginx

# 4. 清除浏览器缓存（硬刷新: Ctrl+Shift+R）
```

### 问题 5: 文件权限问题

**症状**：
```
Permission denied
```

**解决**：
```bash
# 检查文件权限
ls -la frontend/dist/

# 修复权限
sudo chown -R $(id -u):$(id -g) frontend/dist/
chmod -R 755 frontend/dist/
```

---

## 📝 日常维护

### 更新部署

```bash
cd ~/projects/Pyt

# 1. 停止服务
docker compose -f docker-compose.prod.yml --env-file .env.production down

# 2. 更新代码/配置（如果需要）
git pull  # 或手动更新文件

# 3. 导入新镜像（如果有新版本）
docker load -i /path/to/new-image.tar

# 4. 更新 .env.production 中的 IMAGE_TAG

# 5. 重新启动
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### 查看日志

```bash
# 查看所有服务日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 查看特定服务日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f api
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f nginx
```

### 备份数据

```bash
# 备份数据库
docker exec pepgmp-postgres-prod pg_dump -U pepgmp_prod pepgmp_production > backup-$(date +%Y%m%d).sql

# 备份 Redis 数据（如果启用持久化）
docker exec pepgmp-redis-prod redis-cli -a $REDIS_PASSWORD SAVE
docker cp pepgmp-redis-prod:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb
```

---

## 🎯 快速参考

### 一键部署脚本（待创建）

可以创建一个自动化部署脚本，整合所有步骤：

```bash
#!/bin/bash
# scripts/deploy_to_wsl2.sh

# 1. 构建镜像
# 2. 导出镜像
# 3. 准备部署包
# 4. 传输到 WSL2
# 5. 在 WSL2 中导入镜像
# 6. 生成配置
# 7. 启动服务
```

---

## 📚 相关文档

- [WSL2 生产部署详细步骤](./WSL2生产部署详细步骤.md)
- [macOS 生产部署指南](./macOS生产部署指南.md)
- [前端构建流程分析](./前端构建流程分析.md)
- [容器内前端构建问题分析](./容器内前端构建问题分析.md)

---

**最后更新**: 2025-12-04
