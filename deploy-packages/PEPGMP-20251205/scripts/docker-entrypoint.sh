#!/bin/bash
# Docker Entrypoint Script for API Container
# Purpose: Wait for database, run migrations, then start the application

set -e

echo "========================================================================="
echo "API Container Entrypoint"
echo "========================================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 从环境变量读取数据库配置
DB_HOST="${DATABASE_HOST:-database}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_USER="${POSTGRES_USER:-pepgmp_prod}"
DB_NAME="${POSTGRES_DB:-pepgmp_production}"

# 等待数据库就绪
print_info "Waiting for database to be ready..."
print_info "  Host: $DB_HOST:$DB_PORT"
print_info "  User: $DB_USER"
print_info "  Database: $DB_NAME"

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        print_success "Database is ready!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "  Attempt $RETRY_COUNT/$MAX_RETRIES: Database is unavailable - sleeping..."
            sleep 2
        else
            print_error "Database is not ready after $MAX_RETRIES attempts"
            exit 1
        fi
    fi
done

# 执行数据库迁移（如果使用 Alembic）
# 重要：采用 Fail Fast 策略，迁移失败时立即退出，避免应用在错误的数据库结构下运行
if [ -f "alembic.ini" ] && command -v alembic >/dev/null 2>&1; then
    print_info "Running database migrations..."
    print_info "  Using Alembic for schema migrations"

    if alembic upgrade head; then
        print_success "Database migrations completed successfully"
    else
        print_error "Database migrations failed!"
        print_error "  This is a critical error. The application cannot start with an incompatible database schema."
        print_error "  Please check the migration logs above and fix the issue before restarting."
        print_error ""
        print_error "  Common causes:"
        print_error "    - Database schema is out of sync with migration files"
        print_error "    - Migration conflicts or dependency issues"
        print_error "    - Database connection or permission problems"
        print_error ""
        print_error "  Container will exit now to prevent running with an incompatible database."
        exit 1
    fi
else
    print_info "No Alembic migration found, skipping..."
    print_info "  (This is normal if using SQL-based migrations or ORM auto-creation)"
fi

# 执行应用启动命令
echo ""
print_info "Starting application..."
print_info "  Command: $@"
echo "========================================================================="
echo ""

# 使用 exec 替换当前进程，确保信号正确传递
exec "$@"
