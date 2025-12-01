# WSL2 Ubuntu 部署完整指南

## 📋 概述

本文档提供在 **Windows WSL2 环境下的 Ubuntu** 中部署本项目的完整步骤。所有操作都在 WSL2 的 Ubuntu 环境中执行。

**适用场景：**
- Windows 10/11 系统
- WSL2 已安装并配置 Ubuntu
- Docker Desktop 已安装并启用 WSL2 集成

---

## 🎯 部署架构

```
Windows 系统
  └── WSL2 (Ubuntu)
      ├── 项目代码 (Linux 文件系统: ~/projects/pyt)
      ├── Docker (通过 Docker Desktop WSL2 集成)
      └── Docker Compose 服务
          ├── PostgreSQL
          ├── Redis
          └── API 服务
```

---

## 🚀 完整部署步骤

### 第一步：环境准备

#### 1.1 检查 WSL2 和 Ubuntu

在 **Windows PowerShell**（管理员权限）中检查：

```powershell
# 检查 WSL 版本和已安装的发行版
wsl --list --verbose

# 应该看到类似输出：
#   NAME      STATE           VERSION
# * Ubuntu    Running         2
```

如果没有安装 Ubuntu，安装步骤：

```powershell
# 安装 Ubuntu（从 Microsoft Store 或命令行）
wsl --install -d Ubuntu

# 设置 WSL2 为默认版本
wsl --set-default-version 2

# 设置 Ubuntu 为默认发行版
wsl --set-default Ubuntu
```

#### 1.2 安装和配置 Docker Desktop

1. **下载并安装 Docker Desktop for Windows**
   - 下载地址：https://www.docker.com/products/docker-desktop
   - 安装时选择 **"Use WSL 2 based engine"**

2. **配置 Docker Desktop WSL2 集成**

   打开 Docker Desktop，进入 **Settings**：
   
   - **General** 标签：
     - ✅ 启用 "Use the WSL 2 based engine"
     - ✅ 启用 "Start Docker Desktop when you log in"（可选）
   
   - **Resources > WSL Integration** 标签：
     - ✅ 启用 "Enable integration with my default WSL distro"
     - ✅ 选择 "Ubuntu" 并启用集成

3. **验证 Docker 安装**

   在 **WSL2 Ubuntu** 终端中执行：

   ```bash
   # 检查 Docker 版本
   docker --version
   # 应该输出：Docker version 24.x.x 或更高
   
   # 检查 Docker Compose
   docker compose version
   # 应该输出：Docker Compose version v2.x.x 或更高
   
   # 测试 Docker 是否正常工作
   docker run hello-world
   # 应该看到 "Hello from Docker!" 消息
   ```

#### 1.3 优化 WSL2 资源配置（可选但推荐）

在 **Windows** 中创建或编辑 `%USERPROFILE%\.wslconfig`：

```ini
[wsl2]
# 内存限制（根据系统内存调整，建议至少 8GB）
memory=8GB

# CPU 核心数（根据系统调整，建议至少 4 核）
processors=4

# 交换空间
swap=2GB

# 启用本地端口转发
localhostForwarding=true

# 启用嵌套虚拟化（如果需要）
nestedVirtualization=false
```

保存后，重启 WSL2：

```powershell
# 在 Windows PowerShell 中执行
wsl --shutdown

# 然后重新打开 Ubuntu 终端
```

---

### 第二步：获取项目代码

#### 2.1 在 WSL2 Ubuntu 中克隆项目

**重要：** 将项目放在 WSL2 文件系统中（`~/projects/`），而不是 Windows 文件系统（`/mnt/c/...`），以获得最佳性能。

```bash
# 在 WSL2 Ubuntu 终端中执行

# 创建项目目录
mkdir -p ~/projects
cd ~/projects

# 克隆项目（替换为你的仓库地址）
git clone https://github.com/Tongxz/Pyt.git
# 或使用 SSH
# git clone git@github.com:Tongxz/Pyt.git

# 进入项目目录
cd Pyt
```

