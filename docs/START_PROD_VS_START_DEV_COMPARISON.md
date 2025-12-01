# start_prod.sh 与 start_dev.sh 详细对比分析

## 📋 概述

本文档详细对比 `start_prod.sh`（生产环境启动脚本）和 `start_dev.sh`（开发环境启动脚本）的区别，并分析各自的适用场景。

---

## 🔍 核心区别对比

### 1. **配置文件**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 配置文件 | `.env` | `.env.production` |
| 自动创建 | ✅ 如果不存在，从 `.env.example` 复制 | ❌ 必须手动创建 |
| 权限检查 | ❌ 无 | ✅ 检查并建议设置为 600/400 |
| 权限修复 | ❌ 无 | ✅ 可自动修复为 600 |

**代码对比**:

```12:42:scripts/start_dev.sh
# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，从.env.example复制..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已创建.env文件"
        echo "⚠️  请根据需要修改配置（特别是数据库和Redis密码）"
        echo ""
        read -p "是否现在编辑.env文件？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        echo "❌ .env.example文件不存在"
        exit 1
    fi
fi
```

```32:55:scripts/start_prod.sh
# 检查.env.production文件
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production文件不存在"
    echo ""
    if [ -f ".env.production.example" ]; then
        echo "创建.env.production："
        echo "  cp .env.production.example .env.production"
        echo "  nano .env.production  # 修改配置"
        echo "  chmod 600 .env.production  # 限制权限"
    fi
    exit 1
fi

# 检查文件权限
file_perms=$(stat -f %A .env.production 2>/dev/null || stat -c %a .env.production 2>/dev/null)
if [ "$file_perms" != "600" ] && [ "$file_perms" != "400" ]; then
    echo "⚠️  警告：.env.production文件权限不安全（当前：$file_perms）"
    read -p "是否修改为600？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        chmod 600 .env.production
        echo "✅ 权限已更新"
    fi
fi
```

---

### 2. **服务启动方式**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 启动命令 | `uvicorn` 直接运行 | `gunicorn` + `UvicornWorker` |
| 进程数 | 单进程 | 多进程（默认4个worker） |
| 热重载 | ✅ `--reload` | ❌ 无（生产环境不需要） |
| 日志输出 | 控制台 | 文件（`logs/access.log`, `logs/error.log`） |
| 性能优化 | ❌ 无 | ✅ 配置了 `max-requests`, `keepalive` 等 |

**代码对比**:

