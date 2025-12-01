#!/bin/bash
#
# 生产镜像构建、推送与导出脚本
# 用途: 构建后端与前端生产镜像，推送至私有Registry，并导出tar包
#
# 使用方法:
#   bash scripts/build_prod_images.sh
#

set -e  # 遇到错误立即退出

# =============================================================================
# 配置区域
# =============================================================================
REGISTRY="192.168.30.83:5433"
PROJECT_NAME="pyt"
DATE_TAG=$(date +%Y%m%d)

# 基础镜像（从私有Registry拉取）
CUDA_BASE="${REGISTRY}/nvidia/cuda:12.4.0-runtime-ubuntu22.04"
NODE_BASE="${REGISTRY}/node:20-alpine"
NGINX_BASE="${REGISTRY}/nginx:1.27-alpine"

# 目标镜像
API_IMAGE="${REGISTRY}/${PROJECT_NAME}-api:prod"
FRONTEND_IMAGE="${REGISTRY}/${PROJECT_NAME}-frontend:prod"

# 导出目录
EXPORT_DIR="./docker_exports"

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
# 检查环境
# =============================================================================
check_environment() {
    log_info "检查环境..."

    # 检查Docker是否安装
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker守护进程未运行"
        exit 1
    fi

    # 创建导出目录
    mkdir -p "${EXPORT_DIR}"

    log_success "环境检查通过"
}

# =============================================================================
# 检查私有Registry连接
# =============================================================================
check_registry() {
    log_info "检查私有Registry连接: ${REGISTRY}"

    if curl -f -s "http://${REGISTRY}/v2/_catalog" > /dev/null 2>&1; then
        log_success "私有Registry连接正常"
    else
        log_warn "无法连接到私有Registry，可能需要配置insecure-registries"
        log_warn "请在 /etc/docker/daemon.json 中添加:"
        log_warn '  {"insecure-registries": ["'${REGISTRY}'"]}'
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# =============================================================================
# 构建后端生产镜像
# =============================================================================
build_api_image() {
    log_info "开始构建后端生产镜像..."
    log_info "基础镜像: ${CUDA_BASE}"
    log_info "目标镜像: ${API_IMAGE}"

    docker build -f Dockerfile \
        --build-arg CUDA_IMAGE="${CUDA_BASE}" \
        -t "${API_IMAGE}" \
        -t "${REGISTRY}/${PROJECT_NAME}-api:${DATE_TAG}" \
        . || {
        log_error "后端镜像构建失败"
        exit 1
    }

    log_success "后端镜像构建完成"
}

# =============================================================================
# 构建前端生产镜像
# =============================================================================
build_frontend_image() {
    log_info "开始构建前端生产镜像..."
    log_info "Node基础镜像: ${NODE_BASE}"
    log_info "Nginx基础镜像: ${NGINX_BASE}"
    log_info "目标镜像: ${FRONTEND_IMAGE}"

    docker build -f Dockerfile.frontend \
        --build-arg NODE_IMAGE="${NODE_BASE}" \
        --build-arg NGINX_IMAGE="${NGINX_BASE}" \
        --build-arg VITE_API_BASE=/api/v1 \
        --build-arg BASE_URL=/ \
        --build-arg SKIP_TYPE_CHECK=true \
        -t "${FRONTEND_IMAGE}" \
        -t "${REGISTRY}/${PROJECT_NAME}-frontend:${DATE_TAG}" \
        . || {
        log_error "前端镜像构建失败"
        exit 1
    }

    log_success "前端镜像构建完成"
}

# =============================================================================
# 推送镜像到私有Registry
# =============================================================================
push_images() {
    log_info "推送镜像到私有Registry..."

    log_info "推送后端镜像 (prod tag)..."
    docker push "${API_IMAGE}" || {
        log_error "后端镜像推送失败"
        exit 1
    }

    log_info "推送后端镜像 (日期tag)..."
    docker push "${REGISTRY}/${PROJECT_NAME}-api:${DATE_TAG}" || {
        log_warn "后端镜像日期tag推送失败，继续..."
    }

    log_info "推送前端镜像 (prod tag)..."
    docker push "${FRONTEND_IMAGE}" || {
        log_error "前端镜像推送失败"
        exit 1
    }

    log_info "推送前端镜像 (日期tag)..."
    docker push "${REGISTRY}/${PROJECT_NAME}-frontend:${DATE_TAG}" || {
        log_warn "前端镜像日期tag推送失败，继续..."
    }

    log_success "所有镜像推送完成"
}

# =============================================================================
# 导出镜像到本地tar
# =============================================================================
export_images() {
    log_info "导出镜像到本地tar包..."

    API_TAR="${EXPORT_DIR}/${PROJECT_NAME}-api_prod_${DATE_TAG}.tar"
    FRONTEND_TAR="${EXPORT_DIR}/${PROJECT_NAME}-frontend_prod_${DATE_TAG}.tar"

    log_info "导出后端镜像..."
    docker save -o "${API_TAR}" "${API_IMAGE}" || {
        log_error "后端镜像导出失败"
        exit 1
    }
    log_success "后端镜像已导出: ${API_TAR}"

    log_info "导出前端镜像..."
    docker save -o "${FRONTEND_TAR}" "${FRONTEND_IMAGE}" || {
        log_error "前端镜像导出失败"
        exit 1
    }
    log_success "前端镜像已导出: ${FRONTEND_TAR}"

    # 显示文件大小
    log_info "文件大小:"
    du -h "${API_TAR}"
    du -h "${FRONTEND_TAR}"

    # 询问是否压缩
    read -p "是否压缩tar包? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "压缩tar包..."
        gzip -9 "${API_TAR}" "${FRONTEND_TAR}" || {
            log_warn "压缩失败，但tar包已生成"
        }
        log_success "压缩完成"
        du -h "${API_TAR}.gz"
        du -h "${FRONTEND_TAR}.gz"
    fi
}

# =============================================================================
# 显示摘要
# =============================================================================
show_summary() {
    log_success "=========================================="
    log_success "  生产镜像构建完成"
    log_success "=========================================="
    echo ""
    log_info "推送到Registry的镜像:"
    echo "  - ${API_IMAGE}"
    echo "  - ${REGISTRY}/${PROJECT_NAME}-api:${DATE_TAG}"
    echo "  - ${FRONTEND_IMAGE}"
    echo "  - ${REGISTRY}/${PROJECT_NAME}-frontend:${DATE_TAG}"
    echo ""
    log_info "本地导出文件:"
    ls -lh "${EXPORT_DIR}"/*_${DATE_TAG}.tar* 2>/dev/null || true
    echo ""
    log_info "验证Registry内容:"
    echo "  curl http://${REGISTRY}/v2/_catalog"
    echo ""
    log_info "在其他机器加载镜像:"
    echo "  docker load -i ${PROJECT_NAME}-api_prod_${DATE_TAG}.tar"
    echo "  docker load -i ${PROJECT_NAME}-frontend_prod_${DATE_TAG}.tar"
    echo ""
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    log_info "=========================================="
    log_info "  生产镜像构建、推送与导出"
    log_info "=========================================="
    log_info "Registry: ${REGISTRY}"
    log_info "日期标签: ${DATE_TAG}"
    echo ""

    check_environment
    check_registry

    echo ""
    read -p "开始构建? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "用户取消"
        exit 0
    fi

    build_api_image
    build_frontend_image
    push_images
    export_images
    show_summary

    log_success "全部完成！"
}

# 执行主流程
main "$@"
