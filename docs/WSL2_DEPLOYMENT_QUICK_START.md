# WSL2 快速部署指南

## 📋 概述

本指南说明如何在 WSL2 Ubuntu 环境中部署已在 Windows 上构建成功的 Docker 镜像。

**前提条件**：
- ✅ 已在 Windows 上成功构建镜像（`pepgmp-backend:20251201` 和 `pepgmp-frontend:20251201`）
- ✅ WSL2 Ubuntu 已安装并配置
- ✅ Docker Desktop 已安装并启用 WSL2 集成

---

## 🚀 快速部署步骤

### 方法1: 使用 Docker Desktop WSL2 集成（推荐）

Docker Desktop 的 WSL2 集成会自动共享镜像，**无需手动传输**。

#### 步骤1: 验证镜像在 WSL2 中可用

在 **WSL2 Ubuntu** 终端中执行：

```bash
# 检查 Docker 是否正常工作
docker --version
docker compose version

# 查看镜像（应该能看到 Windows 上构建的镜像）
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251201
# pepgmp-backend:latest
# pepgmp-frontend:20251201
# pepgmp-frontend:latest
```

**如果看不到镜像**，说明 Docker Desktop WSL2 集成可能未正确配置，请参考"故障排查"部分。

#### 步骤2: 准备项目代码

**重要**：将项目放在 WSL2 文件系统中（`~/projects/`），而不是 Windows 文件系统（`/mnt/c/...`），以获得最佳性能。

```bash
# 在 WSL2 Ubuntu 中
cd ~

# 如果项目在 Windows 文件系统中，需要复制到 WSL2 文件系统
# 方法1: 使用 git clone（推荐）
mkdir -p ~/projects
cd ~/projects
git clone <your-repo-url> Pyt
cd Pyt

# 方法2: 从 Windows 文件系统复制（如果已经在 Windows 中）
# cp -r /mnt/c/Users/YourName/Code/PythonCode/Pyt ~/projects/Pyt
# cd ~/projects/Pyt
```

#### 步骤3: 配置环境变量

```bash
# 创建生产环境配置文件
cp .env.production.example .env.production 2>/dev/null || touch .env.production

# 编辑配置文件
nano .env.production
# 或使用 VS Code（在 Windows 中）
code .env.production
```

**关键配置项**：

```env
# ==================== 环境设置 ====================
ENVIRONMENT=production
LOG_LEVEL=INFO

# ==================== 镜像版本 ====================
IMAGE_TAG=20251201

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://pepgmp_prod:YOUR_STRONG_PASSWORD@database:5432/pepgmp_production
DATABASE_PASSWORD=YOUR_STRONG_PASSWORD

# ==================== Redis 配置 ====================
REDIS_URL=redis://:YOUR_STRONG_PASSWORD@redis:6379/0
REDIS_PASSWORD=YOUR_STRONG_PASSWORD

# ==================== API 配置 ====================
API_PORT=8000
API_HOST=0.0.0.0
```

#### 步骤4: 启动服务

```bash
# 使用 Docker Compose 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api
```

#### 步骤5: 验证部署

```bash
# 等待服务启动（首次部署需要60-70秒）
sleep 60

# 检查服务健康状态
curl http://localhost:8000/api/v1/monitoring/health

# 检查数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT version();"

# 检查 Redis 连接
docker exec pepgmp-redis-prod redis-cli -a YOUR_REDIS_PASSWORD ping
```

---

### 方法2: 手动传输镜像（如果方法1不可用）

如果 Docker Desktop WSL2 集成未正确配置，可以手动传输镜像。

#### 步骤1: 在 Windows 中导出镜像

在 **Windows PowerShell** 中执行：

```powershell
# 导出后端镜像
docker save pepgmp-backend:20251201 -o pepgmp-backend-20251201.tar

# 导出前端镜像
docker save pepgmp-frontend:20251201 -o pepgmp-frontend-20251201.tar

# 压缩镜像文件（可选，减小传输大小）
Compress-Archive -Path pepgmp-backend-20251201.tar -DestinationPath pepgmp-backend-20251201.zip
Compress-Archive -Path pepgmp-frontend-20251201.tar -DestinationPath pepgmp-frontend-20251201.zip
```

#### 步骤2: 传输镜像到 WSL2

