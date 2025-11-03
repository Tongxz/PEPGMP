#!/bin/bash

# 生产环境部署脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================================================="
echo "                     生产环境部署"
echo "========================================================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 部署模式
DEPLOY_MODE=${1:-docker}  # docker, k8s, local

echo "部署模式: $DEPLOY_MODE"
echo ""

# ==================== 预部署检查 ====================
echo "==================== 预部署检查 ===================="
echo ""

# 检查Git状态
if [ -d ".git" ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  警告：工作目录有未提交的更改${NC}"
        git status --short
        echo ""
        read -p "继续部署？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Git工作目录干净${NC}"
    fi
    
    current_branch=$(git branch --show-current)
    echo "当前分支: $current_branch"
    
    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        echo -e "${YELLOW}⚠️  警告：不在main/master分支${NC}"
        read -p "继续部署？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 检查.env.production
if [ ! -f ".env.production" ]; then
    echo -e "${RED}❌ .env.production文件不存在${NC}"
    echo ""
    echo "创建步骤："
    echo "  1. cp .env.production.example .env.production"
    echo "  2. 编辑.env.production并设置强密码"
    echo "  3. chmod 600 .env.production"
    exit 1
fi

# 验证配置
echo ""
echo "验证生产环境配置..."
export ENVIRONMENT=production
set -a
source .env.production
set +a

if ! python scripts/validate_config.py; then
    echo -e "${RED}❌ 配置验证失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 配置验证通过${NC}"

# 检查密码强度
echo ""
echo "检查密码强度..."
weak_passwords=0

if [ ${#ADMIN_PASSWORD} -lt 16 ]; then
    echo -e "${YELLOW}⚠️  ADMIN_PASSWORD长度不足16字符${NC}"
    weak_passwords=$((weak_passwords + 1))
fi

if [ ${#SECRET_KEY} -lt 32 ]; then
    echo -e "${YELLOW}⚠️  SECRET_KEY长度不足32字符${NC}"
    weak_passwords=$((weak_passwords + 1))
fi

if [ "$ADMIN_PASSWORD" == "admin123" ] || [ "$ADMIN_PASSWORD" == "CHANGE_ME_VERY_STRONG_PASSWORD_MIN_16_CHARS" ]; then
    echo -e "${RED}❌ ADMIN_PASSWORD使用默认值，不安全！${NC}"
    exit 1
fi

if [ $weak_passwords -gt 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $weak_passwords 个弱密码${NC}"
    read -p "继续部署？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# ==================== 部署 ====================
echo "==================== 开始部署 ===================="
echo ""

case $DEPLOY_MODE in
    docker)
        echo "使用Docker Compose部署..."
        echo ""
        
        # 检查Docker
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker未安装${NC}"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}❌ Docker Compose未安装${NC}"
            exit 1
        fi
        
        # 构建镜像
        echo "1. 构建Docker镜像..."
        docker build -f Dockerfile.prod.new -t pyt-api:latest . || {
            echo -e "${RED}❌ 镜像构建失败${NC}"
            exit 1
        }
        echo -e "${GREEN}✅ 镜像构建成功${NC}"
        echo ""
        
        # 停止旧服务
        echo "2. 停止旧服务..."
        docker-compose -f docker-compose.prod.yml down || true
        echo ""
        
        # 启动新服务
        echo "3. 启动新服务..."
        docker-compose -f docker-compose.prod.yml up -d
        echo -e "${GREEN}✅ 服务启动成功${NC}"
        echo ""
        
        # 等待服务启动
        echo "4. 等待服务启动..."
        for i in {1..30}; do
            if curl -sf http://localhost:${API_PORT:-8000}/api/v1/monitoring/health > /dev/null; then
                echo -e "${GREEN}✅ 服务已启动并响应${NC}"
                break
            else
                echo "等待中... ($i/30)"
                sleep 2
            fi
        done
        echo ""
        
        # 显示服务状态
        echo "5. 服务状态："
        docker-compose -f docker-compose.prod.yml ps
        ;;
        
    k8s)
        echo "使用Kubernetes部署..."
        echo ""
        
        # 检查kubectl
        if ! command -v kubectl &> /dev/null; then
            echo -e "${RED}❌ kubectl未安装${NC}"
            exit 1
        fi
        
        # 应用配置
        echo "1. 应用Kubernetes配置..."
        kubectl apply -f k8s/
        echo ""
        
        # 等待部署完成
        echo "2. 等待部署完成..."
        kubectl rollout status deployment/pyt-api
        echo ""
        
        # 显示Pod状态
        echo "3. Pod状态："
        kubectl get pods -l app=pyt-api
        ;;
        
    local)
        echo "本地部署..."
        echo ""
        
        # 运行数据库迁移（如果需要）
        # python manage.py migrate
        
        # 启动服务
        ./scripts/start_prod.sh
        ;;
        
    *)
        echo -e "${RED}❌ 未知的部署模式: $DEPLOY_MODE${NC}"
        echo "支持的模式: docker, k8s, local"
        exit 1
        ;;
esac

# ==================== 部署后验证 ====================
echo ""
echo "==================== 部署后验证 ===================="
echo ""

# 健康检查
echo "1. 健康检查..."
if curl -sf http://localhost:${API_PORT:-8000}/api/v1/monitoring/health | jq .; then
    echo -e "${GREEN}✅ 健康检查通过${NC}"
else
    echo -e "${YELLOW}⚠️  健康检查失败或jq未安装${NC}"
fi
echo ""

# API测试
echo "2. API测试..."
if curl -sf http://localhost:${API_PORT:-8000}/docs > /dev/null; then
    echo -e "${GREEN}✅ API文档可访问${NC}"
else
    echo -e "${YELLOW}⚠️  API文档不可访问${NC}"
fi
echo ""

# ==================== 完成 ====================
echo "========================================================================="
echo "                     部署完成"
echo "========================================================================="
echo ""
echo "服务信息："
echo "  环境: production"
echo "  API: http://localhost:${API_PORT:-8000}"
echo "  文档: http://localhost:${API_PORT:-8000}/docs"
echo "  健康检查: http://localhost:${API_PORT:-8000}/api/v1/monitoring/health"
echo ""
echo "日志查看："
if [ "$DEPLOY_MODE" == "docker" ]; then
    echo "  docker-compose -f docker-compose.prod.yml logs -f api"
fi
echo ""
echo "停止服务："
if [ "$DEPLOY_MODE" == "docker" ]; then
    echo "  docker-compose -f docker-compose.prod.yml down"
fi
echo ""
echo -e "${GREEN}✅ 部署成功完成${NC}"
echo ""
