#!/bin/bash

# 开发环境数据恢复脚本
# 用途: 从备份恢复开发环境的PostgreSQL和Redis数据
# 使用: bash scripts/restore_dev_data.sh [备份目录] [时间戳]

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
DB_CONTAINER="pepgmp-postgres-dev"
DB_USER="pepgmp_dev"
DB_NAME="pepgmp_development"
REDIS_CONTAINER="pepgmp-redis-dev"

# 支持从旧数据库恢复
DB_NAME_OLD="pyt_development"

echo "========================================================================="
echo "                 开发环境数据恢复"
echo "========================================================================="

# 检查参数
if [ -z "$TIMESTAMP" ]; then
    echo -e "${YELLOW}⚠️  未指定时间戳，查找最新备份...${NC}"
    # 先尝试新数据库名，再尝试旧数据库名
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR/db/backup_${DB_NAME}_"*.sql.gz "$BACKUP_DIR/db/backup_${DB_NAME_OLD}_"*.sql.gz 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        echo -e "${RED}❌ 错误: 未找到备份文件${NC}"
        echo "用法: bash scripts/restore_dev_data.sh [备份目录] [时间戳]"
        exit 1
    fi
    TIMESTAMP=$(basename "$LATEST_BACKUP" | sed -E "s/backup_(pyt|pepgmp)_development_(.*)\.sql\.gz/\2/")
    echo -e "${GREEN}找到最新备份: $TIMESTAMP${NC}"
fi

echo "备份目录: $BACKUP_DIR"
echo "时间戳: $TIMESTAMP"
echo ""

# 检查容器是否运行
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo -e "${RED}❌ 错误: 数据库容器 $DB_CONTAINER 未运行${NC}"
    echo "请先启动容器: docker compose up -d database"
    exit 1
fi

# 1. 恢复PostgreSQL数据库
echo -e "${BLUE}📦 步骤1: 恢复PostgreSQL数据库${NC}"
# 先尝试新数据库名，再尝试旧数据库名
BACKUP_FILE_DB="$BACKUP_DIR/db/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
if [ ! -f "$BACKUP_FILE_DB" ]; then
    BACKUP_FILE_DB="$BACKUP_DIR/db/backup_${DB_NAME_OLD}_${TIMESTAMP}.sql.gz"
fi

if [ ! -f "$BACKUP_FILE_DB" ]; then
    echo -e "${RED}❌ 错误: 备份文件不存在${NC}"
    echo "尝试查找: $BACKUP_DIR/db/backup_*_${TIMESTAMP}.sql.gz"
    exit 1
fi

echo "使用备份文件: $BACKUP_FILE_DB"

echo "正在恢复数据库..."
echo -e "${YELLOW}⚠️  警告: 这将覆盖现有数据库数据！${NC}"

# 非交互式模式：如果设置了SKIP_CONFIRM环境变量，跳过确认
if [ "${SKIP_CONFIRM:-}" != "yes" ]; then
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 1
    fi
else
    echo "非交互式模式：自动确认"
fi

# 删除现有数据库并重新创建
echo "删除现有数据库..."
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" || true
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# 恢复数据
echo "恢复数据..."
if gunzip -c "$BACKUP_FILE_DB" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"; then
    echo -e "${GREEN}✅ 数据库恢复成功${NC}"
else
    echo -e "${RED}❌ 数据库恢复失败${NC}"
    exit 1
fi

echo ""

# 2. 恢复Redis数据（可选）
echo -e "${BLUE}📦 步骤2: 恢复Redis数据（可选）${NC}"
BACKUP_FILE_REDIS="$BACKUP_DIR/redis/backup_redis_${TIMESTAMP}.rdb"

if [ -f "$BACKUP_FILE_REDIS" ]; then
    if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
        echo "正在恢复Redis数据..."
        # 停止Redis写入
        docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a pepgmp_dev_redis CONFIG SET appendonly no || true
        # 复制RDB文件
        docker cp "$BACKUP_FILE_REDIS" "$REDIS_CONTAINER:/data/dump.rdb"
        # 重启Redis容器以加载RDB
        docker restart "$REDIS_CONTAINER"
        echo -e "${GREEN}✅ Redis数据恢复成功（需要重启容器）${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis容器未运行，跳过恢复${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Redis备份文件不存在，跳过恢复${NC}"
fi

echo ""

echo "========================================================================="
echo -e "${GREEN}                     恢复完成${NC}"
echo "========================================================================="
echo ""
echo "数据已从备份恢复: $TIMESTAMP"
echo ""
echo "验证步骤:"
echo "  1. 检查数据库: docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c '\\dt'"
echo "  2. 检查Redis: docker exec $REDIS_CONTAINER redis-cli -a pepgmp_dev_redis PING"
