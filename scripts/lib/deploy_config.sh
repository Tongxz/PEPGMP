#!/bin/bash
# ============================================================================
# 部署配置文件 - 统一管理所有部署相关变量
# Deploy Configuration - Centralized management of deployment variables
# ============================================================================
#
# 用法 / Usage:
#   source "$SCRIPT_DIR/lib/deploy_config.sh"
#
# 此文件定义了所有部署脚本共享的配置变量，确保一致性。
# This file defines all shared configuration variables for deployment scripts.
# ============================================================================

# ==================== 项目信息 / Project Info ====================
PROJECT_NAME="${PROJECT_NAME:-pepgmp}"

# ==================== 镜像名称 / Image Names ====================
# 统一使用 pepgmp-backend 和 pepgmp-frontend
# 与 docker-compose.prod.yml 保持一致
BACKEND_IMAGE_NAME="${BACKEND_IMAGE_NAME:-pepgmp-backend}"
FRONTEND_IMAGE_NAME="${FRONTEND_IMAGE_NAME:-pepgmp-frontend}"

# ==================== Dockerfile 路径 / Dockerfile Paths ====================
# 生产环境使用 Dockerfile.prod
BACKEND_DOCKERFILE="${BACKEND_DOCKERFILE:-Dockerfile.prod}"
FRONTEND_DOCKERFILE="${FRONTEND_DOCKERFILE:-Dockerfile.frontend}"

# ==================== 版本标签 / Version Tags ====================
# 默认使用日期作为版本号
DEFAULT_VERSION_TAG=$(date +%Y%m%d)
VERSION_TAG="${VERSION_TAG:-$DEFAULT_VERSION_TAG}"

# ==================== Registry 配置 / Registry Configuration ====================
# 统一 Registry 来源优先级:
# 1) IMAGE_REGISTRY 环境变量
# 2) .env.production 里的 IMAGE_REGISTRY
# 3) REGISTRY_URL 环境变量
# 4) 默认值
IMAGE_REGISTRY_RAW="${IMAGE_REGISTRY:-}"
if [ -z "$IMAGE_REGISTRY_RAW" ] && [ -f ".env.production" ]; then
    IMAGE_REGISTRY_RAW="$(grep -E '^IMAGE_REGISTRY=' .env.production | tail -n 1 | cut -d '=' -f2-)"
fi

if [ -n "$IMAGE_REGISTRY_RAW" ]; then
    REGISTRY_URL="${IMAGE_REGISTRY_RAW#http://}"
    REGISTRY_URL="${REGISTRY_URL#https://}"
    REGISTRY_URL="${REGISTRY_URL%/}"
else
    REGISTRY_URL="${REGISTRY_URL:-11.25.125.115:5433}"
fi

# Compose 推荐使用带尾部 / 的 IMAGE_REGISTRY
IMAGE_REGISTRY="${REGISTRY_URL}/"

# Registry 中的完整镜像路径
REGISTRY_BACKEND_IMAGE="${REGISTRY_URL}/${BACKEND_IMAGE_NAME}"
REGISTRY_FRONTEND_IMAGE="${REGISTRY_URL}/${FRONTEND_IMAGE_NAME}"

# ==================== 部署目录 / Deployment Directories ====================
# WSL/Linux 默认部署目录
DEFAULT_DEPLOY_DIR="${HOME}/projects/PEPGMP"
DEPLOY_DIR="${DEPLOY_DIR:-$DEFAULT_DEPLOY_DIR}"

# 镜像导出目录
EXPORT_DIR="${EXPORT_DIR:-./docker-images}"

# ==================== Docker Compose 文件 / Docker Compose Files ====================
COMPOSE_FILE_DEV="docker-compose.yml"
COMPOSE_FILE_PROD="docker-compose.prod.yml"
COMPOSE_FILE_1PANEL="docker-compose.prod.1panel.yml"

# ==================== 端口配置 / Port Configuration ====================
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-80}"
NGINX_HTTP_PORT="${NGINX_HTTP_PORT:-80}"
NGINX_HTTPS_PORT="${NGINX_HTTPS_PORT:-443}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"

# ==================== 超时配置 / Timeout Configuration ====================
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-120}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-5}"

# ==================== 跨平台兼容性函数 / Cross-platform Compatibility ====================

# 检测操作系统
detect_os() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            if grep -q Microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# 获取当前操作系统
CURRENT_OS=$(detect_os)

# 跨平台的 sed -i 命令
# macOS 需要 sed -i ''，Linux 使用 sed -i
sed_inplace() {
    if [ "$CURRENT_OS" = "macos" ]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# 跨平台的 stat 命令获取文件大小
get_file_size() {
    local file="$1"
    if [ "$CURRENT_OS" = "macos" ]; then
        stat -f%z "$file" 2>/dev/null
    else
        stat -c%s "$file" 2>/dev/null
    fi
}

# 跨平台的 stat 命令获取文件权限
get_file_perms() {
    local file="$1"
    if [ "$CURRENT_OS" = "macos" ]; then
        stat -f "%OLp" "$file" 2>/dev/null
    else
        stat -c "%a" "$file" 2>/dev/null
    fi
}

# 检查命令是否存在
command_exists() {
    command -v "$1" &> /dev/null
}

# ==================== 颜色定义 / Color Definitions ====================
# 用于脚本输出美化
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ==================== 日志函数 / Logging Functions ====================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}[STEP]${NC} $1"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ==================== 配置验证 / Configuration Validation ====================
validate_deploy_config() {
    local errors=0

    # 检查必要的命令
    if ! command_exists docker; then
        log_error "Docker 未安装或不在 PATH 中"
        errors=$((errors + 1))
    fi

    # 检查 Docker 是否运行
    if command_exists docker && ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行"
        errors=$((errors + 1))
    fi

    # 检查 Dockerfile 是否存在
    if [ ! -f "$BACKEND_DOCKERFILE" ] && [ -f "$(dirname "$0")/../$BACKEND_DOCKERFILE" ]; then
        log_warning "请在项目根目录运行此脚本"
    fi

    return $errors
}

# ==================== 显示配置 / Display Configuration ====================
show_deploy_config() {
    echo ""
    echo "==================== 部署配置 ===================="
    echo "操作系统:       $CURRENT_OS"
    echo "项目名称:       $PROJECT_NAME"
    echo ""
    echo "后端镜像:       $BACKEND_IMAGE_NAME"
    echo "前端镜像:       $FRONTEND_IMAGE_NAME"
    echo "版本标签:       $VERSION_TAG"
    echo ""
    echo "后端Dockerfile: $BACKEND_DOCKERFILE"
    echo "前端Dockerfile: $FRONTEND_DOCKERFILE"
    echo ""
    echo "Registry:       $REGISTRY_URL"
    echo "部署目录:       $DEPLOY_DIR"
    echo "=================================================="
    echo ""
}

# ==================== 导出变量 / Export Variables ====================
export PROJECT_NAME
export BACKEND_IMAGE_NAME
export FRONTEND_IMAGE_NAME
export BACKEND_DOCKERFILE
export FRONTEND_DOCKERFILE
export VERSION_TAG
export REGISTRY_URL
export IMAGE_REGISTRY
export DEPLOY_DIR
export CURRENT_OS
