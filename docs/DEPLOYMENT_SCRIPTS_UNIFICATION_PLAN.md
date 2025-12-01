# 部署脚本统一方案

## 📋 当前脚本分析

### 现有脚本概览

| 脚本 | 用途 | 部署方式 | Python环境 | 数据库/Redis | 应用运行位置 |
|------|------|---------|------------|--------------|-------------|
| `start_dev.sh` | 开发环境 | 混合（DB容器+本地API） | ✅ 必须（宿主机） | ✅ Docker Compose | 宿主机（uvicorn） |
| `start_prod.sh` | 生产环境 | 非容器化 | ✅ 必须（宿主机） | ❌ 需手动启动 | 宿主机（Gunicorn） |
| `start_prod_wsl.sh` | WSL生产环境 | 完全容器化 | ⚠️ 可选（容器内） | ✅ Docker Compose | 容器（Gunicorn） |

### 共同功能点

所有脚本都包含：
1. ✅ 环境检测和验证
2. ✅ 配置文件检查（.env 或 .env.production）
3. ✅ 配置验证（validate_config.py）
4. ✅ 数据库初始化（init_database.py）
5. ✅ 端口占用检查
6. ✅ 服务启动

### 差异点

| 功能 | start_dev.sh | start_prod.sh | start_prod_wsl.sh |
|------|--------------|---------------|-------------------|
| **环境变量文件** | `.env` | `.env.production` | `.env.production` |
| **Python检测** | 必须存在 | 必须存在 | 可选（容器内执行） |
| **虚拟环境** | 必须存在 | 可选 | 可选 |
| **Docker检查** | 检查并启动DB/Redis | 仅检查连接 | 必须（启动所有服务） |
| **应用服务器** | uvicorn (开发模式) | Gunicorn | Gunicorn (容器内) |
| **热重载** | ✅ 启用 | ❌ 禁用 | ❌ 禁用 |
| **日志级别** | INFO | INFO | INFO |
| **WSL检测** | ❌ 无 | ❌ 无 | ✅ 有 |

---

## 🎯 统一方案设计

### 方案概述

创建一个**统一的启动脚本** `scripts/start.sh`，通过**环境参数**和**配置文件**控制不同的部署模式。

### 核心设计原则

1. **单一入口点**：一个脚本支持所有场景
2. **参数驱动**：通过命令行参数控制行为
3. **环境自适应**：自动检测环境（WSL、Docker、Python等）
4. **向后兼容**：保留现有脚本作为快捷方式
5. **代码复用**：提取公共函数到共享库

---

## 📐 统一脚本架构

### 脚本结构

```
scripts/
├── start.sh                    # 统一启动脚本（主入口）
├── lib/
│   ├── common.sh               # 公共函数库
│   ├── env_detection.sh        # 环境检测函数
│   ├── config_validation.sh    # 配置验证函数
│   ├── docker_utils.sh         # Docker工具函数
│   └── service_manager.sh     # 服务管理函数
├── start_dev.sh                # 开发环境快捷方式（调用start.sh）
├── start_prod.sh               # 生产环境快捷方式（调用start.sh）
└── start_prod_wsl.sh           # WSL生产环境快捷方式（调用start.sh）
```

### 使用方式

```bash
# 方式1：使用统一脚本（推荐）
./scripts/start.sh --env dev
./scripts/start.sh --env prod --mode containerized
./scripts/start.sh --env prod --mode host

# 方式2：使用快捷方式（向后兼容）
./scripts/start_dev.sh
./scripts/start_prod.sh
./scripts/start_prod_wsl.sh
```

---

## 🔧 统一脚本功能设计

### 命令行参数

```bash
./scripts/start.sh [OPTIONS]

选项：
  --env <dev|prod>              环境类型（必需）
  --mode <containerized|host>   部署模式（可选，默认：auto）
  --compose-file <file>         Docker Compose文件（可选）
  --port <port>                 端口号（可选，默认：8000）
  --workers <num>               Gunicorn workers（可选，默认：4）
  --no-check                   跳过环境检查（可选）
  --no-init-db                 跳过数据库初始化（可选）
  --help                        显示帮助信息
```

### 环境检测逻辑

```bash
# 自动检测顺序
1. 检测 WSL 环境
2. 检测 Docker 可用性
3. 检测 Python 可用性
4. 检测虚拟环境
5. 根据检测结果自动选择最佳部署模式
```

### 部署模式选择

