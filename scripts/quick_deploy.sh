#!/bin/bash

################################################################################
# 一键部署脚本
# 用途: 自动完成构建镜像 -> 推送到Registry -> 部署到生产服务器的全流程
# 使用: bash scripts/quick_deploy.sh <生产服务器IP> [SSH用户名] [镜像标签]
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PRODUCTION_HOST="${1}"
PRODUCTION_USER="${2:-ubuntu}"
IMAGE_TAG="${3:-latest}"
REGISTRY_URL="192.168.30.83:5433"
IMAGE_NAME="pepgmp-backend"
VERSION=$(date +%Y%m%d_%H%M%S)

echo "========================================================================="
echo -e "${BLUE}一键部署到生产环境${NC}"
echo "========================================================================="
echo ""
echo "目标服务器: ${PRODUCTION_HOST}"
echo "SSH用户: ${PRODUCTION_USER}"
echo "镜像标签: ${IMAGE_TAG}"
echo "版本: ${VERSION}"
echo "Registry: ${REGISTRY_URL}"
echo ""

# 检查参数
if [ -z "$PRODUCTION_HOST" ]; then
    echo -e "${RED}错误: 请提供生产服务器地址${NC}"
    echo "使用方法: bash $0 <生产服务器IP> [SSH用户名] [镜像标签]"
    echo "示例: bash $0 192.168.1.100 ubuntu latest"
    exit 1
fi

# 确认部署
echo -e "${YELLOW}=========================================================================${NC}"
echo -e "${YELLOW}警告: 即将执行完整部署流程！${NC}"
echo -e "${YELLOW}=========================================================================${NC}"
echo "将执行以下步骤:"
echo "  1. 构建Docker镜像"
echo "  2. 推送到Registry"
echo "  3. 部署到生产服务器"
echo ""
read -p "确认要继续吗？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "部署已取消"
    exit 0
fi
echo ""

# ==================== 步骤1: 构建镜像 ====================
echo -e "${GREEN}[步骤1/4]${NC} 构建Docker镜像..."
echo ""

if docker build -f Dockerfile.prod -t ${IMAGE_NAME}:${IMAGE_TAG} .; then
    echo -e "${GREEN}✓ 镜像构建成功${NC}"
else
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi
echo ""

# ==================== 步骤2: 推送到Registry ====================
echo -e "${GREEN}[步骤2/4]${NC} 推送镜像到Registry..."
echo ""

if bash scripts/push_to_registry.sh ${IMAGE_TAG} ${VERSION}; then
    echo -e "${GREEN}✓ 镜像推送成功${NC}"
else
    echo -e "${RED}✗ 镜像推送失败${NC}"
    exit 1
fi
echo ""

# ==================== 步骤3: 部署到生产服务器 ====================
echo -e "${GREEN}[步骤3/4]${NC} 部署到生产服务器..."
echo ""

if bash scripts/deploy_from_registry.sh ${PRODUCTION_HOST} ${PRODUCTION_USER} ${IMAGE_TAG}; then
    echo -e "${GREEN}✓ 部署成功${NC}"
else
    echo -e "${RED}✗ 部署失败${NC}"
    exit 1
fi
echo ""

# ==================== 步骤4: 健康检查 ====================
echo -e "${GREEN}[步骤4/4]${NC} 健康检查..."
echo ""

echo "等待服务启动..."
sleep 10

if curl -sf http://${PRODUCTION_HOST}:8000/api/v1/monitoring/health > /dev/null; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
    curl -s http://${PRODUCTION_HOST}:8000/api/v1/monitoring/health | python3 -m json.tool
else
    echo -e "${YELLOW}⚠ 健康检查失败，请手动验证${NC}"
fi
echo ""

# ==================== 完成 ====================
echo "========================================================================="
echo -e "${GREEN}部署完成！${NC}"
echo "========================================================================="
echo ""
echo "部署信息:"
echo "  服务器: ${PRODUCTION_HOST}"
echo "  镜像: ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "  版本: ${VERSION}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "验证命令:"
echo "  curl http://${PRODUCTION_HOST}:8000/api/v1/monitoring/health"
echo "  ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'docker ps'"
echo ""

