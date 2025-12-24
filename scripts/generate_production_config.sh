#!/bin/bash

################################################################################
# Generate Production Environment Configuration File
# Purpose: Automatically generate .env.production file with strong random passwords
# Usage: bash scripts/generate_production_config.sh [-y]
#   -y: Non-interactive mode, automatically overwrite existing file
################################################################################

set -e

# Set locale to avoid encoding issues
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse command line arguments
NON_INTERACTIVE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-y]"
            echo "  -y, --yes    Non-interactive mode, automatically overwrite existing file"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "========================================================================="
echo -e "${BLUE}Generate Production Environment Configuration${NC}"
echo "========================================================================="
echo ""

# Auto-detect host user UID/GID
HOST_UID=$(id -u)
HOST_GID=$(id -g)
echo -e "${BLUE}[INFO]${NC} Auto-detected host user: UID=${HOST_UID}, GID=${HOST_GID}"
echo ""

# Check if .env.production already exists
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}Warning: .env.production already exists${NC}"
    if [ "$NON_INTERACTIVE" = true ]; then
        echo "Non-interactive mode: automatically overwriting existing file"
    else
        read -p "Overwrite existing file? (y/n) [n]: " confirm
        confirm=${confirm:-n}
        if [ "$confirm" != "yes" ] && [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "Operation cancelled"
            exit 0
        fi
    fi
    # Backup existing file
    cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
    echo "[OK] Backup created for existing configuration file"
fi
echo ""

# Function to generate random password
generate_password() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Get user input
if [ "$NON_INTERACTIVE" = false ]; then
    echo "Please enter configuration (press Enter for default values):"
    echo ""

    read -p "API Port [8000]: " API_PORT
    API_PORT=${API_PORT:-8000}

    read -p "Admin Username [admin]: " ADMIN_USERNAME
    ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

    read -p "CORS Origins [*]: " CORS_ORIGINS
    CORS_ORIGINS=${CORS_ORIGINS:-*}

    read -p "Image Tag [latest]: " IMAGE_TAG_INPUT
    IMAGE_TAG=${IMAGE_TAG_INPUT:-latest}
else
    # Non-interactive mode: use defaults
    API_PORT=8000
    ADMIN_USERNAME=admin
    CORS_ORIGINS=*
    IMAGE_TAG=latest
    echo "Non-interactive mode: using default values"
    echo "  API Port: ${API_PORT}"
    echo "  Admin Username: ${ADMIN_USERNAME}"
    echo "  CORS Origins: ${CORS_ORIGINS}"
    echo "  Image Tag: ${IMAGE_TAG}"
fi
echo ""

echo "Generating strong random passwords..."

DATABASE_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)
SECRET_KEY=$(generate_password)
JWT_SECRET_KEY=$(generate_password)
ADMIN_PASSWORD=$(generate_password)

echo "✓ Password generation completed"
echo ""

# Generate configuration file
cat > .env.production << EOF
# ========================================================================
# Production Environment Configuration
# ========================================================================
#
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
#
# ⚠️  Warning: This file contains sensitive information, please keep it secure!
# - Do not commit to Git repository
# - Restrict file access: chmod 600 .env.production
# - Update passwords regularly
#
# ========================================================================

# ==================== Application Basic Configuration ====================
ENVIRONMENT=production
API_PORT=${API_PORT}
LOG_LEVEL=INFO
IMAGE_TAG=${IMAGE_TAG}

# ==================== Host User Configuration ====================
# 宿主机用户 UID/GID（用于 frontend-init 容器设置文件权限）
# 自动探测当前运行脚本用户的 UID/GID，确保文件权限与当前用户完美匹配
# 如需手动修改，请使用: id -u (获取 UID), id -g (获取 GID)
HOST_UID=${HOST_UID}
HOST_GID=${HOST_GID}

