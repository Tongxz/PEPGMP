#!/bin/bash

# 数据库恢复脚本
# 用途: 从备份文件恢复PostgreSQL数据库
# 使用: bash scripts/restore_db.sh <备份文件路径>

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BACKUP_FILE="$1"
DB_CONTAINER="pepgmp-postgres-prod"
DB_USER="pepgmp_prod"
DB_NAME="pepgmp_production"

echo "========================================================================="
echo "                     数据库恢复"
echo "========================================================================="

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}错误: 请提供备份文件路径${NC}"
    echo "使用: bash scripts/restore_db.sh <备份文件路径>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}错误: 文件不存在: $BACKUP_FILE${NC}"
    exit 1
fi

echo "备份文件: $BACKUP_FILE"
echo "目标数据库: $DB_NAME (容器: $DB_CONTAINER)"
echo ""
echo -e "${YELLOW}⚠️  警告: 此操作将覆盖现有数据库！${NC}"
read -p "确认恢复？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "正在恢复数据库..."

# 检查文件类型（是否压缩）
if [[ "$BACKUP_FILE" == *.gz ]]; then
    # 解压并恢复
    cat "$BACKUP_FILE" | gzip -d | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"
else
    # 直接恢复
    cat "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 数据库恢复成功${NC}"
else
    echo ""
    echo -e "${RED}❌ 数据库恢复失败${NC}"
    exit 1
fi

echo "========================================================================="


