#!/bin/bash

# 开发环境启动脚本
set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 启动开发环境 ==="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source venv/bin/activate

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

# 检查python-dotenv
echo ""
echo "检查依赖..."
if ! python -c "import dotenv" 2>/dev/null; then
    echo "⚠️  python-dotenv未安装"
    read -p "是否现在安装？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install python-dotenv
    else
        echo "警告: 未安装python-dotenv，将仅使用环境变量"
    fi
fi

# 检查Docker服务
echo ""
echo "检查依赖服务..."
if command -v docker &> /dev/null; then
    if ! docker ps | grep -q pyt-postgres-dev; then
        echo "⚠️  PostgreSQL服务未运行"
        echo "   启动命令: docker-compose up -d database"
    else
        echo "✅ PostgreSQL服务运行中"
    fi
    
    if ! docker ps | grep -q pyt-redis-dev; then
        echo "⚠️  Redis服务未运行"
        echo "   启动命令: docker-compose up -d redis"
    else
        echo "✅ Redis服务运行中"
    fi
else
    echo "⚠️  Docker未安装或未运行"
fi

# 验证配置
echo ""
echo "验证配置..."
if python -c "from src.config.env_config import Config; Config().validate()" 2>/dev/null; then
    echo "✅ 配置验证通过"
else
    echo "❌ 配置验证失败，请检查.env文件"
    exit 1
fi

# 启动后端
echo ""
echo "✅ 启动后端服务..."
echo "   访问地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo "   按 Ctrl+C 停止服务"
echo ""

python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
