#!/bin/bash

# 重新构建开发环境脚本
# 用途: 停止旧容器，重新构建新容器，恢复数据
# 使用: bash scripts/rebuild_dev_environment.sh [备份目录] [时间戳]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
BACKUP_DIR="${1:-./backups/dev}"
TIMESTAMP="${2}"

echo "========================================================================="
echo "             重新构建开发环境"
echo "========================================================================="
echo ""

# 1. 停止旧容器
echo -e "${BLUE}📦 步骤1: 停止旧容器${NC}"
echo "停止所有开发环境容器..."
docker compose down 2>/dev/null || true

# 停止可能存在的旧容器
OLD_CONTAINERS=("pyt-postgres-dev" "pyt-redis-dev" "pyt-api-dev" "pyt-frontend-dev")
for container in "${OLD_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "停止并删除旧容器: $container"
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
    fi
done

echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# 2. 清理旧网络（可选）
echo -e "${BLUE}📦 步骤2: 清理旧网络${NC}"
OLD_NETWORKS=("pyt-dev-network")
for network in "${OLD_NETWORKS[@]}"; do
    if docker network ls --format '{{.Name}}' | grep -q "^${network}$"; then
        echo "删除旧网络: $network"
        docker network rm "$network" 2>/dev/null || true
    fi
done

echo -e "${GREEN}✅ 旧网络已清理${NC}"
echo ""

# 3. 重新构建镜像
echo -e "${BLUE}📦 步骤3: 重新构建Docker镜像${NC}"
echo "构建API镜像..."
docker compose build api

echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# 4. 启动新容器
echo -e "${BLUE}📦 步骤4: 启动新容器${NC}"
echo "启动数据库和Redis..."
docker compose up -d database redis

# 等待数据库就绪
echo "等待数据库就绪..."
sleep 5
for i in {1..30}; do
    if docker exec pepgmp-postgres-dev pg_isready -U pepgmp_dev -d pepgmp_development > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 数据库已就绪${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ 数据库启动超时${NC}"
        exit 1
    fi
    sleep 1
done

echo -e "${GREEN}✅ 容器启动完成${NC}"
echo ""

# 5. 恢复数据（如果提供了时间戳）
if [ -n "$TIMESTAMP" ]; then
    echo -e "${BLUE}📦 步骤5: 恢复数据${NC}"
    if [ -f "scripts/restore_dev_data.sh" ]; then
        bash scripts/restore_dev_data.sh "$BACKUP_DIR" "$TIMESTAMP"
    else
        echo -e "${YELLOW}⚠️  恢复脚本不存在，跳过数据恢复${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未提供时间戳，跳过数据恢复${NC}"
    echo "如需恢复数据，请运行: bash scripts/restore_dev_data.sh $BACKUP_DIR [时间戳]"
fi

echo ""

# 6. 启动所有服务
echo -e "${BLUE}📦 步骤6: 启动所有服务${NC}"
docker compose up -d

echo ""
echo "========================================================================="
echo -e "${GREEN}                     重建完成${NC}"
echo "========================================================================="
echo ""
echo "服务状态:"
docker compose ps
echo ""
echo "下一步:"
echo "  1. 查看日志: docker compose logs -f"
echo "  2. 检查健康状态: docker compose ps"
echo "  3. 访问前端: http://localhost:5173"
echo "  4. 访问API: http://localhost:8000"

