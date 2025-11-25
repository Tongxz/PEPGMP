# 项目重命名影响分析：Pyt → pepGMP

## 📋 概述

本文档详细分析了将项目名称从 **"Pyt"** 改为 **"pepGMP"** 的所有影响范围和需要修改的地方。

**重命名范围**: Pyt → pepGMP  
**影响级别**: 🔴 **高影响** - 涉及数据库、Docker、配置、文档等多个层面  
**预计工作量**: 中等（需要系统性修改多个文件）

---

## 🎯 重命名映射表

| 原名称 | 新名称 | 说明 |
|--------|--------|------|
| `Pyt` | `pepGMP` | 项目名称 |
| `pyt` | `pepgmp` | 小写项目名称（用于标识符） |
| `pepgmp_development` | `pepgmp_development` | 开发环境数据库名 |
| `pepgmp_production` | `pepgmp_production` | 生产环境数据库名 |
| `pepgmp_dev` | `pepgmp_dev` | 开发环境数据库用户 |
| `pepgmp_prod` | `pepgmp_prod` | 生产环境数据库用户 |
| `pepgmp-backend` | `pepgmp-backend` | Docker镜像名称 |
| `pepgmp-api-prod` | `pepgmp-api-prod` | API容器名称 |
| `pepgmp-postgres-prod` | `pepgmp-postgres-prod` | PostgreSQL容器名称 |
| `pepgmp-redis-prod` | `pepgmp-redis-prod` | Redis容器名称 |
| `pepgmp-frontend` | `pepgmp-frontend` | 前端项目名称 |

---

## 📊 影响范围统计

### 文件影响统计

- **数据库相关**: ~159 处匹配（55个文件）
- **Docker相关**: ~184 处匹配（43个文件）
- **配置文件**: 多个关键配置文件
- **文档文件**: 大量文档引用
- **脚本文件**: 多个部署和工具脚本

---

## 🔴 一、必须修改的地方（P0 - 阻塞）

### 1.1 项目配置文件

#### 1.1.1 `pyproject.toml` ✅

**当前内容**:
```toml
[project]
name = "human-behavior-detection"
```

**需要修改**:
```toml
[project]
name = "pepgmp"  # 或保持 "human-behavior-detection"，仅改内部标识
```

**影响**: 项目包名称，影响pip安装和包管理

#### 1.1.2 `frontend/package.json` ✅

**当前内容**:
```json
{
  "name": "pepgmp-frontend",
  ...
}
```

**需要修改**:
```json
{
  "name": "pepgmp-frontend",
  ...
}
```

**影响**: 前端项目名称，npm包管理

---

### 1.2 数据库配置（关键）🔴

#### 1.2.1 数据库名称

**需要修改的地方**:
- `pepgmp_development` → `pepgmp_development`
- `pepgmp_production` → `pepgmp_production`
- `pyt_test` → `pepgmp_test` (如存在)

**涉及文件**:
- ✅ 所有 `docker-compose*.yml` 文件
- ✅ `.env` 和 `.env.production` 文件
- ✅ `src/config/env_config.py`
- ✅ `src/database/connection.py`
- ✅ `src/database/init_db.py`
- ✅ 所有包含 `DATABASE_URL` 的配置文件

**示例修改**:
```yaml
# docker-compose.yml
environment:
  POSTGRES_DB: pepgmp_development  # 原: pepgmp_development
```

```bash
# .env
DATABASE_URL=postgresql://pepgmp_dev:password@localhost:5432/pepgmp_development
# 原: postgresql://pepgmp_dev:password@localhost:5432/pepgmp_development
```

#### 1.2.2 数据库用户名

**需要修改的地方**:
- `pepgmp_dev` → `pepgmp_dev`
- `pepgmp_prod` → `pepgmp_prod`

**涉及文件**:
- ✅ 所有 `docker-compose*.yml` 文件
- ✅ `.env` 和 `.env.production` 文件
- ✅ 所有数据库连接配置

