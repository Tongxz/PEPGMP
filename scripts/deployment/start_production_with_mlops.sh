#!/bin/bash

# 生产环境启动脚本 - 包含MLOps功能
# 支持MLflow实验跟踪和DVC模型版本管理

set -e

echo "🚀 启动生产环境 (包含MLOps功能)..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

# 检查必要的目录
REQUIRED_DIRS=("config" "logs" "output" "data" "models" "mlruns")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "📁 创建目录: $dir"
        mkdir -p "$dir"
    fi
done

# 检查必要的文件
REQUIRED_FILES=("docker-compose.prod.yml" "config/unified_params.yaml")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    fi
done

# 检查环境变量文件
if [ ! -f ".env.prod" ]; then
    echo "⚠️  未找到 .env.prod 文件，使用默认配置"
    cat > .env.prod << EOF
# 生产环境配置
POSTGRES_DB=pyt_production
POSTGRES_USER=pyt_user
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_PORT=5432

REDIS_PASSWORD=change_me_in_production
REDIS_PORT=6379

API_PORT=8000
FRONTEND_PORT=8080
MLFLOW_PORT=5000

SECRET_KEY=change_me_in_production
JWT_SECRET=change_me_in_production
LOG_LEVEL=INFO

# MLOps配置
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=production_detection
DVC_REMOTE_URL=/dvc/remote
EOF
fi

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.mlops.yml down 2>/dev/null || true

# 启动基础服务
echo "🔧 启动基础服务 (数据库、Redis、API、前端)..."
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 等待基础服务启动
echo "⏳ 等待基础服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

# 启动MLOps服务
echo "🤖 启动MLOps服务 (MLflow、DVC)..."
docker-compose -f docker-compose.prod.mlops.yml --env-file .env.prod up -d

# 等待MLOps服务启动
echo "⏳ 等待MLOps服务启动..."
sleep 15

# 检查所有服务状态
echo "🔍 检查所有服务状态..."
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.mlops.yml ps

# 显示访问信息
echo ""
echo "✅ 生产环境启动完成！"
echo ""
echo "📊 服务访问地址:"
echo "  - 前端界面: http://localhost:8080"
echo "  - API接口: http://localhost:8000"
echo "  - API文档: http://localhost:8000/docs"
echo "  - MLflow UI: http://localhost:5000"
echo ""
echo "🔧 管理命令:"
echo "  - 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  - 停止服务: docker-compose -f docker-compose.prod.yml down"
echo "  - 重启服务: docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "📁 数据目录:"
echo "  - 实验数据: ./mlruns/"
echo "  - 模型文件: ./models/"
echo "  - 日志文件: ./logs/"
echo "  - 输出文件: ./output/"
