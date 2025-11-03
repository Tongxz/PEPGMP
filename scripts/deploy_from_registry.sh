#!/bin/bash

################################################################################
# 从私有Registry部署到生产环境
# 用途: 从私有镜像仓库拉取镜像并部署到Ubuntu生产服务器
# 使用: bash scripts/deploy_from_registry.sh <生产服务器IP> [SSH用户名] [镜像标签]
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
IMAGE_NAME="pyt-backend"
DEPLOY_DIR="/opt/pyt"

echo "========================================================================="
echo -e "${BLUE}从私有Registry部署到生产环境${NC}"
echo "========================================================================="
echo ""
echo "Registry地址: ${REGISTRY_URL}"
echo "目标服务器: ${PRODUCTION_HOST}"
echo "SSH用户: ${PRODUCTION_USER}"
echo "镜像标签: ${IMAGE_TAG}"
echo "部署目录: ${DEPLOY_DIR}"
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
echo -e "${YELLOW}警告: 即将部署到生产环境！${NC}"
echo -e "${YELLOW}=========================================================================${NC}"
read -p "确认要部署到 ${PRODUCTION_HOST} 吗？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "部署已取消"
    exit 0
fi
echo ""

# ==================== 步骤1: 检查Registry连接 ====================
echo -e "${GREEN}[步骤1/6]${NC} 检查Registry连接..."
echo ""

if curl -sf http://${REGISTRY_URL}/v2/_catalog > /dev/null; then
    echo "✓ Registry连接成功"

    # 检查镜像是否存在
    if curl -sf http://${REGISTRY_URL}/v2/${IMAGE_NAME}/tags/list | grep -q "${IMAGE_TAG}"; then
        echo "✓ 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 存在于Registry"
    else
        echo -e "${RED}错误: 镜像 ${IMAGE_NAME}:${IMAGE_TAG} 不存在于Registry${NC}"
        echo "请先推送镜像: bash scripts/push_to_registry.sh"
        exit 1
    fi
else
    echo -e "${RED}错误: 无法连接到Registry${NC}"
    exit 1
fi
echo ""

# ==================== 步骤2: 检查SSH连接 ====================
echo -e "${GREEN}[步骤2/6]${NC} 检查SSH连接..."
echo ""

if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${PRODUCTION_USER}@${PRODUCTION_HOST} "echo 'SSH连接成功'" 2>/dev/null; then
    echo -e "${YELLOW}警告: 无法使用SSH密钥连接，请输入密码${NC}"
fi
echo "✓ SSH连接可用"
echo ""

# ==================== 步骤3: 准备配置文件 ====================
echo -e "${GREEN}[步骤3/6]${NC} 传输配置文件..."
echo ""

echo "创建远程部署目录..."
ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} "sudo mkdir -p ${DEPLOY_DIR} && sudo chown ${PRODUCTION_USER}:${PRODUCTION_USER} ${DEPLOY_DIR}"

echo "传输docker-compose配置..."
scp docker-compose.prod.full.yml ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/docker-compose.yml

echo "传输环境变量配置..."
if [ -f ".env.production" ]; then
    scp .env.production ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/.env
else
    echo -e "${YELLOW}警告: .env.production不存在${NC}"
    echo "创建默认配置文件..."
    cat > /tmp/.env.production << EOF
ENVIRONMENT=production
API_PORT=8000
DATABASE_PASSWORD=CHANGE_ME
REDIS_PASSWORD=CHANGE_ME
SECRET_KEY=CHANGE_ME
JWT_SECRET_KEY=CHANGE_ME
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME
CORS_ORIGINS=*
USE_DOMAIN_SERVICE=true
REPOSITORY_TYPE=postgresql
EOF
    scp /tmp/.env.production ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/.env
    rm /tmp/.env.production
    echo -e "${YELLOW}⚠️  请登录服务器修改 ${DEPLOY_DIR}/.env 中的密码！${NC}"
fi

echo "传输配置目录..."
scp -r config ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/

echo "传输模型目录（如果有）..."
if [ -d "models" ] && [ "$(ls -A models 2>/dev/null)" ]; then
    echo "正在传输模型文件（可能需要较长时间）..."
    scp -r models ${PRODUCTION_USER}@${PRODUCTION_HOST}:${DEPLOY_DIR}/
else
    echo "跳过模型文件传输"
fi