#### 2.2 检查项目结构

```bash
# 确认项目文件存在
ls -la

# 应该看到以下关键文件：
# - main.py
# - pyproject.toml
# - requirements.txt
# - docker-compose.yml
# - Dockerfile.prod
# - scripts/start_prod_wsl.sh
```

---

### 第三步：Python 环境（可选）

**重要说明：** 如果所有服务都通过 Docker 容器运行，**理论上不需要在 WSL2 Ubuntu 中安装 Python**。所有 Python 代码都在容器内执行。

但是，以下场景可能需要 Python：
- 运行启动脚本中的配置验证和数据库初始化（但这些可以在容器内执行）
- 本地开发和调试
- 运行管理工具脚本

#### 选项 A：完全容器化部署（推荐，不需要安装 Python）

如果只使用 Docker 容器运行服务，可以跳过 Python 安装。启动脚本会使用 `docker exec` 在容器内执行 Python 脚本。

**优点：**
- ✅ 环境更干净，不需要管理 Python 版本和依赖
- ✅ 避免宿主机和容器的依赖冲突
- ✅ 部署更简单

**缺点：**
- ❌ 无法在宿主机直接运行 Python 脚本
- ❌ 本地开发调试需要进入容器

#### 选项 B：安装 Python（用于本地开发和工具脚本）

如果需要本地运行 Python 脚本，可以安装 Python：

```bash
# 更新包列表
sudo apt update

# 安装 Python 3.10 和 pip
sudo apt install -y python3.10 python3.10-venv python3-pip

# 验证安装
python3 --version
# 应该输出：Python 3.10.x 或更高

pip3 --version
```

**创建虚拟环境（可选）：**

```bash
# 在项目根目录下创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 提示符应该变成：(venv) username@hostname:~/projects/Pyt$
```

**安装项目依赖（仅用于本地开发）：**

```bash
# 升级 pip
pip install --upgrade pip setuptools wheel

# 安装项目依赖（使用 pyproject.toml）
pip install -e .

# 验证关键依赖
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
```

**注意：** 如果需要 CUDA 支持的 PyTorch，需要单独安装：

```bash
# 卸载 CPU 版本的 PyTorch
pip uninstall torch torchvision torchaudio

# 安装 CUDA 版本的 PyTorch（CUDA 12.1）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 验证 CUDA 是否可用
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**推荐：** 对于生产环境部署，建议使用**选项 A（完全容器化）**，不需要在宿主机安装 Python。

---

### 第四步：配置环境变量

#### 4.1 创建生产环境配置文件

```bash
# 检查是否有示例配置文件
ls -la .env*

# 如果有 .env.production.example，复制它
if [ -f .env.production.example ]; then
    cp .env.production.example .env.production
else
    # 否则创建新的配置文件
    touch .env.production
fi

# 设置文件权限（仅所有者可读写）
chmod 600 .env.production
```

#### 4.2 编辑配置文件

```bash
# 使用你喜欢的编辑器编辑配置文件
nano .env.production
# 或
vim .env.production
# 或使用 VS Code（在 Windows 中）
code .env.production
```

**关键配置项：**

```env
# ==================== 环境设置 ====================
ENVIRONMENT=production
LOG_LEVEL=INFO

# ==================== API 配置 ====================
API_PORT=8000
API_HOST=0.0.0.0

# ==================== 数据库配置 ====================
# 使用 Docker Compose 中的服务名称作为主机名
DATABASE_URL=postgresql://pepgmp_prod:YOUR_STRONG_PASSWORD@database:5432/pepgmp_production

# ==================== Redis 配置 ====================
REDIS_URL=redis://:YOUR_STRONG_PASSWORD@redis:6379/0

# ==================== 安全配置 ====================
# 必须修改！生成强密钥
SECRET_KEY=YOUR_VERY_LONG_SECRET_KEY_MIN_32_CHARS_HERE
ADMIN_PASSWORD=YOUR_VERY_STRONG_PASSWORD_MIN_16_CHARS

