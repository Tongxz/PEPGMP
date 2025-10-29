# 部署指南

本指南是“人体行为检测系统”生产环境部署的权威操作手册。它将引导您完成从环境准备到服务启动、验证和日常维护的全过程。

---

## 1. 部署架构概览

本系统采用基于 Docker Compose 的容器化部署方案，其核心思想是 **服务分离**：

- **核心服务**: 由 `docker-compose.prod.yml` 文件管理，包含运行系统所必需的所有组件（如FastAPI应用、数据库、Redis等）。
- **MLOps服务**: 由 `docker-compose.prod.mlops.yml` 文件管理，提供可选但推荐的机器学习运维功能（如MLflow）。

这种分离式设计允许您根据需要，选择仅部署核心功能，或部署包含MLOps的全功能套件。

---

## 2. 环境准备

在开始部署之前，请确保您的服务器满足以下条件：

- **操作系统**: 推荐使用 Linux (Ubuntu 20.04 / 22.04 LTS)。
- **Docker**: 最新稳定版。 [安装指南](https://docs.docker.com/engine/install/)
- **Docker Compose**: 最新稳定版。 [安装指南](https://docs.docker.com/compose/install/)
- **NVIDIA GPU (推荐)**: 若要启用GPU加速，需要配备NVIDIA显卡。
- **NVIDIA 驱动**: 安装与您的显卡和CUDA版本兼容的最新驱动。
- **NVIDIA Container Toolkit**: 确保Docker可以利用GPU资源。 [安装指南](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

**验证环境**: 
```bash
# 1. 验证 Docker 和 Docker Compose
docker --version
docker-compose --version

# 2. 验证GPU和驱动 (如果使用GPU)
nvidia-smi

# 3. 验证Docker的GPU支持 (如果使用GPU)
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```
如果最后一条命令成功输出GPU信息，则环境准备就绪。

---

## 3. 部署步骤

### 步骤一：获取项目代码

```bash
git clone <your-project-repository-url>
cd <project-directory>
```

### 步骤二：创建并配置环境变量

部署配置通过根目录下的 `.env.prod` 文件进行管理。您需要从模板文件创建它。

```bash
# 从模板复制配置文件
cp config/production.env.example .env.prod
```

接下来，**必须编辑 `.env.prod` 文件**，填入您的生产环境配置。以下是关键配置项：

```dotenv
# .env.prod

# ===================================
# 数据库配置 (必须修改)
# ===================================
POSTGRES_DB=pyt_production
POSTGRES_USER=pyt_user
POSTGRES_PASSWORD=your_strong_and_secret_password # ‼️ 必须修改为一个强密码

# ===================================
# Redis 配置 (必须修改)
# ===================================
REDIS_PASSWORD=your_strong_redis_password # ‼️ 必须修改为一个强密码

# ===================================
# 应用安全配置 (必须修改)
# ===================================
SECRET_KEY=a_very_long_random_string_for_general_security # ‼️ 必须修改
JWT_SECRET=another_very_long_random_string_for_jwt # ‼️ 必须修改

# ===================================
# 服务端口 (可按需修改)
# ===================================
API_PORT=8000
FRONTEND_PORT=8080
MLFLOW_PORT=5000

# ===================================
# MLOps 配置 (可按需修改)
# ===================================
MLFLOW_TRACKING_URI=http://<your_server_ip>:5000

# ===================================
# 日志级别 (保持默认或按需修改)
# ===================================
LOG_LEVEL=INFO
```

### 步骤三：准备持久化目录

确保项目根目录下存在用于数据持久化的目录，如果不存在，请创建它们：

```bash
mkdir -p data models logs output
```

### 步骤四：拉取或构建Docker镜像

根据您的`docker-compose`文件配置，您可以选择从私有仓库拉取预构建的镜像，或在本地构建。

```bash
# 选项A: 从仓库拉取 (推荐)
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.mlops.yml pull

# 选项B: 在本地构建
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.mlops.yml build
```

### 步骤五：启动服务

我们分两步启动，以保证逻辑清晰。

**1. 启动核心服务:**

```bash
# -f 指定配置文件，-d 表示后台运行
docker-compose -f docker-compose.prod.yml up -d
```

**2. (可选) 启动MLOps服务:**

如果您需要实验跟踪功能，请执行此步骤。

```bash
docker-compose -f docker-compose.prod.mlops.yml up -d
```

---

## 4. 验证与访问

服务启动后，等待约1-2分钟让所有服务完成健康检查，然后进行验证。

### 步骤一：检查容器状态

```bash
# 检查核心服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查MLOps服务状态
docker-compose -f docker-compose.prod.mlops.yml ps
```
确保所有服务的 `State` 均为 `Up`，`Status` 显示为 `healthy`。

### 步骤二：访问服务

在浏览器中访问以下地址（请将 `your_server_ip` 替换为您的服务器IP地址）：

| 服务 | 访问地址 | 说明 |
| :--- | :--- | :--- |
| **前端界面** | `http://<your_server_ip>:8080` | 主要的用户操作界面。 |
| **API文档** | `http://<your_server_ip>:8000/docs` | 后端API的Swagger UI。 |
| **MLflow界面** | `http://<your_server_ip>:5000` | MLOps实验跟踪平台。 |

---

## 5. 日常维护与监控

### 查看服务日志

日志是排查问题的首要工具。

```bash
# 查看API服务的实时日志
docker-compose -f docker-compose.prod.yml logs -f api

# 查看MLflow服务的实时日志
docker-compose -f docker-compose.prod.mlops.yml logs -f mlflow

# 查看所有核心服务的日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 停止服务

```bash
# 停止并移除核心服务容器
docker-compose -f docker-compose.prod.yml down

# 停止并移除MLOps服务容器
docker-compose -f docker-compose.prod.mlops.yml down
```

### 数据备份

定期备份您的持久化数据至关重要。

```bash
# 定义备份目录
BACKUP_DIR="/path/to/your/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份数据库 (示例，具体取决于docker-compose中的卷名)
docker run --rm -v pyt_postgres_prod_data:/dbdata -v "$BACKUP_DIR":/backup alpine tar czf /backup/postgres_backup.tar.gz -C /dbdata .

# 备份模型、配置和MLflow实验数据
tar -czf "$BACKUP_DIR/models_backup.tar.gz" -C ./models .
tar -czf "$BACKUP_DIR/mlruns_backup.tar.gz" -C ./mlruns .
tar -czf "$BACKUP_DIR/config_backup.tar.gz" -C ./config .

echo "备份完成: $BACKUP_DIR"
```

---

## 6. 故障排除

- **问题：容器无法启动或状态为 `unhealthy`**
  - **解决方案**: 使用 `docker-compose logs <service_name>` 查看具体错误日志。常见原因包括：`.env.prod` 配置错误、端口被占用、数据库连接失败等。

- **问题：MLflow无法连接到数据库**
  - **解决方案**: 确认 `docker-compose.prod.mlops.yml` 中的数据库连接信息与 `docker-compose.prod.yml` 中的数据库服务配置及 `.env.prod` 文件完全一致。

- **问题：GPU在容器内不可用**
  - **解决方案**: 确保已正确安装NVIDIA驱动和NVIDIA Container Toolkit，并可成功运行环境准备中的验证命令。
