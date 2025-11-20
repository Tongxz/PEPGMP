#!/bin/bash

# 生产环境启动脚本 (WSL 版本)
# Production Environment Startup Script (WSL Version)
# 在 Windows WSL 环境中运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================================================="
echo "                     启动生产环境 (WSL)"
echo "========================================================================="
echo ""

# 检测 WSL 环境
if [ -f /proc/version ]; then
    if grep -qi microsoft /proc/version; then
        echo "✅ 检测到 WSL 环境"
        WSL_DISTRO=$(wslpath -u "$(wslvar USERPROFILE)" 2>/dev/null || echo "WSL")
        echo "  WSL 发行版: ${WSL_DISTRO:-未知}"
    else
        echo "⚠️  未检测到 WSL 环境，但继续执行..."
    fi
else
    echo "⚠️  无法检测 WSL 环境，但继续执行..."
fi
echo ""

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  警告：不建议使用root用户运行"
   read -p "继续？(y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi

# 检查虚拟环境（可选，如果使用本地 Python）
if [ -d "venv" ]; then
    echo "✅ 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查.env.production文件
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production文件不存在"
    echo ""
    if [ -f ".env.production.example" ]; then
        echo "创建步骤："
        echo "  cp .env.production.example .env.production"
        echo "  nano .env.production  # 或使用其他编辑器"
        echo "  chmod 600 .env.production"
    fi
    exit 1
fi

# 检查文件权限
file_perms=$(stat -c %a .env.production 2>/dev/null || stat -f %A .env.production 2>/dev/null)
if [ "$file_perms" != "600" ] && [ "$file_perms" != "400" ]; then
    echo "⚠️  警告：.env.production文件权限不安全（当前：$file_perms）"
    read -p "是否修改为600？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        chmod 600 .env.production
        echo "✅ 权限已更新"
    fi
fi

# 设置环境
export ENVIRONMENT=production

# 加载生产环境配置
echo "✅ 加载生产环境配置..."
set -a
source .env.production
set +a
echo ""

# 验证配置
echo "验证配置..."
if python scripts/validate_config.py; then
    echo "✅ 配置验证通过"
else
    echo "❌ 配置验证失败"
    exit 1
fi
echo ""

# 检查必需的服务
echo "检查依赖服务..."

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    echo ""
    echo "安装步骤："
    echo "  1. 安装 Docker Desktop for Windows"
    echo "  2. 在 Docker Desktop Settings > General 中启用 'Use the WSL 2 based engine'"
    echo "  3. 在 Docker Desktop Settings > Resources > WSL Integration 中启用当前 WSL 发行版"
    echo "  4. 重启 WSL: wsl --shutdown (在 Windows PowerShell 中)"
    exit 1
fi

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行"
    echo ""
    echo "请确保："
    echo "  1. Docker Desktop 正在运行"
    echo "  2. WSL 集成已启用（Docker Desktop Settings > Resources > WSL Integration）"
    echo "  3. 当前 WSL 发行版已启用 Docker 集成"
    exit 1
fi

echo "✅ Docker运行中"

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

