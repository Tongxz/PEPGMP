#!/bin/bash
# 公共函数库
# Common function library

# ==================== 日志函数 ====================

log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_warning() {
    echo "⚠️  $1"
}

log_error() {
    echo "❌ $1" >&2
}

# ==================== 工具函数 ====================

# 检查命令是否存在
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        if lsof -ti:${port} > /dev/null 2>&1; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -an 2>/dev/null | grep -q ":${port}.*LISTEN"; then
            return 1  # 端口被占用
        else
            return 0  # 端口可用
        fi
    else
        log_warning "无法检查端口占用（lsof和netstat都不可用）"
        return 0  # 假设端口可用
    fi
}

# 释放端口（杀死占用端口的进程）
free_port() {
    local port=$1
    log_warning "端口 ${port} 已被占用，正在停止占用进程..."

    if command -v lsof &> /dev/null; then
        local pids=$(lsof -ti:${port} 2>/dev/null)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 2

            if check_port "$port"; then
                log_success "端口 ${port} 已释放"
                return 0
            else
                log_error "无法释放端口 ${port}"
                return 1
            fi
        fi
    else
        log_error "无法释放端口（lsof不可用）"
        return 1
    fi
}

# 确认操作
confirm_action() {
    local prompt="$1"
    read -p "$prompt (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}
