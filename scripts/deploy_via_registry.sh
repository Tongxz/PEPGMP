#!/bin/bash
# Registry 部署脚本（同一网络后使用）
# 功能：构建 → 推送Registry → 生产服务器拉取并部署
# 适用：Registry和生产服务器在同一网络时
# 使用：bash scripts/deploy_via_registry.sh [生产服务器IP] [版本号]

set -e

# --- 配置部分 ---
REGISTRY="11.25.125.115:5433"          # Registry地址（HTTP）
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

# 检查参数
if [ -z "$PRODUCTION_IP" ]; then
    log_error "请提供生产服务器IP"
    echo "使用方法: bash $0 <生产服务器IP> [SSH用户] [部署目录] [版本号]"
    echo "示例: bash $0 192.168.1.100 ubuntu /home/ubuntu/projects/PEPGMP 20251215-1430"
    exit 1
fi

echo "========================================================================="
echo "                    Registry 部署（同一网络）"
echo "========================================================================="
log_info "Registry: $REGISTRY"
log_info "后端镜像: $FULL_BACKEND_IMAGE"
log_info "前端镜像: $FULL_FRONTEND_IMAGE"
log_info "生产服务器: $PRODUCTION_USER@$PRODUCTION_IP"
log_info "部署目录: $DEPLOY_DIR"
log_info "版本标签: $TAG"
echo ""

# ==================== 步骤1: 验证Registry连接 ====================
log_info "[1/7] 验证Registry连接..."
if curl -sf "http://$REGISTRY/v2/_catalog" > /dev/null 2>&1; then
    log_success "Registry连接成功"
else
    log_error "无法连接到Registry: $REGISTRY"
    log_info "请检查是否连接到指定WiFi"
    exit 1
fi
echo ""

# ==================== 步骤2: 验证SSH连接 ====================
log_info "[2/7] 验证SSH连接..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes $PRODUCTION_USER@$PRODUCTION_IP "echo 'SSH OK'" > /dev/null 2>&1; then
    log_success "SSH连接成功"
else
    log_warning "SSH密钥认证失败，将提示输入密码"
fi
echo ""

# ==================== 步骤3: 验证生产服务器可访问Registry ====================
log_info "[3/7] 验证生产服务器可访问Registry..."
if ssh $PRODUCTION_USER@$PRODUCTION_IP "curl -sf http://$REGISTRY/v2/_catalog > /dev/null" 2>/dev/null; then
    log_success "生产服务器可以访问Registry"
else
    log_warning "生产服务器无法访问Registry"
    log_info "如果生产硬件尚未接入同一网络，请使用混合部署方案:"
    echo "  bash scripts/deploy_mixed_registry.sh $PRODUCTION_IP"
    read -p "是否继续? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi
echo ""

# ==================== 步骤3.5: 同步关键部署配置 ====================
log_info "[3.5/7] 同步关键部署配置（docker-compose / nginx / init_db.sql）..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    if [ ! -d "$DEPLOY_DIR" ]; then
        sudo mkdir -p $DEPLOY_DIR
        sudo chown $PRODUCTION_USER:$PRODUCTION_USER $DEPLOY_DIR
    fi
    mkdir -p $DEPLOY_DIR/nginx $DEPLOY_DIR/scripts
EOF

scp docker-compose.prod.yml $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/docker-compose.prod.yml
scp nginx/nginx.conf $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/nginx/nginx.conf
if [ -f "scripts/init_db.sql" ]; then
    scp scripts/init_db.sql $PRODUCTION_USER@$PRODUCTION_IP:$DEPLOY_DIR/scripts/init_db.sql
fi
log_success "关键部署配置同步完成"
echo ""

# ==================== 步骤4: 构建镜像 ====================
log_info "[4/7] 构建镜像: backend+frontend ($TAG)"

if [ ! -f "Dockerfile.prod" ]; then
    log_error "Dockerfile.prod 不存在"
    exit 1
fi

# 生产 GPU（RTX 50 / sm_120）需要较新的 PyTorch wheel。
# 与 deploy_mixed_registry.sh 保持一致：默认使用 nightly/cu126，可按需在 Dockerfile.prod 里切换 stable。
TORCH_INSTALL_MODE_DEFAULT="nightly"
TORCH_INDEX_URL_DEFAULT="https://download.pytorch.org/whl/nightly/cu128"

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    log_info "检测到ARM架构，使用buildx构建linux/amd64镜像"
    if ! docker buildx version > /dev/null 2>&1; then
        log_error "需要Docker Buildx来构建多架构镜像"
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
    docker buildx use "${BUILDER_NAME}" > /dev/null 2>&1 || true

    export DOCKER_BUILDKIT=1
    docker buildx build \
      --builder "${BUILDER_NAME}" \
      --platform linux/amd64 \
      --pull=false \
      -f Dockerfile.prod \
      --build-arg BASE_IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04" \
      --build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
      --build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
      -t $FULL_BACKEND_IMAGE \
      --load .

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
    export DOCKER_BUILDKIT=1
    docker build \
      -f Dockerfile.prod \
      --build-arg BASE_IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04" \
      --build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
      --build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
      -t $FULL_BACKEND_IMAGE \
      .

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
    docker images $FULL_BACKEND_IMAGE --format "  后端大小: {{.Size}}"
    docker images $FULL_FRONTEND_IMAGE --format "  前端大小: {{.Size}}"
else
    log_error "镜像构建失败"
    exit 1
fi
echo ""

# ==================== 步骤5: 推送到Registry ====================
log_info "[5/7] 推送到Registry..."
log_info "提示: Docker层缓存机制，只会上传变更的层"

docker push $FULL_BACKEND_IMAGE
docker push $FULL_FRONTEND_IMAGE