| 环境 | Docker可用 | Python可用 | 推荐模式 | 说明 |
|------|-----------|-----------|---------|------|
| dev | ✅ | ✅ | **混合模式** | DB容器 + 本地API |
| dev | ✅ | ❌ | **完全容器化** | 所有服务容器化 |
| prod | ✅ | ✅ | **容器化（推荐）** | 所有服务容器化 |
| prod | ✅ | ❌ | **容器化** | 所有服务容器化 |
| prod | ❌ | ✅ | **宿主机模式** | 所有服务宿主机运行 |
| WSL | ✅ | ✅ | **容器化（推荐）** | 所有服务容器化 |
| WSL | ✅ | ❌ | **容器化** | 所有服务容器化 |

---

## 📝 统一脚本实现方案

### 1. 公共函数库 (`lib/common.sh`)

```bash
#!/bin/bash
# 公共函数库

# 颜色输出
log_info() { echo "ℹ️  $1"; }
log_success() { echo "✅ $1"; }
log_warning() { echo "⚠️  $1"; }
log_error() { echo "❌ $1"; }

# 检查命令是否存在
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查端口占用
check_port() {
    local port=$1
    if lsof -ti:${port} > /dev/null 2>&1; then
        return 1  # 端口被占用
    else
        return 0  # 端口可用
    fi
}

# 释放端口
free_port() {
    local port=$1
    # ... 实现逻辑
}
```

### 2. 环境检测 (`lib/env_detection.sh`)

```bash
#!/bin/bash
# 环境检测函数

detect_wsl() {
    if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
        return 0  # 是WSL
    else
        return 1  # 不是WSL
    fi
}

detect_docker() {
    if check_command docker && docker info > /dev/null 2>&1; then
        return 0  # Docker可用
    else
        return 1  # Docker不可用
    fi
}

detect_python() {
    if check_command python3 || check_command python; then
        PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
        return 0  # Python可用
    else
        return 1  # Python不可用
    fi
}

detect_venv() {
    if [ -d "venv" ]; then
        return 0  # 虚拟环境存在
    else
        return 1  # 虚拟环境不存在
    fi
}
```

### 3. 配置管理 (`lib/config_validation.sh`)

```bash
#!/bin/bash
# 配置验证函数

load_env_file() {
    local env_file=$1
    if [ ! -f "$env_file" ]; then
        log_error "$env_file 文件不存在"
        return 1
    fi
    
    # 检查文件权限
    local perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file" 2>/dev/null)
    if [ "$perms" != "600" ] && [ "$perms" != "400" ]; then
        log_warning "配置文件权限不安全（当前：$perms）"
    fi
    
    # 加载环境变量
    set -a
    source "$env_file"
    set +a
    return 0
}

validate_config() {
    local python_cmd=$1
    if [ -n "$python_cmd" ]; then
        # 在宿主机执行
        $python_cmd scripts/validate_config.py
    else
        # 在容器内执行
        docker exec $API_CONTAINER python scripts/validate_config.py
    fi
}
```

### 4. Docker工具 (`lib/docker_utils.sh`)

```bash
#!/bin/bash
# Docker工具函数

get_compose_command() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        return 1
    fi
}

start_docker_services() {
    local compose_file=$1
    local services=$2  # 服务列表，如 "database redis" 或 "api"
    
    local compose_cmd=$(get_compose_command)
    if [ -z "$compose_cmd" ]; then
        log_error "Docker Compose 未安装"
        return 1
    fi
    
    $compose_cmd -f "$compose_file" up -d $services
}

check_docker_service() {
    local service_name=$1
    if docker ps --format "{{.Names}}" | grep -q "^${service_name}$"; then
        return 0  # 服务运行中
    else
        return 1  # 服务未运行
    fi
}
```

### 5. 服务管理 (`lib/service_manager.sh`)

```bash
#!/bin/bash
# 服务管理函数

init_database() {
    local python_cmd=$1
    local container_name=$2
    
    if [ -n "$container_name" ] && check_docker_service "$container_name"; then
        # 在容器内执行
        docker exec "$container_name" python scripts/init_database.py
    elif [ -n "$python_cmd" ]; then
        # 在宿主机执行
        $python_cmd scripts/init_database.py
    else
        log_warning "无法执行数据库初始化（容器未运行且宿主机无Python）"
        return 1
    fi
}

start_api_host() {
    local env=$1
    local port=$2
    local workers=$3
    
    if [ "$env" = "dev" ]; then
        # 开发模式：uvicorn
        python -m uvicorn src.api.app:app \
            --host 0.0.0.0 \
            --port "$port" \
            --reload \
            --log-level info
    else
        # 生产模式：Gunicorn
        gunicorn src.api.app:app \
            --workers "$workers" \
            --worker-class uvicorn.workers.UvicornWorker \
            --bind 0.0.0.0:"$port" \
            --timeout 120 \
            --keepalive 5 \
            --max-requests 1000 \
            --max-requests-jitter 50 \
            --access-logfile logs/access.log \
            --error-logfile logs/error.log \
            --log-level info
    fi
}
```