# ==================== GPU 配置（如果使用）====================
CUDA_VISIBLE_DEVICES=0
DEVICE=cuda

# ==================== 其他配置 ====================
# 根据项目需要添加其他配置
```

**生成安全密钥：**

```bash
# 生成随机密钥（32 字符）
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成随机密码（16 字符）
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

### 第五步：配置 Docker Compose

#### 5.1 检查 Docker Compose 配置文件

```bash
# 检查生产环境配置文件
ls -la docker-compose*.yml

# 应该看到：
# - docker-compose.yml (开发环境)
# - docker-compose.prod.yml (生产环境，如果存在)
```

#### 5.2 创建或修改生产环境配置

如果 `docker-compose.prod.yml` 不存在，可以基于 `docker-compose.yml` 创建：

```bash
# 复制开发配置作为模板
cp docker-compose.yml docker-compose.prod.yml

# 编辑生产配置
nano docker-compose.prod.yml
```

**关键配置要点：**

1. **数据持久化**：使用 Docker volumes（推荐）或 WSL2 文件系统路径

   ```yaml
   volumes:
     # 方式1：使用 Docker volumes（推荐，性能最佳）
     postgres_prod_data:
       driver: local
     redis_prod_data:
       driver: local
     
     # 方式2：使用 WSL2 文件系统路径（如果需要直接访问文件）
     # - ~/docker-data/pyt/postgres:/var/lib/postgresql/data
     # - ~/docker-data/pyt/redis:/data
   ```

2. **网络配置**：确保服务间可以通信

   ```yaml
   networks:
     backend:
       driver: bridge
   ```

3. **环境变量**：从 `.env.production` 加载

   ```yaml
   services:
     api:
       env_file:
         - .env.production
   ```

---

### 第六步：初始化数据库

#### 6.1 启动数据库服务

```bash
# 只启动数据库和 Redis（不启动 API）
docker compose -f docker-compose.prod.yml up -d database redis

# 等待服务就绪（约 10-30 秒）
sleep 10

# 检查服务状态
docker compose -f docker-compose.prod.yml ps
```

#### 6.2 运行数据库迁移

**方式 A：在容器内执行（推荐，不需要宿主机 Python）**

```bash
# 等待 API 容器启动（如果还没有）
docker compose -f docker-compose.prod.yml up -d api

# 等待容器就绪
sleep 10

# 在容器内执行数据库初始化
docker exec pepgmp-api-prod python scripts/init_database.py

# 或运行迁移脚本（如果存在）
if [ -f scripts/migrations/run_migration_002.py ]; then
    docker exec pepgmp-api-prod python scripts/migrations/run_migration_002.py
fi
```

**方式 B：在宿主机执行（需要安装 Python）**

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 运行数据库初始化脚本（如果存在）
if [ -f scripts/init_database.py ]; then
    python scripts/init_database.py
fi

# 或运行迁移脚本（如果存在）
if [ -f scripts/migrations/run_migration_002.py ]; then
    python scripts/migrations/run_migration_002.py
fi
```

#### 6.3 验证数据库连接

**方式 A：在容器内执行（推荐）**

```bash
# 测试数据库连接
docker exec pepgmp-api-prod python -c "
import os
import asyncpg
import asyncio

async def test_db():
    db_url = os.getenv('DATABASE_URL', 'postgresql://pepgmp_prod:password@database:5432/pepgmp_production')
    conn = await asyncpg.connect(db_url)
    result = await conn.fetchval('SELECT version()')
    print(f'PostgreSQL version: {result}')
    await conn.close()

asyncio.run(test_db())
"
```

**方式 B：在宿主机执行（需要安装 Python）**

```bash
# 测试数据库连接
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.production')
import asyncpg
import asyncio

async def test_db():
    db_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(db_url)
    result = await conn.fetchval('SELECT version()')
    print(f'PostgreSQL version: {result}')
    await conn.close()

asyncio.run(test_db())
"
```

---

### 第七步：启动服务

#### 7.1 使用启动脚本（推荐）

```bash
# 确保在项目根目录
cd ~/projects/Pyt

