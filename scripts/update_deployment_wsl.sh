#!/bin/bash
# WSL/Ubuntu 快速更新部署脚本
# Purpose: 快速更新前后端代码并重新部署
# Usage: bash scripts/update_deployment_wsl.sh [DEPLOY_DIR] [VERSION_TAG] [UPDATE_TYPE]

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DEPLOY_DIR="${1:-$HOME/projects/Pyt-deploy}"
VERSION_TAG="${2:-$(date +%Y%m%d)}"
UPDATE_TYPE="${3:-all}"  # all, backend, frontend

echo "========================================================================="
echo -e "${BLUE}WSL/Ubuntu 快速更新部署${NC}"
echo "========================================================================="
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "部署目录: $DEPLOY_DIR"
echo "新镜像版本: $VERSION_TAG"
echo "更新类型: $UPDATE_TYPE"
echo ""

# Check functions
check_passed() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_failed() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

check_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# ==================== 步骤 1: 检查环境 ====================
check_info "步骤 1: 检查环境..."

if [ ! -d "$PROJECT_ROOT" ]; then
    check_failed "项目根目录不存在: $PROJECT_ROOT"
fi

if [ ! -d "$DEPLOY_DIR" ]; then
    check_failed "部署目录不存在: $DEPLOY_DIR"
fi

if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    check_failed ".env.production 不存在，请先运行完整部署"
fi

check_passed "环境检查通过"

# ==================== 步骤 2: 同步代码（如需要） ====================
check_info "步骤 2: 同步代码..."

# 检查是否需要从 Windows 文件系统同步
if [ -d "/mnt/c" ] && [ -f "/mnt/c/Users/$USER/Code/Pyt/docker-compose.prod.yml" ]; then
    WINDOWS_PROJECT="/mnt/c/Users/$USER/Code/Pyt"
    check_info "检测到 Windows 文件系统中的项目"
    read -p "是否从 Windows 文件系统同步代码? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        check_info "同步代码到 WSL 文件系统..."
        if [ -f "$PROJECT_ROOT/scripts/sync_code_to_wsl.sh" ]; then
            bash "$PROJECT_ROOT/scripts/sync_code_to_wsl.sh" "$WINDOWS_PROJECT" "$PROJECT_ROOT"
        else
            check_warning "同步脚本不存在，手动同步..."
            rsync -avz --progress \
                --exclude='node_modules' \
                --exclude='venv' \
                --exclude='dist' \
                --exclude='.git' \
                "$WINDOWS_PROJECT/" "$PROJECT_ROOT/"
        fi
        check_passed "代码同步完成"
    fi
fi

# ==================== 步骤 3: 构建新镜像 ====================
check_info "步骤 3: 构建新镜像..."

cd "$PROJECT_ROOT"

case "$UPDATE_TYPE" in
    backend)
        check_info "仅构建后端镜像..."
        export DOCKER_BUILDKIT=1
        docker build -f Dockerfile.prod \
            -t pepgmp-backend:$VERSION_TAG \
            -t pepgmp-backend:latest \
            .
        check_passed "后端镜像构建完成"
        ;;
    frontend)
        check_info "仅构建前端镜像..."
        export DOCKER_BUILDKIT=1
        docker build -f Dockerfile.frontend \
            --build-arg VITE_API_BASE=/api/v1 \
            --build-arg BASE_URL=/ \
            --build-arg SKIP_TYPE_CHECK=true \
            -t pepgmp-frontend:$VERSION_TAG \
            -t pepgmp-frontend:latest \
            .
        check_passed "前端镜像构建完成"
        ;;
    all)
        check_info "构建所有镜像..."
        bash "$PROJECT_ROOT/scripts/build_prod_only.sh" "$VERSION_TAG"
        check_passed "所有镜像构建完成"
        ;;
    *)
        check_failed "未知的更新类型: $UPDATE_TYPE (支持: all, backend, frontend)"
        ;;
esac

# 验证镜像
check_info "验证镜像..."
BACKEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-backend:$VERSION_TAG" || echo "0")
FRONTEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-frontend:$VERSION_TAG" || echo "0")

if [ "$UPDATE_TYPE" = "backend" ] || [ "$UPDATE_TYPE" = "all" ]; then
    if [ "$BACKEND_FOUND" -gt 0 ]; then
        check_passed "后端镜像存在: pepgmp-backend:$VERSION_TAG"
    else
        check_failed "后端镜像不存在"
    fi
