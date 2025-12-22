#!/bin/bash
# 混合部署脚本（网络隔离适配版）
# 功能：构建 -> (可选推送) -> 导出 -> 暂停换网 -> 传输 -> 部署
# 适用：开发机无法同时连接Registry和生产网络的情况

set -e

# --- 配置部分 ---
REGISTRY="11.25.125.115:5433"
IMAGE_NAME_BACKEND="pepgmp-backend"
IMAGE_NAME_FRONTEND="pepgmp-frontend"
PRODUCTION_IP="${1}"
PRODUCTION_USER="${2:-ubuntu}"
DEPLOY_DIR="${3:-/home/ubuntu/projects/PEPGMP}"
TAG="${4:-$(date +%Y%m%d-%H%M)}"
FULL_BACKEND_IMAGE="$REGISTRY/$IMAGE_NAME_BACKEND:$TAG"
FULL_FRONTEND_IMAGE="$REGISTRY/$IMAGE_NAME_FRONTEND:$TAG"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 交互式确认函数
wait_for_network_switch() {
    echo ""
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW}   🚧 暂停：请切换网络！ 🚧${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    echo "当前阶段完成。请断开 Registry 网络，连接到生产环境网络。"
    echo "目标服务器: $PRODUCTION_IP"
    echo ""
    read -p "网络切换完成后，请按 [Enter] 键继续..."
    echo ""
}

# 检查参数
if [ -z "$PRODUCTION_IP" ]; then
    log_error "请提供生产服务器IP"
    exit 1
fi

echo "========================================================================="
echo "               混合部署方案（网络隔离适配版）"
echo "========================================================================="
log_info "Registry: $REGISTRY"
log_info "版本标签: $TAG"
echo ""

# 检查tar文件是否已存在（支持从中间步骤继续）
TAR_FILE_BACKEND="/tmp/pepgmp-backend-$TAG.tar.gz"
TAR_FILE_FRONTEND="/tmp/pepgmp-frontend-$TAG.tar.gz"
SKIP_BUILD=false
if [ -f "$TAR_FILE_BACKEND" ] && [ -f "$TAR_FILE_FRONTEND" ]; then
    log_warning "检测到已存在的tar文件:"
    echo "  - $TAR_FILE_BACKEND"
    echo "  - $TAR_FILE_FRONTEND"
    read -p "是否使用现有文件跳过构建步骤? (Y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        SKIP_BUILD=true
        log_info "将使用现有tar文件，跳过构建和导出步骤"
    else
        log_info "将重新构建镜像"
        rm -f "$TAR_FILE_BACKEND" "$TAR_FILE_FRONTEND"
    fi
fi

# ==================== 步骤1: 构建镜像 (本地执行，无需网络) ====================
if [ "$SKIP_BUILD" = "false" ]; then
    log_info "[1/7] 构建镜像..."

    # 架构检测与构建
    ARCH=$(uname -m)
    if [ ! -f "Dockerfile.prod" ]; then
        log_error "Dockerfile.prod 不存在"
        exit 1
    fi

    # 检查本地是否有基础镜像
    BASE_IMAGE="nvidia/cuda:12.4.0-runtime-ubuntu22.04"
    if ! docker images $BASE_IMAGE --format "{{.Repository}}:{{.Tag}}" | grep -q "$BASE_IMAGE"; then
        log_error "本地没有基础镜像: $BASE_IMAGE"
        log_info "请先拉取镜像: docker pull $BASE_IMAGE"
        exit 1
    fi

    log_info "本地基础镜像已找到: $BASE_IMAGE"

# 生产构建依赖需要外网下载（PyTorch CUDA wheel / PyPI 依赖）。
# 由于你当前没有内部镜像源、私有 Registry 也不可用，这里必须在“可上网”的网络环境下完成构建，
# 构建完成后再切换到生产网络进行 scp 传输（混合部署的设计就是为此服务）。
TORCH_INSTALL_MODE_DEFAULT="nightly"
TORCH_INDEX_URL_DEFAULT="https://download.pytorch.org/whl/nightly/cu126"
PIP_MIRROR_DEFAULT="https://pypi.tuna.tsinghua.edu.cn/simple/"
log_info "检查构建依赖下载源连通性..."
if ! curl -sf --connect-timeout 5 "$TORCH_INDEX_URL_DEFAULT" > /dev/null 2>&1; then
    log_error "无法访问 PyTorch 下载源: $TORCH_INDEX_URL_DEFAULT"
    log_error "当前网络无法完成生产镜像构建（没有内部镜像源/Registry 也不可用）。"
    log_info "请切换到可上网网络（例如手机热点/办公网络）后重新执行本脚本完成构建；"
    log_info "构建完成导出 tar 后，再按提示切回生产网络执行 scp 传输。"
    exit 1