if [ $? -eq 0 ]; then
    log_success "镜像已推送到Registry:"
    echo "  - $FULL_BACKEND_IMAGE"
    echo "  - $FULL_FRONTEND_IMAGE"
else
    log_error "镜像推送失败"
    exit 1
fi
echo ""

# ==================== 步骤6: 备份当前版本 ====================
log_info "[6/7] 在生产服务器上备份当前版本..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    cd $DEPLOY_DIR

    if [ -f .env.production ]; then
        CURRENT_TAG=\$(grep "^IMAGE_TAG=" .env.production | cut -d'=' -f2 || echo "unknown")
        echo "当前版本: \$CURRENT_TAG"

        # 保留当前镜像用于回滚
        if docker images | grep -q "pepgmp-backend:\$CURRENT_TAG"; then
            echo "✓ 保留旧镜像用于回滚"
        fi
    fi
EOF
echo ""

# ==================== 步骤7: 在生产服务器拉取并部署 ====================
log_info "[7/7] 在生产服务器拉取并部署..."
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
        echo "错误: .env.production 不存在，请先执行首次部署"
        exit 1
    fi

    # 更新配置（使用Registry）
    echo "更新配置..."
    # 设置IMAGE_REGISTRY（防止重复追加）
    if grep -q "^IMAGE_REGISTRY=" .env.production; then
        sed -i "s|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=$REGISTRY/|" .env.production
    else
        # 如果不存在，在文件末尾追加（确保有换行）
        echo "" >> .env.production
        echo "IMAGE_REGISTRY=$REGISTRY/" >> .env.production
    fi

    # 更新IMAGE_TAG（防止重复追加）
    if grep -q "^IMAGE_TAG=" .env.production; then
        sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$TAG|" .env.production
    else
        # 如果不存在，在文件末尾追加（确保有换行）
        echo "" >> .env.production
        echo "IMAGE_TAG=$TAG" >> .env.production
    fi

    echo "✓ 配置已更新:"
    grep "IMAGE_REGISTRY\|IMAGE_TAG" .env.production

    # 配置Docker信任Registry（如果尚未配置）
    echo ""
    echo "检查Docker Registry配置..."
    if [ ! -f /etc/docker/daemon.json ] || ! grep -q "insecure-registries" /etc/docker/daemon.json; then
        echo "需要配置Docker信任Registry（需要sudo权限）"
        sudo mkdir -p /etc/docker
        if [ ! -f /etc/docker/daemon.json ]; then
            echo '{"insecure-registries": ["'"$REGISTRY"'"]}' | sudo tee /etc/docker/daemon.json > /dev/null
        else
            # 使用jq添加insecure-registries（如果安装了jq）
            if command -v jq > /dev/null 2>&1; then
                sudo jq '. + {"insecure-registries": ["'"$REGISTRY"'"]}' /etc/docker/daemon.json | sudo tee /etc/docker/daemon.json.tmp > /dev/null
                sudo mv /etc/docker/daemon.json.tmp /etc/docker/daemon.json
            else
                echo "警告: 需要手动配置 /etc/docker/daemon.json"
                echo "添加: \"insecure-registries\": [\"$REGISTRY\"]"
            fi
        fi
        sudo systemctl restart docker
        echo "✓ Docker已配置信任Registry"
        sleep 2
    else
        echo "✓ Docker Registry配置已存在"
    fi

    # 拉取新镜像
    echo ""
    echo "拉取新镜像..."
    docker compose -f docker-compose.prod.yml --env-file .env.production pull api frontend-init

    # 滚动更新服务
    echo ""
    echo "更新服务..."
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api

    echo ""
    echo "提取前端静态文件..."
    docker compose -f docker-compose.prod.yml --env-file .env.production up --abort-on-container-exit frontend-init
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps nginx

    # 等待服务启动
    echo ""
    echo "等待服务启动（10秒）..."
    sleep 10

    # 检查容器状态
    echo ""
    echo "容器状态:"
    docker compose -f docker-compose.prod.yml ps api

    # 清理悬空的废弃镜像（Dangling images）
    # 这会删除未被使用的旧镜像层，防止磁盘空间占满
    echo ""
    echo "清理旧镜像..."
    docker image prune -f
    echo "✓ 旧镜像已清理"
EOF

if [ $? -eq 0 ]; then
    log_success "服务部署完成"
else
    log_error "服务部署失败"
    exit 1
fi

echo ""
log_info "[8/8] 健康检查..."
sleep 5

if ssh $PRODUCTION_USER@$PRODUCTION_IP "curl -sf http://localhost/api/v1/monitoring/health > /dev/null" 2>/dev/null; then
    log_success "健康检查通过"
else
    log_warning "健康检查失败，请检查日志"
    log_info "查看日志: ssh $PRODUCTION_USER@$PRODUCTION_IP 'cd $DEPLOY_DIR && docker compose logs api --tail 50'"
fi

echo ""
log_success "========================================================================="
log_success "                        部署完成"
log_success "========================================================================="
echo ""
log_info "部署信息:"
echo "  Registry: $REGISTRY"
echo "  后端镜像: $FULL_BACKEND_IMAGE"
echo "  前端镜像: $FULL_FRONTEND_IMAGE"
echo "  生产服务器: $PRODUCTION_IP"
echo ""
log_info "常用命令:"
echo "  查看日志: ssh $PRODUCTION_USER@$PRODUCTION_IP 'cd $DEPLOY_DIR && docker compose logs -f api'"
echo "  查看状态: ssh $PRODUCTION_USER@$PRODUCTION_IP 'cd $DEPLOY_DIR && docker compose ps'"
echo "  回滚版本: ssh $PRODUCTION_USER@$PRODUCTION_IP 'cd $DEPLOY_DIR && bash scripts/update_image_version.sh <旧版本>'"
echo ""
