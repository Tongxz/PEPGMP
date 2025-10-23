#!/bin/bash
# Docker文件重组脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Docker文件重组脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 步骤1: 备份现有文件
echo -e "\n${BLUE}[1/7] 备份现有文件${NC}"
mkdir -p docker_backup

if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker_backup/
    echo -e "${GREEN}✅ 备份: docker-compose.yml${NC}"
fi

if [ -f "docker-compose.dev-db.yml" ]; then
    cp docker-compose.dev-db.yml docker_backup/
    echo -e "${GREEN}✅ 备份: docker-compose.dev-db.yml${NC}"
fi

if [ -f "docker-compose.prod.yml" ]; then
    cp docker-compose.prod.yml docker_backup/
    echo -e "${GREEN}✅ 备份: docker-compose.prod.yml${NC}"
fi

if [ -f "docker-compose.prod.full.yml" ]; then
    cp docker-compose.prod.full.yml docker_backup/
    echo -e "${GREEN}✅ 备份: docker-compose.prod.full.yml${NC}"
fi

if [ -f "Dockerfile" ]; then
    cp Dockerfile docker_backup/
    echo -e "${GREEN}✅ 备份: Dockerfile${NC}"
fi

if [ -f "Dockerfile.dev" ]; then
    cp Dockerfile.dev docker_backup/
    echo -e "${GREEN}✅ 备份: Dockerfile.dev${NC}"
fi

if [ -f "Dockerfile.api" ]; then
    cp Dockerfile.api docker_backup/
    echo -e "${GREEN}✅ 备份: Dockerfile.api${NC}"
fi

if [ -f "Dockerfile.supervisor" ]; then
    cp Dockerfile.supervisor docker_backup/
    echo -e "${GREEN}✅ 备份: Dockerfile.supervisor${NC}"
fi

if [ -d "backup" ]; then
    cp -r backup docker_backup/
    echo -e "${GREEN}✅ 备份: backup/${NC}"
fi

echo -e "${GREEN}✅ 备份完成${NC}"

# 步骤2: 删除冗余文件
echo -e "\n${BLUE}[2/7] 删除冗余文件${NC}"

if [ -f "docker-compose.prod.full.yml" ]; then
    rm docker-compose.prod.full.yml
    echo -e "${YELLOW}🗑️  删除: docker-compose.prod.full.yml${NC}"
fi

if [ -f "Dockerfile" ]; then
    rm Dockerfile
    echo -e "${YELLOW}🗑️  删除: Dockerfile${NC}"
fi

if [ -f "Dockerfile.api" ]; then
    rm Dockerfile.api
    echo -e "${YELLOW}🗑️  删除: Dockerfile.api${NC}"
fi

if [ -f "Dockerfile.supervisor" ]; then
    rm Dockerfile.supervisor
    echo -e "${YELLOW}🗑️  删除: Dockerfile.supervisor${NC}"
fi

if [ -d "backup" ]; then
    rm -rf backup
    echo -e "${YELLOW}🗑️  删除: backup/${NC}"
fi

echo -e "${GREEN}✅ 冗余文件删除完成${NC}"

# 步骤3: 替换docker-compose.yml
echo -e "\n${BLUE}[3/7] 更新 docker-compose.yml${NC}"
if [ -f "docker-compose.yml.new" ]; then
    mv docker-compose.yml.new docker-compose.yml
    echo -e "${GREEN}✅ 更新: docker-compose.yml${NC}"
else
    echo -e "${RED}❌ 文件不存在: docker-compose.yml.new${NC}"
    exit 1
fi

# 步骤4: 替换docker-compose.prod.yml
echo -e "\n${BLUE}[4/7] 更新 docker-compose.prod.yml${NC}"
if [ -f "docker-compose.prod.yml.new" ]; then
    mv docker-compose.prod.yml.new docker-compose.prod.yml
    echo -e "${GREEN}✅ 更新: docker-compose.prod.yml${NC}"
