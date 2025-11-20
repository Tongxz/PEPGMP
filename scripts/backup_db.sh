#!/bin/bash

# 数据库备份脚本
# 用途: 备份PostgreSQL数据库，支持保留策略
# 使用: bash scripts/backup_db.sh [备份目录] [保留天数]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
BACKUP_DIR="${1:-./backups/db}"
RETENTION_DAYS="${2:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER="pyt-postgres-prod"
DB_USER="pyt_prod"
DB_NAME="pyt_production"

echo "========================================================================="
echo "                     数据库备份"
echo "========================================================================="
echo "备份目录: $BACKUP_DIR"
echo "保留天数: $RETENTION_DAYS"
echo "容器名称: $DB_CONTAINER"
echo ""

# 检查Docker容器
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo -e "${RED}❌ 错误: 数据库容器 $DB_CONTAINER 未运行${NC}"
    exit 1
fi

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行备份
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
echo "正在备份数据库..."

# 使用pg_dump导出并gzip压缩
if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    echo -e "${GREEN}✅ 备份成功: $BACKUP_FILE${NC}"
    
    # 获取文件大小
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "文件大小: $FILE_SIZE"
else
    echo -e "${RED}❌ 备份失败${NC}"
    # 删除可能生成的空文件
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo ""

# 清理旧备份
echo "清理 $RETENTION_DAYS 天前的旧备份..."
CLEANUP_COUNT=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS | wc -l)

if [ "$CLEANUP_COUNT" -gt 0 ]; then
    find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo -e "${YELLOW}已删除 $CLEANUP_COUNT 个旧备份${NC}"
else
    echo "没有需要清理的旧备份"
fi

echo ""
echo "========================================================================="
echo "                     备份完成"
echo "========================================================================="


