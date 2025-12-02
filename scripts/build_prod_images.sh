#!/bin/bash
#
# 生产镜像构建、推送与导出脚本
# Production Image Build, Push and Export Script
#
# 用途: 构建后端与前端生产镜像，推送至私有 Registry，并导出 tar 包
# Purpose: Build backend and frontend production images, push to private registry, export tar files
#
# 使用方法 / Usage:
#   bash scripts/build_prod_images.sh [VERSION_TAG]
#   bash scripts/build_prod_images.sh 20251202
#   bash scripts/build_prod_images.sh v1.0.0
#

set -e  # 遇到错误立即退出

# =============================================================================
# 加载统一配置
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 加载统一配置
if [ -f "$SCRIPT_DIR/lib/deploy_config.sh" ]; then
    source "$SCRIPT_DIR/lib/deploy_config.sh"
else
    echo "[ERROR] 配置文件不存在: $SCRIPT_DIR/lib/deploy_config.sh"
    exit 1
fi

# 版本标签（从参数或默认配置）
VERSION_TAG="${1:-$VERSION_TAG}"

# =============================================================================
# 配置区域（使用统一配置中的变量）
# =============================================================================
# 镜像名称（来自 deploy_config.sh）
BACKEND_IMAGE="$BACKEND_IMAGE_NAME"
FRONTEND_IMAGE="$FRONTEND_IMAGE_NAME"

# Registry 镜像路径
REGISTRY_BACKEND="${REGISTRY_URL}/${BACKEND_IMAGE}"
REGISTRY_FRONTEND="${REGISTRY_URL}/${FRONTEND_IMAGE}"

# 可选：从私有 Registry 拉取基础镜像（如果配置了）
# CUDA_BASE="${REGISTRY_URL}/nvidia/cuda:12.4.0-runtime-ubuntu22.04"
# NODE_BASE="${REGISTRY_URL}/node:20-alpine"
# NGINX_BASE="${REGISTRY_URL}/nginx:1.27-alpine"

# =============================================================================
# 显示配置
# =============================================================================
echo "========================================================================="
echo "                生产镜像构建、推送与导出"
echo "========================================================================="
echo ""
log_info "版本标签: ${VERSION_TAG}"
log_info "后端镜像: ${BACKEND_IMAGE}:${VERSION_TAG}"
log_info "前端镜像: ${FRONTEND_IMAGE}:${VERSION_TAG}"
log_info "Registry: ${REGISTRY_URL}"
log_info "操作系统: ${CURRENT_OS}"
echo ""

# =============================================================================
# 检查环境
# =============================================================================
check_environment() {
    log_step "检查环境"

    # 检查 Docker 是否安装
    if ! command_exists docker; then
        log_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi

    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行"
        exit 1
    fi

    # 检查 Dockerfile 是否存在
    if [ ! -f "$BACKEND_DOCKERFILE" ]; then
        log_error "后端 Dockerfile 不存在: $BACKEND_DOCKERFILE"
        exit 1
    fi

    if [ ! -f "$FRONTEND_DOCKERFILE" ]; then
        log_warning "前端 Dockerfile 不存在: $FRONTEND_DOCKERFILE"
        log_info "将跳过前端镜像构建"
        BUILD_FRONTEND=false
    else
        BUILD_FRONTEND=true
    fi

    # 创建导出目录
    mkdir -p "${EXPORT_DIR}"

    log_success "环境检查通过"
}

# =============================================================================
# 检查私有 Registry 连接
# =============================================================================
check_registry() {
    log_step "检查私有 Registry 连接: ${REGISTRY_URL}"

    if curl -f -s "http://${REGISTRY_URL}/v2/_catalog" > /dev/null 2>&1; then
        log_success "私有 Registry 连接正常"
        REGISTRY_AVAILABLE=true
    else
        log_warning "无法连接到私有 Registry"
        log_info "可能需要配置 insecure-registries"
        log_info "请在 /etc/docker/daemon.json 中添加:"
        echo '  {"insecure-registries": ["'${REGISTRY_URL}'"]}'
        echo ""
        read -p "是否继续（跳过推送到 Registry）? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        REGISTRY_AVAILABLE=false
    fi
}

