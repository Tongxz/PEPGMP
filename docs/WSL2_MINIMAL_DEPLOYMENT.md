# WSL2 最小化部署指南（仅镜像部署）

## 📋 概述

如果你已经在 Windows 上构建了 Docker 镜像并导出到 WSL2，**不需要完整的项目代码**，只需要必要的配置文件和目录。

**前提条件**：
- ✅ Docker 镜像已导入到 WSL2（`pepgmp-backend:20251201`, `pepgmp-frontend:20251201`）
- ✅ 1Panel 已安装

---

## 🎯 需要哪些文件？

### 必需文件（最小化部署）

只需要以下文件和目录：

```
~/projects/PEPGMP
├── docker-compose.prod.yml          # Docker Compose 配置文件（必需）
├── .env.production                  # 环境变量配置（必需）
├── config/                          # 配置文件目录（必需，容器挂载）
│   ├── cameras.yaml
│   ├── enhanced_detection_config.yaml
│   └── ...
├── models/                          # 模型文件目录（可选，如果使用）
│   └── ...
└── data/                            # 数据目录（可选，用于临时文件）
    └── ...
```

**不需要的文件**：
- ❌ `src/` - 源代码（已在镜像中）
- ❌ `frontend/` - 前端代码（已在镜像中）
- ❌ `requirements.txt` - 依赖文件（已在镜像中）
- ❌ `Dockerfile.prod` - 构建文件（不需要）
- ❌ `tests/`, `docs/`, `scripts/` - 开发文件（不需要）

---

## 🚀 最小化部署步骤

### 步骤1: 创建最小化项目目录

在 WSL2 Ubuntu 中：

```bash
# 创建项目目录
mkdir -p ~/projects/Pyt
cd ~/projects/Pyt

# 创建必要的子目录
mkdir -p config models data logs
```

### 步骤2: 复制必需文件

**方式1: 从 Windows 文件系统复制（推荐）**

```bash
# 在 WSL2 Ubuntu 中
# 复制 Docker Compose 文件
cp /mnt/c/Users/YourName/Code/PEPGMPhonCode/Pyt/docker-compose.prod.yml ~/projects/PEPGMP

# 复制配置文件目录
cp -r /mnt/c/Users/YourName/Code/PEPGMPhonCode/Pyt/config ~/projects/PEPGMP

# 复制模型目录（如果存在）
cp -r /mnt/c/Users/YourName/Code/PEPGMPhonCode/Pyt/models ~/projects/PEPGMP 2>/dev/null || mkdir -p ~/projects/PEPGMPmodels

# 创建数据目录
mkdir -p ~/projects/PEPGMPdata
```

**方式2: 使用 Git（如果项目在 Git 仓库中）**

```bash
# 只克隆必要的文件
cd ~/projects
git clone <your-repo-url> Pyt
cd Pyt

# 删除不需要的目录（可选，节省空间）
rm -rf src frontend tests docs scripts
```

### 步骤3: 创建环境变量文件

```bash
cd ~/projects/Pyt

# 创建 .env.production 文件
cat > .env.production << 'EOF'
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
EOF

# 设置文件权限
chmod 600 .env.production
```

### 步骤4: 修改 Docker Compose 文件

确保 `docker-compose.prod.yml` 使用已导入的镜像，而不是构建：

```yaml
services:
  api:
    # 移除 build 部分，直接使用镜像
    image: pepgmp-backend:20251201  # 使用你导入的镜像
    # 不要使用 build:
    # build:
    #   context: .
    #   dockerfile: Dockerfile.prod
```

### 步骤5: 在 1Panel 中部署

1. **登录 1Panel**
2. **进入容器管理** > **Compose**
3. **创建新项目**：
   - 项目名称：`pepgmp-production`
   - 工作目录：`/home/你的用户名/projects/Pyt`
4. **上传或编辑 Compose 文件**：使用修改后的 `docker-compose.prod.yml`
5. **启动服务**

---

## 📦 创建最小化部署包脚本

创建一个脚本来自动准备最小化部署：

```bash
#!/bin/bash
# 创建最小化部署包

PROJECT_DIR="$HOME/projects/Pyt"
WINDOWS_PROJECT="/mnt/c/Users/YourName/Code/PEPGMPhonCode/Pyt"

# 创建目录
mkdir -p "$PROJECT_DIR"/{config,models,data,logs}

# 复制必需文件
echo "复制 Docker Compose 文件..."
cp "$WINDOWS_PROJECT/docker-compose.prod.yml" "$PROJECT_DIR/"

echo "复制配置文件..."
cp -r "$WINDOWS_PROJECT/config"/* "$PROJECT_DIR/config/" 2>/dev/null || true

echo "复制模型文件（如果存在）..."
cp -r "$WINDOWS_PROJECT/models"/* "$PROJECT_DIR/models/" 2>/dev/null || true

echo "创建环境变量文件..."
if [ ! -f "$PROJECT_DIR/.env.production" ]; then
    cat > "$PROJECT_DIR/.env.production" << 'EOF'
ENVIRONMENT=production
LOG_LEVEL=INFO
IMAGE_TAG=20251201
DATABASE_PASSWORD=your_strong_password
REDIS_PASSWORD=your_strong_password
SECRET_KEY=your_secret_key_here
EOF
    chmod 600 "$PROJECT_DIR/.env.production"
    echo "⚠️  请编辑 .env.production 文件设置密码和密钥"
fi

echo "✅ 最小化部署包已准备完成：$PROJECT_DIR"
echo ""
echo "下一步："
echo "1. 编辑 $PROJECT_DIR/.env.production 设置密码"
echo "2. 在 1Panel 中创建 Compose 项目"
echo "3. 使用 $PROJECT_DIR 作为工作目录"
```