**示例修改**:
```yaml
# docker-compose.yml
environment:
  POSTGRES_USER: pepgmp_dev  # 原: pepgmp_dev
```

---

### 1.3 Docker 配置（关键）🔴

#### 1.3.1 Docker 镜像名称

**需要修改的地方**:
- `pepgmp-backend:latest` → `pepgmp-backend:latest`

**涉及文件**:
- ✅ `Dockerfile.prod`
- ✅ `Dockerfile.dev`
- ✅ 所有 `docker-compose*.yml` 文件
- ✅ `scripts/push_to_registry.sh`
- ✅ `scripts/deploy_from_registry.sh`
- ✅ `scripts/build_prod_images.sh`
- ✅ 所有部署脚本

**示例修改**:
```yaml
# docker-compose.prod.yml
api:
  image: pepgmp-backend:latest  # 原: pepgmp-backend:latest
```

```bash
# scripts/push_to_registry.sh
IMAGE_NAME="pepgmp-backend"  # 原: pepgmp-backend
```

#### 1.3.2 Docker 容器名称

**需要修改的地方**:
- `pepgmp-api-prod` → `pepgmp-api-prod`
- `pepgmp-postgres-prod` → `pepgmp-postgres-prod`
- `pepgmp-redis-prod` → `pepgmp-redis-prod`
- `pyt-api-dev` → `pepgmp-api-dev`
- `pyt-postgres-dev` → `pepgmp-postgres-dev`
- `pyt-redis-dev` → `pepgmp-redis-dev`
- `pepgmp-frontend-dev` → `pepgmp-frontend-dev`

**涉及文件**:
- ✅ 所有 `docker-compose*.yml` 文件
- ✅ 所有部署脚本
- ✅ 所有检查脚本

**示例修改**:
```yaml
# docker-compose.prod.yml
services:
  api:
    container_name: pepgmp-api-prod  # 原: pepgmp-api-prod
  database:
    container_name: pepgmp-postgres-prod  # 原: pepgmp-postgres-prod
  redis:
    container_name: pepgmp-redis-prod  # 原: pepgmp-redis-prod
```

#### 1.3.3 Docker Registry 路径

**需要修改的地方**:
- `192.168.30.83:5433/pepgmp-backend` → `192.168.30.83:5433/pepgmp-backend`

**涉及文件**:
- ✅ `scripts/push_to_registry.sh`
- ✅ `scripts/deploy_from_registry.sh`
- ✅ 所有部署文档

**示例修改**:
```bash
# scripts/push_to_registry.sh
REGISTRY_URL="192.168.30.83:5433"
IMAGE_NAME="pepgmp-backend"  # 原: pepgmp-backend
```

---

### 1.4 环境变量和配置文件

#### 1.4.1 `.env` 和 `.env.production`

**需要修改的地方**:
```bash
# 数据库配置
DATABASE_URL=postgresql://pepgmp_dev:password@localhost:5432/pepgmp_development
DATABASE_NAME=pepgmp_development
DATABASE_USER=pepgmp_dev

# Redis配置（如包含项目名）
REDIS_URL=redis://:password@localhost:6379/0
```

**涉及文件**:
- ✅ `.env.example`
- ✅ `.env` (本地)
- ✅ `.env.production`
- ✅ `scripts/generate_production_config.sh`

#### 1.4.2 配置文件中的默认值

**涉及文件**:
- ✅ `src/config/env_config.py` - 默认数据库名称和用户
- ✅ `src/database/connection.py` - 数据库连接配置

---

### 1.5 脚本文件

#### 1.5.1 部署脚本

**需要修改的脚本**:
- ✅ `scripts/deploy_from_registry.sh`
- ✅ `scripts/push_to_registry.sh`
- ✅ `scripts/build_prod_images.sh`
- ✅ `scripts/backup_db.sh`
- ✅ `scripts/restore_db.sh`
- ✅ `scripts/check_deployment_readiness.sh`
- ✅ `scripts/generate_production_config.sh`