# =============================================================================
# 构建后端生产镜像
# =============================================================================
build_backend_image() {
    log_step "构建后端生产镜像"
    log_info "Dockerfile: ${BACKEND_DOCKERFILE}"
    log_info "目标镜像: ${BACKEND_IMAGE}:${VERSION_TAG}"

    # 启用 BuildKit 以支持增量构建优化
    export DOCKER_BUILDKIT=1

    docker build -f "${BACKEND_DOCKERFILE}" \
        -t "${BACKEND_IMAGE}:${VERSION_TAG}" \
        -t "${BACKEND_IMAGE}:latest" \
        . || {
        log_error "后端镜像构建失败"
        exit 1
    }

    log_success "后端镜像构建完成"
    log_info "已创建以下标签:"
    docker images "${BACKEND_IMAGE}:${VERSION_TAG}" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
    docker images "${BACKEND_IMAGE}:latest" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
}

# =============================================================================
# 构建前端生产镜像
# =============================================================================
build_frontend_image() {
    if [ "$BUILD_FRONTEND" != true ]; then
        log_info "跳过前端镜像构建"
        return 0
    fi

    log_step "构建前端生产镜像"
    log_info "Dockerfile: ${FRONTEND_DOCKERFILE}"
    log_info "目标镜像: ${FRONTEND_IMAGE}:${VERSION_TAG}"

    # 启用 BuildKit
    export DOCKER_BUILDKIT=1

    docker build -f "${FRONTEND_DOCKERFILE}" \
        --build-arg VITE_API_BASE=/api/v1 \
        --build-arg BASE_URL=/ \
        --build-arg SKIP_TYPE_CHECK=true \
        -t "${FRONTEND_IMAGE}:${VERSION_TAG}" \
        -t "${FRONTEND_IMAGE}:latest" \
        . || {
        log_error "前端镜像构建失败"
        exit 1
    }

    log_success "前端镜像构建完成"
    log_info "已创建以下标签:"
    docker images "${FRONTEND_IMAGE}:${VERSION_TAG}" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
    docker images "${FRONTEND_IMAGE}:latest" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
}

# =============================================================================
# 推送镜像到私有 Registry
# =============================================================================
push_images() {
    if [ "$REGISTRY_AVAILABLE" != true ]; then
        log_warning "跳过推送到 Registry（Registry 不可用）"
        return 0
    fi

    log_step "推送镜像到私有 Registry"

    # 标记后端镜像
    log_info "标记后端镜像..."
    docker tag "${BACKEND_IMAGE}:${VERSION_TAG}" "${REGISTRY_BACKEND}:${VERSION_TAG}"
    docker tag "${BACKEND_IMAGE}:${VERSION_TAG}" "${REGISTRY_BACKEND}:latest"

    # 推送后端镜像
    log_info "推送后端镜像..."
    docker push "${REGISTRY_BACKEND}:${VERSION_TAG}" || {
        log_error "后端镜像推送失败"
        exit 1
    }
    docker push "${REGISTRY_BACKEND}:latest" || {
        log_warning "后端镜像 latest 标签推送失败"
    }

    if [ "$BUILD_FRONTEND" = true ]; then
        # 标记前端镜像
        log_info "标记前端镜像..."
        docker tag "${FRONTEND_IMAGE}:${VERSION_TAG}" "${REGISTRY_FRONTEND}:${VERSION_TAG}"
        docker tag "${FRONTEND_IMAGE}:${VERSION_TAG}" "${REGISTRY_FRONTEND}:latest"

        # 推送前端镜像
        log_info "推送前端镜像..."
        docker push "${REGISTRY_FRONTEND}:${VERSION_TAG}" || {
            log_error "前端镜像推送失败"
            exit 1
        }
        docker push "${REGISTRY_FRONTEND}:latest" || {
            log_warning "前端镜像 latest 标签推送失败"
        }
    fi

    log_success "所有镜像推送完成"
}

