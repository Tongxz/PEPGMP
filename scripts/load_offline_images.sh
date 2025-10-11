#!/bin/bash
#
# 离线镜像加载脚本
# 用途: 从tar包加载镜像并推送到私有Registry（适用于无外网环境）
#
# 使用方法:
#   bash scripts/load_offline_images.sh [tar_directory]
#

set -e  # 遇到错误立即退出

# =============================================================================
# 配置区域
# =============================================================================
REGISTRY="192.168.30.83:5433"
TAR_DIR="${1:-./docker_exports/base_images}"

# 基础镜像
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
# 检查tar文件
# =============================================================================
check_tar_files() {
    log_info "检查tar文件..."
    log_info "搜索目录: ${TAR_DIR}"

    if [[ ! -d "${TAR_DIR}" ]]; then
        log_error "目录不存在: ${TAR_DIR}"
        exit 1
    fi

    # 查找tar或tar.gz文件
    CUDA_TAR=$(find "${TAR_DIR}" -name "base_cuda.tar*" -o -name "*cuda*.tar*" | head -1)
    NODE_TAR=$(find "${TAR_DIR}" -name "base_node.tar*" -o -name "*node*.tar*" | head -1)
    NGINX_TAR=$(find "${TAR_DIR}" -name "base_nginx.tar*" -o -name "*nginx*.tar*" | head -1)

    if [[ -z "${CUDA_TAR}" ]] || [[ -z "${NODE_TAR}" ]] || [[ -z "${NGINX_TAR}" ]]; then
        log_error "未找到所有必需的tar文件"
        echo "需要的文件:"
        echo "  - CUDA镜像tar (找到: ${CUDA_TAR:-未找到})"
        echo "  - Node镜像tar (找到: ${NODE_TAR:-未找到})"
        echo "  - Nginx镜像tar (找到: ${NGINX_TAR:-未找到})"
        exit 1
    fi

    log_success "找到所有tar文件"
}

# =============================================================================
# 解压并加载镜像
# =============================================================================
load_and_push_image() {
    local tar_file=$1
    local image_name=$2
    local target_image="${REGISTRY}/${image_name}"

    log_info "=========================================="
    log_info "处理: ${tar_file}"
    log_info "=========================================="

    # 如果是.gz文件，先解压
    if [[ "${tar_file}" == *.gz ]]; then
        log_info "解压gz文件..."
        gunzip -k "${tar_file}" || {
            log_error "解压失败"
            return 1
        }
        tar_file="${tar_file%.gz}"
    fi

    # 加载镜像
    log_info "加载镜像到Docker..."
    if docker load -i "${tar_file}"; then
        log_success "镜像加载成功"
    else
        log_error "镜像加载失败"
        return 1
    fi

    # 标记镜像
    log_info "标记镜像: ${target_image}"
    docker tag "${image_name}" "${target_image}"

    # 推送到私有Registry
    log_info "推送到私有Registry..."
    if docker push "${target_image}"; then
        log_success "镜像推送成功: ${target_image}"
    else
        log_error "镜像推送失败"
        return 1
    fi

    echo ""
}

# =============================================================================
# 显示摘要
# =============================================================================
show_summary() {
    log_success "=========================================="
    log_success "  离线镜像加载完成"
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
    log_info "下一步: 运行生产镜像构建脚本"
    echo "  bash scripts/build_prod_images.sh"
    echo ""
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    log_info "=========================================="
    log_info "  离线镜像加载工具"
    log_info "=========================================="
    log_info "目标Registry: ${REGISTRY}"
    log_info "Tar文件目录: ${TAR_DIR}"
    echo ""

    check_tar_files

    echo ""
    log_info "将加载以下镜像:"
    echo "  1. ${CUDA_TAR}"
    echo "  2. ${NODE_TAR}"
    echo "  3. ${NGINX_TAR}"
    echo ""

    read -p "开始加载并推送? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "用户取消"
        exit 0
    fi

    # 加载并推送每个镜像
    load_and_push_image "${CUDA_TAR}" "${CUDA_IMAGE}"
    load_and_push_image "${NODE_TAR}" "${NODE_IMAGE}"
    load_and_push_image "${NGINX_TAR}" "${NGINX_IMAGE}"

    show_summary

    log_success "全部完成！"
}

# 执行主流程
main "$@"