```bash
# 在 WSL2 Ubuntu 中
# 从 Windows 文件系统复制到 WSL2 文件系统
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-backend-20251201.tar ~/
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-frontend-20251201.tar ~/

# 如果压缩了，先解压
# unzip ~/pepgmp-backend-20251201.zip -d ~/
# unzip ~/pepgmp-frontend-20251201.zip -d ~/
```

#### 步骤3: 在 WSL2 中导入镜像

```bash
# 导入镜像
docker load -i ~/pepgmp-backend-20251201.tar
docker load -i ~/pepgmp-frontend-20251201.tar

# 验证镜像
docker images | grep pepgmp

# 清理临时文件
rm ~/pepgmp-*.tar
```

然后继续执行"方法1"的步骤3-5。

---

## 🔧 使用部署脚本（推荐）

项目提供了专门的 WSL2 部署脚本：

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 使用统一启动脚本
bash scripts/start_prod_wsl.sh

# 或直接使用统一脚本
bash scripts/start.sh --env prod --mode containerized
```

---

## 📋 常用命令

### 服务管理

```bash
# 启动服务
docker compose -f docker-compose.prod.yml up -d

# 停止服务
docker compose -f docker-compose.prod.yml down

# 重启服务
docker compose -f docker-compose.prod.yml restart api

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f database
docker compose -f docker-compose.prod.yml logs -f redis
```

### 容器管理

```bash
# 进入 API 容器
docker exec -it pepgmp-api-prod bash

# 进入数据库容器
docker exec -it pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production

# 查看容器资源使用
docker stats pepgmp-api-prod
```

### 数据库管理

```bash
# 检查数据库初始化
bash scripts/check_database_init.sh pepgmp-postgres-prod pepgmp_prod pepgmp_production

# 备份数据库
docker exec pepgmp-postgres-prod pg_dump -U pepgmp_prod pepgmp_production > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i pepgmp-postgres-prod psql -U pepgmp_prod pepgmp_production < backup_20251201.sql
```

---

## 🔍 故障排查

### 问题1: WSL2 中看不到 Windows 构建的镜像

**症状**：`docker images` 看不到 `pepgmp-backend:20251201`

**解决方案**：

1. **检查 Docker Desktop WSL2 集成**：
   - 打开 Docker Desktop
   - Settings > Resources > WSL Integration
   - 确保 "Ubuntu" 已启用

2. **重启 Docker Desktop**：
   - 在 Windows 中重启 Docker Desktop
   - 然后在 WSL2 中测试：`docker ps`

3. **手动传输镜像**（参考方法2）

### 问题2: 端口被占用

**症状**：`Error: bind: address already in use`

**解决方案**：

```bash
# 检查端口占用
sudo netstat -tulpn | grep :8000
# 或
sudo lsof -i :8000

# 停止占用端口的进程
# 或修改 docker-compose.prod.yml 中的端口映射
```

### 问题3: 数据库连接失败

**症状**：`could not connect to server`

**解决方案**：

```bash
# 检查数据库容器状态
docker compose -f docker-compose.prod.yml ps database

# 检查数据库日志
docker compose -f docker-compose.prod.yml logs database

# 等待数据库完全启动（首次启动需要60-70秒）
sleep 60

# 验证数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"
```

### 问题4: 文件权限问题

**症状**：`Permission denied` 或容器无法写入文件

**解决方案**：

```bash
# 确保配置文件权限正确
chmod 600 .env.production

# 确保挂载目录权限正确
sudo chown -R $USER:$USER ./config ./models ./data
chmod -R 755 ./config ./models
```

---

## 📚 相关文档

- [WSL2 Ubuntu 部署完整指南](WSL2_UBUNTU_DEPLOYMENT_GUIDE.md)
- [Windows 生产环境部署指南](WINDOWS_PRODUCTION_DEPLOYMENT.md)
- [Docker 镜像源配置问题解决方案](DOCKER_MIRROR_FIX.md)
- [Docker 增量构建优化方案](DOCKER_INCREMENTAL_BUILD_OPTIMIZATION.md)

---

## 🎯 快速参考

### 完整部署命令（一键执行）

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 1. 验证镜像
docker images | grep pepgmp

# 2. 配置环境变量（如果还没有）
cp .env.production.example .env.production
nano .env.production  # 编辑配置

# 3. 启动服务
docker compose -f docker-compose.prod.yml up -d

# 4. 等待服务启动
sleep 60

# 5. 验证部署
curl http://localhost:8000/api/v1/monitoring/health
```

---

**最后更新**: 2025-12-01  
**适用版本**: Docker Desktop with WSL2 Integration