# 检查数据库连接（如果配置了）
if [[ $DATABASE_URL == postgresql://* ]]; then
    db_host=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    db_port=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    if [ -n "$db_host" ] && [ -n "$db_port" ]; then
        echo "检查PostgreSQL连接 ($db_host:$db_port)..."
        if command -v nc &> /dev/null; then
            if nc -z $db_host $db_port 2>/dev/null; then
                echo "✅ PostgreSQL可访问 ($db_host:$db_port)"
            else
                echo "⚠️  PostgreSQL不可访问 ($db_host:$db_port)"
            fi
        fi
    fi
fi

# 检查Redis连接（如果配置了）
if [[ $REDIS_URL == redis://* ]]; then
    redis_host=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    redis_port=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    if [ -n "$redis_host" ] && [ -n "$redis_port" ]; then
        echo "检查Redis连接 ($redis_host:$redis_port)..."
        if command -v nc &> /dev/null; then
            if nc -z $redis_host $redis_port 2>/dev/null; then
                echo "✅ Redis可访问 ($redis_host:$redis_port)"
            else
                echo "⚠️  Redis不可访问 ($redis_host:$redis_port)"
            fi
        fi
    fi
fi

echo ""

# 确认启动
echo "========================================================================="
echo "准备启动生产服务"
echo "========================================================================="
echo "  环境: $ENVIRONMENT"
echo "  Workers: ${GUNICORN_WORKERS:-4}"
echo "  端口: ${API_PORT:-8000}"
echo "  日志: /app/logs/"
echo ""
read -p "确认启动？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "✅ 启动生产服务..."
echo "   访问地址: http://localhost:${API_PORT:-8000}"
echo "   API文档: http://localhost:${API_PORT:-8000}/docs"
echo "   健康检查: http://localhost:${API_PORT:-8000}/api/v1/monitoring/health"
echo "   按 Ctrl+C 停止服务"
echo ""

# 自动初始化/迁移数据库
echo "🔄 检查数据库结构..."
if python scripts/init_database.py; then
    echo "✅ 数据库检查完成"
else
    echo "⚠️  数据库初始化警告 (非致命错误，可能是连接问题或数据已存在)"
fi
echo ""

# 检查并清理端口占用
echo "检查端口占用..."
PORT=${API_PORT:-8000}
if command -v lsof &> /dev/null; then
    if lsof -ti:${PORT} > /dev/null 2>&1; then
        echo "⚠️  端口 ${PORT} 已被占用，正在停止占用进程..."
        lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
        sleep 2
        if lsof -ti:${PORT} > /dev/null 2>&1; then
            echo "❌ 无法停止占用端口 ${PORT} 的进程，请手动处理"
            echo "提示: 可以使用以下命令查看占用端口的进程:"
            echo "  lsof -i:${PORT}"
            echo "  netstat -tulpn | grep :${PORT}"
            exit 1
        else
            echo "✅ 端口 ${PORT} 已释放"
        fi
    else
        echo "✅ 端口 ${PORT} 可用"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":${PORT} "; then
        echo "⚠️  端口 ${PORT} 已被占用"
        echo "请手动停止占用端口的进程"
        netstat -tulpn | grep ":${PORT} "
        exit 1
    else
        echo "✅ 端口 ${PORT} 可用"
    fi
else
    echo "⚠️  无法检查端口占用（lsof 和 netstat 都不可用）"
fi
echo ""

# 启动服务（使用Docker Compose）
echo "启动Docker Compose服务..."

# 检查是否存在 WSL 专用配置文件
COMPOSE_FILE="docker-compose.prod.yml"
if [ -f "docker-compose.prod.wsl.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.wsl.yml"
    echo "使用 WSL 专用配置文件: $COMPOSE_FILE"
fi

# 检查 Docker Compose 版本
if docker compose version &> /dev/null; then
    # Docker Compose V2
    docker compose -f $COMPOSE_FILE up -d
else
    # Docker Compose V1
    docker-compose -f $COMPOSE_FILE up -d
fi

if [ $? -ne 0 ]; then
    echo "❌ 服务启动失败"
    exit 1
fi

echo ""
echo "✅ 生产服务已启动"
echo ""
echo "查看服务状态:"
if docker compose version &> /dev/null; then
    docker compose -f $COMPOSE_FILE ps
else
    docker-compose -f $COMPOSE_FILE ps
fi
echo ""
echo "查看日志:"
if docker compose version &> /dev/null; then
    echo "  docker compose -f $COMPOSE_FILE logs -f api"
else
    echo "  docker-compose -f $COMPOSE_FILE logs -f api"
fi
echo ""
echo "停止服务:"
if docker compose version &> /dev/null; then
    echo "  docker compose -f $COMPOSE_FILE down"
else
    echo "  docker-compose -f $COMPOSE_FILE down"
fi
echo ""

