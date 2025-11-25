# 配置和启动快速指南

## 快速开始

### 1. 首次设置

```bash
# 1. 创建配置文件
cp .env.example .env

# 2. 编辑配置文件（可选，默认配置已可用）
nano .env

# 3. 启动依赖服务（PostgreSQL和Redis）
docker-compose up -d database redis

# 4. 验证配置
python scripts/validate_config.py

# 5. 启动开发服务器
./scripts/start_dev.sh
```

### 2. 日常使用

```bash
# 直接启动（已配置好）
./scripts/start_dev.sh
```

## 配置文件说明

### .env文件

`.env`文件包含所有环境配置，**不会提交到Git**。

**关键配置项**:
```bash
# 数据库连接
DATABASE_URL=postgresql://user:password@host:port/dbname

# Redis连接
REDIS_URL=redis://:password@host:port/db

# 领域服务
USE_DOMAIN_SERVICE=true
ROLLOUT_PERCENT=100

# API配置
API_PORT=8000
API_RELOAD=true
```

### 配置文件层次

```
优先级（从高到低）：
1. 环境变量（命令行设置）
2. .env.local（本地覆盖，不提交）
3. .env.{ENVIRONMENT}（环境特定）
4. .env（默认配置）
5. 代码中的默认值
```

## 常用命令

### 验证配置

```bash
python scripts/validate_config.py
```

**输出示例**:
```
============================================================
✅ 配置验证通过
============================================================
   环境: development
   日志级别: DEBUG
   数据库: ***@localhost:5432/pepgmp_development
   Redis: ***@localhost:6379/0
   领域服务: 启用
   灰度百分比: 100%
   API端口: 8000
============================================================
```

### 启动开发服务器

```bash
./scripts/start_dev.sh
```

**脚本会自动**:
- ✅ 检查并激活虚拟环境
- ✅ 检查并创建.env文件
- ✅ 检查python-dotenv
- ✅ 检查Docker服务
- ✅ 验证配置
- ✅ 启动后端服务

### 手动启动（不推荐）

如果需要手动启动：

```bash
# 激活虚拟环境
source venv/bin/activate

# 验证配置
python scripts/validate_config.py

# 启动服务
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**注意**: 手动启动时，配置会自动从.env文件加载。

## 不同环境的配置

### 开发环境

使用`.env`文件：
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development
REDIS_URL=redis://:pepgmp_dev_redis@localhost:6379/0
```

### 测试环境

创建`.env.testing`文件：
```bash
ENVIRONMENT=testing
LOG_LEVEL=INFO
DATABASE_URL=postgresql://test_user:test_password@test-db:5432/pyt_testing
REDIS_URL=redis://:test_redis_password@test-redis:6379/0
```

使用时：
```bash
export ENVIRONMENT=testing
./scripts/start_dev.sh
```

### 生产环境

创建`.env.production`文件（不提交到Git）：
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql://prod_user:strong_password@prod-db:5432/pepgmp_production
REDIS_URL=redis://:strong_redis_password@prod-redis:6379/0
ADMIN_PASSWORD=very_strong_password
SECRET_KEY=production-secret-key-64-chars-long
```

## 安全注意事项

### ⚠️ 不要做

1. ❌ 不要提交`.env`文件到Git
2. ❌ 不要在代码中硬编码密码
3. ❌ 不要在命令行中暴露密码
4. ❌ 不要使用默认密码用于生产环境

### ✅ 应该做

1. ✅ 使用`.env`文件管理配置
2. ✅ 使用强密码用于生产环境
3. ✅ 限制`.env`文件权限（`chmod 600 .env`）
4. ✅ 定期更新密码
5. ✅ 使用环境变量或密钥管理服务

## 故障排除

### 配置验证失败

**问题**: `❌ 配置验证失败: 缺少必需的配置项: DATABASE_URL, REDIS_URL`

**解决**:
```bash
# 1. 检查.env文件是否存在
ls -la .env

# 2. 如果不存在，从示例创建
cp .env.example .env

# 3. 验证配置
python scripts/validate_config.py
```

### python-dotenv未安装

**问题**: `python-dotenv未安装`

**解决**:
```bash
pip install python-dotenv
```

### Docker服务未运行

**问题**: `PostgreSQL服务未运行`

**解决**:
```bash
# 启动所有服务
docker-compose up -d

# 或只启动数据库
docker-compose up -d database redis
```

### 端口已被占用

**问题**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 停止进程
pkill -f "uvicorn.*app:app"

# 重新启动
./scripts/start_dev.sh
```

## 更多信息

- 详细配置说明: `docs/configuration_management_best_practices.md`
- 环境配置模块: `src/config/env_config.py`
- 配置示例: `.env.example`

## 参考

- [12-Factor App](https://12factor.net/)
- [python-dotenv文档](https://github.com/theskumar/python-dotenv)
