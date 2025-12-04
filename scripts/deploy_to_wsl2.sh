#!/bin/bash
# WSL2/Ubuntu 自动化部署脚本
# 从 macOS 开发环境自动部署到 WSL2/Ubuntu
# Usage: bash scripts/deploy_to_wsl2.sh [WSL2_HOST] [VERSION_TAG] [DEPLOY_DIR]

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
WSL2_HOST="${1:-}"
VERSION_TAG="${2:-$(date +%Y%m%d)}"
DEPLOY_DIR="${3:-~/projects/Pyt}"

echo "========================================================================="
echo -e "${BLUE}WSL2/Ubuntu 自动化部署脚本${NC}"
echo "========================================================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo "WSL2 host: ${WSL2_HOST:-未指定，将使用本地准备}"
echo "Version tag: $VERSION_TAG"
echo "Deploy directory: $DEPLOY_DIR"
echo ""

# Check functions
check_passed() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_failed() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

check_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# ==================== 步骤 1: 检查环境 ====================
check_info "步骤 1: 检查环境..."

if ! command -v docker &> /dev/null; then
    check_failed "Docker 未安装"
fi

if ! docker info &> /dev/null; then
    check_failed "Docker 守护进程未运行"
fi

check_passed "Docker 环境检查通过"

# ==================== 步骤 2: 检查镜像 ====================
check_info "步骤 2: 检查镜像..."

if ! docker images | grep -q "pepgmp-backend:$VERSION_TAG"; then
    check_warning "后端镜像不存在，开始构建..."
    bash "$SCRIPT_DIR/build_prod_only.sh" "$VERSION_TAG"
else
    check_passed "后端镜像已存在: pepgmp-backend:$VERSION_TAG"
fi

if ! docker images | grep -q "pepgmp-frontend:$VERSION_TAG"; then
    check_warning "前端镜像不存在，开始构建..."
    bash "$SCRIPT_DIR/build_prod_only.sh" "$VERSION_TAG"
else
    check_passed "前端镜像已存在: pepgmp-frontend:$VERSION_TAG"
fi

# ==================== 步骤 3: 导出镜像 ====================
check_info "步骤 3: 导出镜像..."

mkdir -p "$PROJECT_ROOT/docker-images"

BACKEND_TAR="$PROJECT_ROOT/docker-images/pepgmp-backend-$VERSION_TAG.tar"
FRONTEND_TAR="$PROJECT_ROOT/docker-images/pepgmp-frontend-$VERSION_TAG.tar"

if [ ! -f "$BACKEND_TAR" ]; then
    check_info "导出后端镜像..."
    docker save pepgmp-backend:$VERSION_TAG -o "$BACKEND_TAR"
    check_passed "后端镜像已导出: $BACKEND_TAR"
else
    check_passed "后端镜像已存在: $BACKEND_TAR"
fi

if [ ! -f "$FRONTEND_TAR" ]; then
    check_info "导出前端镜像..."
    docker save pepgmp-frontend:$VERSION_TAG -o "$FRONTEND_TAR"
    check_passed "前端镜像已导出: $FRONTEND_TAR"
else
    check_passed "前端镜像已存在: $FRONTEND_TAR"
fi

# ==================== 步骤 4: 准备部署包 ====================
check_info "步骤 4: 准备部署包..."

DEPLOY_PACKAGE_DIR="$PROJECT_ROOT/deploy-packages/Pyt-$VERSION_TAG"

if [ -d "$DEPLOY_PACKAGE_DIR" ]; then
    read -p "部署包已存在，是否覆盖? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DEPLOY_PACKAGE_DIR"
    else
        check_warning "跳过部署包准备"
        DEPLOY_PACKAGE_DIR=""
    fi
fi

if [ -n "$DEPLOY_PACKAGE_DIR" ]; then
    check_info "创建部署包..."
    bash "$SCRIPT_DIR/prepare_minimal_deploy.sh" "$DEPLOY_PACKAGE_DIR"
    check_passed "部署包已创建: $DEPLOY_PACKAGE_DIR"
fi

# ==================== 步骤 5: 传输到 WSL2 ====================
if [ -n "$WSL2_HOST" ]; then
    check_info "步骤 5: 传输到 WSL2 ($WSL2_HOST)..."

    # 检查 SSH 连接
    if ! ssh -o ConnectTimeout=5 "$WSL2_HOST" "echo 'SSH connection OK'" &> /dev/null; then
        check_failed "无法连接到 WSL2 主机: $WSL2_HOST"
    fi

    check_info "传输镜像文件..."
    scp "$BACKEND_TAR" "$FRONTEND_TAR" "$WSL2_HOST:/tmp/"

    check_info "传输部署包..."
    if [ -n "$DEPLOY_PACKAGE_DIR" ]; then
        rsync -avz --progress "$DEPLOY_PACKAGE_DIR/" "$WSL2_HOST:$DEPLOY_DIR/"
    fi

    check_passed "文件传输完成"

    # ==================== 步骤 6: 在 WSL2 中部署 ====================
    check_info "步骤 6: 在 WSL2 中部署..."

    ssh "$WSL2_HOST" << EOF
        set -e

        echo "========================================================================="
        echo "在 WSL2 中部署"
        echo "========================================================================="

        # 导入镜像
        echo "[i] 导入镜像..."
        docker load -i /tmp/pepgmp-backend-$VERSION_TAG.tar
        docker load -i /tmp/pepgmp-frontend-$VERSION_TAG.tar

        # 清理临时文件
        rm -f /tmp/pepgmp-*.tar

        # 进入部署目录
        cd $DEPLOY_DIR

        # 生成配置文件（如果不存在）
        if [ ! -f .env.production ]; then
            echo "[i] 生成配置文件..."
            bash scripts/generate_production_config.sh -y
        fi

        # 更新 IMAGE_TAG
        if grep -q "IMAGE_TAG=" .env.production; then
            sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production
        else
            echo "IMAGE_TAG=$VERSION_TAG" >> .env.production
        fi

        # 启动服务
        echo "[i] 启动服务..."
        docker compose -f docker-compose.prod.yml --env-file .env.production up -d

        echo "[i] 等待服务启动..."
        sleep 10

        # 检查服务状态
        echo "[i] 检查服务状态..."
        docker compose -f docker-compose.prod.yml --env-file .env.production ps

        echo ""
        echo "[✓] 部署完成！"
        echo ""
        echo "访问地址:"
        echo "  前端: http://localhost/"
        echo "  API: http://localhost:8000/api/v1/monitoring/health"
EOF

    check_passed "WSL2 部署完成"
else
    check_warning "未指定 WSL2 主机，跳过远程部署"
    check_info "部署包和镜像文件已准备完成："
    echo "  镜像文件: $PROJECT_ROOT/docker-images/"
    echo "  部署包: $DEPLOY_PACKAGE_DIR"
    echo ""
    echo "手动部署步骤："
    echo "  1. 将镜像文件传输到 WSL2"
    echo "  2. 将部署包传输到 WSL2"
    echo "  3. 在 WSL2 中运行："
    echo "     docker load -i /path/to/pepgmp-backend-$VERSION_TAG.tar"
    echo "     docker load -i /path/to/pepgmp-frontend-$VERSION_TAG.tar"
    echo "     cd $DEPLOY_DIR"
    echo "     bash scripts/generate_production_config.sh"
    echo "     docker compose -f docker-compose.prod.yml --env-file .env.production up -d"
fi

echo ""
check_passed "========================================================================="
check_passed "部署准备完成"
check_passed "========================================================================="