**示例修改**:
```bash
# scripts/backup_db.sh
DB_NAME="pepgmp_production"  # 原: pepgmp_production
DB_USER="pepgmp_prod"  # 原: pepgmp_prod
CONTAINER_NAME="pepgmp-postgres-prod"  # 原: pepgmp-postgres-prod
```

#### 1.5.2 检查脚本

**需要修改的脚本**:
- ✅ `scripts/check_cameras_in_db.py`
- ✅ `scripts/check_db_structure.py`
- ✅ `scripts/check_saved_records.py`
- ✅ `tools/check_service_status.sh`

---

## 🟡 二、建议修改的地方（P1 - 重要）

### 2.1 代码中的硬编码引用

#### 2.1.1 数据库相关代码

**涉及文件**:
- ✅ `src/database/init_db.py` - 数据库初始化
- ✅ `src/infrastructure/repositories/postgresql_*.py` - 数据库仓库
- ✅ `src/services/database_service.py` - 数据库服务

**检查方法**:
```bash
grep -r "pepgmp_development\|pepgmp_production\|pepgmp_dev\|pepgmp_prod" src/
```

#### 2.1.2 Docker 服务相关代码

**涉及文件**:
- ✅ `src/infrastructure/deployment/docker_service.py`
- ✅ `scripts/test_deployment_service.py`

---

### 2.2 文档文件

#### 2.2.1 部署文档

**需要更新的文档**:
- ✅ `docs/DEPLOYMENT_PREPARATION_CHECKLIST.md`
- ✅ `docs/DEPLOYMENT_PROCESS_GUIDE.md`
- ✅ `docs/DEPLOYMENT_TEST_PLAN.md`
- ✅ `docs/production_deployment_guide.md`
- ✅ `docs/INTRANET_DEPLOYMENT_NOTES.md`
- ✅ `docs/DEPLOYMENT_DOCUMENTATION_INDEX.md`

**修改内容**: 所有容器名称、镜像名称、数据库名称的引用

#### 2.2.2 配置文档

**需要更新的文档**:
- ✅ `docs/configuration_management_best_practices.md`
- ✅ `docs/CONFIGURATION_ANALYSIS.md`
- ✅ `docs/configuration_quick_start.md`

**修改内容**: 所有配置示例中的项目名称

#### 2.2.3 其他文档

**需要更新的文档**:
- ✅ `README.md` - 项目介绍
- ✅ `docs/DATABASE_INITIALIZATION.md`
- ✅ `docs/docker_compose_usage_guide.md`
- ✅ 所有包含项目名称的文档

---

### 2.3 前端文件

#### 2.3.1 前端配置

**涉及文件**:
- ✅ `frontend/index.html` - 页面标题（如包含项目名）
- ✅ `frontend/src/views/Home.vue` - 首页显示（如包含项目名）
- ✅ `frontend/src/layouts/MainLayout.vue` - 布局标题（如包含项目名）

**检查方法**:
```bash
grep -r "Pyt\|pyt" frontend/src/
```

---

## 🟢 三、可选修改的地方（P2 - 建议）

### 3.1 工作目录名称

**当前**: `/Users/zhou/Code/Pyt`  
**建议**: `/Users/zhou/Code/pepGMP` 或保持原样

**影响**: 
- ⚠️ 如果更改，需要更新所有绝对路径引用
- ✅ 如果保持原样，不影响功能

### 3.2 Git 仓库名称

**当前**: 可能为 `Pyt`  
**建议**: 改为 `pepGMP`

**影响**: 
- ⚠️ 需要重命名远程仓库
- ⚠️ 需要更新所有克隆链接

### 3.3 日志和输出文件

**涉及文件**:
- ✅ 日志文件路径（如包含项目名）
- ✅ 输出文件路径（如包含项目名）

---

## 📋 修改检查清单

### 配置文件 ✅

```
□ pyproject.toml - 项目名称
□ frontend/package.json - 前端项目名称
□ .env.example - 环境变量示例
□ .env - 本地环境变量
□ .env.production - 生产环境变量
```

