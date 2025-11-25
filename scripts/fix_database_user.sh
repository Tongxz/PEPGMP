#!/bin/bash

# 修复数据库用户脚本
# 用途: 在PostgreSQL容器中手动创建用户和数据库

set -e

CONTAINER="pepgmp-postgres-dev"
DB_USER="pepgmp_dev"
DB_PASSWORD="pepgmp_dev_password"
DB_NAME="pepgmp_development"

echo "修复数据库用户和数据库..."
echo "容器: $CONTAINER"
echo "用户: $DB_USER"
echo "数据库: $DB_NAME"
echo ""

# 方法1: 尝试使用环境变量中的用户（如果存在）
echo "尝试方法1: 使用环境变量用户..."
if docker exec "$CONTAINER" sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "SELECT 1;"' > /dev/null 2>&1; then
    echo "✅ 可以使用环境变量用户"
    docker exec "$CONTAINER" sh -c "psql -U \"\$POSTGRES_USER\" -d postgres -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\" 2>&1 || echo '用户可能已存在'"
    docker exec "$CONTAINER" sh -c "psql -U \"\$POSTGRES_USER\" -d postgres -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\" 2>&1 || echo '数据库可能已存在'"
else
    echo "⚠️  方法1失败，尝试方法2..."
    
    # 方法2: 检查是否有其他可用的超级用户
    echo "尝试方法2: 查找可用的超级用户..."
    SUPER_USER=$(docker exec "$CONTAINER" sh -c 'psql -t -A -c "SELECT usename FROM pg_user WHERE usesuper = true LIMIT 1;"' 2>/dev/null | head -1 | tr -d ' ')
    
    if [ -n "$SUPER_USER" ] && [ "$SUPER_USER" != "" ]; then
        echo "找到超级用户: $SUPER_USER"
        docker exec "$CONTAINER" sh -c "psql -U $SUPER_USER -d postgres -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\" 2>&1 || echo '用户可能已存在'"
        docker exec "$CONTAINER" sh -c "psql -U $SUPER_USER -d postgres -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\" 2>&1 || echo '数据库可能已存在'"
    else
        echo "❌ 无法找到可用的超级用户"
        echo "需要完全重新初始化数据库"
        exit 1
    fi
fi

echo ""
echo "验证用户和数据库..."
if docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ 用户和数据库创建成功！"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT current_user, current_database();"
else
    echo "❌ 验证失败"
    exit 1
fi

