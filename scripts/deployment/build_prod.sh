#!/bin/bash
# 生产环境构建脚本

set -e

REGISTRY="192.168.30.83:5433"
PROJECT_NAME="pyt"
API_IMAGE="${REGISTRY}/${PROJECT_NAME}-api:prod"
FRONTEND_IMAGE="${REGISTRY}/${PROJECT_NAME}-frontend:prod"

echo "=========================================="
echo "生产环境构建和部署"
echo "=========================================="

# 构建API镜像
echo "构建API镜像..."
docker build -f Dockerfile.prod -t ${API_IMAGE} .

# 构建前端镜像
echo "构建前端镜像..."
docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE} .

# 推送镜像
echo "推送镜像..."
docker push ${API_IMAGE}
docker push ${FRONTEND_IMAGE}

# 部署服务
echo "部署服务..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
