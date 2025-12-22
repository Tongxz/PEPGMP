#!/bin/bash
# 自动更新生产环境镜像版本号
# Auto-update production image version in .env.production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

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

ENV_FILE=".env.production"

# 检查 .env.production 是否存在
if [ ! -f "$ENV_FILE" ]; then
    log_error ".env.production 文件不存在"
    exit 1
fi

# 获取参数：版本号（可选）
VERSION_TAG="${1:-auto}"

# 如果未指定版本号，自动查找最新的日期版本号镜像
if [ "$VERSION_TAG" = "auto" ]; then
    log_info "自动查找最新的日期版本号镜像..."

    # 查找所有 pepgmp-backend 镜像的日期版本号（格式：YYYYMMDD）
    LATEST_TAG=$(docker images pepgmp-backend --format "{{.Tag}}" | grep -E "^[0-9]{8}$" | sort -r | head -1)

    if [ -z "$LATEST_TAG" ]; then
        log_warning "未找到日期版本号镜像，尝试查找所有版本..."
        # 查找所有非 latest 的标签
        LATEST_TAG=$(docker images pepgmp-backend --format "{{.Tag}}" | grep -v "^latest$" | sort -r | head -1)
    fi

    if [ -z "$LATEST_TAG" ]; then
        log_error "未找到可用的镜像版本"
        log_info "请先构建镜像: bash scripts/build_prod_only.sh"
        exit 1
    fi

    VERSION_TAG="$LATEST_TAG"
    log_info "找到最新版本: ${VERSION_TAG}"
fi

# 更新 .env.production 中的 IMAGE_TAG
log_info "更新 ${ENV_FILE} 中的 IMAGE_TAG=${VERSION_TAG}..."

# 检查是否已存在 IMAGE_TAG
if grep -q "^IMAGE_TAG=" "$ENV_FILE"; then
    # 更新现有行
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS 使用 sed -i ''
        sed -i '' "s/^IMAGE_TAG=.*/IMAGE_TAG=${VERSION_TAG}/" "$ENV_FILE"
    else
        # Linux 使用 sed -i
        sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${VERSION_TAG}/" "$ENV_FILE"
    fi
    log_success "已更新 IMAGE_TAG=${VERSION_TAG}"
else
    # 添加新行
    echo "" >> "$ENV_FILE"
    echo "# Docker镜像版本号（自动更新）" >> "$ENV_FILE"
    echo "IMAGE_TAG=${VERSION_TAG}" >> "$ENV_FILE"
    log_success "已添加 IMAGE_TAG=${VERSION_TAG}"
fi

echo ""
log_success "========================================================================="
log_success "                     版本号更新完成"
log_success "========================================================================="
echo ""
log_info "当前配置:"
echo "  IMAGE_TAG=${VERSION_TAG}"
echo ""
log_info "下一步:"
echo "  1. 使用 Docker Compose 启动:"
echo "     docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "  2. 验证使用的镜像版本:"
echo "     docker compose -f docker-compose.prod.yml config | grep image"
echo ""