```160:160:scripts/start_dev.sh
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

```133:144:scripts/start_prod.sh
# 启动服务（使用Gunicorn）
gunicorn src.api.app:app \
    --workers ${GUNICORN_WORKERS:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${API_PORT:-8000} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
```

**关键差异**:
- **开发环境**: 单进程 + 热重载，适合快速迭代
- **生产环境**: 多进程 + 无重载，适合高并发和稳定性

---

### 3. **Docker服务管理**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 自动启动Docker服务 | ✅ 自动检查并启动 PostgreSQL、Redis | ❌ 不管理Docker服务 |
| 容器名称检查 | ✅ 检查 `pyt-postgres-dev`, `pyt-redis-dev` | ❌ 无 |
| 服务就绪等待 | ✅ 等待数据库启动（8秒） | ❌ 无 |

**代码对比**:

```58:107:scripts/start_dev.sh
# 检查并启动Docker服务
echo ""
echo "检查依赖服务..."
if command -v docker &> /dev/null; then
    # 检查Docker是否正在运行
    if ! docker info > /dev/null 2>&1; then
        echo "⚠️  Docker未运行，请启动Docker Desktop"
        echo "   等待Docker启动..."
        sleep 5
        if ! docker info > /dev/null 2>&1; then
            echo "❌ Docker仍未就绪，请手动启动Docker Desktop后重试"
            exit 1
        fi
    fi

    # 检查并启动PostgreSQL
    if ! docker ps | grep -q pyt-postgres-dev; then
        echo "⚠️  PostgreSQL服务未运行，正在启动..."
        docker-compose up -d database 2>&1 | grep -v "the attribute.*version.*is obsolete" || true
        echo "   等待PostgreSQL启动..."
        sleep 8
        if docker ps | grep -q pyt-postgres-dev; then
            echo "✅ PostgreSQL服务已启动"
        else
            echo "❌ PostgreSQL启动失败"
            exit 1
        fi
    else
        echo "✅ PostgreSQL服务运行中"
    fi

    # 检查并启动Redis
    if ! docker ps | grep -q pyt-redis-dev; then
        echo "⚠️  Redis服务未运行，正在启动..."
        docker-compose up -d redis 2>&1 | grep -v "the attribute.*version.*is obsolete" || true
        echo "   等待Redis启动..."
        sleep 3
        if docker ps | grep -q pyt-redis-dev; then
            echo "✅ Redis服务已启动"
        else
            echo "❌ Redis启动失败"
            exit 1
        fi
    else
        echo "✅ Redis服务运行中"
    fi
else
    echo "⚠️  Docker未安装或未运行"
    echo "   请安装Docker Desktop或使用其他方式提供数据库服务"
fi
```

```78:105:scripts/start_prod.sh
# 检查必需的服务
echo "检查依赖服务..."

# 检查数据库
if [[ $DATABASE_URL == postgresql://* ]]; then
    db_host=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    db_port=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    if command -v nc &> /dev/null; then
        if nc -z $db_host $db_port 2>/dev/null; then
            echo "✅ PostgreSQL可访问 ($db_host:$db_port)"
        else
            echo "⚠️  PostgreSQL不可访问 ($db_host:$db_port)"
        fi
    fi
fi

# 检查Redis
if [[ $REDIS_URL == redis://* ]]; then
    redis_host=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    redis_port=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    if command -v nc &> /dev/null; then
        if nc -z $redis_host $redis_port 2>/dev/null; then
            echo "✅ Redis可访问 ($redis_host:$redis_port)"
        else
            echo "⚠️  Redis不可访问 ($redis_host:$redis_port)"
        fi
    fi
fi
```

**关键差异**:
- **开发环境**: 自动管理Docker服务，适合本地开发
- **生产环境**: 仅检查服务可访问性，假设服务已由Docker Compose或其他方式管理

---

### 4. **数据库初始化**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 自动初始化 | ✅ 运行 `scripts/init_database.py` | ❌ 无 |
| 数据库迁移 | ✅ 自动执行 | ❌ 无 |

**代码对比**:

```123:129:scripts/start_dev.sh
# 自动初始化/迁移数据库
echo "🔄 检查数据库结构..."
if python scripts/init_database.py; then
    echo "✅ 数据库检查完成"
else
    echo "⚠️  数据库初始化警告 (非致命错误，可能是连接问题或数据已存在)"
fi
echo ""
```

**关键差异**:
- **开发环境**: 自动初始化数据库，方便快速开始开发
- **生产环境**: 不自动初始化，数据库应该已经由部署脚本或Docker Compose初始化

---

### 5. **端口管理**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 端口检查 | ✅ 检查并清理占用端口的进程 | ❌ 无 |
| 端口清理 | ✅ 自动kill占用进程 | ❌ 无 |

**代码对比**:

```132:148:scripts/start_dev.sh
# 检查并清理端口占用
echo ""
echo "检查端口占用..."
PORT=8000
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "⚠️  端口 ${PORT} 已被占用，正在停止占用进程..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 2
    if lsof -ti:${PORT} > /dev/null 2>&1; then
        echo "❌ 无法停止占用端口 ${PORT} 的进程，请手动处理"
        exit 1
    else
        echo "✅ 端口 ${PORT} 已释放"
    fi
else
    echo "✅ 端口 ${PORT} 可用"
fi
echo ""
```

**关键差异**:
- **开发环境**: 自动处理端口冲突，方便开发
- **生产环境**: 不处理端口冲突，假设端口已正确配置

---

### 6. **安全特性**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| Root用户检查 | ❌ 无 | ✅ 警告不建议使用root |
| 文件权限检查 | ❌ 无 | ✅ 检查 `.env.production` 权限 |
| 配置验证 | ✅ 使用 `Config().validate()` | ✅ 使用 `validate_config.py` |

**代码对比**:

```16:24:scripts/start_prod.sh
# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  警告：不建议使用root用户运行"
   read -p "继续？(y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi
```

---

### 7. **调试功能**

| 特性 | start_dev.sh | start_prod.sh |
|------|-------------|---------------|
| 调试ROI保存 | ✅ 支持 `SAVE_DEBUG_ROI` | ❌ 无 |
| 热重载 | ✅ `--reload` | ❌ 无 |
| 详细日志 | ✅ `--log-level info` | ✅ `--log-level info` |

**代码对比**:

```119:121:scripts/start_dev.sh
# 设置调试ROI保存（可选）
export SAVE_DEBUG_ROI="${SAVE_DEBUG_ROI:-true}"
export DEBUG_ROI_DIR="${DEBUG_ROI_DIR:-debug/roi}"
```

---

## 🎯 适用场景分析

### start_dev.sh 适用场景

✅ **推荐使用**:
1. **本地开发环境**
   - 快速启动开发服务
   - 自动管理Docker服务
   - 自动初始化数据库
   - 支持热重载，方便调试

2. **功能开发**
   - 需要频繁重启服务
   - 需要调试ROI保存功能
   - 需要快速迭代

3. **测试环境**
   - 快速搭建测试环境
   - 自动处理依赖服务

❌ **不推荐使用**:
- 生产环境部署
- 需要高并发支持
- 需要多进程处理

---

### start_prod.sh 适用场景

✅ **推荐使用**:
1. **本地测试生产配置**
   - 使用生产环境配置测试
   - 验证生产环境配置是否正确
   - 测试Gunicorn多进程模式

2. **非容器化生产部署**
   - 直接在服务器上运行（不使用Docker）
   - 需要更多控制权
   - 需要自定义进程管理

3. **生产环境调试**
   - 需要复现生产环境问题
   - 需要测试生产配置

❌ **不推荐使用**:
- 实际生产环境部署（应使用Docker Compose）
- 开发环境（应使用 `start_dev.sh`）

---

## 🏗️ 生产环境部署架构

根据项目文档，**实际生产环境部署**应该使用：

### 推荐方式：Docker Compose 部署

```bash
# 1. 构建并推送镜像
bash scripts/build_prod_images.sh
bash scripts/push_to_registry.sh

# 2. 在生产服务器上部署
bash scripts/deploy_from_registry.sh
# 或
docker compose -f docker-compose.prod.yml up -d
```

**优势**:
- ✅ 容器化部署，环境一致
- ✅ 自动管理所有服务（数据库、Redis、API）
- ✅ 支持健康检查、自动重启
- ✅ 易于扩展和维护
- ✅ 支持Nginx反向代理、SSL等

### 备选方式：直接运行 start_prod.sh

```bash
# 在生产服务器上直接运行
bash scripts/start_prod.sh
```

**适用场景**:
- 非容器化环境
- 需要更多控制权
- 资源受限环境

---

## 📊 对比总结表

| 维度 | start_dev.sh | start_prod.sh | 推荐 |
|------|-------------|---------------|------|
| **开发环境** | ✅ 完美 | ❌ 不适用 | start_dev.sh |
| **生产环境（Docker）** | ❌ 不适用 | ⚠️ 可用但不推荐 | docker-compose.prod.yml |
| **生产环境（非Docker）** | ❌ 不适用 | ✅ 适用 | start_prod.sh |
| **本地测试生产配置** | ❌ 不适用 | ✅ 适用 | start_prod.sh |
| **自动服务管理** | ✅ 是 | ❌ 否 | - |
| **多进程支持** | ❌ 否 | ✅ 是 | - |
| **热重载** | ✅ 是 | ❌ 否 | - |
| **安全特性** | ⚠️ 基础 | ✅ 完整 | - |
| **性能优化** | ❌ 无 | ✅ 有 | - |

---

## 💡 最佳实践建议

### 1. 开发环境

```bash
# 使用 start_dev.sh
bash scripts/start_dev.sh
```

**原因**:
- 自动管理Docker服务
- 自动初始化数据库
- 支持热重载
- 自动处理端口冲突

### 2. 生产环境（推荐）

```bash
# 使用 Docker Compose 部署
bash scripts/deploy_from_registry.sh
# 或
docker compose -f docker-compose.prod.yml up -d
```

**原因**:
- 容器化部署，环境一致
- 自动管理所有服务
- 支持健康检查、自动重启
- 易于扩展和维护

### 3. 本地测试生产配置

```bash
# 使用 start_prod.sh
export ENVIRONMENT=production
bash scripts/start_prod.sh
```

**原因**:
- 使用生产环境配置
- 测试Gunicorn多进程模式
- 验证生产配置是否正确

---

## 🔧 改进建议

### 对 start_prod.sh 的改进建议

1. **添加Docker Compose支持**
   ```bash
   # 如果检测到 docker-compose.prod.yml，优先使用Docker Compose
   if [ -f "docker-compose.prod.yml" ]; then
       echo "检测到Docker Compose配置，建议使用:"
       echo "  docker compose -f docker-compose.prod.yml up -d"
       read -p "是否继续使用直接运行模式？(y/n) " -n 1 -r
       # ...
   fi
   ```

2. **添加systemd服务文件生成**
   ```bash
   # 生成systemd服务文件，方便管理
   if [ ! -f "/etc/systemd/system/pepgmp-api.service" ]; then
       echo "是否生成systemd服务文件？(y/n)"
       # 生成服务文件
   fi
   ```

3. **添加日志轮转配置**
   ```bash
   # 检查logrotate配置
   if [ ! -f "/etc/logrotate.d/pepgmp-api" ]; then
       echo "是否配置日志轮转？(y/n)"
       # 配置logrotate
   fi
   ```

### 对 start_dev.sh 的改进建议

1. **添加容器名称兼容性**
   ```bash
   # 支持新旧容器名称
   OLD_CONTAINERS=("pyt-postgres-dev" "pepgmp-postgres-dev")
   NEW_CONTAINERS=("pepgmp-postgres-dev")
   ```

2. **改进错误处理**
   ```bash
   # 更好的错误提示和恢复建议
   if ! docker ps | grep -q pepgmp-postgres-dev; then
       echo "尝试启动PostgreSQL..."
       # 提供更详细的错误信息
   fi
   ```

---

## 📝 结论

1. **开发环境**: 使用 `start_dev.sh` ✅
   - 自动管理服务
   - 支持热重载
   - 适合快速开发

2. **生产环境**: 优先使用 **Docker Compose** ✅
   - 容器化部署
   - 环境一致
   - 易于维护

3. **测试生产配置**: 使用 `start_prod.sh` ✅
   - 本地测试生产配置
   - 验证Gunicorn配置

4. **非容器化生产**: 使用 `start_prod.sh` ⚠️
   - 需要更多手动配置
   - 需要自行管理服务

**最终建议**:
- **开发**: `start_dev.sh`
- **生产**: `docker-compose.prod.yml` + `deploy_from_registry.sh`
- **测试生产配置**: `start_prod.sh`
