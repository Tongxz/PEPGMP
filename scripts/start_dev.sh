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

# 检查并启动Docker服务
echo ""
echo "检查依赖服务..."
if command -v docker &> /dev/null; then
    # 检查Docker是否正在运行
    if ! docker info > /dev/null 2>&1; then
        echo "⚠️  Docker未运行，请启动Docker Desktop"
        echo "   等待Docker启动..."
        sleep 5
        if ! docker info > /dev/null 2>&1; then
            echo "❌ Docker仍未就绪，请手动启动Docker Desktop后重试"
            exit 1
        fi
    fi

    # 检查并启动PostgreSQL
    if ! docker ps | grep -q pyt-postgres-dev; then
        echo "⚠️  PostgreSQL服务未运行，正在启动..."
        docker-compose up -d database 2>&1 | grep -v "the attribute.*version.*is obsolete" || true
        echo "   等待PostgreSQL启动..."
        sleep 8
        if docker ps | grep -q pyt-postgres-dev; then
            echo "✅ PostgreSQL服务已启动"
        else
            echo "❌ PostgreSQL启动失败"
            exit 1
        fi
    else
        echo "✅ PostgreSQL服务运行中"
    fi

    # 检查并启动Redis
    if ! docker ps | grep -q pyt-redis-dev; then
        echo "⚠️  Redis服务未运行，正在启动..."
        docker-compose up -d redis 2>&1 | grep -v "the attribute.*version.*is obsolete" || true
        echo "   等待Redis启动..."
        sleep 3
        if docker ps | grep -q pyt-redis-dev; then
            echo "✅ Redis服务已启动"
        else
            echo "❌ Redis启动失败"
            exit 1
        fi
    else
        echo "✅ Redis服务运行中"
    fi
else
    echo "⚠️  Docker未安装或未运行"
    echo "   请安装Docker Desktop或使用其他方式提供数据库服务"
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

# 设置调试ROI保存（可选）
export SAVE_DEBUG_ROI="${SAVE_DEBUG_ROI:-true}"
export DEBUG_ROI_DIR="${DEBUG_ROI_DIR:-debug/roi}"

# 自动初始化/迁移数据库
echo "🔄 检查数据库结构..."
if python scripts/init_database.py; then
    echo "✅ 数据库检查完成"
else
    echo "⚠️  数据库初始化警告 (非致命错误，可能是连接问题或数据已存在)"
fi
echo ""

# 检查并清理端口占用
echo ""
echo "检查端口占用..."
PORT=8000
if lsof -ti:${PORT} > /dev/null 2>&1; then
    echo "⚠️  端口 ${PORT} 已被占用，正在停止占用进程..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 2
    if lsof -ti:${PORT} > /dev/null 2>&1; then
        echo "❌ 无法停止占用端口 ${PORT} 的进程，请手动处理"
        exit 1
    else
        echo "✅ 端口 ${PORT} 已释放"
    fi
else
    echo "✅ 端口 ${PORT} 可用"
fi
echo ""

# 启动后端
echo ""
echo "✅ 启动后端服务..."
echo "   访问地址: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo "   ROI调试保存: ${SAVE_DEBUG_ROI} (目录: ${DEBUG_ROI_DIR})"
echo "   按 Ctrl+C 停止服务"
echo ""

python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
