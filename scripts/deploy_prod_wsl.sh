#!/bin/bash
# WSL/Ubuntu 生产环境一键部署脚本
# Purpose: 在 WSL/Ubuntu 中一键完成生产环境部署
# Usage: bash scripts/deploy_prod_wsl.sh [DEPLOY_DIR] [VERSION_TAG] [SKIP_BUILD]

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DEPLOY_DIR="${1:-$HOME/projects/PEPGMP-deploy}"
VERSION_TAG="${2:-$(date +%Y%m%d)}"
SKIP_BUILD="${3:-false}"

echo "========================================================================="
echo -e "${BLUE}WSL/Ubuntu 生产环境一键部署${NC}"
echo "========================================================================="
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "部署目录: $DEPLOY_DIR"
echo "镜像版本标签: $VERSION_TAG"
echo "跳过构建: $SKIP_BUILD"
echo ""

# Check functions
check_passed() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_failed() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

check_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# ==================== 步骤 1: 检查 Docker 环境 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 1]${NC} 检查 Docker 环境"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if ! command -v docker &> /dev/null; then
    check_failed "Docker 未安装"
fi

if ! docker info &> /dev/null; then
    check_failed "Docker 守护进程未运行"
fi

check_passed "Docker 已安装并运行"
check_info "Docker 版本: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    check_failed "Docker Compose 不可用"
fi

check_passed "Docker Compose 可用"

echo ""

# ==================== 步骤 2: 检查端口可用性 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 2]${NC} 检查端口可用性"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

PORT_80_IN_USE=$(ss -tuln 2>/dev/null | grep -c ":80 " || echo "0")
PORT_8000_IN_USE=$(ss -tuln 2>/dev/null | grep -c ":8000 " || echo "0")

if [ "$PORT_80_IN_USE" -gt 0 ]; then
    check_warning "端口 80 已被占用"
    check_info "可能需要修改 docker-compose.prod.yml 使用其他端口"
else
    check_passed "端口 80 可用"
fi

if [ "$PORT_8000_IN_USE" -gt 0 ]; then
    check_warning "端口 8000 已被占用"
else
    check_passed "端口 8000 可用"
fi

echo ""

# ==================== 步骤 3: 检查 GPU 支持（可选） ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 3]${NC} 检查 GPU 支持（可选）"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        check_passed "NVIDIA GPU 驱动已安装"
        check_info "GPU 信息:"
        nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | head -1

        # 检查 Docker GPU 支持
        if docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi &> /dev/null; then
            check_passed "Docker GPU 支持正常"
        else
            check_warning "Docker GPU 支持可能未配置"
        fi
    else
        check_warning "nvidia-smi 命令失败"
    fi
else
    check_info "未检测到 NVIDIA GPU（这是正常的，如果不需要 GPU）"
fi

echo ""

# ==================== 步骤 4: 构建镜像（如需要） ====================
if [ "$SKIP_BUILD" != "true" ]; then
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}[步骤 4]${NC} 构建生产镜像"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cd "$PROJECT_ROOT"

    # 检查镜像是否已存在
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "pepgmp-backend:$VERSION_TAG"; then
        check_info "后端镜像已存在: pepgmp-backend:$VERSION_TAG"
        read -p "是否重新构建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            check_info "开始构建镜像..."
            bash "$PROJECT_ROOT/scripts/build_prod_only.sh" "$VERSION_TAG"
        else
            check_info "使用现有镜像"
        fi
    else
        check_info "开始构建镜像..."
        bash "$PROJECT_ROOT/scripts/build_prod_only.sh" "$VERSION_TAG"
    fi

    # 验证镜像
    check_info "验证镜像..."
    BACKEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-backend:$VERSION_TAG" || echo "0")
    FRONTEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-frontend:$VERSION_TAG" || echo "0")

    if [ "$BACKEND_FOUND" -gt 0 ]; then
        check_passed "后端镜像存在: pepgmp-backend:$VERSION_TAG"
    else
        check_failed "后端镜像不存在: pepgmp-backend:$VERSION_TAG"
    fi

    if [ "$FRONTEND_FOUND" -gt 0 ]; then
        check_passed "前端镜像存在: pepgmp-frontend:$VERSION_TAG"
    else
        check_failed "前端镜像不存在: pepgmp-frontend:$VERSION_TAG"
    fi

    echo ""
fi

# ==================== 步骤 5: 准备部署目录 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 5]${NC} 准备部署目录"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "$DEPLOY_DIR" ]; then
    check_info "创建部署目录: $DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"
    check_passed "目录已创建"
else
    check_passed "部署目录已存在"
fi

# 运行 prepare_minimal_deploy.sh
check_info "运行 prepare_minimal_deploy.sh..."
if bash "$PROJECT_ROOT/scripts/prepare_minimal_deploy.sh" "$DEPLOY_DIR" "no"; then
    check_passed "部署包已准备"
else
    check_failed "准备部署包失败"
fi

echo ""