# =============================================================================
# 导出镜像到本地 tar
# =============================================================================
export_images() {
    log_step "导出镜像到本地 tar 包"

    BACKEND_TAR="${EXPORT_DIR}/${BACKEND_IMAGE}-${VERSION_TAG}.tar"
    FRONTEND_TAR="${EXPORT_DIR}/${FRONTEND_IMAGE}-${VERSION_TAG}.tar"

    log_info "导出后端镜像..."
    docker save -o "${BACKEND_TAR}" "${BACKEND_IMAGE}:${VERSION_TAG}" || {
        log_error "后端镜像导出失败"
        exit 1
    }
    log_success "后端镜像已导出: ${BACKEND_TAR}"

    if [ "$BUILD_FRONTEND" = true ]; then
        log_info "导出前端镜像..."
        docker save -o "${FRONTEND_TAR}" "${FRONTEND_IMAGE}:${VERSION_TAG}" || {
            log_error "前端镜像导出失败"
            exit 1
        }
        log_success "前端镜像已导出: ${FRONTEND_TAR}"
    fi

    # 显示文件大小
    echo ""
    log_info "导出文件大小:"
    du -h "${BACKEND_TAR}"
    if [ "$BUILD_FRONTEND" = true ] && [ -f "${FRONTEND_TAR}" ]; then
        du -h "${FRONTEND_TAR}"
    fi

    # 询问是否压缩
    echo ""
    read -p "是否压缩 tar 包? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "压缩 tar 包..."
        gzip -9 "${BACKEND_TAR}" || log_warning "后端镜像压缩失败"
        if [ "$BUILD_FRONTEND" = true ] && [ -f "${FRONTEND_TAR}" ]; then
            gzip -9 "${FRONTEND_TAR}" || log_warning "前端镜像压缩失败"
        fi
        log_success "压缩完成"
        echo ""
        log_info "压缩后文件大小:"
        ls -lh "${EXPORT_DIR}"/*.gz 2>/dev/null || true
    fi
}

# =============================================================================
# 显示摘要
# =============================================================================
show_summary() {
    echo ""
    log_success "=========================================="
    log_success "  生产镜像构建完成"
    log_success "=========================================="
    echo ""
    log_info "本地镜像:"
    echo "  - ${BACKEND_IMAGE}:${VERSION_TAG}"
    echo "  - ${BACKEND_IMAGE}:latest"
    if [ "$BUILD_FRONTEND" = true ]; then
        echo "  - ${FRONTEND_IMAGE}:${VERSION_TAG}"
        echo "  - ${FRONTEND_IMAGE}:latest"
    fi
    echo ""

    if [ "$REGISTRY_AVAILABLE" = true ]; then
        log_info "Registry 镜像:"
        echo "  - ${REGISTRY_BACKEND}:${VERSION_TAG}"
        echo "  - ${REGISTRY_BACKEND}:latest"
        if [ "$BUILD_FRONTEND" = true ]; then
            echo "  - ${REGISTRY_FRONTEND}:${VERSION_TAG}"
            echo "  - ${REGISTRY_FRONTEND}:latest"
        fi
        echo ""
    fi

    log_info "本地导出文件:"
    ls -lh "${EXPORT_DIR}"/*${VERSION_TAG}* 2>/dev/null || echo "  (无)"
    echo ""

    log_info "在其他机器加载镜像:"
    echo "  docker load -i ${BACKEND_IMAGE}-${VERSION_TAG}.tar"
    if [ "$BUILD_FRONTEND" = true ]; then
        echo "  docker load -i ${FRONTEND_IMAGE}-${VERSION_TAG}.tar"
    fi
    echo ""

    log_info "更新 .env.production 版本号:"
    echo "  bash scripts/update_image_version.sh ${VERSION_TAG}"
    echo ""
}

# =============================================================================
# 主流程
# =============================================================================
main() {
    check_environment
    check_registry

    echo ""
    read -p "开始构建? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "用户取消"
        exit 0
    fi

    build_backend_image
    build_frontend_image
    push_images
    export_images
    show_summary

    log_success "全部完成！"
}

# 执行主流程
main "$@"