# ==================== Database Configuration ====================
# PostgreSQL 连接字符串
# 标准驱动: postgresql://user:password@host:port/database
# 异步驱动 (推荐用于 FastAPI/Uvicorn): postgresql+asyncpg://user:password@host:port/database
# 注意: 如果使用异步驱动，需要确保安装了 asyncpg 驱动: pip install asyncpg
DATABASE_URL=postgresql://pepgmp_prod:${DATABASE_PASSWORD}@database:5432/pepgmp_production
# DATABASE_URL=postgresql+asyncpg://pepgmp_prod:${DATABASE_PASSWORD}@database:5432/pepgmp_production
POSTGRES_USER=pepgmp_prod
POSTGRES_DB=pepgmp_production
DATABASE_PASSWORD=${DATABASE_PASSWORD}

# ==================== Redis Configuration ====================
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=${REDIS_PASSWORD}

# ==================== Security Configuration ====================
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# Admin Account
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ==================== CORS Configuration ====================
CORS_ORIGINS=${CORS_ORIGINS}

# ==================== Camera Configuration ====================
CAMERAS_YAML_PATH=/app/config/cameras.yaml

# ==================== Domain Service Configuration ====================
USE_DOMAIN_SERVICE=true
REPOSITORY_TYPE=postgresql
ROLLOUT_PERCENT=100

# ==================== File Monitoring Configuration ====================
WATCHFILES_FORCE_POLLING=1

# ==================== TensorRT Configuration ====================
# 是否自动转换模型为 TensorRT 格式（需要 TensorRT 库和 CUDA GPU）
# 生产环境如有 GPU 和 TensorRT，建议设置为 true 以提升性能
# 首次转换可能需要几分钟时间，转换后的引擎文件会被缓存
AUTO_CONVERT_TENSORRT=false

# ==================== Gunicorn Configuration ====================
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120

# ==================== MLflow Configuration (Optional) ====================
# MLFLOW_PORT=5000
# MLFLOW_TRACKING_URI=http://mlflow:5000

# ==================== Monitoring Configuration (Optional) ====================
# PROMETHEUS_ENABLED=true
# GRAFANA_ADMIN_USER=admin
# GRAFANA_ADMIN_PASSWORD=$(generate_password)

# ==================== Email Configuration (Optional) ====================
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@example.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM=noreply@example.com

# ==================== Sentry Configuration (Optional) ====================
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# ========================================================================
# Configuration Generation Complete
# ========================================================================
EOF

# Set file permissions
chmod 600 .env.production

echo "========================================================================="
echo -e "${GREEN}Configuration file generated successfully!${NC}"
echo "========================================================================="
echo ""
echo "File location: .env.production"
echo "File permissions: 600 (owner read/write only)"
echo ""
echo -e "${YELLOW}Important information (please save carefully):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Admin Account:"
echo "  Username: ${ADMIN_USERNAME}"
echo "  Password: ${ADMIN_PASSWORD}"
echo ""
echo "Database Password: ${DATABASE_PASSWORD}"
echo "Redis Password: ${REDIS_PASSWORD}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}⚠️  Please save the above information to a password manager!${NC}"
echo ""

# Generate credentials record file
cat > .env.production.credentials << EOF
========================================================================
Production Environment Credentials
Production Credentials
========================================================================

Generated: $(date '+%Y-%m-%d %H:%M:%S')

Admin Account:
  Username: ${ADMIN_USERNAME}
  Password: ${ADMIN_PASSWORD}

Database:
  Username: pepgmp_prod
  Database: pepgmp_production
  Password: ${DATABASE_PASSWORD}

Redis:
  Password: ${REDIS_PASSWORD}

Security Keys:
  SECRET_KEY: ${SECRET_KEY}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}

========================================================================
⚠️  Important: Please keep this file secure and delete it after confirming the information!
========================================================================
EOF

chmod 600 .env.production.credentials

echo "Credentials saved to: .env.production.credentials"
echo ""
echo "Next steps:"
echo "  1. View full config: cat .env.production"
echo "  2. View credentials: cat .env.production.credentials"
echo "  3. Delete credentials after saving: rm .env.production.credentials"
echo "  4. Start deployment:"
echo "     - Mixed (network isolated): bash scripts/deploy_mixed_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP"
echo "     - Registry (same network): bash scripts/deploy_via_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP"
echo ""
echo "========================================================================="
