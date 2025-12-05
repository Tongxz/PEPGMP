#!/bin/bash
# 环境检测函数
# Environment detection functions

# 检测WSL环境
detect_wsl() {
    if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
        return 0  # 是WSL
    else
        return 1  # 不是WSL
    fi
}

# 检测Docker
detect_docker() {
    if check_command docker && docker info > /dev/null 2>&1; then
        return 0  # Docker可用
    else
        return 1  # Docker不可用
    fi
}

# 检测Docker Compose
detect_docker_compose() {
    if docker compose version &> /dev/null 2>&1; then
        return 0  # Docker Compose V2可用
    elif command -v docker-compose &> /dev/null; then
        return 0  # Docker Compose V1可用
    else
        return 1  # Docker Compose不可用
    fi
}

# 检测Python
detect_python() {
    if check_command python3; then
        PYTHON_CMD=$(command -v python3)
        return 0  # Python可用
    elif check_command python; then
        PYTHON_CMD=$(command -v python)
        return 0  # Python可用
    else
        PYTHON_CMD=""
        return 1  # Python不可用
    fi
}

# 检测虚拟环境
detect_venv() {
    if [ -d "venv" ]; then
        return 0  # 虚拟环境存在
    else
        return 1  # 虚拟环境不存在
    fi
}

# 综合环境检测
detect_environment() {
    # 初始化环境变量
    IS_WSL=false
    HAS_DOCKER=false
    DOCKER_RUNNING=false
    HAS_DOCKER_COMPOSE=false
    HAS_PYTHON=false
    HAS_VENV=false
    PYTHON_CMD=""

    # 检测WSL
    if detect_wsl; then
        IS_WSL=true
        log_info "检测到 WSL 环境"
    fi

    # 检测Docker
    if detect_docker; then
        HAS_DOCKER=true
        DOCKER_RUNNING=true
        log_success "Docker 可用且运行中"
    else
        log_warning "Docker 不可用或未运行"
    fi

    # 检测Docker Compose
    if detect_docker_compose; then
        HAS_DOCKER_COMPOSE=true
        if docker compose version &> /dev/null 2>&1; then
            log_success "Docker Compose V2 可用"
        else
            log_success "Docker Compose V1 可用"
        fi
    else
        log_warning "Docker Compose 不可用"
    fi

    # 检测Python
    if detect_python; then
        HAS_PYTHON=true
        log_success "Python 可用: $PYTHON_CMD"
    else
        log_warning "Python 不可用"
    fi

    # 检测虚拟环境
    if detect_venv; then
        HAS_VENV=true
        log_success "虚拟环境存在"
    else
        log_info "虚拟环境不存在（可选）"
    fi

    # 导出变量（供其他脚本使用）
    export IS_WSL
    export HAS_DOCKER
    export DOCKER_RUNNING
    export HAS_DOCKER_COMPOSE
    export HAS_PYTHON
    export HAS_VENV
    export PYTHON_CMD
}
