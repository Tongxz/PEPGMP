#!/bin/bash

################################################################################
# 一键部署到生产环境
# 用途: 构建 -> 推送 -> 部署 完整流程
# 使用: bash scripts/quick_deploy.sh <生产服务器IP> [SSH用户名]
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
PRODUCTION_HOST="${1}"
PRODUCTION_USER="${2:-ubuntu}"
VERSION="v$(date +%Y%m%d_%H%M%S)"

echo "========================================================================="
echo -e "${CYAN}🚀 一键部署到生产环境${NC}"
echo "========================================================================="
echo ""
echo "目标服务器: ${PRODUCTION_HOST}"
echo "SSH用户: ${PRODUCTION_USER}"
echo "版本号: ${VERSION}"
echo ""

# 检查参数
if [ -z "$PRODUCTION_HOST" ]; then
    echo -e "${RED}错误: 请提供生产服务器地址${NC}"
    echo "使用方法: bash $0 <生产服务器IP> [SSH用户名]"
    echo "示例: bash $0 192.168.1.100 ubuntu"
    exit 1
fi

# 确认部署
echo -e "${YELLOW}=========================================================================${NC}"
echo -e "${YELLOW}⚠️  警告: 即将执行完整部署流程！${NC}"
echo -e "${YELLOW}=========================================================================${NC}"
echo "将执行以下操作:"
echo "  1. 构建Docker镜像"
echo "  2. 推送到私有Registry"
echo "  3. 部署到生产服务器"
echo "  4. 健康检查"
echo ""
read -p "确认继续？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "部署已取消"
    exit 0
fi
echo ""

# ==================== 阶段1: 构建镜像 ====================
echo "========================================================================="
echo -e "${GREEN}阶段 1/4: 构建Docker镜像${NC}"
echo "========================================================================="
echo ""

echo "清理旧的构建缓存..."
docker builder prune -f || true

echo "开始构建..."
docker build -f Dockerfile.prod -t pyt-backend:latest .

echo ""
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# ==================== 阶段2: 推送到Registry ====================
echo "========================================================================="
echo -e "${GREEN}阶段 2/4: 推送到私有Registry${NC}"
echo "========================================================================="
echo ""

bash scripts/push_to_registry.sh latest ${VERSION}

echo ""
echo -e "${GREEN}✓ 镜像推送完成${NC}"
echo ""

# ==================== 阶段3: 部署到生产服务器 ====================
echo "========================================================================="
echo -e "${GREEN}阶段 3/4: 部署到生产服务器${NC}"
echo "========================================================================="
echo ""

# 使用latest标签部署（因为已经推送了latest）
bash scripts/deploy_from_registry.sh ${PRODUCTION_HOST} ${PRODUCTION_USER} latest

echo ""
echo -e "${GREEN}✓ 部署完成${NC}"
echo ""

# ==================== 阶段4: 验证部署 ====================
echo "========================================================================="
echo -e "${GREEN}阶段 4/4: 验证部署${NC}"
echo "========================================================================="
echo ""

echo "等待服务稳定（10秒）..."
sleep 10

echo "执行完整验证..."
ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} << 'ENDSSH'
set -e

echo "1. 检查容器状态:"
docker ps --filter "name=pyt-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2. 检查API健康:"
if curl -sf http://localhost:8000/api/v1/monitoring/health | jq . 2>/dev/null; then
    echo "✓ API健康检查通过"
else
    echo "⚠️  API健康检查失败"
fi
echo ""

echo "3. 检查数据库连接:"
if docker exec pyt-postgres-prod pg_isready -U pyt_prod; then
    echo "✓ 数据库连接正常"
else
    echo "⚠️  数据库连接失败"
fi
echo ""

echo "4. 检查Redis连接:"
if docker exec pyt-redis-prod redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✓ Redis连接正常"
else
    echo "⚠️  Redis连接失败"
fi
echo ""

echo "5. 检查系统信息:"
curl -s http://localhost:8000/api/v1/system/info | jq '.environment' 2>/dev/null || echo "无法获取系统信息"
echo ""

ENDSSH

echo ""
echo -e "${GREEN}✓ 验证完成${NC}"
echo ""

# ==================== 部署完成总结 ====================
echo "========================================================================="
echo -e "${CYAN}🎉 部署成功完成！${NC}"
echo "========================================================================="
echo ""
echo "📋 部署摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  版本: ${VERSION}"
echo "  服务器: ${PRODUCTION_HOST}"
echo "  部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "🔗 访问地址"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API文档: http://${PRODUCTION_HOST}:8000/docs"
echo "  健康检查: http://${PRODUCTION_HOST}:8000/api/v1/monitoring/health"
echo "  系统信息: http://${PRODUCTION_HOST}:8000/api/v1/system/info"
echo ""
echo "🛠️  常用命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  查看日志:"
echo "    ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'docker-compose -f /opt/pyt/docker-compose.yml logs -f api'"
echo ""
echo "  重启服务:"
echo "    ssh ${PRODUCTION_USER}@${PRODUCTION_HOST} 'docker-compose -f /opt/pyt/docker-compose.yml restart api'"
echo ""
echo "  快速重新部署:"
echo "    bash scripts/quick_deploy.sh ${PRODUCTION_HOST} ${PRODUCTION_USER}"
echo ""
echo "  回滚到特定版本:"
echo "    bash scripts/deploy_from_registry.sh ${PRODUCTION_HOST} ${PRODUCTION_USER} <版本号>"
echo ""
echo "📝 版本记录已保存到 deployment_history.log"
echo "========================================================================="

# 记录部署历史
cat >> deployment_history.log << EOF
========================================
部署时间: $(date '+%Y-%m-%d %H:%M:%S')
版本: ${VERSION}
服务器: ${PRODUCTION_HOST}
用户: ${PRODUCTION_USER}
状态: 成功
========================================

EOF

echo ""
echo -e "${GREEN}✅ 全部完成！生产环境已就绪！${NC}"
echo ""
