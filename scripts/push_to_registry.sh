#!/bin/bash

################################################################################
# 推送镜像到私有Registry
# 用途: 将构建好的Docker镜像推送到私有镜像仓库
# 使用: bash scripts/push_to_registry.sh
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
REGISTRY_URL="192.168.30.83:5433"
IMAGE_NAME="pyt-backend"
IMAGE_TAG="${1:-latest}"
VERSION="${2:-$(date +%Y%m%d_%H%M%S)}"

echo "========================================================================="
echo -e "${BLUE}推送镜像到私有Registry${NC}"
echo "========================================================================="
echo ""
echo "Registry地址: ${REGISTRY_URL}"
echo "镜像名称: ${IMAGE_NAME}"
echo "标签: ${IMAGE_TAG}"
echo "版本: ${VERSION}"
echo ""

# ==================== 步骤1: 检查本地镜像 ====================
echo -e "${GREEN}[步骤1/5]${NC} 检查本地镜像..."
echo ""

if ! docker images | grep -q "${IMAGE_NAME}.*${IMAGE_TAG}"; then
    echo -e "${RED}错误: 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在${NC}"
    echo "请先构建镜像: docker build -f Dockerfile.prod -t ${IMAGE_NAME}:${IMAGE_TAG} ."
    exit 1
fi
echo "✓ 本地镜像存在: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# ==================== 步骤2: 标记镜像 ====================
echo -e "${GREEN}[步骤2/5]${NC} 标记镜像..."
echo ""

# 标记latest
echo "标记为 ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}

# 标记版本号
echo "标记为 ${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}"
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}

echo "✓ 镜像标记完成"
echo ""

# ==================== 步骤3: 测试Registry连接 ====================
echo -e "${GREEN}[步骤3/5]${NC} 测试Registry连接..."
echo ""

if curl -sf http://${REGISTRY_URL}/v2/_catalog > /dev/null; then
    echo "✓ Registry连接成功"
else
    echo -e "${YELLOW}警告: 无法连接到Registry，但将继续尝试推送${NC}"
fi
echo ""

# ==================== 步骤4: 配置Docker信任私有Registry ====================
echo -e "${GREEN}[步骤4/5]${NC} 配置Docker..."
echo ""

# 检查daemon.json
DOCKER_CONFIG=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "检测到macOS系统"
    echo "请确保Docker Desktop已配置信任此Registry"
    echo "位置: Docker Desktop -> Preferences -> Docker Engine"
    echo "添加配置: \"insecure-registries\": [\"${REGISTRY_URL}\"]"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    DOCKER_CONFIG="/etc/docker/daemon.json"
    echo "检测到Linux系统"
    if [ -f "$DOCKER_CONFIG" ]; then
        if grep -q "insecure-registries" "$DOCKER_CONFIG"; then
            echo "✓ Registry配置已存在"
        else
            echo -e "${YELLOW}需要配置信任Registry，请运行:${NC}"
            echo "sudo bash -c 'cat > /etc/docker/daemon.json << EOF
{
  \"insecure-registries\": [\"${REGISTRY_URL}\"]
}
EOF'"
            echo "sudo systemctl restart docker"
        fi
    fi
fi
echo ""

# ==================== 步骤5: 推送镜像 ====================
echo -e "${GREEN}[步骤5/5]${NC} 推送镜像到Registry..."
echo ""

echo "推送 ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
if docker push ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}; then
    echo "✓ 推送 ${IMAGE_TAG} 成功"
else
    echo -e "${RED}错误: 推送失败${NC}"
    echo "可能的原因:"
    echo "1. Registry不可访问"
    echo "2. Docker未配置信任此Registry"
    echo "3. 网络连接问题"
    exit 1
fi
echo ""

echo "推送 ${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}"
if docker push ${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}; then
    echo "✓ 推送 ${VERSION} 成功"
fi
echo ""

# ==================== 推送完成 ====================
echo "========================================================================="
echo -e "${GREEN}镜像推送成功！${NC}"
echo "========================================================================="
echo ""
echo "推送的镜像:"
echo "  - ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}"
echo "  - ${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}"
echo ""
echo "镜像大小:"
docker images ${REGISTRY_URL}/${IMAGE_NAME} --format "{{.Repository}}:{{.Tag}} - {{.Size}}"
echo ""
echo "查看Registry中的镜像:"
echo "  curl http://${REGISTRY_URL}/v2/_catalog"
echo "  curl http://${REGISTRY_URL}/v2/${IMAGE_NAME}/tags/list"
echo ""
echo "下一步:"
echo "  在生产服务器上部署:"
echo "  bash scripts/deploy_from_registry.sh <生产服务器IP>"
echo ""
echo "========================================================================="
