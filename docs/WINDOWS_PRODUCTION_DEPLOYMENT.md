# Windows WSL 生产环境部署指南

## 📋 概述

本文档介绍在 **Windows WSL (Windows Subsystem for Linux)** 环境中部署生产环境的方案。所有部署操作都在 WSL 的 Linux 环境中执行，使用标准的 Linux 工具和命令。

## 🎯 部署架构

### WSL 部署架构

```
Windows 系统
  └── WSL2 (Linux 环境)
      ├── Docker (通过 Docker Desktop WSL2 集成)
      ├── 项目代码 (Linux 文件系统)
      └── Docker Compose 服务
          ├── PostgreSQL
          ├── Redis
          └── API 服务
```

### 为什么使用 WSL？

**优势：**
- ✅ **性能接近原生 Linux**：WSL2 使用真实的 Linux 内核
- ✅ **完整的 Linux 工具链**：可以使用所有 Linux 命令和工具
- ✅ **文件系统性能好**：WSL2 文件系统性能优于 Windows 路径挂载
- ✅ **与 Windows 集成**：可以同时访问 Windows 和 Linux 文件系统
- ✅ **Docker 集成**：Docker Desktop 原生支持 WSL2 后端

## 🚀 部署步骤

### 1. 环境准备

#### 1.1 安装 WSL2

```powershell
# 以管理员身份运行 PowerShell
wsl --install

# 或手动安装
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 重启后，设置 WSL2 为默认版本
wsl --set-default-version 2
```

#### 1.2 安装 Docker Desktop

1. 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. 安装时选择 **"Use WSL 2 based engine"**
3. 在 Settings > General 中启用：
   - ✅ Use the WSL 2 based engine
   - ✅ Start Docker Desktop when you log in

#### 1.3 验证安装

```powershell
# 检查 WSL2
wsl --list --verbose

# 检查 Docker
docker --version
docker-compose --version

# 或 Docker Compose V2
docker compose version
```

### 2. 项目配置

#### 2.1 创建生产环境配置文件

```powershell
# 复制示例配置
Copy-Item .env.production.example .env.production

# 编辑配置（使用你喜欢的编辑器）
notepad .env.production
# 或
code .env.production
```

#### 2.2 配置关键参数

```env
# 数据库配置（使用 Docker 容器名称）
DATABASE_URL=postgresql://pyt_prod:YOUR_STRONG_PASSWORD@pyt-postgres-prod:5432/pyt_production

# Redis 配置
REDIS_URL=redis://:YOUR_STRONG_PASSWORD@pyt-redis-prod:6379/0

# API 配置
API_PORT=8000
ENVIRONMENT=production

# 安全配置（必须修改！）
SECRET_KEY=YOUR_VERY_LONG_SECRET_KEY_MIN_32_CHARS
ADMIN_PASSWORD=YOUR_VERY_STRONG_PASSWORD_MIN_16_CHARS
```

#### 2.3 设置文件权限

```powershell
# 限制 .env.production 访问权限
icacls .env.production /inheritance:r /grant:r "${env:USERNAME}:(R)"
```

### 3. 数据持久化配置

#### 3.1 推荐：使用 Docker Volumes（最佳性能）

在 `docker-compose.prod.yml` 中使用命名 volumes：

```yaml
volumes:
  postgres_prod_data:
    driver: local
  redis_prod_data:
    driver: local
  app_logs:
    driver: local
  app_output:
    driver: local
```

**优势：**
- ✅ 性能最佳（存储在 WSL2 虚拟磁盘中）
- ✅ 自动管理，无需手动创建目录
- ✅ 跨平台兼容

#### 3.2 备选：使用 WSL2 文件系统路径

如果需要直接访问文件，使用 WSL2 文件系统路径：

```yaml
volumes:
  # 使用 WSL2 文件系统路径（推荐）
  - ~/docker-data/pyt/postgres:/var/lib/postgresql/data
  - ~/docker-data/pyt/redis:/data
  - ~/docker-data/pyt/logs:/app/logs
  - ~/docker-data/pyt/output:/app/output
```

**⚠️ 重要提示：**
- ✅ 使用 WSL2 文件系统路径（`~/` 或 `/home/username/`）
- ❌ **避免**使用 Windows 路径（`/mnt/c/...`），性能很差
- 确保路径存在：`mkdir -p ~/docker-data/pyt/{postgres,redis,logs,output}`

