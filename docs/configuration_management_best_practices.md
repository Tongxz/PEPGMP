# 配置管理最佳实践方案

## 问题分析

### 当前问题

**启动命令过长**:
```bash
export DATABASE_URL="postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development" && \
export REDIS_URL="redis://:pyt_dev_redis@localhost:6379/0" && \
export LOG_LEVEL=DEBUG && \
export AUTO_CONVERT_TENSORRT=false && \
export USE_DOMAIN_SERVICE=true && \
export ROLLOUT_PERCENT=100 && \
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

**问题**:
1. ❌ 配置项太多，命令冗长
2. ❌ 敏感信息（密码）暴露在命令行
3. ❌ 难以维护和共享
4. ❌ 容易出错（拼写错误、遗漏配置）
5. ❌ 不符合12-Factor App原则
6. ❌ 无法版本控制敏感信息

## 解决方案

### 1. 使用.env文件管理配置（推荐）⭐⭐⭐

基于**12-Factor App**原则，配置应该从环境中读取。

#### 1.1 创建配置文件

**`.env.example`** (可提交到Git):
```bash
# 应用配置
ENVIRONMENT=development
LOG_LEVEL=DEBUG
AUTO_CONVERT_TENSORRT=false

# 数据库配置
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=pyt_development
DATABASE_USER=pyt_dev
DATABASE_PASSWORD=change_me_in_production

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=change_me_in_production

# 或者使用URL格式（推荐）
# DATABASE_URL=postgresql://user:password@host:port/dbname
# REDIS_URL=redis://:password@host:port/db

# 领域服务配置
USE_DOMAIN_SERVICE=true
ROLLOUT_PERCENT=100

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# 安全配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_in_production
SECRET_KEY=change_me_in_production

# 摄像头配置
CAMERAS_YAML_PATH=config/cameras.yaml

# 可选配置
# WATCHFILES_FORCE_POLLING=true
```

**`.env`** (实际配置，不提交到Git):
```bash
# 应用配置
ENVIRONMENT=development
LOG_LEVEL=DEBUG
AUTO_CONVERT_TENSORRT=false

# 数据库配置（URL格式）
DATABASE_URL=postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development

# Redis配置（URL格式）
REDIS_URL=redis://:pyt_dev_redis@localhost:6379/0

# 领域服务配置
USE_DOMAIN_SERVICE=true
ROLLOUT_PERCENT=100

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# 安全配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SECRET_KEY=your-secret-key-here

# 摄像头配置
CAMERAS_YAML_PATH=config/cameras.yaml
```

**`.env.production`** (生产环境配置):
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
AUTO_CONVERT_TENSORRT=true

DATABASE_URL=postgresql://prod_user:strong_password@prod-db:5432/pyt_production
REDIS_URL=redis://:strong_redis_password@prod-redis:6379/0

USE_DOMAIN_SERVICE=true
ROLLOUT_PERCENT=100

API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

ADMIN_USERNAME=admin
ADMIN_PASSWORD=very_strong_password
SECRET_KEY=production-secret-key-64-chars-long

CAMERAS_YAML_PATH=/app/config/cameras.yaml
```

#### 1.2 使用python-dotenv加载配置

**安装依赖**:
```bash
pip install python-dotenv
```

