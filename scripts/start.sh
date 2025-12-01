#!/bin/bash
# 统一启动脚本
# Unified startup script for all deployment scenarios

set -e

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 加载公共函数库
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/env_detection.sh"
source "$SCRIPT_DIR/lib/config_validation.sh"
source "$SCRIPT_DIR/lib/docker_utils.sh"
source "$SCRIPT_DIR/lib/service_manager.sh"

# ==================== 参数解析 ====================

ENV=""
MODE="auto"
COMPOSE_FILE=""
PORT=8000
WORKERS=4
NO_CHECK=false
NO_INIT_DB=false
NO_VALIDATE=false

show_help() {
    cat << EOF
统一启动脚本 - 支持开发和生产环境部署

用法: $0 [选项]

选项:
  --env <dev|prod>              环境类型（必需）
  --mode <containerized|hybrid|host>  部署模式（可选，默认：auto）
  --compose-file <file>         Docker Compose文件（可选）
  --port <port>                 端口号（可选，默认：8000）
  --workers <num>               Gunicorn workers（可选，默认：4）
  --no-check                    跳过环境检查（可选）
  --no-init-db                  跳过数据库初始化（可选）
  --no-validate                 跳过配置验证（可选）
  --help                        显示此帮助信息

示例:
  # 开发环境
  $0 --env dev

  # 生产环境（容器化）
  $0 --env prod --mode containerized

  # 生产环境（宿主机）
  $0 --env prod --mode host

EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --no-check)
            NO_CHECK=true
            shift
            ;;
        --no-init-db)
            NO_INIT_DB=true
            shift
            ;;
        --no-validate)
            NO_VALIDATE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查必需参数
if [ -z "$ENV" ]; then
    log_error "必须指定环境类型: --env <dev|prod>"
    show_help
    exit 1
fi

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    log_error "环境类型必须是 dev 或 prod"
    exit 1
fi

# ==================== 环境检测 ====================

echo "========================================================================="
if [ "$ENV" = "dev" ]; then
    echo "                     启动开发环境"
else
    echo "                     启动生产环境"
fi
echo "========================================================================="
echo ""

if [ "$NO_CHECK" != "true" ]; then
    log_info "检测环境..."
    detect_environment
    echo ""
fi

# ==================== 用户检查 ====================

if [ "$EUID" -eq 0 ]; then
    log_warning "不建议使用root用户运行"
    if ! confirm_action "继续？"; then
        exit 1
    fi
fi

# ==================== 配置文件处理 ====================

ENV_FILE=""
if [ "$ENV" = "dev" ]; then
    ENV_FILE=".env"
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env文件不存在，从.env.example复制..."
            cp .env.example .env
            log_success "已创建.env文件"
            if confirm_action "是否现在编辑.env文件？"; then
                ${EDITOR:-nano} .env
            fi
        else
            log_error ".env文件不存在且无.env.example模板"
            exit 1
        fi
    fi
else
    ENV_FILE=".env.production"
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production文件不存在"
        if [ -f ".env.production.example" ]; then
            echo ""
            echo "创建步骤："
            echo "  cp .env.production.example .env.production"
            echo "  nano .env.production  # 修改配置"
            echo "  chmod 600 .env.production"
        fi
        exit 1
    fi
fi

# 加载环境变量
if ! load_env_file "$ENV_FILE" true; then
    exit 1
fi

# 设置环境变量
export ENVIRONMENT="$ENV"

# ==================== 配置验证 ====================

if [ "$NO_VALIDATE" != "true" ]; then
    validate_config "$PYTHON_CMD" "" "$COMPOSE_FILE" "$ENV_FILE" || {
        if [ "$ENV" = "prod" ]; then
            log_error "生产环境配置验证失败，退出"
            exit 1
        else
            log_warning "配置验证失败，但继续执行（开发环境）"
        fi
    }
    echo ""
fi

# ==================== 自动选择部署模式 ====================

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

# ==================== 部署函数 ====================