#### 3.3 推荐目录结构（WSL2 文件系统）

```bash
~/docker-data/
└── pyt/
    ├── postgres/      # PostgreSQL 数据
    ├── redis/         # Redis 数据
    ├── logs/          # 应用日志
    ├── output/        # 输出文件
    └── models/        # 模型文件
```

### 4. 启动服务

#### 4.1 方式一：从 Windows PowerShell 启动（推荐）

```powershell
# 在 Windows PowerShell 中运行（会自动切换到 WSL）
.\scripts\start_prod_wsl.ps1
```

这个脚本会：
- 检查 WSL 是否安装
- 检查 Docker Desktop WSL 集成
- 自动切换到 WSL 并执行 bash 脚本

#### 4.2 方式二：直接在 WSL 中启动

```bash
# 在 WSL 终端中运行
cd /mnt/c/path/to/project  # 或使用 WSL 文件系统中的路径
bash scripts/start_prod_wsl.sh
```

#### 4.3 手动启动（在 WSL 中）

```bash
# 在 WSL 终端中执行

# 构建镜像
docker build -f Dockerfile.prod -t pyt-api:latest .

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
```

### 5. 验证部署

**在 WSL 中验证：**
```bash
# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

**在 Windows PowerShell 中验证：**
```powershell
# 健康检查
Invoke-WebRequest -Uri http://localhost:8000/api/v1/monitoring/health

# 或使用 curl（如果已安装）
curl http://localhost:8000/api/v1/monitoring/health
```

## 🔧 性能优化建议

### 1. WSL2 性能优化

#### 1.1 文件系统性能（重要！）

**关键建议：将项目放在 WSL2 文件系统中**

**问题：** 如果项目在 Windows 文件系统（`/mnt/c/...`），性能会显著下降

**解决方案：**
- ✅ **推荐**：将项目复制到 WSL2 文件系统（`~/projects/pyt` 或 `/home/username/projects/pyt`）
- ✅ 使用 Docker volumes 存储数据（性能最好）
- ❌ **避免**：直接在 `/mnt/c/...` 路径下运行项目

**迁移项目到 WSL2 文件系统：**
```bash
# 在 WSL 中执行
# 1. 创建项目目录
mkdir -p ~/projects
cd ~/projects

# 2. 从 Windows 路径复制项目（如果需要）
# 或者直接 git clone
git clone <your-repo-url> pyt
cd pyt

# 3. 后续所有操作都在 WSL2 文件系统中进行
```

#### 1.2 WSL2 资源配置

创建或编辑 `%USERPROFILE%\.wslconfig`：

```ini
[wsl2]
memory=8GB          # 根据系统内存调整
processors=4         # CPU 核心数
swap=2GB
localhostForwarding=true
```

重启 WSL2：
```powershell
wsl --shutdown
```

### 2. Docker Desktop 优化

#### 2.1 启用 WSL2 后端（必须！）

在 Docker Desktop Settings > General 中：
- ✅ **必须启用**："Use the WSL 2 based engine"
- ✅ "Start Docker Desktop when you log in"（可选）

#### 2.2 启用 WSL 集成

在 Docker Desktop Settings > Resources > WSL Integration 中：
- ✅ 启用 "Enable integration with my default WSL distro"
- ✅ 选择要集成的 Linux 发行版（如 Ubuntu）
- ✅ 确保你的 WSL 发行版已启用

#### 2.3 资源限制

在 Docker Desktop Settings > Resources 中设置：
- **CPUs**: 根据系统调整（建议至少 4 核）
- **Memory**: 建议至少 8GB（根据系统内存调整）
- **Swap**: 2GB
- **Disk image size**: 根据数据量调整

### 3. 网络性能

#### 3.1 使用 Docker 网络

```yaml
networks:
  backend:
    driver: bridge
    internal: true  # 内部网络，不暴露到外部
```

#### 3.2 避免端口冲突

```powershell
# 检查端口占用
netstat -ano | findstr :8000