**创建配置加载模块** `src/config/env_config.py`:
```python
"""环境配置加载模块."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """应用配置类."""

    def __init__(self, env_file: Optional[str] = None):
        """初始化配置.

        Args:
            env_file: 环境文件路径，如果为None则按优先级加载
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # 按优先级加载配置文件
            # 1. .env.local (本地覆盖，不提交)
            # 2. .env.{ENVIRONMENT} (环境特定)
            # 3. .env (默认配置)
            project_root = Path(__file__).parent.parent.parent

            # 加载默认配置
            default_env = project_root / ".env"
            if default_env.exists():
                load_dotenv(default_env)

            # 加载环境特定配置
            environment = os.getenv("ENVIRONMENT", "development")
            env_specific = project_root / f".env.{environment}"
            if env_specific.exists():
                load_dotenv(env_specific, override=True)

            # 加载本地覆盖配置
            local_env = project_root / ".env.local"
            if local_env.exists():
                load_dotenv(local_env, override=True)

    # 应用配置
    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def auto_convert_tensorrt(self) -> bool:
        return os.getenv("AUTO_CONVERT_TENSORRT", "false").lower() == "true"

    # 数据库配置
    @property
    def database_url(self) -> str:
        return os.getenv("DATABASE_URL", "")

    # Redis配置
    @property
    def redis_url(self) -> str:
        return os.getenv("REDIS_URL", "")

    # 领域服务配置
    @property
    def use_domain_service(self) -> bool:
        return os.getenv("USE_DOMAIN_SERVICE", "false").lower() == "true"

    @property
    def rollout_percent(self) -> int:
        return int(os.getenv("ROLLOUT_PERCENT", "0"))

    # API配置
    @property
    def api_host(self) -> str:
        return os.getenv("API_HOST", "0.0.0.0")

    @property
    def api_port(self) -> int:
        return int(os.getenv("API_PORT", "8000"))

    @property
    def api_reload(self) -> bool:
        return os.getenv("API_RELOAD", "false").lower() == "true"

    # 安全配置
    @property
    def admin_username(self) -> str:
        return os.getenv("ADMIN_USERNAME", "admin")

    @property
    def admin_password(self) -> str:
        return os.getenv("ADMIN_PASSWORD", "")

    @property
    def secret_key(self) -> str:
        return os.getenv("SECRET_KEY", "")

    # 摄像头配置
    @property
    def cameras_yaml_path(self) -> str:
        return os.getenv("CAMERAS_YAML_PATH", "config/cameras.yaml")

    def validate(self) -> bool:
        """验证必需的配置项是否存在.

        Returns:
            配置是否有效
        """
        required = [
            ("DATABASE_URL", self.database_url),
            ("REDIS_URL", self.redis_url),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(f"缺少必需的配置项: {', '.join(missing)}")

        return True


# 全局配置实例
config = Config()
```

#### 1.3 修改应用启动

**`src/api/app.py`** (添加配置加载):
```python
# 在文件顶部添加
from src.config.env_config import config

# 验证配置
config.validate()
```

### 2. 创建启动脚本

#### 2.1 开发环境启动脚本

**`scripts/start_dev.sh`**:
```bash
#!/bin/bash

# 开发环境启动脚本
set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 启动开发环境 ==="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source venv/bin/activate

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，从.env.example复制..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已创建.env文件，请根据需要修改配置"
        echo "⚠️  特别注意修改数据库和Redis密码"
    else
        echo "❌ .env.example文件不存在"
        exit 1
    fi
fi

# 安装依赖（可选）
# pip install -r requirements.txt

# 检查Docker服务
echo ""
echo "检查依赖服务..."
if ! docker ps | grep -q pyt-postgres-dev; then
    echo "⚠️  PostgreSQL服务未运行"
    echo "   启动命令: docker-compose up -d database"
fi

if ! docker ps | grep -q pyt-redis-dev; then
    echo "⚠️  Redis服务未运行"
    echo "   启动命令: docker-compose up -d redis"
fi

# 启动后端
echo ""
echo "✅ 启动后端服务..."
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

**`scripts/start_dev.ps1`** (Windows版本):
```powershell
# 开发环境启动脚本 (Windows)

$ErrorActionPreference = "Stop"

# 项目根目录
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

Set-Location $PROJECT_ROOT

Write-Host "=== 启动开发环境 ===" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "❌ 虚拟环境不存在，请先运行: python -m venv venv" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
Write-Host "✅ 激活虚拟环境..." -ForegroundColor Green
& "venv\Scripts\Activate.ps1"

# 检查.env文件
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env文件不存在，从.env.example复制..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ 已创建.env文件，请根据需要修改配置" -ForegroundColor Green
        Write-Host "⚠️  特别注意修改数据库和Redis密码" -ForegroundColor Yellow
    } else {
        Write-Host "❌ .env.example文件不存在" -ForegroundColor Red
        exit 1
    }
}

# 启动后端
Write-Host ""
Write-Host "✅ 启动后端服务..." -ForegroundColor Green
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

#### 2.2 生产环境启动脚本

**`scripts/start_prod.sh`**:
```bash
#!/bin/bash

# 生产环境启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 启动生产环境 ==="
echo ""

# 激活虚拟环境
source venv/bin/activate

# 加载生产环境配置
export ENVIRONMENT=production

# 检查.env.production文件
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production文件不存在"
    exit 1
fi

# 验证配置
python -c "from src.config.env_config import Config; Config('.env.production').validate()"

# 使用Gunicorn启动（生产环境）
gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
```

### 3. Git配置

