#!/bin/bash
# 准备跨网络部署包
# 包含镜像文件和部署配置文件
# Usage: bash scripts/prepare_deployment_package.sh [VERSION_TAG]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 版本号
VERSION_TAG="${1:-$(date +%Y%m%d)}"

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

echo "========================================================================="
echo "                     准备跨网络部署包"
echo "========================================================================="
echo ""
log_info "版本标签: $VERSION_TAG"
log_info "项目根目录: $PROJECT_ROOT"
echo ""

# ==================== 步骤 1: 检查镜像 ====================
log_info "步骤 1: 检查镜像..."

if ! docker images | grep -q "pepgmp-backend:$VERSION_TAG"; then
    log_warning "后端镜像不存在，开始构建..."
    bash "$SCRIPT_DIR/build_prod_only.sh" "$VERSION_TAG"
else
    log_success "后端镜像已存在: pepgmp-backend:$VERSION_TAG"
fi

if ! docker images | grep -q "pepgmp-frontend:$VERSION_TAG"; then
    log_warning "前端镜像不存在，开始构建..."
    bash "$SCRIPT_DIR/build_prod_only.sh" "$VERSION_TAG"
else
    log_success "前端镜像已存在: pepgmp-frontend:$VERSION_TAG"
fi

# ==================== 步骤 2: 导出镜像 ====================
log_info "步骤 2: 导出镜像..."

IMAGES_DIR="$PROJECT_ROOT/docker-images"
mkdir -p "$IMAGES_DIR"

BACKEND_TAR="$IMAGES_DIR/pepgmp-backend-$VERSION_TAG.tar"
FRONTEND_TAR="$IMAGES_DIR/pepgmp-frontend-$VERSION_TAG.tar"

if [ ! -f "$BACKEND_TAR" ]; then
    log_info "导出后端镜像..."
    docker save pepgmp-backend:$VERSION_TAG -o "$BACKEND_TAR"
    log_success "后端镜像已导出: $BACKEND_TAR"
    log_info "文件大小: $(du -h "$BACKEND_TAR" | cut -f1)"
else
    log_success "后端镜像已存在: $BACKEND_TAR"
fi

if [ ! -f "$FRONTEND_TAR" ]; then
    log_info "导出前端镜像..."
    docker save pepgmp-frontend:$VERSION_TAG -o "$FRONTEND_TAR"
    log_success "前端镜像已导出: $FRONTEND_TAR"
    log_info "文件大小: $(du -h "$FRONTEND_TAR" | cut -f1)"
else
    log_success "前端镜像已存在: $FRONTEND_TAR"
fi

# ==================== 步骤 3: 准备部署包 ====================
log_info "步骤 3: 准备部署包..."

DEPLOY_PACKAGE_DIR="$PROJECT_ROOT/deploy-packages/PEPGMP-$VERSION_TAG"

if [ -d "$DEPLOY_PACKAGE_DIR" ]; then
    read -p "部署包已存在，是否覆盖? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "跳过部署包准备"
    else
        rm -rf "$DEPLOY_PACKAGE_DIR"
        bash "$SCRIPT_DIR/prepare_minimal_deploy.sh" "$DEPLOY_PACKAGE_DIR"
        log_success "部署包已更新: $DEPLOY_PACKAGE_DIR"
    fi
else
    bash "$SCRIPT_DIR/prepare_minimal_deploy.sh" "$DEPLOY_PACKAGE_DIR"
    log_success "部署包已创建: $DEPLOY_PACKAGE_DIR"
fi

# ==================== 步骤 4: 创建传输包 ====================
log_info "步骤 4: 创建传输包..."

PACKAGE_NAME="pyt-deployment-$VERSION_TAG"
PACKAGE_DIR="$PROJECT_ROOT/$PACKAGE_NAME"
PACKAGE_TAR="$PROJECT_ROOT/$PACKAGE_NAME.tar.gz"

# 清理旧的打包目录
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# 复制镜像文件
log_info "复制镜像文件..."
mkdir -p "$PACKAGE_DIR/docker-images"
cp "$BACKEND_TAR" "$PACKAGE_DIR/docker-images/"
cp "$FRONTEND_TAR" "$PACKAGE_DIR/docker-images/"

# 复制部署包
log_info "复制部署包..."
cp -r "$DEPLOY_PACKAGE_DIR" "$PACKAGE_DIR/deploy-package"

# 创建部署说明文件
cat > "$PACKAGE_DIR/README.md" << EOF
# 部署包说明

## 版本信息
- 版本标签: $VERSION_TAG
- 创建时间: $(date)

## 包含内容
- docker-images/ - Docker 镜像文件
  - pepgmp-backend-$VERSION_TAG.tar
  - pepgmp-frontend-$VERSION_TAG.tar
- deploy-package/ - 部署配置文件
  - docker-compose.prod.yml
  - config/
  - scripts/
  - nginx/

## 部署步骤

### 1. 解压文件
\`\`\`bash
tar -xzf $PACKAGE_NAME.tar.gz
cd $PACKAGE_NAME
\`\`\`

### 2. 导入镜像
\`\`\`bash
cd docker-images
docker load -i pepgmp-backend-$VERSION_TAG.tar
docker load -i pepgmp-frontend-$VERSION_TAG.tar
\`\`\`

### 3. 准备部署目录
\`\`\`bash
mkdir -p ~/projects/PEPGMP
cd ~/projects/PEPGMP
cp -r ../$PACKAGE_NAME/deploy-package/* .
\`\`\`

### 4. 生成配置
\`\`\`bash
bash scripts/generate_production_config.sh
# 输入镜像版本: $VERSION_TAG
\`\`\`

### 5. 启动服务
\`\`\`bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
\`\`\`

### 6. 验证部署
\`\`\`bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl http://localhost:8000/api/v1/monitoring/health
curl -I http://localhost/
\`\`\`

## GPU 环境配置

如果需要在 GPU 环境中运行，确保：
1. NVIDIA 驱动已安装: \`nvidia-smi\`
2. Docker GPU 支持: \`docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi\`
3. 根据需要修改 docker-compose.prod.yml 添加 GPU 配置

详细说明请参考: docs/跨网络GPU环境部署指南.md
EOF

# 打包
log_info "打包文件..."
cd "$PROJECT_ROOT"
tar -czf "$PACKAGE_TAR" "$PACKAGE_NAME"

# 清理临时目录
rm -rf "$PACKAGE_DIR"

# 显示结果
log_success "========================================================================="
log_success "部署包创建完成"
log_success "========================================================================="
echo ""
log_info "部署包位置: $PACKAGE_TAR"
log_info "文件大小: $(du -h "$PACKAGE_TAR" | cut -f1)"
echo ""
log_info "包含内容:"
echo "  - Docker 镜像文件（后端 + 前端）"
echo "  - 部署配置文件"
echo "  - 部署说明文档"
echo ""
log_info "下一步:"
echo "  1. 将 $PACKAGE_TAR 传输到 WSL/Ubuntu Server"
echo "  2. 在目标环境中解压并按照 README.md 部署"
echo ""
log_info "传输方式:"
echo "  - Windows 文件系统: 复制到 /mnt/c/... 然后在 WSL 中访问"
echo "  - U盘/移动硬盘: 复制到移动设备"
echo "  - 网络传输: scp $PACKAGE_TAR user@server:/tmp/"
echo ""
