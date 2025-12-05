#!/bin/bash
# 将代码从 Windows 文件系统同步到 WSL 文件系统
# Usage: bash scripts/sync_code_to_wsl.sh [SOURCE_PATH] [TARGET_PATH]

set -e

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

# 默认路径
SOURCE_PATH="${1:-/mnt/c/Users/$USER/Code/PEPGMP}"
TARGET_PATH="${2:-$HOME/projects/PEPGMP}"

echo "========================================================================="
echo "                     同步代码到 WSL 文件系统"
echo "========================================================================="
echo ""
log_info "源路径: $SOURCE_PATH"
log_info "目标路径: $TARGET_PATH"
echo ""

# 检查源路径
if [ ! -d "$SOURCE_PATH" ]; then
    log_error "源路径不存在: $SOURCE_PATH"
    echo ""
    echo "请指定正确的源路径，例如："
    echo "  bash scripts/sync_code_to_wsl.sh /mnt/c/Users/$USER/Code/PEPGMP"
    exit 1
fi

log_success "源路径存在"

# 检查目标路径
if [ -d "$TARGET_PATH" ]; then
    log_warning "目标路径已存在: $TARGET_PATH"
    read -p "是否覆盖? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "已取消"
        exit 0
    fi
    log_info "备份现有目录..."
    mv "$TARGET_PATH" "${TARGET_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# 创建目标目录
mkdir -p "$(dirname "$TARGET_PATH")"

# 同步代码
log_info "开始同步代码..."
log_info "使用 rsync（支持增量更新）..."

if command -v rsync &> /dev/null; then
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='dist' \
        --exclude='build' \
        --exclude='*.egg-info' \
        --exclude='logs' \
        --exclude='output' \
        --exclude='data' \
        --exclude='models' \
        "$SOURCE_PATH/" "$TARGET_PATH/"
else
    log_warning "rsync 未安装，使用 cp（较慢）..."
    cp -r "$SOURCE_PATH" "$TARGET_PATH"
fi

log_success "代码同步完成"

# 验证同步
log_info "验证同步结果..."
if [ -f "$TARGET_PATH/docker-compose.prod.yml" ] && [ -d "$TARGET_PATH/scripts" ]; then
    log_success "关键文件已同步"
    log_info "  - docker-compose.prod.yml: ✅"
    log_info "  - scripts/ 目录: ✅"
else
    log_error "关键文件缺失，请检查同步结果"
    exit 1
fi

# 设置权限
log_info "设置文件权限..."
chmod +x "$TARGET_PATH/scripts"/*.sh 2>/dev/null || true

log_success "========================================================================="
log_success "同步完成"
log_success "========================================================================="
echo ""
log_info "下一步操作:"
echo "  cd $TARGET_PATH"
echo "  VERSION_TAG=\$(date +%Y%m%d)"
echo "  bash scripts/build_prod_only.sh \$VERSION_TAG"
echo ""
