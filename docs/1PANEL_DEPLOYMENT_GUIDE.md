# 1Panel 可视化面板部署指南

## 📋 概述

本指南说明如何在 **1Panel** 可视化面板中部署本项目。1Panel 是一个开源的 Linux 服务器运维管理面板，提供了 Docker 容器管理的图形界面。

**前提条件**：
- ✅ WSL2 Ubuntu 已安装
- ✅ 1Panel 已安装并运行
- ✅ Docker 镜像已导入到 WSL2 中（`pepgmp-backend:20251201` 和 `pepgmp-frontend:20251201`）

**重要说明**：
- ⚠️ **不需要完整的项目代码**，只需要必要的配置文件和目录
- ✅ 源代码已在镜像中，不需要 `src/` 目录
- ✅ 只需要：`docker-compose.prod.yml`、`.env.production`、`config/`、`models/`（可选）

---

## 🚀 部署步骤

### 方法1: 使用 Docker Compose（推荐）

1Panel 支持通过 Docker Compose 文件部署，这是最推荐的方式。

#### 步骤1: 准备最小化部署包

**重要**：不需要完整的项目代码，只需要必要的文件。

#### 方式1: 使用准备脚本（推荐）

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects

# 从 Windows 项目目录运行准备脚本
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh

# 或指定目标目录
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh ~/projects/Pyt
```

#### 方式2: 手动准备

```bash
# 创建部署目录
mkdir -p ~/projects/Pyt/{config,models,data,logs}
cd ~/projects/Pyt

