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

# 生产 GPU（RTX 50 / sm_120）需要较新的 PyTorch wheel。
# 与 deploy_mixed_registry.sh 保持一致：默认使用 nightly/cu126，可按需在 Dockerfile.prod 里切换 stable。
TORCH_INSTALL_MODE_DEFAULT="nightly"
TORCH_INDEX_URL_DEFAULT="https://download.pytorch.org/whl/nightly/cu126"

# 检测架构并设置构建平台
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    # macOS ARM (M1/M2) 或 Linux ARM，需要构建 Linux amd64 镜像用于生产环境
    BUILD_PLATFORM="linux/amd64"
    log_info "检测到 ARM 架构，将构建 Linux amd64 镜像用于生产环境"
    log_info "构建平台: ${BUILD_PLATFORM}"

    # 检查是否安装了 buildx
    if ! docker buildx version &> /dev/null; then
        log_error "需要 Docker Buildx 来构建多架构镜像"
        log_info "安装方法: Docker Desktop 已包含 buildx，或运行: docker buildx install"
        exit 1
    fi

    # 关键：Docker Desktop 中 buildx builder 会用 “*” 标记当前 builder（例如 desktop-linux*）。
    # 另外 builder 与 docker context 绑定：当前 context=desktop-linux 时，使用 default builder 会报错。
    CURRENT_CTX="$(docker context show 2>/dev/null || echo "")"
    BUILDER_NAME="$CURRENT_CTX"
    if ! docker buildx ls | awk '{print $1}' | sed 's/\*$//' | grep -qx "${BUILDER_NAME}"; then
        # fallback：优先 desktop-linux，其次 default
        if docker buildx ls | awk '{print $1}' | sed 's/\*$//' | grep -qx 'desktop-linux'; then
            BUILDER_NAME="desktop-linux"
        else
            BUILDER_NAME="default"
        fi
    fi
    docker buildx use "${BUILDER_NAME}" 2>/dev/null || true
else
    # x86_64 架构，直接构建
    BUILD_PLATFORM="linux/amd64"
    log_info "检测到 x86_64 架构，直接构建"
fi

# 启用 BuildKit 以支持增量构建优化和缓存挂载
export DOCKER_BUILDKIT=1

# 根据架构选择构建命令
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    # 使用 buildx 构建 Linux amd64 镜像
    BUILD_CMD=\"docker buildx build --builder ${BUILDER_NAME} --platform ${BUILD_PLATFORM} --pull=false -f Dockerfile.prod --build-arg BASE_IMAGE=nvidia/cuda:12.4.0-runtime-ubuntu22.04 --build-arg TORCH_INSTALL_MODE=${TORCH_INSTALL_MODE_DEFAULT} --build-arg TORCH_INDEX_URL=${TORCH_INDEX_URL_DEFAULT} -t pepgmp-backend:${VERSION_TAG} -t pepgmp-backend:latest --load .\"
else
    # 直接构建
    BUILD_CMD=\"docker build -f Dockerfile.prod --build-arg BASE_IMAGE=nvidia/cuda:12.4.0-runtime-ubuntu22.04 --build-arg TORCH_INSTALL_MODE=${TORCH_INSTALL_MODE_DEFAULT} --build-arg TORCH_INDEX_URL=${TORCH_INDEX_URL_DEFAULT} -t pepgmp-backend:${VERSION_TAG} -t pepgmp-backend:latest .\"
fi

log_info "执行构建命令: ${BUILD_CMD}"
if eval ${BUILD_CMD}; then
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

    # 根据架构选择构建命令
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        FRONTEND_BUILD_CMD="docker buildx build --platform ${BUILD_PLATFORM} -f Dockerfile.frontend --build-arg VITE_API_BASE=/api/v1 --build-arg BASE_URL=/ --build-arg SKIP_TYPE_CHECK=true -t pepgmp-frontend:${VERSION_TAG} -t pepgmp-frontend:latest --load ."
    else
        FRONTEND_BUILD_CMD="docker build -f Dockerfile.frontend --build-arg VITE_API_BASE=/api/v1 --build-arg BASE_URL=/ --build-arg SKIP_TYPE_CHECK=true -t pepgmp-frontend:${VERSION_TAG} -t pepgmp-frontend:latest ."
    fi

    log_info "执行构建命令: ${FRONTEND_BUILD_CMD}"
    if eval ${FRONTEND_BUILD_CMD}; then
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
echo "  1. 生产部署（仅保留两条主线）："
echo "     - 混合部署（网络隔离：导出/传输镜像 tar）"
echo "       bash scripts/deploy_mixed_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP ${VERSION_TAG}"
echo "     - Registry 部署（同一网络：生产机可访问 Registry）"
echo "       bash scripts/deploy_via_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP ${VERSION_TAG}"
echo ""
echo "  2. 本机验证（可选）："
echo "     docker compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
log_warning "注意: 生产环境建议使用版本号标签 (${VERSION_TAG})，而不是 :latest"
echo ""
