#!/bin/bash

# 检查数据库初始化状态脚本
# 用途: 验证PostgreSQL容器是否正确初始化了用户和数据库
# 使用: bash scripts/check_database_init.sh [容器名] [用户名] [数据库名]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置（可通过参数覆盖）
CONTAINER="${1:-pepgmp-postgres-prod}"
DB_USER="${2:-pepgmp_prod}"
DB_NAME="${3:-pepgmp_production}"

echo "========================================================================="
echo "              数据库初始化状态检查"
echo "========================================================================="
echo "容器: $CONTAINER"
echo "用户: $DB_USER"
echo "数据库: $DB_NAME"
echo ""

# 1. 检查容器是否运行
echo -e "${BLUE}📦 步骤1: 检查容器状态${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo -e "${RED}❌ 错误: 容器 $CONTAINER 未运行${NC}"
    echo ""
    echo "解决方案:"
    echo "  docker compose up -d database"
    exit 1
fi

echo -e "${GREEN}✅ 容器运行中${NC}"
echo ""

# 2. 检查PostgreSQL服务
echo -e "${BLUE}📦 步骤2: 检查PostgreSQL服务${NC}"
if ! docker exec "$CONTAINER" pg_isready > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL服务未就绪${NC}"
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL服务正常${NC}"
echo ""

# 3. 检查用户是否存在
echo -e "${BLUE}📦 步骤3: 检查数据库用户${NC}"
if docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 用户 $DB_USER 存在${NC}"
    USER_EXISTS=true
else
    echo -e "${RED}❌ 用户 $DB_USER 不存在${NC}"
    USER_EXISTS=false
fi
echo ""

# 4. 检查数据库是否存在
echo -e "${BLUE}📦 步骤4: 检查数据库${NC}"
if docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 数据库 $DB_NAME 存在且可访问${NC}"
    DB_EXISTS=true
else
    echo -e "${RED}❌ 数据库 $DB_NAME 不存在或不可访问${NC}"
    DB_EXISTS=false
fi
echo ""

# 5. 检查表结构
if [ "$DB_EXISTS" = true ]; then
    echo -e "${BLUE}📦 步骤5: 检查表结构${NC}"
    TABLE_COUNT=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" != "" ]; then
        echo -e "${GREEN}✅ 数据库包含 $TABLE_COUNT 个表${NC}"
    else
        echo -e "${YELLOW}⚠️  数据库表数量未知或为0${NC}"
    fi
    echo ""
fi

# 6. 总结
echo "========================================================================="
if [ "$USER_EXISTS" = true ] && [ "$DB_EXISTS" = true ]; then
    echo -e "${GREEN}                     检查通过${NC}"
    echo "========================================================================="
    echo ""
    echo "✅ 数据库初始化正常"
    echo "   用户: $DB_USER"
    echo "   数据库: $DB_NAME"
    if [ -n "$TABLE_COUNT" ]; then
        echo "   表数量: $TABLE_COUNT"
    fi
    echo ""
    exit 0
else
    echo -e "${RED}                     检查失败${NC}"
    echo "========================================================================="
    echo ""
    echo "❌ 数据库初始化失败"
    echo ""
    echo "可能原因:"
    if [ "$USER_EXISTS" = false ]; then
        echo "  - 用户 $DB_USER 未创建"
    fi
    if [ "$DB_EXISTS" = false ]; then
        echo "  - 数据库 $DB_NAME 未创建"
    fi
    echo ""
    echo "解决方案:"
    echo "  1. 检查数据卷是否为空（首次部署应使用新数据卷）"
    echo "  2. 清理数据卷并重新初始化:"
    echo "     docker compose down"
    echo "     docker volume rm postgres_prod_data"
    echo "     docker compose up -d database"
    echo "     # 等待60-70秒确保初始化完成"
    echo "  3. 或使用修复脚本:"
    echo "     bash scripts/fix_database_user.sh"
    echo ""
    exit 1
fi

