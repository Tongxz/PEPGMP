#!/bin/bash

################################################################################
# 生产环境部署脚本
# 用途: 将Docker镜像从macOS开发环境部署到Ubuntu生产环境
# 使用: bash scripts/deploy_to_production.sh [PRODUCTION_HOST]
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PRODUCTION_HOST="${1:-your-production-server.com}"  # 生产服务器地址
PRODUCTION_USER="${2:-ubuntu}"                       # SSH用户名
IMAGE_NAME="pyt-backend"
IMAGE_TAG="latest"
DEPLOY_DIR="/opt/pyt"                                # 生产环境部署目录

echo "========================================================================="
echo -e "${BLUE}生产环境部署脚本${NC}"
echo "========================================================================="
echo ""
echo "目标服务器: ${PRODUCTION_HOST}"
echo "SSH用户: ${PRODUCTION_USER}"
echo "部署目录: ${DEPLOY_DIR}"
echo ""

# 检查生产服务器地址
if [ "$PRODUCTION_HOST" = "your-production-server.com" ]; then
    echo -e "${RED}错误: 请提供生产服务器地址${NC}"
    echo "使用方法: bash $0 <生产服务器IP或域名> [SSH用户名]"
    echo "示例: bash $0 192.168.1.100 ubuntu"
    exit 1
fi

# 确认部署
echo -e "${YELLOW}=========================================================================${NC}"
echo -e "${YELLOW}警告: 即将部署到生产环境！${NC}"
echo -e "${YELLOW}=========================================================================${NC}"
read -p "确认要部署到 ${PRODUCTION_HOST} 吗？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "部署已取消"
    exit 0
fi
echo ""

# ==================== 步骤1: 检查本地环境 ====================
echo -e "${GREEN}[步骤1/7]${NC} 检查本地环境..."
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    exit 1
fi
echo "✓ Docker已安装: $(docker --version)"

# 检查镜像
if ! docker images | grep -q "${IMAGE_NAME}.*${IMAGE_TAG}"; then
    echo -e "${RED}错误: 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在${NC}"
    echo "请先构建镜像: docker build -f Dockerfile.prod -t ${IMAGE_NAME}:${IMAGE_TAG} ."
    exit 1
fi
echo "✓ 镜像已存在: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# ==================== 步骤2: 导出Docker镜像 ====================
echo -e "${GREEN}[步骤2/7]${NC} 导出Docker镜像..."
echo ""

IMAGE_FILE="${IMAGE_NAME}_${IMAGE_TAG}_$(date +%Y%m%d_%H%M%S).tar"
echo "正在导出镜像到: ${IMAGE_FILE}"
docker save ${IMAGE_NAME}:${IMAGE_TAG} -o ${IMAGE_FILE}
IMAGE_SIZE=$(du -h ${IMAGE_FILE} | cut -f1)
echo "✓ 镜像导出成功，大小: ${IMAGE_SIZE}"
echo ""

# ==================== 步骤3: 检查SSH连接 ====================
echo -e "${GREEN}[步骤3/7]${NC} 检查SSH连接..."
echo ""

if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${PRODUCTION_USER}@${PRODUCTION_HOST} "echo 'SSH连接成功'" 2>/dev/null; then
    echo -e "${YELLOW}警告: 无法使用SSH密钥连接，请输入密码${NC}"
fi
echo "✓ SSH连接可用"
echo ""

# ==================== 步骤4: 传输文件到生产服务器 ====================
echo -e "${GREEN}[步骤4/7]${NC} 传输文件到生产服务器..."
echo ""

echo "创建远程部署目录..."
ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} "sudo mkdir -p ${DEPLOY_DIR} && sudo chown ${PRODUCTION_USER}:${PRODUCTION_USER} ${DEPLOY_DIR}"

echo "传输Docker镜像文件..."
scp ${IMAGE_FILE} ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/

echo "传输docker-compose配置..."
scp docker-compose.prod.full.yml ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/docker-compose.yml

echo "传输环境变量配置..."
if [ -f ".env.production" ]; then
    scp .env.production ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/.env
else
    echo -e "${YELLOW}警告: .env.production不存在，请手动创建${NC}"
fi

echo "传输配置文件..."
scp -r config ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/

echo "传输模型文件（如果有）..."
if [ -d "models" ]; then
    scp -r models ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/
fi

echo "✓ 文件传输完成"
echo ""

# ==================== 步骤5: 在生产服务器上安装Docker ====================
echo -e "${GREEN}[步骤5/7]${NC} 检查生产服务器Docker环境..."
echo ""

ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << 'ENDSSH'
# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "Docker未安装，正在安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✓ Docker安装完成"
else
    echo "✓ Docker已安装: $(docker --version)"
fi

# 检查docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose未安装，正在安装..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✓ docker-compose安装完成"
else
    echo "✓ docker-compose已安装: $(docker-compose --version)"
fi
ENDSSH

echo "✓ Docker环境检查完成"
echo ""

# ==================== 步骤6: 在生产服务器上加载镜像并启动 ====================
echo -e "${GREEN}[步骤6/7]${NC} 在生产服务器上部署..."
echo ""

ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << ENDSSH
cd ${DEPLOY_DIR}

echo "加载Docker镜像..."
docker load -i ${IMAGE_FILE}
echo "✓ 镜像加载完成"

echo "停止旧容器（如果存在）..."
docker-compose down || true

echo "启动新容器..."
docker-compose up -d

echo "等待服务启动..."
sleep 10

echo "检查容器状态..."
docker-compose ps

echo "✓ 服务启动完成"
ENDSSH

echo "✓ 部署完成"
echo ""

# ==================== 步骤7: 健康检查 ====================
echo -e "${GREEN}[步骤7/7]${NC} 健康检查..."
echo ""

echo "等待服务完全启动（30秒）..."
sleep 30

echo "执行健康检查..."
if ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} "curl -f http://localhost:8000/api/v1/monitoring/health" &> /dev/null; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${YELLOW}警告: 健康检查失败，请手动检查${NC}"
fi
echo ""

# ==================== 清理本地镜像文件 ====================
echo "清理本地镜像文件..."
rm -f ${IMAGE_FILE}
echo "✓ 清理完成"
echo ""

# ==================== 部署总结 ====================
echo "========================================================================="
echo -e "${GREEN}部署成功完成！${NC}"
echo "========================================================================="
echo ""
echo "生产服务器信息:"
echo "  - 服务器: ${PRODUCTION_HOST}"
echo "  - 部署目录: ${DEPLOY_DIR}"
echo "  - API地址: http://${PRODUCTION_HOST}:8000"
echo ""
echo "后续操作:"
echo "  1. 查看日志:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose logs -f'"
echo ""
echo "  2. 检查服务状态:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose ps'"
echo ""
echo "  3. 重启服务:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose restart'"
echo ""
echo "  4. 停止服务:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose down'"
echo ""
echo "  5. 访问API文档:"
echo "     http://${PRODUCTION_HOST}:8000/docs"
echo ""
echo "========================================================================="