# 复制必需文件
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/docker-compose.prod.yml .
cp -r /mnt/c/Users/YourName/Code/PythonCode/Pyt/config/* config/
cp -r /mnt/c/Users/YourName/Code/PythonCode/Pyt/models/* models/ 2>/dev/null || true

# 创建环境变量文件
cat > .env.production << 'EOF'
ENVIRONMENT=production
LOG_LEVEL=INFO
IMAGE_TAG=20251201
DATABASE_PASSWORD=your_strong_password
REDIS_PASSWORD=your_strong_password
SECRET_KEY=your_secret_key_here
EOF
chmod 600 .env.production
```

**需要的文件清单**：
- ✅ `docker-compose.prod.yml` - Docker Compose 配置
- ✅ `.env.production` - 环境变量配置
- ✅ `config/` - 配置文件目录（容器会挂载）
- ✅ `models/` - 模型文件目录（可选，如果需要）
- ✅ `data/` - 数据目录（可选）

**不需要的文件**：
- ❌ `src/` - 源代码（已在镜像中）
- ❌ `frontend/` - 前端代码（已在镜像中）
- ❌ `Dockerfile.prod` - 构建文件（不需要）
- ❌ `requirements.txt` - 依赖文件（不需要）

#### 步骤2: 在 1Panel 中创建应用

1. **登录 1Panel**
   - 打开浏览器访问：`http://localhost:端口`（1Panel 默认端口）
   - 使用安装时设置的用户名和密码登录

2. **进入容器管理**
   - 点击左侧菜单 **"容器"** 或 **"Docker"**
   - 选择 **"Compose"** 或 **"编排"** 标签

3. **创建 Compose 项目**
   - 点击 **"创建"** 或 **"新建"** 按钮
   - 项目名称：`pepgmp-production`
   - 选择 **"从文件创建"** 或 **"导入 Compose 文件"**

4. **上传或编辑 Compose 文件**
   - 方式1：上传 `docker-compose.prod.yml` 文件
   - 方式2：在编辑器中粘贴 `docker-compose.prod.yml` 的内容

#### 步骤3: 配置环境变量

在 1Panel 的 Compose 编辑器中，确保环境变量配置正确：

**方式1: 使用 .env.production 文件**
- 在 1Panel 中上传 `.env.production` 文件
- 或在 Compose 文件中指定：`env_file: - .env.production`

**方式2: 在 Compose 文件中直接配置**
- 在 `environment:` 部分添加环境变量

**关键环境变量**：
```yaml
environment:
  - ENVIRONMENT=production
  - IMAGE_TAG=20251201
  - DATABASE_PASSWORD=your_strong_password
  - REDIS_PASSWORD=your_strong_password
  - DATABASE_URL=postgresql://pepgmp_prod:your_strong_password@database:5432/pepgmp_production
  - REDIS_URL=redis://:your_strong_password@redis:6379/0
```

#### 步骤4: 修改镜像配置

确保 Compose 文件中的镜像配置使用已导入的镜像：

```yaml
services:
  api:
    image: pepgmp-backend:20251201  # 使用已导入的镜像
    # 或使用 latest
    # image: pepgmp-backend:latest
```

#### 步骤5: 启动服务

1. 在 1Panel 中点击 **"启动"** 或 **"部署"** 按钮
2. 等待服务启动（首次启动需要60-70秒）
3. 查看服务状态

---

### 方法2: 使用 1Panel 容器管理界面

如果不想使用 Docker Compose，可以在 1Panel 中逐个创建容器。

#### 步骤1: 创建 PostgreSQL 容器

1. 进入 **"容器"** > **"创建容器"**
2. 配置如下：

```
容器名称: pepgmp-postgres-prod
镜像: postgres:16-alpine
端口映射: 5432:5432（可选，生产环境建议不映射）
环境变量:
  - POSTGRES_DB=pepgmp_production
  - POSTGRES_USER=pepgmp_prod
  - POSTGRES_PASSWORD=your_strong_password
  - PGDATA=/var/lib/postgresql/data/pgdata
数据卷:
  - postgres_prod_data:/var/lib/postgresql/data
网络: 创建新网络 pepgmp_backend
重启策略: unless-stopped
```

#### 步骤2: 创建 Redis 容器

1. 创建新容器
2. 配置如下：

```
容器名称: pepgmp-redis-prod
镜像: redis:7-alpine
命令: redis-server --appendonly yes --requirepass your_strong_password --maxmemory 512mb --maxmemory-policy allkeys-lru
数据卷:
  - redis_prod_data:/data
网络: pepgmp_backend
重启策略: unless-stopped
```

#### 步骤3: 创建 API 容器

1. 创建新容器
2. 配置如下：

```
容器名称: pepgmp-api-prod
镜像: pepgmp-backend:20251201
端口映射: 8000:8000
环境变量:
  - ENVIRONMENT=production
  - DATABASE_URL=postgresql://pepgmp_prod:your_strong_password@pepgmp-postgres-prod:5432/pepgmp_production
  - REDIS_URL=redis://:your_strong_password@pepgmp-redis-prod:6379/0
数据卷:
  - ./config:/app/config:ro
  - ./models:/app/models:ro
  - ./data:/app/data
  - ./logs:/app/logs
网络: pepgmp_backend
依赖容器: pepgmp-postgres-prod, pepgmp-redis-prod
重启策略: unless-stopped
```

#### 步骤4: 创建前端容器（可选）

```
容器名称: pepgmp-frontend-prod
镜像: pepgmp-frontend:20251201
端口映射: 8080:80
网络: pepgmp_backend
重启策略: unless-stopped
```

---

## 📋 1Panel 中的常用操作

### 查看容器状态

1. 进入 **"容器"** 页面
2. 查看所有容器的运行状态
3. 点击容器名称查看详细信息

### 查看日志

1. 在容器列表中点击容器名称
2. 选择 **"日志"** 标签
3. 实时查看容器日志

### 重启容器

1. 在容器列表中选择容器
2. 点击 **"重启"** 按钮

### 进入容器终端

1. 在容器列表中选择容器
2. 点击 **"终端"** 或 **"执行命令"**
3. 可以执行命令或进入交互式终端

### 修改配置

1. 对于 Compose 项目：编辑 Compose 文件后点击 **"更新"**
2. 对于单个容器：停止容器 > 修改配置 > 重新创建

---

## 🔧 环境变量配置

### 在 1Panel 中配置环境变量

**方式1: 通过 Compose 文件**
- 在 Compose 编辑器中直接编辑 `environment:` 部分

**方式2: 通过 .env 文件**
- 在项目目录中创建 `.env.production` 文件
- 在 Compose 文件中引用：`env_file: - .env.production`

**方式3: 通过 1Panel 环境变量管理**
- 在容器配置中添加环境变量
- 或使用 1Panel 的 **"环境变量"** 功能（如果支持）

### 推荐的环境变量配置

创建 `.env.production` 文件：

```env
# ==================== 环境设置 ====================
ENVIRONMENT=production
LOG_LEVEL=INFO
IMAGE_TAG=20251201

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://pepgmp_prod:your_strong_password@database:5432/pepgmp_production
DATABASE_PASSWORD=your_strong_password

# ==================== Redis 配置 ====================
REDIS_URL=redis://:your_strong_password@redis:6379/0
REDIS_PASSWORD=your_strong_password

# ==================== API 配置 ====================
API_PORT=8000
API_HOST=0.0.0.0

# ==================== 安全配置 ====================
SECRET_KEY=your_secret_key_here
ADMIN_PASSWORD=your_admin_password
```

---

## 📊 监控和管理

### 1Panel 监控功能

1. **资源监控**
   - 查看 CPU、内存、磁盘使用情况
   - 查看容器资源占用

2. **日志管理**
   - 集中查看所有容器日志
   - 日志搜索和过滤

3. **性能监控**
   - 容器性能指标
   - 网络流量监控

### 数据库管理

1. **使用 1Panel 数据库管理**（如果安装了）
   - 创建数据库连接
   - 管理数据库和表

2. **使用命令行**
   ```bash
   # 在 1Panel 终端中或 WSL2 中
   docker exec -it pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production
   ```

---

## 🔍 故障排查

### 问题1: 容器无法启动

**检查步骤**：
1. 在 1Panel 中查看容器日志
2. 检查环境变量配置是否正确
3. 检查端口是否被占用
4. 检查镜像是否存在：`docker images | grep pepgmp`

### 问题2: 数据库连接失败

**解决方案**：
1. 确保 PostgreSQL 容器已启动并健康
2. 检查环境变量中的数据库连接字符串
3. 验证网络配置（容器是否在同一网络）

### 问题3: 镜像找不到

**解决方案**：
```bash
# 在 WSL2 中验证镜像
docker images | grep pepgmp

# 如果镜像不存在，重新导入
docker load -i ~/pepgmp-backend-20251201.tar
docker load -i ~/pepgmp-frontend-20251201.tar
```

### 问题4: 文件权限问题

**解决方案**：
```bash
# 在 WSL2 中设置文件权限
cd ~/projects/Pyt
chmod 600 .env.production
chmod -R 755 config models
```

---

## 🎯 快速部署检查清单

- [ ] 镜像已导入到 WSL2（`docker images | grep pepgmp`）
- [ ] 项目文件在 WSL2 文件系统中（`~/projects/Pyt`）
- [ ] `.env.production` 配置文件已创建并配置
- [ ] Docker Compose 文件已准备好
- [ ] 1Panel 可以访问项目目录
- [ ] 端口未被占用（8000, 5432, 6379）
- [ ] 数据库密码和 Redis 密码已设置

---

## 📚 相关文档

- [WSL2 快速部署指南](WSL2_DEPLOYMENT_QUICK_START.md)
- [WSL2 Ubuntu 部署完整指南](WSL2_UBUNTU_DEPLOYMENT_GUIDE.md)
- [Docker Compose 配置](../docker-compose.prod.yml)

---

**最后更新**: 2025-12-01  
**适用版本**: 1Panel + WSL2 Ubuntu

