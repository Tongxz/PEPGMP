#!/bin/bash
# Docker工具函数
# Docker utility functions

# 获取Docker Compose命令
get_compose_command() {
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
        return 0
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
        return 0
    else
        return 1
    fi
}

# 启动Docker服务
start_docker_services() {
    local compose_file=$1
    local services=$2  # 服务列表，如 "database redis" 或 "api"

    local compose_cmd=$(get_compose_command)
    if [ -z "$compose_cmd" ]; then
        log_error "Docker Compose 未安装"
        return 1
    fi

    log_info "启动Docker服务: $services"
    $compose_cmd -f "$compose_file" up -d $services 2>&1 | grep -v "the attribute.*version.*is obsolete" || true

    return 0
}

# 检查Docker服务是否运行
check_docker_service() {
    local service_name=$1
    if docker ps --format "{{.Names}}" | grep -q "^${service_name}$"; then
        return 0  # 服务运行中
    else
        return 1  # 服务未运行
    fi
}

# 等待Docker服务就绪
wait_for_docker_service() {
    local service_name=$1
    local max_wait=${2:-30}  # 默认等待30秒

    log_info "等待服务就绪: $service_name (最多 ${max_wait} 秒)..."

    for i in $(seq 1 $max_wait); do
        if check_docker_service "$service_name"; then
            # 对于PostgreSQL，检查是否真的就绪
            if [[ "$service_name" == *"postgres"* ]]; then
                # 尝试连接数据库
                if docker exec "$service_name" pg_isready -U ${DATABASE_USER:-postgres} > /dev/null 2>&1; then
                    log_success "服务已就绪: $service_name"
                    return 0
                fi
            elif [[ "$service_name" == *"redis"* ]]; then
                # 尝试连接Redis
                if docker exec "$service_name" redis-cli ping > /dev/null 2>&1; then
                    log_success "服务已就绪: $service_name"
                    return 0
                fi
            else
                log_success "服务已就绪: $service_name"
                return 0
            fi
        fi

        if [ $i -lt $max_wait ]; then
            sleep 1
        fi
    done

    log_error "服务启动超时: $service_name"
    return 1
}

# 检查数据库连接
check_database_connection() {
    if [ -z "$DATABASE_URL" ]; then
        log_warning "DATABASE_URL 未设置"
        return 1
    fi

    # 从DATABASE_URL提取主机和端口
    local db_host=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local db_port=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if [ -z "$db_host" ] || [ -z "$db_port" ]; then
        log_warning "无法从DATABASE_URL解析主机和端口"
        return 1
    fi

    if command -v nc &> /dev/null; then
        if nc -z "$db_host" "$db_port" 2>/dev/null; then
            log_success "数据库可访问 ($db_host:$db_port)"
            return 0
        else
            log_warning "数据库不可访问 ($db_host:$db_port)"
            return 1
        fi
    else
        log_info "nc命令不可用，跳过数据库连接检查"
        return 0
    fi
}

# 检查Redis连接
check_redis_connection() {
    if [ -z "$REDIS_URL" ]; then
        log_warning "REDIS_URL 未设置"
        return 1
    fi

    # 从REDIS_URL提取主机和端口
    local redis_host=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local redis_port=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if [ -z "$redis_host" ]; then
        redis_host="localhost"
    fi
    if [ -z "$redis_port" ]; then
        redis_port="6379"
    fi

    if command -v nc &> /dev/null; then
        if nc -z "$redis_host" "$redis_port" 2>/dev/null; then
            log_success "Redis可访问 ($redis_host:$redis_port)"
            return 0
        else
            log_warning "Redis不可访问 ($redis_host:$redis_port)"
            return 1
        fi
    else
        log_info "nc命令不可用，跳过Redis连接检查"
        return 0
    fi
}

# 获取容器名称
get_container_name() {
    local compose_file=$1
    local service_name=$2

    if [ ! -f "$compose_file" ]; then
        log_error "Docker Compose文件不存在: $compose_file"
        return 1
    fi

    # 尝试从docker-compose.yml中提取容器名
    # 方法1: 从container_name字段提取
    local container_name=$(grep -A 10 "^[[:space:]]*${service_name}:" "$compose_file" | grep "container_name:" | sed 's/.*container_name:[[:space:]]*\(.*\)/\1/' | tr -d '"' | tr -d "'" | head -1)

    if [ -n "$container_name" ]; then
        echo "$container_name"
        return 0
    fi

    # 方法2: 使用项目名称 + 服务名称（Docker Compose默认命名规则）
    local project_name=$(basename "$(dirname "$(readlink -f "$compose_file")")" 2>/dev/null || echo "pyt")
    project_name=$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')

    # 尝试常见的容器命名模式
    local possible_names=(
        "${project_name}-${service_name}-1"
        "${project_name}_${service_name}_1"
        "pepgmp-${service_name}-dev"
        "pepgmp-${service_name}-prod"
        "pyt-${service_name}-dev"
    )

    for name in "${possible_names[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${name}$"; then
            echo "$name"
            return 0
        fi
    done

    # 如果都找不到，尝试通过服务名直接查找
    if docker ps --format "{{.Names}}" | grep -q "${service_name}"; then
        docker ps --format "{{.Names}}" | grep "${service_name}" | head -1
        return 0
    fi

    return 1
}

# 启动API容器
start_api_container() {
    local compose_file=$1
    local services=${2:-api}  # 默认启动api服务

    local compose_cmd=$(get_compose_command)
    if [ -z "$compose_cmd" ]; then
        log_error "Docker Compose 未安装"
        return 1
    fi

    log_info "启动容器服务: $services"
    $compose_cmd -f "$compose_file" up -d $services 2>&1 | grep -v "the attribute.*version.*is obsolete" || true

    if [ $? -eq 0 ]; then
        log_success "容器服务已启动"
        return 0
    else
        log_error "容器服务启动失败"
        return 1
    fi
}