else
    echo -e "${RED}❌ 文件不存在: docker-compose.prod.yml.new${NC}"
    exit 1
fi

# 步骤5: 更新Dockerfile.dev
echo -e "\n${BLUE}[5/7] 更新 Dockerfile.dev${NC}"
if [ -f "Dockerfile.dev" ]; then
    echo -e "${GREEN}✅ Dockerfile.dev 已存在${NC}"
else
    echo -e "${YELLOW}⚠️  Dockerfile.dev 不存在，需要手动创建${NC}"
fi

# 步骤6: 更新Dockerfile.prod
echo -e "\n${BLUE}[6/7] 更新 Dockerfile.prod${NC}"
if [ -f "Dockerfile.prod" ]; then
    echo -e "${GREEN}✅ Dockerfile.prod 已存在${NC}"
else
    echo -e "${YELLOW}⚠️  Dockerfile.prod 不存在，需要手动创建${NC}"
fi

# 步骤7: 创建部署脚本
echo -e "\n${BLUE}[7/7] 创建部署脚本${NC}"

# 创建开发环境构建脚本
cat > scripts/deployment/build_dev.sh << 'EOF'
#!/bin/bash
# 开发环境构建脚本

set -e

echo "=========================================="
echo "开发环境构建"
echo "=========================================="

# 停止旧服务
docker-compose down

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
EOF

chmod +x scripts/deployment/build_dev.sh
echo -e "${GREEN}✅ 创建: scripts/deployment/build_dev.sh${NC}"

# 创建生产环境构建脚本
cat > scripts/deployment/build_prod.sh << 'EOF'
#!/bin/bash
# 生产环境构建脚本

set -e

REGISTRY="192.168.30.83:5433"
PROJECT_NAME="pyt"
API_IMAGE="${REGISTRY}/${PROJECT_NAME}-api:prod"
FRONTEND_IMAGE="${REGISTRY}/${PROJECT_NAME}-frontend:prod"

echo "=========================================="
echo "生产环境构建和部署"
echo "=========================================="

# 构建API镜像
echo "构建API镜像..."
docker build -f Dockerfile.prod -t ${API_IMAGE} .

# 构建前端镜像
echo "构建前端镜像..."
docker build -f Dockerfile.frontend -t ${FRONTEND_IMAGE} .

# 推送镜像
echo "推送镜像..."
docker push ${API_IMAGE}
docker push ${FRONTEND_IMAGE}

# 部署服务
echo "部署服务..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
EOF

chmod +x scripts/deployment/build_prod.sh
echo -e "${GREEN}✅ 创建: scripts/deployment/build_prod.sh${NC}"

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Docker文件重组完成！${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}文件变更总结:${NC}"
echo -e "${GREEN}✅ 保留:${NC}"
echo -e "  - docker-compose.yml (开发环境)"
echo -e "  - docker-compose.dev-db.yml (开发数据库)"
echo -e "  - docker-compose.prod.yml (生产环境)"
echo -e "  - Dockerfile.dev (开发环境)"
echo -e "  - Dockerfile.prod (生产环境)"
echo -e "  - Dockerfile.frontend (前端)"

echo -e "\n${YELLOW}🗑️  删除:${NC}"
echo -e "  - docker-compose.prod.full.yml"
echo -e "  - Dockerfile"
echo -e "  - Dockerfile.api"
echo -e "  - Dockerfile.supervisor"
echo -e "  - backup/"

echo -e "\n${YELLOW}📁 备份位置:${NC}"
echo -e "  - docker_backup/"

echo -e "\n${YELLOW}📝 新增脚本:${NC}"
echo -e "  - scripts/deployment/build_dev.sh"
echo -e "  - scripts/deployment/build_prod.sh"

echo -e "\n${BLUE}下一步:${NC}"
echo -e "  1. 测试开发环境: docker-compose up -d"
echo -e "  2. 测试生产环境: docker-compose -f docker-compose.prod.yml up -d"
echo -e "  3. 查看日志: docker-compose logs -f"
