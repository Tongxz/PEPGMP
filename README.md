# 人体行为检测系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/Framework-FastAPI-green.svg" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/AI-PyTorch-orange.svg" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="License: MIT"/>
</p>

一个基于深度学习的企业级实时人体行为检测系统，专注于工业环境中的安全合规监控。支持发网佩戴、洗手行为等多种场景的智能识别与分析。

---

## ✨ 核心功能

- **多目标实时检测**: 基于YOLOv8的高性能人体检测，并支持GPU加速。
- **多行为复合识别**: 支持发网佩戴、洗手、手部消毒等多种行为的复合检测。
- **高精度姿态分析**: 集成MediaPipe和YOLOv8-Pose，实现高精度姿态估计。
- **可配置监控区域**: 支持自定义多边形监控区域，专注于关键区域的检测。
- **企业级部署**: 提供完整的Docker和Docker Compose部署方案，支持生产环境。
- **完善的API**: 提供丰富的RESTful API和WebSocket接口，易于集成。

## 🚀 快速上手

本项目提供两种部署方式：**开发环境**和**生产环境**。您可以根据需求选择合适的方式。

### 前提条件

- **必需**:
  - Python 3.10+
  - [Docker Desktop](https://www.docker.com/) (用于运行PostgreSQL和Redis)
  - Git

- **推荐**:
  - Node.js 20+ (前端开发)

---

## 🛠️ 开发环境启动

开发环境适合日常开发、调试和测试。启动脚本会自动处理所有依赖服务的启动。

### 1. 克隆项目并准备环境

```bash
# 克隆项目
git clone <your-project-repository-url>
cd <project-directory>

# 创建并激活虚拟环境（如果还没有）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 配置开发环境

```bash
# 从模板创建.env文件（如果不存在）
cp .env.example .env

# 编辑.env文件，设置开发环境配置
# 重要：确保 ENVIRONMENT=development
nano .env  # 或使用您喜欢的编辑器
```

**关键配置项** (`.env`):
```bash
# 环境设置
ENVIRONMENT=development  # ⚠️ 必须设置为development
LOG_LEVEL=DEBUG

# 数据库配置（开发环境使用Docker容器）
DATABASE_URL=postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development

# Redis配置（开发环境使用Docker容器）
REDIS_URL=redis://:pyt_dev_redis@localhost:6379/0

# API配置
API_PORT=8000
```

### 3. 启动开发服务

```bash
# 使用开发启动脚本（推荐）
bash scripts/start_dev.sh
```

**启动脚本会自动：**
- ✅ 检查并激活虚拟环境
- ✅ 检查并安装依赖（如python-dotenv）
- ✅ 自动启动Docker容器（PostgreSQL、Redis）
- ✅ 验证配置文件
- ✅ 启动后端API服务

**手动启动方式**（如果不想使用启动脚本）：

```bash
# 1. 启动Docker服务
docker-compose up -d database redis

# 2. 等待服务就绪（约10秒）
sleep 10

# 3. 启动后端
source venv/bin/activate
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 启动前端（可选）

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动前端开发服务器
npm run dev
```

### 5. 访问服务

服务启动后，您可以访问：
- **前端界面**: `http://localhost:5173`
- **后端API**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs`
- **健康检查**: `http://localhost:8000/health`

---

## 🚀 生产环境启动

生产环境使用Gunicorn多进程模式，适合正式部署。

### 1. 准备生产环境

```bash
# 克隆项目
git clone <your-project-repository-url>
cd <project-directory>

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate
```

### 2. 配置生产环境

```bash
# 从模板创建生产环境配置
cp .env.production.example .env.production

# 编辑生产配置（⚠️ 必须修改密码和密钥）
nano .env.production  # 或使用您喜欢的编辑器

# 设置安全权限
chmod 600 .env.production
```

**关键配置项** (`.env.production`):
```bash
# 环境设置
ENVIRONMENT=production  # ⚠️ 必须设置为production
LOG_LEVEL=INFO

# 数据库配置（生产环境）
DATABASE_URL=postgresql://pyt_prod:STRONG_PASSWORD@production-db:5432/pyt_production

# Redis配置（生产环境）
REDIS_URL=redis://:STRONG_PASSWORD@production-redis:6379/0

# API配置
API_PORT=8000
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120

# 安全配置（⚠️ 必须修改为强随机值）
SECRET_KEY=your-strong-secret-key-64-chars-long
JWT_SECRET_KEY=your-jwt-secret-key
ADMIN_PASSWORD=your-strong-admin-password
```

**⚠️ 重要安全提示**：
- 生产环境密码必须使用强随机密码（至少32字符）
- 使用 `scripts/generate_production_secrets.py` 生成安全密钥
- 不要将 `.env.production` 提交到Git
- 设置文件权限为 `600`（仅所有者可读写）

### 3. 生成生产密钥（推荐）

```bash
# 使用脚本生成强随机密码和密钥
python scripts/generate_production_secrets.py

# 输出将包含所有必需的配置项，复制到.env.production
```

### 4. 启动生产服务

```bash
# 使用生产启动脚本（推荐）
bash scripts/start_prod.sh
```

**启动脚本会：**
- ✅ 检查 `.env.production` 文件是否存在
- ✅ 验证文件权限（建议600）
- ✅ 设置 `ENVIRONMENT=production`
- ✅ 加载生产环境配置
- ✅ 验证配置完整性
- ✅ 检查依赖服务（数据库、Redis）连通性
- ✅ 使用Gunicorn启动多进程服务

**手动启动方式**：

```bash
# 1. 设置环境变量
export ENVIRONMENT=production
source .env.production

# 2. 验证配置
python scripts/validate_config.py

# 3. 启动服务（使用Gunicorn）
gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### 5. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 查看日志
tail -f logs/access.log
tail -f logs/error.log
```

---

## 📋 配置文件说明

### 开发环境配置文件

| 文件 | 用途 | 是否提交到Git |
|------|------|--------------|
| `.env` | 开发环境实际配置（包含密码） | ❌ 不提交 |
| `.env.example` | 开发环境配置模板 | ✅ 提交 |

**配置示例** (`.env`):
```bash
ENVIRONMENT=development
DATABASE_URL=postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development
REDIS_URL=redis://:pyt_dev_redis@localhost:6379/0
```

### 生产环境配置文件

| 文件 | 用途 | 是否提交到Git |
|------|------|--------------|
| `.env.production` | 生产环境实际配置（包含密码） | ❌ 不提交 |
| `.env.production.example` | 生产环境配置模板 | ✅ 提交 |

**配置示例** (`.env.production`):
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://pyt_prod:STRONG_PASSWORD@prod-db:5432/pyt_production
REDIS_URL=redis://:STRONG_PASSWORD@prod-redis:6379/0
```

### ⚠️ 重要注意事项

1. **环境变量优先级**：
   - 如果设置了 `ENVIRONMENT=production`，系统会自动加载 `.env.production`
   - 如果设置了 `ENVIRONMENT=development`，系统只加载 `.env`
   - **建议**：在 `.env` 中显式设置 `ENVIRONMENT=development`，避免意外加载生产配置

2. **Docker主机名 vs localhost**：
   - 开发环境（本地运行）：使用 `localhost`
   - 生产环境（Docker容器内）：使用容器服务名（如 `database`、`redis`）
   - **示例**：
     ```bash
     # 开发环境
     DATABASE_URL=postgresql://user:pass@localhost:5432/db

     # 生产环境（Docker内部）
     DATABASE_URL=postgresql://user:pass@database:5432/db
     ```

3. **配置文件加载顺序**：
   ```
   1. .env (默认)
   2. .env.{ENVIRONMENT} (如果ENVIRONMENT设置了)
   3. .env.local (本地覆盖，不提交)
   ```

4. **备份文件清理**：
   - 所有 `.env.bak.*` 文件都是备份，可以安全删除
   - 有Git历史记录，不需要本地备份

### 快照存储配置

新增检测快照持久化后，可通过以下环境变量控制存储行为：

| 环境变量 | 默认值 | 作用 |
|----------|--------|------|
| `SNAPSHOT_BASE_DIR` | `datasets/raw` | 快照根目录，建议使用绝对路径确保多进程可见 |
| `SNAPSHOT_IMAGE_FORMAT` | `jpg` | 保存格式，支持 `jpg` / `png` |
| `SNAPSHOT_IMAGE_QUALITY` | `90` | JPEG 图像质量（1-100），数值越大画质越好文件越大 |

> ⚠️ 建议确保目录具有写入权限，并纳入备份策略。

### 数据集生成配置

通过 MLOps 接口生成训练数据集时，可使用以下环境变量定制输出位置及标注文件：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DATASET_OUTPUT_DIR` | `datasets/exports` | 自动生成数据集的根目录 |
| `DATASET_ANNOTATION_FORMAT` | `csv` | 当前支持 `csv` |
| `DATASET_ANNOTATION_FILENAME` | `annotations.csv` | 标注文件名称 |

接口会将检测快照拷贝至 `images/` 子目录，并生成 `annotations.csv` 描述快照与违规信息。

### 模型训练配置

工作流中的“模型训练”步骤会读取自动生成的数据集并输出基于 YOLOv8 的分类模型，可通过以下环境变量调整行为：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MODEL_TRAINING_OUTPUT_DIR` | `models/mlops` | 训练得到的模型文件保存目录 |
| `MODEL_TRAINING_REPORT_DIR` | `models/mlops/reports` | 训练报告输出目录 |
| `MODEL_TRAINING_TEST_SIZE` | `0.2` | 训练/验证集划分比例 |
| `MODEL_TRAINING_RANDOM_STATE` | `42` | 随机种子，保证可复现 |
| `YOLO_TRAIN_MODEL` | `yolov8n-cls.pt` | YOLO 预训练分类权重 |
| `YOLO_TRAIN_EPOCHS` | `30` | 训练轮数 |
| `YOLO_TRAIN_IMAGE_SIZE` | `224` | 输入图像尺寸 |
| `YOLO_TRAIN_BATCH_SIZE` | `32` | 批大小 |
| `YOLO_TRAIN_DEVICE` | `auto` | 训练设备 (`cuda`, `cpu` 或 `auto`) |
| `YOLO_TRAIN_PATIENCE` | `10` | 早停策略的容忍轮数 |

### 洗手工作流配置

洗手合规训练工作流依赖额外的会话元数据与时序训练配置，可通过以下环境变量调整：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `HANDWASH_SESSION_DIR` | `data/handwash/sessions` | 洗手会话元数据与视频的根目录 |
| `HANDWASH_DATASET_OUTPUT_DIR` | `datasets/handwash` | 洗手数据集输出目录 |
| `HANDWASH_FRAME_INTERVAL` | `0.5` | 姿态采样间隔（秒） |
| `HANDWASH_MIN_SESSION_DURATION` | `3.0` | 参与训练的最小时长限制（秒） |
| `HANDWASH_MAX_SESSIONS` | `200` | 单次生成允许的最大会话数 |
| `HANDWASH_TRAINING_OUTPUT_DIR` | `models/handwash` | 洗手模型权重存储路径 |
| `HANDWASH_TRAINING_REPORT_DIR` | `models/handwash/reports` | 洗手训练报告目录 |
| `HANDWASH_TRAINING_EPOCHS` | `20` | 手洗时序模型训练轮数 |
| `HANDWASH_TRAINING_BATCH_SIZE` | `8` | 训练批大小 |
| `HANDWASH_TRAINING_LR` | `0.001` | 学习率 |
| `HANDWASH_TRAINING_DEVICE` | `auto` | 训练设备（`cuda` / `cpu` / `auto`） |
| `HANDWASH_TRAINING_VAL_SPLIT` | `0.2` | 验证集占比 |
| `HANDWASH_TRAINING_SEED` | `42` | 随机种子 |

---

## 🐳 Docker服务管理

### 开发环境Docker服务

启动脚本会自动管理Docker服务，您也可以手动操作：

```bash
# 启动数据库和Redis
docker-compose up -d database redis

# 查看服务状态
docker ps | grep -E "postgres|redis"

# 查看日志
docker-compose logs -f database
docker-compose logs -f redis

# 停止服务
docker-compose down
```

### 生产环境Docker服务

生产环境通常部署在独立的服务器上，使用专门的Docker Compose配置：

```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps
```

---

## 🔧 常用脚本

### 开发脚本

```bash
# 启动开发环境
bash scripts/start_dev.sh

# 设置开发环境（首次运行）
bash scripts/setup_dev.sh

# 验证配置
python scripts/validate_config.py
```

### 生产脚本

```bash
# 启动生产服务
bash scripts/start_prod.sh

# 部署到生产环境
bash scripts/deploy_prod.sh

# 生成生产密钥
python scripts/generate_production_secrets.py

# 检查部署就绪状态
bash scripts/check_deployment_readiness.sh
```

### 数据迁移脚本

```bash
# 从YAML迁移相机配置到数据库
python scripts/migrate_cameras_from_yaml.py

# 从JSON迁移区域配置到数据库
python scripts/migrate_regions_from_json.py

# 导出相机配置到YAML（备份）
python scripts/export_cameras_to_yaml.py

# 导出区域配置到JSON（备份）
python scripts/export_regions_to_json.py
```

---

## 🆘 故障排除

### 问题1: 数据库连接失败

**错误**: `Error 8 connecting to database:5432`

**解决方案**:
1. 检查Docker是否运行: `docker ps`
2. 检查容器状态: `docker-compose ps`
3. 检查 `.env` 文件中的 `DATABASE_URL` 是否正确
   - 开发环境应使用 `localhost`
   - 生产环境（Docker内）应使用 `database`

### 问题2: 配置文件未加载

**错误**: 服务使用旧的配置或Docker内部主机名

**解决方案**:
1. 确认 `.env` 文件中 `ENVIRONMENT=development`
2. 检查是否有 `.env.production` 覆盖了 `.env`
3. 重启服务以确保配置重新加载

### 问题3: Redis连接失败

**错误**: `Error 8 connecting to redis:6379`

**解决方案**:
1. 检查Redis容器是否运行: `docker ps | grep redis`
2. 检查 `.env` 文件中的 `REDIS_URL` 是否正确
3. 开发环境应使用 `localhost:6379`

---

## 📚 深入了解

想要更深入地了解项目的设计、部署和贡献方式吗？我们为您准备了全新的、结构化的文档中心。

### 核心文档

- **[➡️ 完整知识库 (docs/INDEX.md)](./docs/INDEX.md)**: **所有开发者的必读入口。** 这里包含了项目架构、部署指南、模型说明等所有核心文档。

- **[➡️ 系统架构文档 (docs/SYSTEM_ARCHITECTURE.md)](./docs/SYSTEM_ARCHITECTURE.md)**: 详细的系统架构说明，包括DDD架构设计、数据流、API端点等。

- **[➡️ 最近更新索引 (docs/RECENT_UPDATES_INDEX.md)](./docs/RECENT_UPDATES_INDEX.md)**: **最新更新文档索引**，快速查找最近的更新和文档。

### 最近更新（2025-11-04）

#### 代码重构 ✅
- **[代码重构完成报告](./docs/MAIN_REFACTORING_FINAL_SUMMARY.md)**: main.py 简化（1,226→368行，-70%）
- **[重构测试报告](./docs/REFACTORING_TEST_RESULTS.md)**: 完整测试验证结果

#### 问题修复 ✅
- **[P0问题修复](./docs/P0_ISSUES_FIX_COMPLETE.md)**: 数据库时区和greenlet依赖修复
- **[P1问题修复](./docs/P1_ISSUES_FIX_COMPLETE.md)**: 文档和XGBoost修复
- **[全部工作总结](./docs/ALL_ISSUES_FIX_SUMMARY.md)**: 完整工作总结

#### 依赖管理 ✅
- **[可选依赖指南](./docs/OPTIONAL_DEPENDENCIES.md)**: 完整的依赖管理指南
- **[pyproject.toml依赖组指南](./docs/PYPROJECT_DEPENDENCIES_GUIDE.md)**: 依赖组使用指南

#### XGBoost ML分类器 ✅
- **[XGBoost详细分析](./docs/XGBOOST_ANALYSIS.md)**: 技术原理和选择理由
- **[XGBoost启用指南](./docs/XGBOOST_ENABLE_GUIDE.md)**: 启用步骤和配置

### 配置和部署文档

- **[➡️ 配置管理指南](docs/configuration_quick_start.md)**: 详细的配置管理说明和快速开始指南
- **[➡️ 生产部署指南](docs/production_deployment_guide.md)**: 生产环境部署的详细指南
- **[➡️ 生产密钥指南](docs/production_secrets_guide.md)**: 如何安全地生成和管理生产环境密钥

### 其他文档

- **[➡️ 贡献者指南 (CONTRIBUTING.md)](./CONTRIBUTING.md)**: 如果您希望为项目贡献代码，请从这里开始。它详细说明了开发环境搭建、代码规范和Git工作流。

- **[➡️ API文档 (docs/API_文档.md)](./docs/API_文档.md)**: 完整的API接口文档和使用示例。

## 🛠️ 技术栈

### 后端技术
- **框架**: FastAPI, Python 3.8+
- **AI/ML**: PyTorch, Ultralytics (YOLOv8), MediaPipe
- **数据库**: PostgreSQL (主数据源), Redis (缓存和消息队列)
- **架构**: 领域驱动设计（DDD）, SOLID原则, 仓储模式, 依赖注入

### 可选依赖

本项目的部分依赖是**按需安装**的，根据您的硬件设备和功能需求选择安装。

#### 使用 pyproject.toml 安装（推荐）

项目已配置可选依赖组，您可以使用以下方式安装：

```bash
# 基础安装（最小依赖，推荐）
pip install -e .

# NVIDIA GPU 用户（推荐）
pip install -e ".[gpu-nvidia]"

# 需要 ML 增强功能
pip install -e ".[ml]"

# NVIDIA GPU + ML 组合（推荐用于 NVIDIA GPU 用户）
pip install -e ".[gpu-nvidia-ml]"

# 或组合多个依赖组
pip install -e ".[gpu-nvidia,ml]"
```

#### 手动安装（备选方式）

如果您不想使用可选依赖组，也可以手动安装：

**NVIDIA GPU监控（仅GPU设备需要）**
```bash
# 仅在使用 NVIDIA GPU 时安装
pip install pynvml
```

**说明**:
- ✅ **CPU/Mac设备**: 无需安装，系统会自动使用PyTorch进行设备检测
- ✅ **NVIDIA GPU**: 推荐安装以获取详细的GPU信息和监控
- ✅ **未安装时**: 系统自动回退到PyTorch，功能不受影响

**XGBoost机器学习分类器 - 洗手行为识别增强**
```bash
pip install xgboost
```

**说明**:
- 用于提升洗手行为识别的准确率，与规则引擎融合使用
- 默认使用规则推理引擎（无需此依赖）
- 安装后可在配置文件中启用（`use_ml_classifier: true`）
- 详细说明请参考: [XGBoost 详细分析](./docs/XGBOOST_ANALYSIS.md)

#### 可选依赖组说明

| 依赖组 | 包含依赖 | 适用场景 |
|--------|---------|----------|
| `gpu-nvidia` | pynvml | NVIDIA GPU 用户 |
| `ml` | xgboost | 洗手行为识别增强 |
| `gpu-nvidia-ml` | pynvml + xgboost | NVIDIA GPU + ML 用户 |
| `dev` | 测试、代码质量工具 | 开发环境 |
| `test` | 测试框架 | 运行测试 |
| `docs` | 文档工具 | 生成文档 |
| `production` | Gunicorn、监控等 | 生产环境 |

### 前端技术
- **框架**: Vue 3, Vite, TypeScript
- **UI组件**: Naive UI

### 基础设施
- **容器化**: Docker, Docker Compose
- **反向代理**: Nginx
- **监控**: 健康检查, 指标收集, 告警系统

## 🏗️ 系统架构

本项目采用**领域驱动设计（DDD）**架构，完全遵循SOLID原则和现代软件工程最佳实践。

### 架构层次

```
┌─────────────────────────────────────┐
│      API层 (REST/WebSocket)         │
├─────────────────────────────────────┤
│      应用层 (Use Cases)              │
├─────────────────────────────────────┤
│      领域层 (Domain Logic)           │
│  • 实体 (Entities)                  │
│  • 值对象 (Value Objects)            │
│  • 领域服务 (Domain Services)       │
│  • 仓储接口 (Repository Interfaces)  │
├─────────────────────────────────────┤
│    基础设施层 (Infrastructure)        │
│  • PostgreSQL仓储实现                │
│  • Redis仓储实现                     │
│  • AI模型集成                        │
└─────────────────────────────────────┘
```

### 核心特性

- ✅ **38个API端点**全部重构，采用领域驱动设计
- ✅ **单一数据源**：相机和区域配置已从YAML/JSON迁移到PostgreSQL
- ✅ **灰度发布机制**：支持渐进式发布和平滑回滚
- ✅ **高测试覆盖率**：单元测试覆盖率≥90%
- ✅ **完整监控**：健康检查、指标收集、告警系统

### 配置管理

- ✅ **数据库存储**：相机配置、区域配置存储在PostgreSQL
- ✅ **文件存储**：算法参数配置文件保留在YAML/JSON（用于版本控制）

详见 [架构文档](./docs/architecture_refactoring_plan.md) 和 [重构完成报告](./docs/REFACTORING_COMPLETE_CHECKLIST.md)

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。
