#!/bin/bash
# 清理旧的部署容器
# 用于解决容器名称冲突问题
# Usage: bash scripts/cleanup_old_containers.sh [CONTAINER_PREFIX]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONTAINER_PREFIX="${1:-pepgmp}"

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
echo "                     清理旧容器"
echo "========================================================================="
echo ""
log_info "容器前缀: $CONTAINER_PREFIX"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# 查找相关容器
CONTAINERS=$(docker ps -a --filter "name=$CONTAINER_PREFIX" --format "{{.Names}}" 2>/dev/null || true)

if [ -z "$CONTAINERS" ]; then
    log_info "未找到相关容器"
    exit 0
fi

echo "找到以下容器:"
echo "$CONTAINERS" | while read -r container; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
    echo "  - $container ($STATUS)"
done
echo ""

# 确认删除
read -p "是否删除这些容器? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "已取消"
    exit 0
fi

# 停止并删除容器
log_info "停止并删除容器..."
echo "$CONTAINERS" | while read -r container; do
    if [ -n "$container" ]; then
        log_info "处理容器: $container"
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    fi
done

log_success "容器清理完成"

# 检查是否还有相关容器
REMAINING=$(docker ps -a --filter "name=$CONTAINER_PREFIX" --format "{{.Names}}" 2>/dev/null || true)
if [ -n "$REMAINING" ]; then
    log_warning "仍有容器存在:"
    echo "$REMAINING"
    log_info "可以手动删除: docker rm -f <container-name>"
else
    log_success "所有相关容器已清理"
fi

echo ""
log_info "下一步: 可以重新启动服务"
echo "  docker compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
