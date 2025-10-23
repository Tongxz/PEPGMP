#!/bin/bash
# 生产环境启动脚本（无GPU版本）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}生产环境启动脚本（无GPU版本）${NC}"
echo -e "${GREEN}========================================${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo -e "${BLUE}项目目录: ${PROJECT_DIR}${NC}"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    exit 1
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose未安装${NC}"
    exit 1
fi

# 检查必需目录
echo -e "\n${GREEN}[0/6] 检查必需目录${NC}"
REQUIRED_DIRS=(
    "config"
    "logs"
    "output"
    "data"
    "models"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "${PROJECT_DIR}/${dir}" ]; then
        echo -e "${YELLOW}创建目录: ${PROJECT_DIR}/${dir}${NC}"
        mkdir -p "${PROJECT_DIR}/${dir}"
    fi
    echo -e "${GREEN}✅ 目录存在: ${dir}${NC}"
done

# 检查必需文件
echo -e "\n${GREEN}[0.5/6] 检查必需文件${NC}"
REQUIRED_FILES=(
    "docker-compose.prod.yml"
    "config/unified_params.yaml"
    "config/regions.json"
    "config/cameras.yaml"
    "scripts/init_db.sql"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "${PROJECT_DIR}/${file}" ]; then
        echo -e "${RED}❌ 文件不存在: ${file}${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 文件存在: ${file}${NC}"
done

# 检查镜像是否存在
echo -e "\n${GREEN}[1/5] 检查镜像${NC}"
if ! docker images | grep -q "pyt-api.*prod"; then
    echo -e "${RED}❌ API镜像不存在${NC}"
    echo -e "${YELLOW}请先导入镜像: docker load -i pyt-api-prod.tar${NC}"
    exit 1
fi

if ! docker images | grep -q "pyt-frontend.*prod"; then
    echo -e "${RED}❌ 前端镜像不存在${NC}"
    echo -e "${YELLOW}请先导入镜像: docker load -i pyt-frontend-prod.tar${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 镜像检查通过${NC}"

# 检查GPU（可选）
echo -e "\n${GREEN}[2/5] 检查GPU（可选）${NC}"
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        nvidia-smi
        echo -e "${GREEN}✅ GPU可用${NC}"
    else
        echo -e "${YELLOW}⚠️  GPU驱动未安装或未正确加载，将使用CPU运行${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  NVIDIA驱动未安装，将使用CPU运行${NC}"
fi

# 停止旧服务
echo -e "\n${GREEN}[3/5] 停止旧服务${NC}"
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
echo -e "${GREEN}✅ 旧服务已停止${NC}"

# 启动服务
echo -e "\n${GREEN}[4/5] 启动服务${NC}"
docker-compose -f docker-compose.prod.yml up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 服务启动成功${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    exit 1
fi

# 等待服务就绪
echo -e "\n${GREEN}[5/5] 等待服务就绪${NC}"
echo -e "${YELLOW}等待30秒...${NC}"
sleep 30

# 检查服务状态
echo -e "\n${GREEN}检查服务状态...${NC}"
docker-compose -f docker-compose.prod.yml ps

# 显示日志
echo -e "\n${GREEN}显示API日志（最后50行）...${NC}"
docker-compose -f docker-compose.prod.yml logs --tail=50 api

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}API地址: http://localhost:8000${NC}"
echo -e "${GREEN}前端地址: http://localhost:8080${NC}"
echo -e "${GREEN}健康检查: http://localhost:8000/health${NC}"
echo -e "${GREEN}========================================${NC}"

# 提示
echo -e "\n${YELLOW}提示:${NC}"
echo -e "${YELLOW}1. 当前使用CPU模式运行${NC}"
echo -e "${YELLOW}2. 如需启用GPU，请安装NVIDIA驱动${NC}"
echo -e "${YELLOW}3. 查看日志: docker-compose -f docker-compose.prod.yml logs -f api${NC}"
echo -e "${YELLOW}4. 停止服务: docker-compose -f docker-compose.prod.yml down${NC}"
echo -e "${YELLOW}5. 重启服务: docker-compose -f docker-compose.prod.yml restart${NC}"