**`.gitignore`** (添加以下内容):
```gitignore
# 环境配置文件
.env
.env.local
.env.*.local
.env.production

# 日志文件
logs/
*.log

# 临时文件
*.tmp
/tmp/

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
```

**保留模板文件**:
```gitignore
# 保留这些文件，用于参考
!.env.example
!.env.development.example
!.env.production.example
```

### 4. Docker配置改进

**`docker-compose.yml`** (使用env_file):
```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: pyt-api-dev
    env_file:
      - .env  # 从.env文件加载环境变量
    ports:
      - "${API_PORT:-8000}:8000"
    volumes:
      - .:/app
    command: python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - pyt-dev-network
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
```

### 5. 配置管理层次结构

```
配置优先级（从高到低）：
1. 环境变量（命令行设置）
2. .env.local（本地覆盖，不提交）
3. .env.{ENVIRONMENT}（环境特定）
4. .env（默认配置）
5. 代码中的默认值
```

### 6. 敏感信息管理

#### 6.1 开发环境

**使用.env文件** ✅
- 本地开发使用`.env`
- 不提交到Git
- 团队成员各自维护

#### 6.2 生产环境

**选项1: 环境变量（推荐）**
```bash
# 在服务器上设置环境变量
export DATABASE_URL="..."
export REDIS_URL="..."
```

**选项2: 配置管理工具**
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Kubernetes Secrets

**选项3: .env.production文件**
- 使用安全的部署流程
- 限制文件访问权限（chmod 600）
- 不提交到Git

### 7. 配置验证

**添加配置验证命令**:

**`scripts/validate_config.py`**:
```python
#!/usr/bin/env python
"""配置验证脚本."""

import sys
from src.config.env_config import Config


def main():
    """验证配置."""
    try:
        config = Config()
        config.validate()
        print("✅ 配置验证通过")
        print(f"   环境: {config.environment}")
        print(f"   数据库: {config.database_url.split('@')[1] if '@' in config.database_url else 'N/A'}")
        print(f"   Redis: {config.redis_url.split('@')[1] if '@' in config.redis_url else 'N/A'}")
        return 0
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

## 实施步骤

### 第一步: 创建配置文件

1. 创建`.env.example`
2. 创建`.env`（从`.env.example`复制）
3. 修改`.env`中的实际密码

### 第二步: 创建配置加载模块

1. 创建`src/config/env_config.py`
2. 实现`Config`类
3. 添加配置验证

### 第三步: 修改应用启动

1. 在`src/api/app.py`中加载配置
2. 验证必需的配置项

### 第四步: 创建启动脚本

1. 创建`scripts/start_dev.sh`
2. 创建`scripts/start_dev.ps1`
3. 赋予执行权限：`chmod +x scripts/start_dev.sh`

### 第五步: 更新.gitignore

1. 添加`.env`到`.gitignore`
2. 保留`.env.example`
3. 提交更改

### 第六步: 更新文档

1. 更新README.md
2. 添加配置说明
3. 更新开发指南

## 使用方法

### 开发环境

**首次使用**:
```bash
# 1. 复制配置文件
cp .env.example .env

# 2. 修改.env中的配置（特别是密码）
nano .env

# 3. 启动服务
./scripts/start_dev.sh
```

**后续使用**:
```bash
# 直接启动
./scripts/start_dev.sh
```

### 生产环境

```bash
# 1. 创建生产配置
cp .env.example .env.production

# 2. 修改生产配置
nano .env.production

# 3. 限制文件权限
chmod 600 .env.production

# 4. 启动服务
./scripts/start_prod.sh
```

## 最佳实践

### ✅ 推荐做法

1. **使用.env文件管理配置**
2. **不要提交敏感信息到Git**
3. **使用配置验证确保必需项存在**
4. **为不同环境创建不同的配置文件**
5. **使用启动脚本标准化启动流程**
6. **文档化所有配置项**

### ❌ 避免做法

1. **在代码中硬编码配置**
2. **在命令行中暴露密码**
3. **提交.env文件到Git**
4. **使用默认密码用于生产环境**
5. **忽略配置验证**

## 参考标准

- **12-Factor App**: https://12factor.net/
- **OWASP Configuration Management**: https://owasp.org/
- **Python环境管理**: python-dotenv

---

**状态**: 配置管理最佳实践方案
**优先级**: 高
**影响**: 提高配置管理的安全性、可维护性和可靠性