fi
if ! curl -sf --connect-timeout 5 "$PIP_MIRROR_DEFAULT" > /dev/null 2>&1; then
    log_error "无法访问 PyPI 镜像源: $PIP_MIRROR_DEFAULT"
    log_error "当前网络无法完成生产镜像构建（依赖无法下载）。"
    log_info "请切换到可上网网络后重新执行本脚本。"
    exit 1
fi
log_success "依赖下载源可达，继续构建。"

    # 检查网络连接（Docker Hub）
    log_info "检查网络连接..."
    if ! curl -sf --connect-timeout 3 "https://auth.docker.io" > /dev/null 2>&1; then
        log_warning "无法连接到 Docker Hub，将使用本地镜像构建"
        USE_OFFLINE_BUILD=true
    else
        USE_OFFLINE_BUILD=false
    fi

    # 开始构建
    export DOCKER_BUILDKIT=1
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        log_info "检测到ARM架构，使用buildx构建linux/amd64..."

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
        docker buildx use "${BUILDER_NAME}" > /dev/null 2>&1 || true

        # 执行构建：
        # - Dockerfile.prod 使用 BASE_IMAGE build-arg（默认 nvidia/cuda:...）
        # - 这里显式传入 BASE_IMAGE，确保与本地检查一致
        docker buildx build \
          --builder "${BUILDER_NAME}" \
          --platform linux/amd64 \
          --pull=false \
          -f Dockerfile.prod \
          --build-arg BASE_IMAGE="nvidia/cuda:12.4.0-runtime-ubuntu22.04" \
          --build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
          --build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
          -t $FULL_BACKEND_IMAGE \
          --load .

        # 构建前端镜像（同样使用 buildx 输出 linux/amd64）
        if [ ! -f "Dockerfile.frontend" ]; then
            log_error "Dockerfile.frontend 不存在，但生产需要 pepgmp-frontend 镜像"
            exit 1
        fi
        docker buildx build \
          --builder "${BUILDER_NAME}" \
          --platform linux/amd64 \
          --pull=false \
          -f Dockerfile.frontend \
          --build-arg VITE_API_BASE=/api/v1 \
          --build-arg BASE_URL=/ \
          --build-arg SKIP_TYPE_CHECK=true \
          -t $FULL_FRONTEND_IMAGE \
          --load .
    else
        docker build -f Dockerfile.prod -t $FULL_BACKEND_IMAGE .
        if [ ! -f "Dockerfile.frontend" ]; then
            log_error "Dockerfile.frontend 不存在，但生产需要 pepgmp-frontend 镜像"
            exit 1
        fi
        docker build -f Dockerfile.frontend \
          --build-arg VITE_API_BASE=/api/v1 \
          --build-arg BASE_URL=/ \
          --build-arg SKIP_TYPE_CHECK=true \
          -t $FULL_FRONTEND_IMAGE .
    fi

    if [ $? -eq 0 ]; then
        log_success "镜像构建完成"
    else
        log_error "构建失败"
        log_info "提示: 如果是因为网络问题无法拉取基础镜像，请："
        echo "  1. 确保本地有镜像: docker images | grep nvidia/cuda"
        echo "  2. 或手动拉取: docker pull $BASE_IMAGE"
        exit 1
    fi
    echo ""

    # ==================== 步骤2: 尝试推送到 Registry ====================
    log_info "[2/7] 检查 Registry 连接并推送..."

    # 非阻塞检测：如果能连上就推，连不上就跳过
    if curl -sf --connect-timeout 3 "http://$REGISTRY/v2/_catalog" > /dev/null 2>&1; then
        log_info "检测到 Registry 在线，正在推送..."
        if docker push $FULL_BACKEND_IMAGE && docker push $FULL_FRONTEND_IMAGE; then
            log_success "镜像已备份到 Registry"
        else
            log_warning "推送失败，但这不影响后续部署"
        fi
    else
        log_warning "⚠️  无法连接 Registry ($REGISTRY)"
        log_warning "   跳过推送步骤，仅使用本地 tar 包部署"
        log_info "   (这是正常的，如果你当前连接的是生产网络)"
    fi
    echo ""

    # ==================== 步骤3: 导出镜像 ====================
    log_info "[3/7] 导出镜像为 tar 文件..."

    docker save $FULL_BACKEND_IMAGE | gzip > $TAR_FILE_BACKEND
    docker save $FULL_FRONTEND_IMAGE | gzip > $TAR_FILE_FRONTEND
    TAR_SIZE_BACKEND=$(ls -lh $TAR_FILE_BACKEND | awk '{print $5}')
    TAR_SIZE_FRONTEND=$(ls -lh $TAR_FILE_FRONTEND | awk '{print $5}')
    log_success "镜像已导出:"
    echo "  - $TAR_FILE_BACKEND ($TAR_SIZE_BACKEND)"
    echo "  - $TAR_FILE_FRONTEND ($TAR_SIZE_FRONTEND)"
    echo ""