# 容器化部署
deploy_containerized() {
    log_info "使用容器化部署模式"

    # 确定Docker Compose文件
    if [ -z "$COMPOSE_FILE" ]; then
        if [ "$ENV" = "dev" ]; then
            COMPOSE_FILE="docker-compose.yml"
        else
            # 检查WSL专用配置
            if [ "$IS_WSL" = true ] && [ -f "docker-compose.prod.wsl.yml" ]; then
                COMPOSE_FILE="docker-compose.prod.wsl.yml"
                log_info "使用 WSL 专用配置文件"
            elif [ -f "docker-compose.prod.yml" ]; then
                COMPOSE_FILE="docker-compose.prod.yml"
            else
                log_error "找不到生产环境Docker Compose文件"
                exit 1
            fi
        fi
    fi

    # 检查Docker
    if [ "$HAS_DOCKER" != true ] || [ "$DOCKER_RUNNING" != true ]; then
        log_error "Docker不可用或未运行"
        exit 1
    fi

    # 检查Docker Compose
    if [ "$HAS_DOCKER_COMPOSE" != true ]; then
        log_error "Docker Compose不可用"
        exit 1
    fi

    # 检查端口占用
    if ! check_port "$PORT"; then
        if ! free_port "$PORT"; then
            exit 1
        fi
    fi
    echo ""

    # 启动服务
    if start_api_container "$COMPOSE_FILE" ""; then
        # 等待容器启动
        sleep 5

        # 获取API容器名
        API_CONTAINER=$(get_container_name "$COMPOSE_FILE" api)

        # 数据库初始化
        if [ "$NO_INIT_DB" != "true" ]; then
            init_database "$PYTHON_CMD" "$API_CONTAINER" 5
        fi

        # 显示访问信息
        echo ""
        log_success "服务已启动"
        log_info "访问地址: http://localhost:$PORT"
        log_info "API文档: http://localhost:$PORT/docs"
        if [ "$ENV" = "prod" ]; then
            log_info "健康检查: http://localhost:$PORT/api/v1/monitoring/health"
        fi
    else
        exit 1
    fi
}

# 混合部署（开发环境：DB容器 + 本地API）
deploy_hybrid() {
    log_info "使用混合部署模式（DB容器 + 本地API）"

    if [ "$ENV" != "dev" ]; then
        log_error "混合模式仅支持开发环境"
        exit 1
    fi

    # 检查Docker
    if [ "$HAS_DOCKER" != true ] || [ "$DOCKER_RUNNING" != true ]; then
        log_error "Docker不可用或未运行"
        exit 1
    fi

    # 检查Python
    if [ "$HAS_PYTHON" != true ]; then
        log_error "Python不可用"
        exit 1
    fi

    # 激活虚拟环境
    if [ "$HAS_VENV" = true ]; then
        activate_venv
    fi

    # 检查python-dotenv
    if ! $PYTHON_CMD -c "import dotenv" 2>/dev/null; then
        log_warning "python-dotenv未安装"
        if confirm_action "是否现在安装？"; then
            pip install python-dotenv
        fi
    fi

    # 启动Docker服务（数据库和Redis）
    log_info "启动Docker服务（数据库和Redis）..."
    if [ -z "$COMPOSE_FILE" ]; then
        COMPOSE_FILE="docker-compose.yml"
    fi

    start_docker_services "$COMPOSE_FILE" "database redis"

    # 等待服务就绪
    wait_for_docker_service "pepgmp-postgres-dev" 30
    wait_for_docker_service "pepgmp-redis-dev" 10

    # 检查连接
    check_database_connection
    check_redis_connection
    echo ""

    # 数据库初始化
    if [ "$NO_INIT_DB" != "true" ]; then
        init_database "$PYTHON_CMD" "" 0
    fi

    # 检查端口占用
    if ! check_port "$PORT"; then
        if ! free_port "$PORT"; then
            exit 1
        fi
    fi
    echo ""

    # 设置调试选项
    export SAVE_DEBUG_ROI="${SAVE_DEBUG_ROI:-true}"
    export DEBUG_ROI_DIR="${DEBUG_ROI_DIR:-debug/roi}"

    # 启动API服务
    start_api_dev "$PORT"
}

# 宿主机部署
deploy_host() {
    log_info "使用宿主机部署模式"

    # 检查Python
    if [ "$HAS_PYTHON" != true ]; then
        log_error "Python不可用"
        exit 1
    fi

    # 激活虚拟环境
    if [ "$HAS_VENV" = true ]; then
        activate_venv
    fi

    # 检查依赖服务连接
    if [ "$ENV" = "prod" ]; then
        check_database_connection || log_warning "数据库连接检查失败"
        check_redis_connection || log_warning "Redis连接检查失败"
        echo ""
    fi

    # 数据库初始化
    if [ "$NO_INIT_DB" != "true" ]; then
        init_database "$PYTHON_CMD" "" 0
    fi

    # 检查端口占用
    if ! check_port "$PORT"; then
        if ! free_port "$PORT"; then
            exit 1
        fi
    fi
    echo ""

    # 确认启动（生产环境）
    if [ "$ENV" = "prod" ]; then
        echo "========================================================================="
        echo "准备启动生产服务"
        echo "========================================================================="
        echo "  环境: $ENVIRONMENT"
        echo "  Workers: $WORKERS"
        echo "  端口: $PORT"
        echo "  日志: logs/"
        echo ""
        if ! confirm_action "确认启动？"; then
            echo "已取消"
            exit 0
        fi
        echo ""
    fi

    # 启动API服务
    if [ "$ENV" = "dev" ]; then
        start_api_dev "$PORT"
    else
        start_api_prod "$PORT" "$WORKERS"
    fi
}

# ==================== 执行部署 ====================

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

