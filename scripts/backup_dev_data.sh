#!/bin/bash

# 开发环境数据备份脚本
# 用途: 备份开发环境的PostgreSQL和Redis数据
# 使用: bash scripts/backup_dev_data.sh [备份目录]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
BACKUP_DIR="${1:-./backups/dev}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER_OLD="pyt-postgres-dev"
DB_CONTAINER_NEW="pepgmp-postgres-dev"
# 根据容器自动检测用户和数据库名
DB_USER_OLD="pyt_dev"
DB_NAME_OLD="pyt_development"
DB_USER_NEW="pepgmp_dev"
DB_NAME_NEW="pepgmp_development"
REDIS_CONTAINER_OLD="pyt-redis-dev"
REDIS_CONTAINER_NEW="pepgmp-redis-dev"

echo "========================================================================="
echo "                 开发环境数据备份"
echo "========================================================================="
echo "备份目录: $BACKUP_DIR"
echo "时间戳: $TIMESTAMP"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR/db"
mkdir -p "$BACKUP_DIR/redis"

# 1. 备份PostgreSQL数据库
echo -e "${BLUE}📦 步骤1: 备份PostgreSQL数据库${NC}"
DB_CONTAINER=""
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NEW}$"; then
    DB_CONTAINER="$DB_CONTAINER_NEW"
    echo "检测到新容器: $DB_CONTAINER"
elif docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER_OLD}$"; then
    DB_CONTAINER="$DB_CONTAINER_OLD"
    echo "检测到旧容器: $DB_CONTAINER"
else
    echo -e "${YELLOW}⚠️  警告: 未找到运行中的数据库容器${NC}"
    echo "跳过数据库备份"
    DB_CONTAINER=""
fi

if [ -n "$DB_CONTAINER" ]; then
    # 根据容器类型选择用户和数据库名
    if [ "$DB_CONTAINER" = "$DB_CONTAINER_OLD" ]; then
        DB_USER="$DB_USER_OLD"
        DB_NAME="$DB_NAME_OLD"
    else
        DB_USER="$DB_USER_NEW"
        DB_NAME="$DB_NAME_NEW"
    fi

    BACKUP_FILE_DB="$BACKUP_DIR/db/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
    echo "正在备份数据库 $DB_NAME (用户: $DB_USER)..."

    if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE_DB"; then
        FILE_SIZE=$(du -h "$BACKUP_FILE_DB" | cut -f1)
        echo -e "${GREEN}✅ 数据库备份成功: $BACKUP_FILE_DB (${FILE_SIZE})${NC}"
    else
        echo -e "${RED}❌ 数据库备份失败${NC}"
        rm -f "$BACKUP_FILE_DB"
        exit 1
    fi
fi

echo ""

# 2. 备份Redis数据
echo -e "${BLUE}📦 步骤2: 备份Redis数据${NC}"
REDIS_CONTAINER=""
if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NEW}$"; then
    REDIS_CONTAINER="$REDIS_CONTAINER_NEW"
    echo "检测到新容器: $REDIS_CONTAINER"
elif docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_OLD}$"; then
    REDIS_CONTAINER="$REDIS_CONTAINER_OLD"
    echo "检测到旧容器: $REDIS_CONTAINER"
else
    echo -e "${YELLOW}⚠️  警告: 未找到运行中的Redis容器${NC}"
    echo "跳过Redis备份"
    REDIS_CONTAINER=""
fi

if [ -n "$REDIS_CONTAINER" ]; then
    BACKUP_FILE_REDIS="$BACKUP_DIR/redis/backup_redis_${TIMESTAMP}.rdb"
    echo "正在备份Redis数据..."

    # Redis使用AOF持久化，备份RDB文件
    if docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a pepgmp_dev_redis SAVE > /dev/null 2>&1; then
        # 复制RDB文件
        if docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_FILE_REDIS" 2>/dev/null; then
            FILE_SIZE=$(du -h "$BACKUP_FILE_REDIS" | cut -f1)
            echo -e "${GREEN}✅ Redis备份成功: $BACKUP_FILE_REDIS (${FILE_SIZE})${NC}"
        else
            echo -e "${YELLOW}⚠️  Redis RDB文件不存在或无法复制（可能使用AOF模式）${NC}"
            # 尝试备份AOF文件
            if docker cp "$REDIS_CONTAINER:/data/appendonly.aof" "$BACKUP_FILE_REDIS.aof" 2>/dev/null; then
                FILE_SIZE=$(du -h "$BACKUP_FILE_REDIS.aof" | cut -f1)
                echo -e "${GREEN}✅ Redis AOF备份成功: $BACKUP_FILE_REDIS.aof (${FILE_SIZE})${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Redis备份跳过（可能没有数据）${NC}"
    fi