# 停止占用进程
Stop-Process -Id <PID> -Force
```

## 🛡️ 安全建议

### 1. 文件权限

```powershell
# .env.production 权限
icacls .env.production /inheritance:r /grant:r "${env:USERNAME}:(R)"

# 日志目录权限
icacls C:\docker-data\pyt\logs /inheritance:r /grant:r "${env:USERNAME}:(F)"
```

### 2. 防火墙配置

```powershell
# 允许 Docker 通过防火墙
New-NetFirewallRule -DisplayName "Docker" -Direction Inbound -Program "C:\Program Files\Docker\Docker\resources\dockerd.exe" -Action Allow
```

### 3. 密码管理

- ✅ 使用强密码（至少 16 字符）
- ✅ 使用密码管理器
- ✅ 定期轮换密码
- ❌ 不要在代码中硬编码密码

### 4. 网络安全

```yaml
# 只暴露必要的端口
ports:
  - "8000:8000"  # API
  # 不暴露数据库和 Redis 端口到外部
```

## 📊 监控和维护

### 1. 日志管理

```powershell
# 查看容器日志
docker-compose -f docker-compose.prod.yml logs -f api

# 查看特定时间段的日志
docker-compose -f docker-compose.prod.yml logs --since 1h api

# 导出日志
docker-compose -f docker-compose.prod.yml logs api > logs/api-$(Get-Date -Format "yyyyMMdd-HHmmss").log
```

### 2. 资源监控

```powershell
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df
```

### 3. 备份策略

```powershell
# 备份数据库
docker exec pyt-postgres-prod pg_dump -U pyt_prod pyt_production > backup_$(Get-Date -Format "yyyyMMdd").sql

# 备份 Redis
docker exec pyt-redis-prod redis-cli --rdb /data/backup.rdb
```

## ⚠️ 常见问题

### 1. 端口占用

**问题：** 端口已被占用

**解决方案：**
```powershell
# 查找占用进程
netstat -ano | findstr :8000

# 停止进程
Stop-Process -Id <PID> -Force
```

### 2. 文件权限问题

**问题：** Docker 无法访问 Windows 路径

**解决方案：**
- 使用 Docker volumes 而不是 bind mounts
- 确保路径存在且权限正确
- 使用 WSL2 文件系统路径

### 3. 性能问题

**问题：** 文件 I/O 性能差

**解决方案：**
- 将数据放在 WSL2 文件系统中
- 使用 Docker volumes
- 优化 WSL2 资源配置

### 4. 网络连接问题

**问题：** 容器无法访问外部网络

**解决方案：**
```powershell
# 重启 Docker Desktop
# 或重置网络
wsl --shutdown
# 然后重启 Docker Desktop
```

## 🔄 更新部署

### 1. 滚动更新

```powershell
# 构建新镜像
docker build -f Dockerfile.prod -t pyt-api:latest .

# 停止旧容器
docker-compose -f docker-compose.prod.yml stop api

# 启动新容器
docker-compose -f docker-compose.prod.yml up -d api
```

### 2. 零停机更新

```powershell
# 使用健康检查和滚动更新
docker-compose -f docker-compose.prod.yml up -d --no-deps api
```

## 📚 参考资源

- [Docker Desktop for Windows 文档](https://docs.docker.com/desktop/windows/)
- [WSL2 文档](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

## 🎯 最佳实践总结

1. ✅ **在 WSL2 环境中部署**（不是 Windows PowerShell）
2. ✅ **将项目放在 WSL2 文件系统中**（`~/projects/` 而不是 `/mnt/c/...`）
3. ✅ **使用 Docker volumes 存储数据**（性能最佳）
4. ✅ **启用 Docker Desktop WSL2 集成**
5. ✅ **使用强密码和安全的文件权限**
6. ✅ **定期备份数据**
7. ✅ **监控资源使用和日志**
8. ✅ **使用健康检查确保服务可用性**
9. ✅ **定期更新 WSL、Docker 和系统**

## 📝 快速参考

### 启动服务

**从 Windows PowerShell：**
```powershell
.\scripts\start_prod_wsl.ps1
```

**在 WSL 中：**
```bash
bash scripts/start_prod_wsl.sh
```

### 常用命令（在 WSL 中执行）

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart api

# 进入容器
docker exec -it pyt-api-prod bash
```

---

**最后更新：** 2025-11-20

