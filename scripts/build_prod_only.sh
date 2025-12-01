#!/bin/bash
# 仅构建生产环境镜像（不推送、不导出）
# Build production images only (no push, no export)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ==================== 版本号配置 ====================
# 支持通过参数指定版本号，否则使用日期版本号
VERSION_TAG="${1:-$(date +%Y%m%d)}"
# 也可以使用语义化版本号，例如: v1.0.0, v1.2.3
# VERSION_TAG="${1:-v1.0.0}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================================================="
echo "                     构建生产环境镜像"
echo "========================================================================="
echo ""
log_info "版本标签: ${VERSION_TAG}"
log_info "提示: 可以指定版本号，例如: bash $0 v1.0.0 或 bash $0 20250101"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker未安装"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker守护进程未运行"
    exit 1
fi

log_success "Docker环境检查通过"
echo ""

# 检查Dockerfile
if [ ! -f "Dockerfile.prod" ]; then
    log_error "Dockerfile.prod 不存在"
    exit 1
fi

if [ ! -f "Dockerfile.frontend" ]; then
    log_warning "Dockerfile.frontend 不存在，将跳过前端镜像构建"
    BUILD_FRONTEND=false
else
    BUILD_FRONTEND=true
fi

echo "========================================================================="
echo "准备构建以下镜像:"
echo "  1. 后端API镜像 (Dockerfile.prod)"
if [ "$BUILD_FRONTEND" = true ]; then
    echo "  2. 前端镜像 (Dockerfile.frontend)"
fi
echo "========================================================================="
echo ""

read -p "确认开始构建? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "已取消"
    exit 0
fi

echo ""

# ==================== 构建后端镜像 ====================
log_info "开始构建后端API镜像..."
log_info "Dockerfile: Dockerfile.prod"
log_info "镜像名称: pepgmp-backend:${VERSION_TAG}"

if docker build -f Dockerfile.prod \
    -t pepgmp-backend:${VERSION_TAG} \
    -t pepgmp-backend:latest \
    .; then
    log_success "后端API镜像构建完成"
    log_info "已创建以下标签:"
    docker images pepgmp-backend:${VERSION_TAG} --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
    docker images pepgmp-backend:latest --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
else
    log_error "后端API镜像构建失败"
    exit 1
fi

echo ""

# ==================== 构建前端镜像 ====================
if [ "$BUILD_FRONTEND" = true ]; then
    log_info "开始构建前端镜像..."
    log_info "Dockerfile: Dockerfile.frontend"
    log_info "镜像名称: pepgmp-frontend:${VERSION_TAG}"

    if docker build -f Dockerfile.frontend \
        --build-arg VITE_API_BASE=/api/v1 \
        --build-arg BASE_URL=/ \
        --build-arg SKIP_TYPE_CHECK=true \
        -t pepgmp-frontend:${VERSION_TAG} \
        -t pepgmp-frontend:latest \
        .; then
        log_success "前端镜像构建完成"
        log_info "已创建以下标签:"
        docker images pepgmp-frontend:${VERSION_TAG} --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
        docker images pepgmp-frontend:latest --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
    else
        log_error "前端镜像构建失败"
        exit 1
    fi

    echo ""
fi

# ==================== 显示构建结果 ====================
log_success "========================================================================="
log_success "                     构建完成"
log_success "========================================================================="
echo ""
log_info "已构建的镜像:"
docker images | grep -E "pepgmp-(backend|frontend)" || docker images | grep "REPOSITORY"
echo ""

# 自动更新 .env.production 中的版本号
if [ -f ".env.production" ]; then
    log_info "自动更新 .env.production 中的镜像版本号..."
    if bash "$SCRIPT_DIR/update_image_version.sh" "${VERSION_TAG}"; then
        log_success "版本号已自动更新"
    else
        log_warning "自动更新版本号失败，请手动运行: bash scripts/update_image_version.sh ${VERSION_TAG}"
    fi
    echo ""
fi

log_info "下一步操作:"
echo "  1. 使用Docker Compose启动（已自动更新版本号）:"
echo "     docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "  2. 或手动运行容器（推荐使用版本号）:"
echo "     docker run -d --name pepgmp-api-prod -p 8000:8000 pepgmp-backend:${VERSION_TAG}"
if [ "$BUILD_FRONTEND" = true ]; then
    echo "     docker run -d --name pepgmp-frontend-prod -p 8080:80 pepgmp-frontend:${VERSION_TAG}"
fi
echo ""
echo "  3. 推送到Registry（如需要）:"
echo "     bash scripts/push_to_registry.sh ${VERSION_TAG}"
echo ""
log_warning "注意: 生产环境建议使用版本号标签 (${VERSION_TAG})，而不是 :latest"
echo ""