---

## 🔍 文件说明

### docker-compose.prod.yml

**必需**：定义服务配置、网络、数据卷等。

**需要修改的地方**：
- 移除 `build:` 部分
- 使用 `image:` 指定已导入的镜像

### .env.production

**必需**：环境变量配置，包含数据库密码、Redis 密码等敏感信息。

### config/

**必需**：配置文件目录，容器会挂载此目录。

包含：
- `cameras.yaml` - 摄像头配置
- `enhanced_detection_config.yaml` - 检测配置
- `regions.json` - 区域配置
- 其他配置文件

### models/

**可选**：模型文件目录。如果应用需要模型文件，需要挂载此目录。

### data/

**可选**：数据目录，用于临时文件和数据库文件。

---

## 🎯 两种部署方案对比

### 方案1: 最小化部署（推荐）

**优点**：
- ✅ 占用空间小
- ✅ 部署快速
- ✅ 只包含运行时需要的文件

**需要文件**：
- docker-compose.prod.yml
- .env.production
- config/
- models/（如果需要）
- data/（如果需要）

### 方案2: 完整项目部署

**优点**：
- ✅ 包含所有文件，便于调试
- ✅ 可以查看日志、脚本等

**需要文件**：
- 整个项目目录

**缺点**：
- ❌ 占用空间大
- ❌ 包含不必要的文件

---

## 📋 快速检查清单

在 WSL2 中验证：

```bash
cd ~/projects/Pyt

# 1. 检查必需文件
ls -la docker-compose.prod.yml .env.production config/

# 2. 检查镜像
docker images | grep pepgmp

# 3. 检查目录权限
ls -ld config models data

# 4. 验证 Compose 文件语法
docker compose -f docker-compose.prod.yml config
```

---

## 🚀 一键准备脚本

创建 `scripts/prepare_minimal_deploy.sh`：

```bash
#!/bin/bash
# 准备最小化部署包

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="$HOME/projects/Pyt"

echo "准备最小化部署包..."
echo "源目录: $PROJECT_ROOT"
echo "目标目录: $DEPLOY_DIR"
echo ""

# 创建目录
mkdir -p "$DEPLOY_DIR"/{config,models,data,logs}

# 复制必需文件
echo "复制 Docker Compose 文件..."
cp "$PROJECT_ROOT/docker-compose.prod.yml" "$DEPLOY_DIR/"

echo "复制配置文件..."
if [ -d "$PROJECT_ROOT/config" ]; then
    cp -r "$PROJECT_ROOT/config"/* "$DEPLOY_DIR/config/"
fi

echo "复制模型文件（如果存在）..."
if [ -d "$PROJECT_ROOT/models" ]; then
    cp -r "$PROJECT_ROOT/models"/* "$DEPLOY_DIR/models/" 2>/dev/null || true
fi

# 创建环境变量文件模板
if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    echo "创建环境变量文件模板..."
    cat > "$DEPLOY_DIR/.env.production" << 'EOF'
# ==================== 环境设置 ====================
ENVIRONMENT=production
LOG_LEVEL=INFO
IMAGE_TAG=20251201

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://pepgmp_prod:CHANGE_ME@database:5432/pepgmp_production
DATABASE_PASSWORD=CHANGE_ME

# ==================== Redis 配置 ====================
REDIS_URL=redis://:CHANGE_ME@redis:6379/0
REDIS_PASSWORD=CHANGE_ME

# ==================== API 配置 ====================
API_PORT=8000
API_HOST=0.0.0.0

# ==================== 安全配置 ====================
SECRET_KEY=CHANGE_ME
ADMIN_PASSWORD=CHANGE_ME
EOF
    chmod 600 "$DEPLOY_DIR/.env.production"
    echo "⚠️  请编辑 $DEPLOY_DIR/.env.production 设置密码和密钥"
fi

# 修改 docker-compose.prod.yml（移除 build，使用镜像）
if grep -q "build:" "$DEPLOY_DIR/docker-compose.prod.yml"; then
    echo "修改 docker-compose.prod.yml（移除 build 配置）..."
    # 这里可以使用 sed 或手动编辑
    echo "⚠️  请手动编辑 $DEPLOY_DIR/docker-compose.prod.yml，移除 build: 部分，使用 image: pepgmp-backend:20251201"
fi

echo ""
echo "✅ 最小化部署包已准备完成：$DEPLOY_DIR"
echo ""
echo "下一步："
echo "1. 编辑 $DEPLOY_DIR/.env.production 设置密码和密钥"
echo "2. 编辑 $DEPLOY_DIR/docker-compose.prod.yml，确保使用已导入的镜像"
echo "3. 在 1Panel 中创建 Compose 项目，使用 $DEPLOY_DIR 作为工作目录"
```

---

## 📚 总结

**回答你的问题**：

**不需要完整的项目文件**，只需要：

1. ✅ **docker-compose.prod.yml** - 服务配置
2. ✅ **.env.production** - 环境变量
3. ✅ **config/** - 配置文件目录（容器会挂载）
4. ✅ **models/** - 模型文件目录（如果需要）
5. ✅ **data/** - 数据目录（如果需要）

**不需要**：
- ❌ 源代码（`src/`）- 已在镜像中
- ❌ 前端代码（`frontend/`）- 已在镜像中
- ❌ 构建文件（`Dockerfile.prod`）- 不需要
- ❌ 开发文件（`tests/`, `docs/`, `scripts/`）- 不需要

这样只需要复制几个必要的文件和目录即可，大大简化了部署过程。
