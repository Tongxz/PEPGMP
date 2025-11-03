#!/bin/bash

################################################################################
# 生成生产环境配置文件
# 用途: 自动生成带有强随机密码的 .env.production 文件
# 使用: bash scripts/generate_production_config.sh
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================================================="
echo -e "${BLUE}生成生产环境配置文件${NC}"
echo "========================================================================="
echo ""

# 检查 .env.production 是否已存在
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}警告: .env.production 已存在${NC}"
    read -p "是否覆盖现有文件？(yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "操作已取消"
        exit 0
    fi
    # 备份现有文件
    cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
    echo "✓ 已备份现有配置文件"
fi
echo ""

# 生成随机密码的函数
generate_password() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# 获取用户输入
echo "请输入配置信息（直接回车使用默认值）:"
echo ""

read -p "API端口 [8000]: " API_PORT
API_PORT=${API_PORT:-8000}

read -p "管理员用户名 [admin]: " ADMIN_USERNAME
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}

read -p "允许的CORS来源 [*]: " CORS_ORIGINS
CORS_ORIGINS=${CORS_ORIGINS:-*}

echo ""
echo "正在生成强随机密码..."

DATABASE_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)
SECRET_KEY=$(generate_password)
JWT_SECRET_KEY=$(generate_password)
ADMIN_PASSWORD=$(generate_password)

echo "✓ 密码生成完成"
echo ""

# 生成配置文件
cat > .env.production << EOF
# ========================================================================
# 生产环境配置
# Production Environment Configuration
# ========================================================================
#
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
#
# ⚠️  警告: 此文件包含敏感信息，请妥善保管！
# - 不要提交到Git仓库
# - 限制文件访问权限: chmod 600 .env.production
# - 定期更新密码
#
# ========================================================================

# ==================== 应用基础配置 ====================
ENVIRONMENT=production
API_PORT=${API_PORT}
LOG_LEVEL=INFO

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://pyt_prod:${DATABASE_PASSWORD}@database:5432/pyt_production
POSTGRES_USER=pyt_prod
POSTGRES_DB=pyt_production
DATABASE_PASSWORD=${DATABASE_PASSWORD}

# ==================== Redis配置 ====================
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=${REDIS_PASSWORD}

# ==================== 安全配置 ====================
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# 管理员账号
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ==================== CORS配置 ====================
CORS_ORIGINS=${CORS_ORIGINS}

# ==================== 摄像头配置 ====================
CAMERAS_YAML_PATH=/app/config/cameras.yaml

# ==================== 领域服务配置 ====================
USE_DOMAIN_SERVICE=true
REPOSITORY_TYPE=postgresql
ROLLOUT_PERCENT=100

# ==================== 文件监控配置 ====================
WATCHFILES_FORCE_POLLING=1

# ==================== TensorRT配置 ====================
AUTO_CONVERT_TENSORRT=false

# ==================== Gunicorn配置 ====================
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120

# ==================== MLflow配置（可选） ====================
# MLFLOW_PORT=5000
# MLFLOW_TRACKING_URI=http://mlflow:5000

# ==================== 监控配置（可选） ====================
# PROMETHEUS_ENABLED=true
# GRAFANA_ADMIN_USER=admin
# GRAFANA_ADMIN_PASSWORD=$(generate_password)

# ==================== 邮件配置（可选） ====================
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@example.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM=noreply@example.com

# ==================== Sentry配置（可选） ====================
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# ========================================================================
# 配置生成完成
# ========================================================================
EOF

# 设置文件权限
chmod 600 .env.production

echo "========================================================================="
echo -e "${GREEN}配置文件生成成功！${NC}"
echo "========================================================================="
echo ""
echo "文件位置: .env.production"
echo "文件权限: 600 (仅所有者可读写)"
echo ""
echo -e "${YELLOW}重要信息（请妥善保存）:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "管理员账号:"
echo "  用户名: ${ADMIN_USERNAME}"
echo "  密码: ${ADMIN_PASSWORD}"
echo ""
echo "数据库密码: ${DATABASE_PASSWORD}"
echo "Redis密码: ${REDIS_PASSWORD}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}⚠️  请将以上信息保存到密码管理器！${NC}"
echo ""

# 生成密码记录文件
cat > .env.production.credentials << EOF
========================================================================
生产环境凭证
Production Credentials
========================================================================

生成时间: $(date '+%Y-%m-%d %H:%M:%S')

管理员账号:
  用户名: ${ADMIN_USERNAME}
  密码: ${ADMIN_PASSWORD}

数据库:
  用户名: pyt_prod
  数据库: pyt_production
  密码: ${DATABASE_PASSWORD}

Redis:
  密码: ${REDIS_PASSWORD}

安全密钥:
  SECRET_KEY: ${SECRET_KEY}
  JWT_SECRET_KEY: ${JWT_SECRET_KEY}

========================================================================
⚠️  重要: 请妥善保管此文件，并在确认信息后删除！
========================================================================
EOF

chmod 600 .env.production.credentials

echo "凭证信息已保存到: .env.production.credentials"
echo ""
echo "下一步:"
echo "  1. 查看完整配置: cat .env.production"
echo "  2. 查看凭证信息: cat .env.production.credentials"
echo "  3. 保存凭证后删除: rm .env.production.credentials"
echo "  4. 开始部署: bash scripts/quick_deploy.sh <服务器IP>"
echo ""
echo "========================================================================="
