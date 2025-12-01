#!/bin/bash
# 配置验证函数
# Configuration validation functions

# 加载环境变量文件
load_env_file() {
    local env_file=$1
    local strict=${2:-false}  # 是否严格模式（默认false）

    if [ ! -f "$env_file" ]; then
        log_error "$env_file 文件不存在"
        return 1
    fi

    # 检查文件权限（仅在生产环境或严格模式下）
    if [ "$strict" = "true" ] || [ "$ENVIRONMENT" = "production" ]; then
        local perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file" 2>/dev/null)
        if [ "$perms" != "600" ] && [ "$perms" != "400" ]; then
            log_warning "配置文件权限不安全（当前：$perms，建议：600）"
            if [ "$ENVIRONMENT" = "production" ]; then
                if confirm_action "是否修改为600？"; then
                    chmod 600 "$env_file"
                    log_success "权限已更新"
                fi
            fi
        fi
    fi

    # 加载环境变量
    set -a
    source "$env_file"
    set +a

    return 0
}

# 验证配置
validate_config() {
    local python_cmd=$1
    local container_name=$2
    local compose_file=$3
    local env_file=$4

    log_info "验证配置..."

    if [ -n "$container_name" ] && [ -n "$compose_file" ]; then
        # 在容器内执行
        local compose_cmd=$(get_compose_command)
        local api_container=$(get_container_name "$compose_file" api)

        if [ -n "$api_container" ] && docker ps --format "{{.Names}}" | grep -q "^${api_container}$"; then
            if docker exec "$api_container" python scripts/validate_config.py 2>/dev/null; then
                log_success "配置验证通过（容器内）"
                return 0
            else
                log_error "配置验证失败（容器内）"
                return 1
            fi
        else
            log_warning "API容器未运行，跳过容器内验证"
            return 0
        fi
    elif [ -n "$python_cmd" ]; then
        # 在宿主机执行
        if $python_cmd scripts/validate_config.py 2>/dev/null; then
            log_success "配置验证通过（宿主机）"
            return 0
        else
            log_error "配置验证失败（宿主机）"
            return 1
        fi
    else
        log_warning "无法验证配置（Python不可用且容器未运行）"
        return 0
    fi
}
