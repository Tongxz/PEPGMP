#!/bin/bash
# 服务管理函数
# Service management functions

# 激活虚拟环境
activate_venv() {
    if [ -d "venv" ]; then
        log_info "激活虚拟环境..."
        source venv/bin/activate
        log_success "虚拟环境已激活"
        return 0
    else
        log_warning "虚拟环境不存在"
        return 1
    fi
}

# 初始化数据库
init_database() {
    local python_cmd=$1
    local container_name=$2
    local wait_seconds=${3:-0}  # 等待秒数（默认0）

    if [ $wait_seconds -gt 0 ]; then
        log_info "等待 ${wait_seconds} 秒后初始化数据库..."
        sleep $wait_seconds
    fi

    log_info "检查数据库结构..."

    if [ -n "$container_name" ] && check_docker_service "$container_name"; then
        # 在容器内执行
        if docker exec "$container_name" python scripts/init_database.py 2>/dev/null; then
            log_success "数据库检查完成（容器内）"
            return 0
        else
            log_warning "数据库初始化警告（容器内，可能是连接问题或数据已存在）"
            return 0  # 非致命错误
        fi
    elif [ -n "$python_cmd" ]; then
        # 在宿主机执行
        if $python_cmd scripts/init_database.py 2>/dev/null; then
            log_success "数据库检查完成（宿主机）"
            return 0
        else
            log_warning "数据库初始化警告（宿主机，可能是连接问题或数据已存在）"
            return 0  # 非致命错误
        fi
    else
        log_warning "无法执行数据库初始化（容器未运行且宿主机无Python）"
        return 0  # 非致命错误
    fi
}

# 启动开发环境API（宿主机）
start_api_dev() {
    local port=$1

    log_success "启动后端服务..."
    log_info "访问地址: http://localhost:$port"
    log_info "API文档: http://localhost:$port/docs"
    log_info "ROI调试保存: ${SAVE_DEBUG_ROI:-true} (目录: ${DEBUG_ROI_DIR:-debug/roi})"
    log_info "按 Ctrl+C 停止服务"
    echo ""

    # 确保logs目录存在
    mkdir -p logs

    $PYTHON_CMD -m uvicorn src.api.app:app \
        --host 0.0.0.0 \
        --port "$port" \
        --reload \
        --log-level info
}

# 启动生产环境API（宿主机）
start_api_prod() {
    local port=$1
    local workers=${2:-4}

    log_success "启动生产服务..."
    log_info "访问地址: http://localhost:$port"
    log_info "API文档: http://localhost:$port/docs"
    log_info "健康检查: http://localhost:$port/api/v1/monitoring/health"
    log_info "Workers: $workers"
    log_info "按 Ctrl+C 停止服务"
    echo ""

    # 确保logs目录存在
    mkdir -p logs

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
}