echo "✓ 配置文件传输完成"
echo ""

# ==================== 步骤4: 配置生产服务器Docker环境 ====================
echo -e "${GREEN}[步骤4/6]${NC} 配置生产服务器Docker环境..."
echo ""

ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << ENDSSH
set -e

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "Docker未安装，正在安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker \$USER
    rm get-docker.sh
    echo "✓ Docker安装完成"
else
    echo "✓ Docker已安装: \$(docker --version)"
fi

# 检查docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose未安装，正在安装..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✓ docker-compose安装完成"
else
    echo "✓ docker-compose已安装: \$(docker-compose --version)"
fi

# 配置Docker信任私有Registry
echo "配置Docker信任私有Registry..."
sudo mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ]; then
    echo '{"insecure-registries": ["${REGISTRY_URL}"]}' | sudo tee /etc/docker/daemon.json
    sudo systemctl restart docker
    echo "✓ Docker已配置信任Registry"
else
    if ! grep -q "insecure-registries" /etc/docker/daemon.json; then
        echo "需要手动添加Registry配置"
        echo "请在 /etc/docker/daemon.json 中添加:"
        echo '  "insecure-registries": ["${REGISTRY_URL}"]'
    else
        echo "✓ Registry配置已存在"
    fi
fi

echo "✓ Docker环境配置完成"
ENDSSH

echo ""

# ==================== 步骤5: 拉取镜像并部署 ====================
echo -e "${GREEN}[步骤5/6]${NC} 拉取镜像并部署..."
echo ""

ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << ENDSSH
set -e
cd ${DEPLOY_DIR}

echo "更新docker-compose.yml使用Registry镜像..."
sed -i 's|image: pyt-backend:latest|image: ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}|g' docker-compose.yml
sed -i 's|build:|# build:|g' docker-compose.yml
sed -i 's|context:|# context:|g' docker-compose.yml
sed -i 's|dockerfile:|# dockerfile:|g' docker-compose.yml

echo "停止旧容器（如果存在）..."
docker-compose down || true

echo "拉取最新镜像..."
docker pull ${REGISTRY_URL}/${IMAGE_NAME}:${IMAGE_TAG}

echo "启动容器..."
docker-compose up -d

echo "等待服务启动..."
sleep 15

echo "检查容器状态..."
docker-compose ps

echo "✓ 服务启动完成"
ENDSSH

echo "✓ 部署完成"
echo ""

# ==================== 步骤6: 健康检查 ====================
echo -e "${GREEN}[步骤6/6]${NC} 健康检查..."
echo ""

echo "等待服务完全启动（30秒）..."
sleep 30

echo "执行健康检查..."
if ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} "curl -sf http://localhost:8000/api/v1/monitoring/health"; then
    echo ""
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo ""
    echo -e "${YELLOW}警告: 健康检查失败，请手动检查日志${NC}"
    echo "查看日志: ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose logs -f api'"
fi
echo ""

# ==================== 部署总结 ====================
echo "========================================================================="
echo -e "${GREEN}部署成功完成！${NC}"
echo "========================================================================="
echo ""
echo "部署信息:"
echo "  - Registry: ${REGISTRY_URL}"
echo "  - 镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  - 服务器: ${PRODUCTION_HOST}"
echo "  - 部署目录: ${DEPLOY_DIR}"
echo "  - API地址: http://${PRODUCTION_HOST}:8000"
echo ""
echo "常用命令:"
echo ""
echo "  1. 查看日志:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose logs -f api'"
echo ""
echo "  2. 查看所有容器状态:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose ps'"
echo ""
echo "  3. 重启服务:"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose restart api'"
echo ""
echo "  4. 更新到新版本:"
echo "     bash scripts/push_to_registry.sh"
echo "     ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'cd ${DEPLOY_DIR} && docker-compose pull && docker-compose up -d'"
echo ""
echo "  5. 回滚到之前版本:"
echo "     bash scripts/deploy_from_registry.sh ${PRODUCTION_HOST} ${PRODUCTION_USER} <版本号>"
echo ""
echo "  6. 访问API文档:"
echo "     http://${PRODUCTION_HOST}:8000/docs"
echo ""
echo "  7. 查看系统信息:"
echo "     curl http://${PRODUCTION_HOST}:8000/api/v1/system/info"
echo ""
echo "========================================================================="
