# 部署脚本对比说明

## 📋 两种部署脚本的区别

项目提供了两种生产环境启动脚本，适用于不同的部署场景：

---

## 1. `start_prod.sh` - 非容器化部署

### 用途
直接在 WSL Ubuntu 宿主机上运行应用（不使用 Docker 容器）

### 工作原理
- 使用 **Gunicorn** 直接在宿主机上运行 FastAPI 应用
- 需要宿主机已安装 Python 和所有依赖
- 只启动应用服务，**不启动数据库和 Redis**（需要单独运行）

### 前置要求

**必须满足：**
1. ✅ Python 3.10+ 已安装
2. ✅ 虚拟环境已创建并安装了所有依赖
3. ✅ Gunicorn 已安装：`pip install gunicorn`
4. ✅ 数据库（PostgreSQL）已运行并可访问
5. ✅ Redis 已运行并可访问
6. ✅ `.env.production` 配置文件已创建

### 执行流程

```bash
# 1. 复制项目到 WSL Ubuntu
cd ~/projects
git clone <repo> Pyt
cd Pyt

# 2. 安装 Python 和依赖
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install gunicorn

# 3. 配置环境变量
cp .env.production.example .env.production
nano .env.production  # 修改配置

# 4. 确保数据库和 Redis 已运行
# （需要单独启动 PostgreSQL 和 Redis，或使用 Docker Compose 只启动数据库服务）

# 5. 执行启动脚本
bash scripts/start_prod.sh
```

### 优点
- ✅ 性能最佳（无容器开销）
- ✅ 资源占用少
- ✅ 调试方便（直接在宿主机运行）

### 缺点
- ❌ 需要手动管理 Python 环境和依赖
- ❌ 需要单独启动数据库和 Redis
- ❌ 环境配置复杂
- ❌ 不同环境可能不一致

---

## 2. `start_prod_wsl.sh` - 容器化部署（推荐）

### 用途
使用 Docker Compose 启动所有服务（数据库、Redis、API）

### 工作原理
- 使用 **Docker Compose** 启动所有服务
- 所有服务都在容器内运行
- 可以在容器内执行 Python 脚本（即使宿主机没有 Python）

### 前置要求

**必须满足：**
1. ✅ Docker Desktop 已安装并启用 WSL2 集成
2. ✅ Docker Compose 可用
3. ✅ `.env.production` 配置文件已创建
4. ⚠️ Python（可选）：如果宿主机有 Python，会在宿主机执行脚本；如果没有，会在容器内执行

### 执行流程

```bash
# 1. 复制项目到 WSL Ubuntu（推荐放在 WSL2 文件系统）
cd ~/projects
git clone <repo> Pyt
cd Pyt

# 2. 配置环境变量
cp .env.production.example .env.production
nano .env.production  # 修改配置

# 3. 执行启动脚本（会自动启动所有服务）
bash scripts/start_prod_wsl.sh
```

**就这么简单！** 脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 验证配置文件
- ✅ 启动所有服务（数据库、Redis、API）
- ✅ 初始化数据库
- ✅ 显示服务状态

### 优点
- ✅ **部署简单**：一条命令启动所有服务
- ✅ **环境一致**：所有服务都在容器内，环境统一
- ✅ **易于管理**：使用 Docker Compose 统一管理
- ✅ **可选 Python**：宿主机不需要安装 Python（脚本会在容器内执行）
- ✅ **易于扩展**：可以轻松添加更多服务

### 缺点
- ⚠️ 需要 Docker Desktop（但这是现代部署的标准）
- ⚠️ 容器有轻微性能开销（但影响很小）

---

## 🎯 推荐方案

### 对于 WSL2 Ubuntu 部署，强烈推荐使用 `start_prod_wsl.sh`

**原因：**
1. ✅ **更简单**：一条命令完成所有部署
2. ✅ **更可靠**：所有服务统一管理，环境一致
3. ✅ **更灵活**：可以轻松添加或移除服务
4. ✅ **更现代**：符合容器化部署的最佳实践

---

## 📊 对比表

| 特性 | `start_prod.sh` | `start_prod_wsl.sh` |
|------|----------------|---------------------|
| **部署方式** | 宿主机直接运行 | Docker 容器化 |
| **需要 Python** | ✅ 必须 | ⚠️ 可选 |
| **需要 Docker** | ❌ 不需要 | ✅ 必须 |
| **启动数据库** | ❌ 需要手动 | ✅ 自动启动 |
| **启动 Redis** | ❌ 需要手动 | ✅ 自动启动 |
| **启动 API** | ✅ 自动 | ✅ 自动 |
| **环境一致性** | ⚠️ 依赖宿主机 | ✅ 容器内统一 |
| **部署复杂度** | ⚠️ 较高 | ✅ 较低 |
| **性能** | ✅ 最佳 | ⚠️ 略低（可忽略） |
| **推荐场景** | 高性能需求、已有数据库 | **生产环境部署（推荐）** |

---

## 🚀 快速开始

### 使用容器化部署（推荐）

```bash
# 1. 在 WSL2 Ubuntu 中克隆项目
cd ~/projects
git clone <repo> Pyt
cd Pyt

# 2. 创建配置文件
cp .env.production.example .env.production
nano .env.production  # 修改配置

# 3. 启动所有服务
bash scripts/start_prod_wsl.sh
```

**完成！** 所有服务会自动启动。

### 使用非容器化部署

```bash
# 1. 在 WSL2 Ubuntu 中克隆项目
cd ~/projects
git clone <repo> Pyt
cd Pyt

# 2. 安装 Python 和依赖
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install gunicorn

# 3. 创建配置文件
cp .env.production.example .env.production
nano .env.production  # 修改配置

# 4. 启动数据库和 Redis（使用 Docker Compose 或本地安装）
docker compose up -d database redis
# 或使用本地安装的 PostgreSQL 和 Redis

# 5. 启动应用
bash scripts/start_prod.sh
```

---

## ❓ 常见问题

### Q: 我应该使用哪个脚本？

**A:** 对于生产环境部署，推荐使用 `start_prod_wsl.sh`（容器化部署），因为：
- 部署更简单
- 环境更一致
- 管理更方便

### Q: 如果我只复制项目到 WSL Ubuntu，执行 `start_prod.sh` 能完成部署吗？

**A:** **不能完全完成**，因为 `start_prod.sh` 需要：
1. Python 环境已安装并配置
2. 所有依赖已安装（包括 Gunicorn）
3. 数据库和 Redis 已运行

你需要先完成这些前置步骤。

### Q: 如果我只复制项目到 WSL Ubuntu，执行 `start_prod_wsl.sh` 能完成部署吗？

**A:** **基本可以**，只需要：
1. Docker Desktop 已安装并启用 WSL2 集成
2. 创建 `.env.production` 配置文件

然后执行脚本即可，脚本会自动启动所有服务。

### Q: 两种方式可以混用吗？

**A:** 可以，例如：
- 使用 Docker Compose 启动数据库和 Redis
- 使用 `start_prod.sh` 在宿主机运行 API 服务

只需要在 `.env.production` 中配置正确的数据库和 Redis 连接地址。

---

**最后更新：** 2025-11-18