# 如果安装了 Python 和虚拟环境，可以激活（可选）
# source venv/bin/activate

# 运行 WSL 启动脚本
bash scripts/start_prod_wsl.sh
```

启动脚本会自动：
- ✅ 检查 WSL 环境
- ✅ 检查 Docker 是否运行
- ✅ 验证配置文件（在容器内或宿主机执行）
- ✅ 检查端口占用
- ✅ 启动所有服务
- ✅ 初始化数据库（在容器内执行）

**注意：** 启动脚本会尝试在宿主机执行 Python 脚本，如果宿主机没有 Python，脚本会使用 `docker exec` 在容器内执行。

#### 7.2 手动启动（如果脚本不可用）

```bash
# 构建生产镜像
docker build -f Dockerfile.prod -t pyt-api:latest .

# 启动所有服务
docker compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api
```

---

### 第八步：验证部署

#### 8.1 健康检查

```bash
# 在 WSL2 Ubuntu 中测试
curl http://localhost:8000/api/v1/monitoring/health

# 应该返回 JSON 响应：
# {"status":"healthy","timestamp":"..."}
```

#### 8.2 检查 API 文档

在 **Windows 浏览器** 中访问：

```
http://localhost:8000/docs
```

应该看到 FastAPI 的 Swagger UI 文档界面。

#### 8.3 检查服务状态

```bash
# 查看所有容器状态
docker compose -f docker-compose.prod.yml ps

# 应该看到所有服务都是 "Up" 状态：
# NAME                    STATUS          PORTS
# pepgmp-api-prod         Up              0.0.0.0:8000->8000/tcp
# pepgmp-postgres-prod    Up              5432/tcp
# pepgmp-redis-prod       Up              6379/tcp
```

#### 8.4 查看日志

```bash
# 查看 API 服务日志
docker compose -f docker-compose.prod.yml logs -f api

# 查看所有服务日志
docker compose -f docker-compose.prod.yml logs -f

# 查看最近 100 行日志
docker compose -f docker-compose.prod.yml logs --tail=100 api
```

---

## 🔧 性能优化

### 1. WSL2 文件系统性能

**关键建议：将项目放在 WSL2 文件系统中**

- ✅ **推荐**：`~/projects/Pyt`（WSL2 文件系统）
- ❌ **避免**：`/mnt/c/Users/.../Pyt`（Windows 文件系统，性能差）

### 2. Docker 数据存储

**推荐使用 Docker volumes：**

```yaml
volumes:
  postgres_prod_data:
    driver: local
  redis_prod_data:
    driver: local
```

**优势：**
- 性能最佳（存储在 WSL2 虚拟磁盘中）
- 自动管理，无需手动创建目录
- 跨平台兼容

### 3. WSL2 资源配置

编辑 `%USERPROFILE%\.wslconfig`：

```ini
[wsl2]
memory=8GB          # 根据系统内存调整
processors=4        # CPU 核心数
swap=2GB
localhostForwarding=true
```

重启 WSL2：`wsl --shutdown`

---

## 🛡️ 安全建议

### 1. 文件权限

```bash
# .env.production 权限（仅所有者可读写）
chmod 600 .env.production

# 日志目录权限
chmod 755 logs/
```

### 2. 密码管理

- ✅ 使用强密码（至少 16 字符）
- ✅ 使用密码管理器
- ✅ 定期轮换密码
- ❌ 不要在代码中硬编码密码

### 3. 网络安全

```yaml
# 只暴露必要的端口
ports:
  - "8000:8000"  # API
  # 不暴露数据库和 Redis 端口到外部
```

---

## ⚠️ 常见问题排查

### 1. Docker 无法启动

**问题：** `docker: command not found` 或 `Cannot connect to the Docker daemon`

**解决方案：**

```bash
# 1. 确保 Docker Desktop 正在运行（在 Windows 中）
# 2. 检查 WSL2 集成是否启用
# 3. 重启 Docker Desktop
# 4. 在 WSL2 中测试
docker run hello-world
```

### 2. 端口已被占用

**问题：** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**解决方案：**

```bash
# 查找占用端口的进程
sudo lsof -i :8000
# 或
sudo netstat -tulpn | grep :8000