# ==================== 步骤 6: 生成生产配置 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 6]${NC} 生成生产配置"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$DEPLOY_DIR"

if [ ! -f ".env.production" ]; then
    check_info "生成 .env.production..."
    if bash "$PROJECT_ROOT/scripts/generate_production_config.sh" -y; then
        check_passed "配置已生成"
    else
        check_failed "生成配置失败"
    fi
else
    check_warning ".env.production 已存在"
    read -p "是否覆盖现有配置? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        bash "$PROJECT_ROOT/scripts/generate_production_config.sh" -y
        check_passed "配置已重新生成"
    else
        check_info "使用现有配置"
    fi
fi

# 更新 IMAGE_TAG
check_info "设置 IMAGE_TAG 为 $VERSION_TAG"
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production 2>/dev/null || \
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production 2>/dev/null || \
    echo "IMAGE_TAG=$VERSION_TAG" >> .env.production

check_passed "IMAGE_TAG 已更新为 $VERSION_TAG"

echo ""

# ==================== 步骤 7: 清理旧容器 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 7]${NC} 清理旧容器"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_info "检查现有容器..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=pepgmp-" --format "{{.Names}}" 2>/dev/null || echo "")

if [ -n "$EXISTING_CONTAINERS" ]; then
    check_warning "发现现有容器:"
    echo "$EXISTING_CONTAINERS" | while read -r container; do
        echo "  - $container"
    done

    check_info "停止并删除旧容器..."
    if docker compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null; then
        check_passed "旧容器已清理"
    else
        # 如果 compose down 失败，手动清理
        check_info "尝试手动清理..."
        docker stop $(docker ps -aq --filter "name=pepgmp-") 2>/dev/null || true
        docker rm $(docker ps -aq --filter "name=pepgmp-") 2>/dev/null || true
        check_passed "容器已清理"
    fi
else
    check_info "未发现现有容器"
fi

echo ""

# ==================== 步骤 8: 启动服务 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 8]${NC} 启动服务"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_info "启动 Docker Compose 服务..."
if docker compose -f docker-compose.prod.yml --env-file .env.production up -d; then
    check_passed "服务已启动"
else
    check_failed "启动服务失败"
fi

# 等待服务就绪
check_info "等待服务就绪..."
sleep 10

# 检查服务状态
check_info "服务状态:"
docker compose -f docker-compose.prod.yml --env-file .env.production ps

echo ""

# ==================== 步骤 9: 验证部署 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[步骤 9]${NC} 验证部署"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查 frontend-init
FRONTEND_INIT_STATUS=$(docker inspect --format='{{.State.Status}}' pepgmp-frontend-init 2>/dev/null || echo "not found")
if [ "$FRONTEND_INIT_STATUS" = "exited" ]; then
    EXIT_CODE=$(docker inspect --format='{{.State.ExitCode}}' pepgmp-frontend-init 2>/dev/null || echo "unknown")
    if [ "$EXIT_CODE" = "0" ]; then
        check_passed "Frontend-init 已完成"
    else
        check_failed "Frontend-init 退出码: $EXIT_CODE"
        check_info "查看日志: docker logs pepgmp-frontend-init"
    fi
else
    check_warning "Frontend-init 状态: $FRONTEND_INIT_STATUS"
fi

# 检查静态文件
if [ -f "frontend/dist/index.html" ]; then
    check_passed "静态文件已存在"
else
    check_warning "静态文件不存在，等待 frontend-init 完成..."
    sleep 5
    if [ -f "frontend/dist/index.html" ]; then
        check_passed "静态文件已存在"
    else
        check_warning "静态文件仍未生成，请检查 frontend-init 日志"
    fi
fi

# 测试 HTTP 端点
echo ""
check_info "测试 HTTP 端点..."

# 测试前端
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check_passed "前端可访问 (HTTP $HTTP_CODE)"
else
    check_warning "前端返回 HTTP $HTTP_CODE"
fi

# 测试 API
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/monitoring/health" 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
    check_passed "API 可访问 (HTTP $API_CODE)"
else
    check_warning "API 返回 HTTP $API_CODE"
fi

echo ""

# ==================== 部署总结 ====================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}部署总结${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "部署目录: $DEPLOY_DIR"
echo "镜像版本: $VERSION_TAG"
echo ""
echo "访问地址:"
echo "  前端: http://localhost/"
echo "  API:  http://localhost:8000/api/v1/monitoring/health"
echo "  健康检查: http://localhost/health"
echo ""
echo "WSL IP 地址（用于 Windows 浏览器访问）:"
WSL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "未知")
echo "  $WSL_IP"
echo ""
echo "常用命令:"
echo "  查看日志:    docker compose -f docker-compose.prod.yml --env-file .env.production logs -f"
echo "  停止服务:    docker compose -f docker-compose.prod.yml --env-file .env.production down"
echo "  重启服务:    docker compose -f docker-compose.prod.yml --env-file .env.production restart"
echo "  查看状态:    docker compose -f docker-compose.prod.yml --env-file .env.production ps"
echo ""
echo "========================================================================="