### Docker 配置 ✅

```
□ Dockerfile.prod - 镜像名称
□ Dockerfile.dev - 镜像名称
□ docker-compose.yml - 容器名称、数据库配置
□ docker-compose.prod.yml - 容器名称、数据库配置
□ docker-compose.prod.full.yml - 容器名称、数据库配置
□ docker-compose.prod.windows.yml - 容器名称、数据库配置
□ docker-compose.test.yml - 容器名称、数据库配置
□ docker-compose.dev-db.yml - 容器名称、数据库配置
□ docker-compose.prod.mlops.yml - 容器名称、数据库配置
```

### 数据库配置 ✅

```
□ 所有 docker-compose*.yml 中的数据库名称
□ 所有 docker-compose*.yml 中的数据库用户名
□ src/config/env_config.py - 默认数据库配置
□ src/database/connection.py - 数据库连接
□ src/database/init_db.py - 数据库初始化
```

### 脚本文件 ✅

```
□ scripts/deploy_from_registry.sh
□ scripts/push_to_registry.sh
□ scripts/build_prod_images.sh
□ scripts/backup_db.sh
□ scripts/restore_db.sh
□ scripts/check_deployment_readiness.sh
□ scripts/generate_production_config.sh
□ scripts/start_dev.sh
□ scripts/start_dev.ps1
□ scripts/start_prod.sh
□ scripts/start_prod.ps1
□ scripts/deploy_prod.sh
□ tools/check_service_status.sh
```

### 代码文件 ✅

```
□ src/infrastructure/deployment/docker_service.py
□ src/infrastructure/repositories/postgresql_*.py
□ src/services/database_service.py
□ scripts/check_cameras_in_db.py
□ scripts/check_db_structure.py
□ scripts/check_saved_records.py
```

### 文档文件 ✅

```
□ README.md
□ docs/DEPLOYMENT_*.md (所有部署文档)
□ docs/configuration_*.md (所有配置文档)
□ docs/CONFIGURATION_ANALYSIS.md
□ docs/DATABASE_INITIALIZATION.md
□ docs/docker_*.md (所有Docker文档)
```

---

## ⚠️ 重要注意事项

### 1. 数据库迁移 🔴

**重要**: 如果生产环境已有数据，需要执行数据库迁移：

```sql
-- 1. 备份现有数据库
pg_dump -U pepgmp_prod pepgmp_production > backup.sql

-- 2. 创建新数据库
CREATE DATABASE pepgmp_production;
CREATE USER pepgmp_prod WITH PASSWORD 'password';

-- 3. 恢复数据
psql -U pepgmp_prod pepgmp_production < backup.sql

-- 4. 更新所有配置后重启服务
```

### 2. Docker 容器和镜像 🔴

**重要**: 需要重新构建和推送镜像：

```bash
# 1. 停止现有容器
docker-compose down

# 2. 重新构建镜像（使用新名称）
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 3. 推送到Registry（使用新路径）
docker tag pepgmp-backend:latest 192.168.30.83:5433/pepgmp-backend:latest
docker push 192.168.30.83:5433/pepgmp-backend:latest

# 4. 删除旧容器和镜像（可选）
docker rm -f pepgmp-api-prod pepgmp-postgres-prod pepgmp-redis-prod
docker rmi pepgmp-backend:latest
```

### 3. 环境变量更新 🔴

**重要**: 所有环境变量文件需要更新：

```bash
# 1. 备份现有配置
cp .env.production .env.production.backup

# 2. 更新配置
sed -i 's/pepgmp_development/pepgmp_development/g' .env.production
sed -i 's/pepgmp_production/pepgmp_production/g' .env.production
sed -i 's/pepgmp_dev/pepgmp_dev/g' .env.production
sed -i 's/pepgmp_prod/pepgmp_prod/g' .env.production

# 3. 验证配置
grep -E "pepgmp|pyt" .env.production
```