# 停止占用进程
sudo kill -9 <PID>

# 或停止所有 Docker 容器
docker compose -f docker-compose.prod.yml down
```

### 3. 数据库连接失败

**问题：** `Connection refused` 或 `Connection timeout`

**解决方案：**

```bash
# 1. 检查数据库容器是否运行
docker compose -f docker-compose.prod.yml ps database

# 2. 检查数据库日志
docker compose -f docker-compose.prod.yml logs database

# 3. 测试数据库连接
docker exec -it pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production

# 4. 检查 DATABASE_URL 配置是否正确
grep DATABASE_URL .env.production
```

### 4. 文件权限问题

**问题：** `Permission denied` 或 `Cannot access file`

**解决方案：**

```bash
# 检查文件权限
ls -la .env.production

# 修复权限
chmod 600 .env.production
chmod 755 logs/
chmod 755 output/
```

### 5. 性能问题

**问题：** 文件 I/O 性能差，服务响应慢

**解决方案：**

1. **确保项目在 WSL2 文件系统中：**
   ```bash
   # 检查当前路径
   pwd
   # 应该在 ~/projects/Pyt 而不是 /mnt/c/...
   ```

2. **使用 Docker volumes 而不是 bind mounts**

3. **优化 WSL2 资源配置**（见上文）

---

## 📊 监控和维护

### 1. 查看服务状态

```bash
# 查看所有容器状态
docker compose -f docker-compose.prod.yml ps

# 查看资源使用
docker stats
```

### 2. 查看日志

```bash
# 实时查看 API 日志
docker compose -f docker-compose.prod.yml logs -f api

# 查看最近 100 行日志
docker compose -f docker-compose.prod.yml logs --tail=100 api

# 查看特定时间段的日志
docker compose -f docker-compose.prod.yml logs --since 1h api
```

### 3. 备份数据

```bash
# 备份数据库
docker exec pepgmp-postgres-prod pg_dump -U pepgmp_prod pepgmp_production > backup_$(date +%Y%m%d).sql

# 备份 Redis
docker exec pepgmp-redis-prod redis-cli --rdb /data/backup.rdb
```

---

## 🔄 更新部署

### 1. 更新代码

```bash
# 在项目目录中
cd ~/projects/Pyt

# 拉取最新代码
git pull origin develop

# 重新构建镜像
docker build -f Dockerfile.prod -t pyt-api:latest .

# 重启服务
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

### 2. 滚动更新（零停机）

```bash
# 使用健康检查和滚动更新
docker compose -f docker-compose.prod.yml up -d --no-deps api

# 等待新容器健康检查通过后，旧容器会自动停止
```

---

## 📚 快速参考

### 常用命令

```bash
# 启动服务
docker compose -f docker-compose.prod.yml up -d

# 停止服务
docker compose -f docker-compose.prod.yml down

# 重启服务
docker compose -f docker-compose.prod.yml restart api

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api

# 进入容器
docker exec -it pepgmp-api-prod bash

# 健康检查
curl http://localhost:8000/api/v1/monitoring/health
```

### 服务访问地址

- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/monitoring/health

---

## 🎯 最佳实践总结

1. ✅ **在 WSL2 Ubuntu 环境中部署**（不是 Windows PowerShell）
2. ✅ **将项目放在 WSL2 文件系统中**（`~/projects/Pyt`）
3. ✅ **使用 Docker volumes 存储数据**（性能最佳）
4. ✅ **启用 Docker Desktop WSL2 集成**
5. ✅ **使用强密码和安全的文件权限**
6. ✅ **定期备份数据**
7. ✅ **监控资源使用和日志**
8. ✅ **使用健康检查确保服务可用性**

---

**最后更新：** 2025-11-18