else
    log_info "[1-3/7] 跳过构建、推送、导出步骤（使用现有tar文件）"
    TAR_SIZE_BACKEND=$(ls -lh $TAR_FILE_BACKEND | awk '{print $5}')
    TAR_SIZE_FRONTEND=$(ls -lh $TAR_FILE_FRONTEND | awk '{print $5}')
    log_info "使用现有文件:"
    echo "  - $TAR_FILE_BACKEND ($TAR_SIZE_BACKEND)"
    echo "  - $TAR_FILE_FRONTEND ($TAR_SIZE_FRONTEND)"
    echo ""
fi

# ==================== 步骤4: 关键点 - 暂停切换网络 ====================

# 先检测一下生产网络通不通，如果不通，说明需要切换
if ! ping -c 1 -W 2 $PRODUCTION_IP > /dev/null 2>&1; then
    wait_for_network_switch

    # 再次检测
    log_info "正在检测生产网络连接..."
    while ! ping -c 1 -W 2 $PRODUCTION_IP > /dev/null 2>&1; do
        log_warning "无法 ping 通 $PRODUCTION_IP，请检查网络..."
        read -p "重试请按 [Enter]，退出请按 [Ctrl+C]..."
    done
    log_success "网络已连通！"
else
    log_info "生产网络已连通，无需切换。"
fi
echo ""

# ==================== 步骤5: 传输文件 ====================
log_info "[5/7] 传输文件到生产服务器..."

# 检查文件是否存在
if [ ! -f "$TAR_FILE_BACKEND" ] || [ ! -f "$TAR_FILE_FRONTEND" ]; then
    log_error "tar文件不存在（需要同时存在 backend+frontend）"
    exit 1
fi

# 同步关键部署配置（避免本地更新了 compose/nginx，但生产机仍然使用旧配置）
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "docker-compose.prod.yml 不存在，无法同步生产配置"
    exit 1
fi
if [ ! -f "nginx/nginx.conf" ]; then
    log_error "nginx/nginx.conf 不存在，无法同步 Nginx 配置"
    exit 1
fi
if [ ! -f "scripts/init_db.sql" ]; then
    log_warning "scripts/init_db.sql 不存在（若生产不依赖该文件可忽略）"
fi

# 预先确保远端目录存在（否则 scp 无法落到目标路径）
log_info "准备远端目录（用于同步 compose/nginx 配置）..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    if [ ! -d "$DEPLOY_DIR" ]; then
        sudo mkdir -p $DEPLOY_DIR
        sudo chown $PRODUCTION_USER:$PRODUCTION_USER $DEPLOY_DIR
    fi
    mkdir -p $DEPLOY_DIR/nginx $DEPLOY_DIR/scripts
EOF

# 支持重试机制
RETRY_COUNT=0
MAX_RETRIES=3
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if scp $TAR_FILE_BACKEND $PRODUCTION_USER@$PRODUCTION_IP:/tmp/ \
        && scp $TAR_FILE_FRONTEND $PRODUCTION_USER@$PRODUCTION_IP:/tmp/ \
        && scp docker-compose.prod.yml $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/docker-compose.prod.yml \
        && scp nginx/nginx.conf $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/nginx/nginx.conf \
        && ( [ -f "scripts/init_db.sql" ] && scp scripts/init_db.sql $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/scripts/init_db.sql || true ); then
        log_success "传输成功"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            log_warning "传输失败，正在重试 ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 2
        else
            log_error "传输失败（已重试 $MAX_RETRIES 次），请检查 SSH 连接"
            log_info "提示："
            echo "  1. 检查SSH连接: ssh $PRODUCTION_USER@$PRODUCTION_IP"
            echo "  2. 检查网络连接: ping $PRODUCTION_IP"
            echo "  3. 可以手动传输: scp $TAR_FILE $PRODUCTION_USER@$PRODUCTION_IP:/tmp/"
            echo "  4. tar文件位置: $TAR_FILE"
            exit 1
        fi
    fi