### 4. 测试验证 ✅

**重要**: 修改后需要全面测试：

```bash
# 1. 测试数据库连接
python scripts/test_database.py

# 2. 测试Docker容器
docker-compose up -d
docker-compose ps

# 3. 测试API
curl http://localhost:8000/api/v1/monitoring/health

# 4. 运行集成测试
pytest tests/integration/ -v
```

---

## 🚀 推荐的重命名流程

### 步骤1: 准备阶段

```bash
# 1. 创建备份分支
git checkout -b backup-before-rename
git push origin backup-before-rename

# 2. 创建重命名分支
git checkout -b rename-pyt-to-pepgmp

# 3. 备份配置文件
cp .env.production .env.production.backup
cp docker-compose.prod.yml docker-compose.prod.yml.backup
```

### 步骤2: 批量替换（使用脚本）

```bash
# 创建重命名脚本
cat > scripts/rename_project.sh << 'EOF'
#!/bin/bash
# 项目重命名脚本: Pyt -> pepGMP

# 定义替换映射
declare -A replacements=(
    ["pepgmp_development"]="pepgmp_development"
    ["pepgmp_production"]="pepgmp_production"
    ["pepgmp_dev"]="pepgmp_dev"
    ["pepgmp_prod"]="pepgmp_prod"
    ["pepgmp-backend"]="pepgmp-backend"
    ["pepgmp-api-prod"]="pepgmp-api-prod"
    ["pepgmp-postgres-prod"]="pepgmp-postgres-prod"
    ["pepgmp-redis-prod"]="pepgmp-redis-prod"
    ["pepgmp-frontend"]="pepgmp-frontend"
)

# 执行替换（排除.git、node_modules、venv等）
find . -type f \( -name "*.py" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.sh" -o -name "*.md" -o -name "*.env*" -o -name "*.toml" \) \
    ! -path "./.git/*" \
    ! -path "./node_modules/*" \
    ! -path "./venv/*" \
    ! -path "./.venv/*" \
    ! -path "./mlruns/*" \
    -exec sed -i '' -e 's/pepgmp_development/pepgmp_development/g' {} \;

# ... 其他替换
EOF

chmod +x scripts/rename_project.sh
```

### 步骤3: 手动检查和验证

```bash
# 1. 检查所有修改
git diff

# 2. 验证关键文件
grep -r "pyt" docker-compose*.yml
grep -r "pyt" .env*

# 3. 测试配置
python scripts/validate_config.py
```

### 步骤4: 数据库迁移（如需要）

```bash
# 1. 备份数据库
bash scripts/backup_db.sh

# 2. 执行数据库迁移脚本
# （需要创建迁移脚本）
```

### 步骤5: 测试和部署

```bash
# 1. 本地测试
docker-compose up -d
pytest tests/ -v

# 2. 提交更改
git add .
git commit -m "refactor: 重命名项目 Pyt -> pepGMP"

# 3. 部署到测试环境
bash scripts/quick_deploy.sh <TEST_SERVER> ubuntu
```

---

## 📊 影响评估总结

| 类别 | 文件数量 | 影响级别 | 工作量 |
|------|----------|----------|--------|
| **配置文件** | ~10 | 🔴 高 | 中等 |
| **Docker配置** | ~10 | 🔴 高 | 中等 |
| **数据库配置** | ~55 | 🔴 高 | 高 |
| **脚本文件** | ~20 | 🟡 中 | 中等 |
| **代码文件** | ~10 | 🟡 中 | 低 |
| **文档文件** | ~30 | 🟢 低 | 低 |
| **总计** | ~135 | - | **中等-高** |

---

## 📚 相关文档

- [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md)
- [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md)
- [配置管理最佳实践](./configuration_management_best_practices.md)

---

**状态**: ✅ **影响分析已完成**  
**建议**: 在非生产环境先测试重命名流程  
**风险**: 🔴 **中等风险** - 需要仔细测试数据库迁移和Docker配置

