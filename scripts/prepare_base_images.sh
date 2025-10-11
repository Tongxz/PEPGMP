#!/bin/bash
#
# 基础镜像预热脚本
# 用途: 从Docker Hub拉取基础镜像，并推送到私有Registry
#
# 使用方法:
#   bash scripts/prepare_base_images.sh
#

set -e  # 遇到错误立即退出

# =============================================================================
# 配置区域
# =============================================================================
REGISTRY="192.168.30.83:5433"

# 基础镜像列表
CUDA_IMAGE="nvidia/cuda:12.4.0-runtime-ubuntu22.04"
NODE_IMAGE="node:20-alpine"
NGINX_IMAGE="nginx:1.27-alpine"

# =============================================================================
# 颜色输出
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# 检查网络连接
# =============================================================================
check_network() {
    log_info "检查Docker Hub连接..."

    if ! curl -f -s "https://hub.docker.com" > /dev/null 2>&1; then
        log_error "无法连接到Docker Hub"
        log_error "请确保网络正常或使用离线方式"
        exit 1
    fi

    log_success "网络连接正常"
}

# =============================================================================
# 拉取并推送镜像
# =============================================================================
pull_and_push_image() {
    local source_image=$1
    local target_image="${REGISTRY}/${source_image}"

    log_info "=========================================="
    log_info "处理镜像: ${source_image}"
    log_info "=========================================="

    # 拉取镜像
    log_info "从Docker Hub拉取镜像..."
    if docker pull "${source_image}"; then
        log_success "镜像拉取成功"
    else
        log_error "镜像拉取失败: ${source_image}"
        return 1
    fi

    # 标记镜像
    log_info "标记镜像: ${target_image}"
    docker tag "${source_image}" "${target_image}"

    # 推送到私有Registry
    log_info "推送到私有Registry..."
    if docker push "${target_image}"; then
        log_success "镜像推送成功: ${target_image}"
    else
        log_error "镜像推送失败: ${target_image}"
        return 1
    fi

    echo ""
}

# =============================================================================
# 导出镜像（离线备份）
# =============================================================================
export_base_images() {
    log_info "=========================================="
    log_info "导出基础镜像（离线备份）"
    log_info "=========================================="

    EXPORT_DIR="./docker_exports/base_images"
    mkdir -p "${EXPORT_DIR}"

    log_info "导出 CUDA 基础镜像..."
    docker save -o "${EXPORT_DIR}/base_cuda.tar" "${CUDA_IMAGE}"

    log_info "导出 Node 基础镜像..."
    docker save -o "${EXPORT_DIR}/base_node.tar" "${NODE_IMAGE}"

    log_info "导出 Nginx 基础镜像..."
    docker save -o "${EXPORT_DIR}/base_nginx.tar" "${NGINX_IMAGE}"

    log_success "基础镜像已导出到: ${EXPORT_DIR}"
    ls -lh "${EXPORT_DIR}"

    # 询问是否压缩
    read -p "是否压缩tar包? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "压缩tar包..."
        gzip -9 "${EXPORT_DIR}"/*.tar
        log_success "压缩完成"
        ls -lh "${EXPORT_DIR}"
    fi
}

# =============================================================================
# 显示摘要
# =============================================================================
show_summary() {
    log_success "=========================================="
    log_success "  基础镜像预热完成"
    log_success "=========================================="
    echo ""
    log_info "已推送到私有Registry的镜像:"
    echo "  - ${REGISTRY}/${CUDA_IMAGE}"
    echo "  - ${REGISTRY}/${NODE_IMAGE}"
    echo "  - ${REGISTRY}/${NGINX_IMAGE}"
    echo ""
    log_info "验证Registry内容:"
    echo "  curl http://${REGISTRY}/v2/_catalog"
    echo ""
    log_info "验证具体镜像标签:"
    echo "  curl http://${REGISTRY}/v2/nvidia/cuda/tags/list"
    echo "  curl http://${REGISTRY}/v2/node/tags/list"
    echo "  curl http://${REGISTRY}/v2/nginx/tags/list"
    echo ""
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    log_info "=========================================="
    log_info "  基础镜像预热工具"
    log_info "=========================================="
    log_info "目标Registry: ${REGISTRY}"
    echo ""
    log_info "将处理以下镜像:"
    echo "  1. ${CUDA_IMAGE}"
    echo "  2. ${NODE_IMAGE}"
    echo "  3. ${NGINX_IMAGE}"
    echo ""

    check_network

    read -p "开始拉取并推送基础镜像? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "用户取消"
        exit 0
    fi

    # 处理每个镜像
    pull_and_push_image "${CUDA_IMAGE}"
    pull_and_push_image "${NODE_IMAGE}"
    pull_and_push_image "${NGINX_IMAGE}"

    # 导出离线备份
    read -p "是否导出离线备份? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        export_base_images
    fi

    show_summary

    log_success "全部完成！现在可以运行 build_prod_images.sh 构建生产镜像"
}

# 执行主流程
main "$@"