done
echo ""

# ==================== 步骤6: 远程部署 ====================
log_info "[6/7] 远程执行部署..."

ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e

    # 检查并创建部署目录
    if [ ! -d "$DEPLOY_DIR" ]; then
        echo "⚠️  部署目录不存在，正在创建: $DEPLOY_DIR"
        sudo mkdir -p $DEPLOY_DIR
        sudo chown $PRODUCTION_USER:$PRODUCTION_USER $DEPLOY_DIR
        echo "✓ 目录已创建"
    fi

    cd $DEPLOY_DIR

    # 检查配置文件
    if [ ! -f .env.production ]; then
        echo "⚠️  配置文件不存在，需要首次部署"
        echo "请先执行首次部署步骤，或手动创建 .env.production"
        exit 1
    fi

    echo "1. 导入镜像 (解压中)..."
    docker load < /tmp/pepgmp-backend-$TAG.tar.gz
    docker load < /tmp/pepgmp-frontend-$TAG.tar.gz

    # 重新打标签
    docker tag $FULL_BACKEND_IMAGE pepgmp-backend:$TAG
    docker tag $FULL_BACKEND_IMAGE pepgmp-backend:latest
    docker tag $FULL_FRONTEND_IMAGE pepgmp-frontend:$TAG
    docker tag $FULL_FRONTEND_IMAGE pepgmp-frontend:latest

    echo "2. 更新版本配置..."
    # 智能更新/追加 TAG
    if grep -q "^IMAGE_TAG=" .env.production; then
        sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$TAG|" .env.production
    else
        echo "" >> .env.production
        echo "IMAGE_TAG=$TAG" >> .env.production
    fi

    # 确保不使用远程 Registry 前缀
    if grep -q "^IMAGE_REGISTRY=" .env.production; then
        sed -i 's|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=|' .env.production
    fi

    echo "3. 重启服务..."
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api
    # 运行 frontend-init 以提取静态文件（一次性任务）
    docker compose -f docker-compose.prod.yml --env-file .env.production up --abort-on-container-exit frontend-init
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps nginx

    echo "4. 清理..."
    rm -f /tmp/pepgmp-backend-$TAG.tar.gz /tmp/pepgmp-frontend-$TAG.tar.gz
    docker image prune -f > /dev/null 2>&1
EOF

if [ $? -eq 0 ]; then
    log_success "部署脚本执行完成"
else
    log_error "远程部署执行失败"
    exit 1
fi

# ==================== 步骤7: 健康检查 ====================
log_info "[7/7] 等待服务启动并检查..."
sleep 5

# 说明：
# - 这里会触发 SSH 认证（如果未配置免密），建议生产环境配置 SSH Key 以便脚本全自动运行。
# - 优先检查 api 容器自身的健康端点（避免 nginx 尚未就绪导致误判）。
MAX_HEALTH_RETRIES=15
HEALTH_OK=false
for i in $(seq 1 $MAX_HEALTH_RETRIES); do
    if ssh $PRODUCTION_USER@$PRODUCTION_IP \
        "docker exec pepgmp-api-prod curl -sf --max-time 5 http://localhost:8000/api/v1/monitoring/health > /dev/null" \
        > /dev/null 2>&1; then
        HEALTH_OK=true
        break
    fi
    log_info "健康检查未就绪，重试 $i/$MAX_HEALTH_RETRIES（等待启动中）..."
    sleep 4
done

if [ "$HEALTH_OK" = "true" ]; then
    log_success "✅ 健康检查通过！API 服务已就绪。"
else
    log_warning "⚠️  健康检查未通过（可能启动失败或启动时间较长）"
    log_info "   建议在生产机执行："
    echo "     ssh $PRODUCTION_USER@$PRODUCTION_IP 'cd $DEPLOY_DIR && docker compose -f docker-compose.prod.yml --env-file .env.production ps'"
    echo "     ssh $PRODUCTION_USER@$PRODUCTION_IP 'docker logs --tail 200 pepgmp-api-prod'"
fi

# 清理本地
rm -f $TAR_FILE_BACKEND $TAR_FILE_FRONTEND
echo ""