fi

echo ""

# 3. 备份Docker卷数据（如果存在）
echo -e "${BLUE}📦 步骤3: 备份Docker卷数据${NC}"
VOLUME_BACKUP_DIR="$BACKUP_DIR/volumes"
mkdir -p "$VOLUME_BACKUP_DIR"

# 检查并备份postgres_dev_data卷
if docker volume ls --format '{{.Name}}' | grep -q "postgres_dev_data"; then
    echo "备份 postgres_dev_data 卷..."
    VOLUME_BACKUP="$VOLUME_BACKUP_DIR/postgres_dev_data_${TIMESTAMP}.tar"
    docker run --rm -v postgres_dev_data:/data -v "$(pwd)/$VOLUME_BACKUP_DIR":/backup alpine tar czf /backup/postgres_dev_data_${TIMESTAMP}.tar.gz -C /data .
    if [ -f "$VOLUME_BACKUP_DIR/postgres_dev_data_${TIMESTAMP}.tar.gz" ]; then
        FILE_SIZE=$(du -h "$VOLUME_BACKUP_DIR/postgres_dev_data_${TIMESTAMP}.tar.gz" | cut -f1)
        echo -e "${GREEN}✅ PostgreSQL卷备份成功 (${FILE_SIZE})${NC}"
    fi
fi

# 检查并备份redis_dev_data卷
if docker volume ls --format '{{.Name}}' | grep -q "redis_dev_data"; then
    echo "备份 redis_dev_data 卷..."
    docker run --rm -v redis_dev_data:/data -v "$(pwd)/$VOLUME_BACKUP_DIR":/backup alpine tar czf /backup/redis_dev_data_${TIMESTAMP}.tar.gz -C /data .
    if [ -f "$VOLUME_BACKUP_DIR/redis_dev_data_${TIMESTAMP}.tar.gz" ]; then
        FILE_SIZE=$(du -h "$VOLUME_BACKUP_DIR/redis_dev_data_${TIMESTAMP}.tar.gz" | cut -f1)
        echo -e "${GREEN}✅ Redis卷备份成功 (${FILE_SIZE})${NC}"
    fi
fi

echo ""

# 4. 生成备份信息文件
INFO_FILE="$BACKUP_DIR/backup_info_${TIMESTAMP}.txt"
cat > "$INFO_FILE" << EOF
开发环境数据备份信息
====================
备份时间: $(date)
备份目录: $BACKUP_DIR
时间戳: $TIMESTAMP

数据库信息:
- 容器: ${DB_CONTAINER:-未运行}
- 用户: $DB_USER
- 数据库: $DB_NAME

Redis信息:
- 容器: ${REDIS_CONTAINER:-未运行}

备份文件:
- 数据库: ${BACKUP_FILE_DB:-未备份}
- Redis: ${BACKUP_FILE_REDIS:-未备份}

恢复说明:
1. 数据库恢复: bash scripts/restore_dev_data.sh $BACKUP_DIR $TIMESTAMP
2. 或使用: docker exec -i pepgmp-postgres-dev psql -U pepgmp_dev -d pepgmp_development < <(gunzip -c $BACKUP_FILE_DB)
EOF

echo -e "${GREEN}✅ 备份信息已保存: $INFO_FILE${NC}"
echo ""

echo "========================================================================="
echo -e "${GREEN}                     备份完成${NC}"
echo "========================================================================="
echo ""
echo "备份位置: $BACKUP_DIR"
echo "时间戳: $TIMESTAMP"
echo ""
echo "下一步:"
echo "  1. 停止旧容器: docker compose down"
echo "  2. 重新构建: docker compose build"
echo "  3. 启动新容器: docker compose up -d"
echo "  4. 恢复数据: bash scripts/restore_dev_data.sh $BACKUP_DIR $TIMESTAMP"