fi

if [ "$UPDATE_TYPE" = "frontend" ] || [ "$UPDATE_TYPE" = "all" ]; then
    if [ "$FRONTEND_FOUND" -gt 0 ]; then
        check_passed "前端镜像存在: pepgmp-frontend:$VERSION_TAG"
    else
        check_failed "前端镜像不存在"
    fi
fi

echo ""

# ==================== 步骤 4: 更新配置 ====================
check_info "步骤 4: 更新配置..."

cd "$DEPLOY_DIR"

# 更新 IMAGE_TAG
check_info "更新 IMAGE_TAG 为 $VERSION_TAG"
if grep -q "^IMAGE_TAG=" .env.production; then
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production
else
    echo "IMAGE_TAG=$VERSION_TAG" >> .env.production
fi

check_passed "配置已更新"

echo ""

# ==================== 步骤 5: 停止旧服务 ====================
check_info "步骤 5: 停止旧服务..."

if docker compose -f docker-compose.prod.yml --env-file .env.production ps | grep -q "Up"; then
    check_info "停止现有服务..."
    docker compose -f docker-compose.prod.yml --env-file .env.production down
    check_passed "服务已停止"
else
    check_info "服务未运行"
fi

echo ""

# ==================== 步骤 6: 清理前端静态文件（如更新前端） ====================
if [ "$UPDATE_TYPE" = "frontend" ] || [ "$UPDATE_TYPE" = "all" ]; then
    check_info "步骤 6: 清理旧的前端静态文件..."

    if [ -d "frontend/dist" ]; then
        rm -rf frontend/dist/*
        check_passed "旧静态文件已清理"
    else
        mkdir -p frontend/dist
        check_passed "创建前端目录"
    fi

    echo ""
fi

# ==================== 步骤 7: 启动新服务 ====================
check_info "步骤 7: 启动新服务..."

check_info "启动 Docker Compose 服务..."
if docker compose -f docker-compose.prod.yml --env-file .env.production up -d; then
    check_passed "服务已启动"
else
    check_failed "启动服务失败"
fi

# 等待服务就绪
check_info "等待服务就绪..."
sleep 10

# 检查服务状态
check_info "服务状态:"
docker compose -f docker-compose.prod.yml --env-file .env.production ps

echo ""

# ==================== 步骤 8: 验证更新 ====================
check_info "步骤 8: 验证更新..."

# 检查 frontend-init（如果更新了前端）
if [ "$UPDATE_TYPE" = "frontend" ] || [ "$UPDATE_TYPE" = "all" ]; then
    FRONTEND_INIT_STATUS=$(docker inspect --format='{{.State.Status}}' pepgmp-frontend-init 2>/dev/null || echo "not found")
    if [ "$FRONTEND_INIT_STATUS" = "exited" ]; then
        EXIT_CODE=$(docker inspect --format='{{.State.ExitCode}}' pepgmp-frontend-init 2>/dev/null || echo "unknown")
        if [ "$EXIT_CODE" = "0" ]; then
            check_passed "Frontend-init 已完成"
        else
            check_warning "Frontend-init 退出码: $EXIT_CODE"
        fi
    fi
fi

# 测试 HTTP 端点
echo ""
check_info "测试 HTTP 端点..."

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check_passed "前端可访问 (HTTP $HTTP_CODE)"
else
    check_warning "前端返回 HTTP $HTTP_CODE"
fi

API_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/health" 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
    check_passed "API 可访问 (HTTP $API_CODE)"
else
    check_warning "API 返回 HTTP $API_CODE"
fi

echo ""

# ==================== 更新总结 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}更新完成${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "部署目录: $DEPLOY_DIR"
echo "新镜像版本: $VERSION_TAG"
echo "更新类型: $UPDATE_TYPE"
echo ""
echo "访问地址:"
echo "  前端: http://localhost/"
echo "  API:  http://localhost:8000/api/v1/monitoring/health"
echo ""
echo "常用命令:"
echo "  查看日志:    docker compose -f docker-compose.prod.yml --env-file .env.production logs -f"
echo "  查看状态:    docker compose -f docker-compose.prod.yml --env-file .env.production ps"
echo ""
echo "========================================================================="