### 6. 主脚本 (`start.sh`)

```bash
#!/bin/bash
# 统一启动脚本

set -e

# 加载公共函数库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/env_detection.sh"
source "$SCRIPT_DIR/lib/config_validation.sh"
source "$SCRIPT_DIR/lib/docker_utils.sh"
source "$SCRIPT_DIR/lib/service_manager.sh"

# 解析命令行参数
ENV=""
MODE="auto"
COMPOSE_FILE=""
PORT=8000
WORKERS=4
NO_CHECK=false
NO_INIT_DB=false

# ... 参数解析逻辑 ...

# 环境检测
IS_WSL=false
HAS_DOCKER=false
HAS_PYTHON=false
HAS_VENV=false
PYTHON_CMD=""

if detect_wsl; then
    IS_WSL=true
    log_info "检测到 WSL 环境"
fi

if detect_docker; then
    HAS_DOCKER=true
    log_success "Docker 可用"
else
    log_warning "Docker 不可用"
fi

if detect_python; then
    HAS_PYTHON=true
    log_success "Python 可用: $PYTHON_CMD"
else
    log_warning "Python 不可用"
fi

if detect_venv; then
    HAS_VENV=true
    source venv/bin/activate
    log_success "虚拟环境已激活"
fi

# 自动选择部署模式
if [ "$MODE" = "auto" ]; then
    if [ "$ENV" = "dev" ]; then
        if [ "$HAS_DOCKER" = true ] && [ "$HAS_PYTHON" = true ]; then
            MODE="hybrid"  # 混合模式：DB容器 + 本地API
        elif [ "$HAS_DOCKER" = true ]; then
            MODE="containerized"  # 完全容器化
        else
            MODE="host"  # 宿主机模式
        fi
    else  # prod
        if [ "$HAS_DOCKER" = true ]; then
            MODE="containerized"  # 容器化（推荐）
        elif [ "$HAS_PYTHON" = true ]; then
            MODE="host"  # 宿主机模式
        else
            log_error "无法确定部署模式：Docker和Python都不可用"
            exit 1
        fi
    fi
fi

log_info "部署模式: $MODE"

# 根据模式执行部署
case "$MODE" in
    "containerized")
        deploy_containerized
        ;;
    "hybrid")
        deploy_hybrid
        ;;
    "host")
        deploy_host
        ;;
    *)
        log_error "未知的部署模式: $MODE"
        exit 1
        ;;
esac
```

---

## 🔄 迁移计划

### 阶段1：创建统一脚本（不破坏现有脚本）

1. ✅ 创建 `scripts/lib/` 目录和公共函数库
2. ✅ 创建 `scripts/start.sh` 统一脚本
3. ✅ 保留现有脚本作为快捷方式（调用 `start.sh`）

### 阶段2：更新现有脚本（向后兼容）

1. ✅ 更新 `start_dev.sh` 调用 `start.sh --env dev`
2. ✅ 更新 `start_prod.sh` 调用 `start.sh --env prod --mode host`
3. ✅ 更新 `start_prod_wsl.sh` 调用 `start.sh --env prod --mode containerized`

### 阶段3：文档更新

1. ✅ 更新部署文档，推荐使用统一脚本
2. ✅ 保留快捷方式的使用说明（向后兼容）

---

## 📊 方案对比

### 统一前

- ❌ 3个独立脚本，代码重复率高
- ❌ 功能不一致（有些有WSL检测，有些没有）
- ❌ 维护成本高（修改需要同步3个文件）
- ❌ 用户体验不一致

### 统一后

- ✅ 1个主脚本 + 公共函数库，代码复用
- ✅ 统一的功能和体验
- ✅ 维护成本低（修改一处即可）
- ✅ 向后兼容（保留快捷方式）
- ✅ 灵活配置（通过参数控制）

---

## 🎯 推荐实施步骤

1. **第一步**：创建公共函数库（`lib/`目录）
2. **第二步**：创建统一脚本（`start.sh`）
3. **第三步**：测试统一脚本（所有场景）
4. **第四步**：更新现有脚本为快捷方式
5. **第五步**：更新文档
6. **第六步**：逐步废弃旧脚本（可选）

---

## ✅ 方案优势

1. **统一性**：一个脚本支持所有场景
2. **灵活性**：通过参数控制行为
3. **可维护性**：代码复用，易于维护
4. **向后兼容**：保留现有快捷方式
5. **可扩展性**：易于添加新功能
6. **用户体验**：一致的交互体验

---

**最后更新：** 2025-11-18


