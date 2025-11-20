#!/bin/bash

# 生产环境启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================================================="
echo "                     启动生产环境"
echo "========================================================================="
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

# 激活虚拟环境（如果使用本地Python）
if [ -d "venv" ]; then
    echo "✅ 激活虚拟环境..."
    source venv/bin/activate
fi

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

# 设置环境
export ENVIRONMENT=production

# 加载生产环境配置
set -a
source .env.production
set +a

echo "✅ 已加载生产环境配置"
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
echo ""

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
