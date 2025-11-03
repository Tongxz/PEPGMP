#!/bin/bash

################################################################################
# 检查部署就绪状态
# 用途: 在部署前检查所有必需的文件和目录
# 使用: bash scripts/check_deployment_readiness.sh
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================================================="
echo -e "${BLUE}检查部署就绪状态${NC}"
echo "========================================================================="
echo ""

ERRORS=0
WARNINGS=0

# ==================== 检查必需文件 ====================
echo -e "${GREEN}[1/5]${NC} 检查必需文件..."
echo ""

# 检查 .env.production
if [ -f ".env.production" ]; then
    echo "✓ .env.production 存在"

    # 检查文件权限
    PERMS=$(stat -f "%OLp" .env.production 2>/dev/null || stat -c "%a" .env.production 2>/dev/null)
    if [ "$PERMS" = "600" ]; then
        echo "  └─ 文件权限正确 (600)"
    else
        echo -e "  └─ ${YELLOW}警告: 文件权限为 $PERMS，建议设置为 600${NC}"
        echo "     运行: chmod 600 .env.production"
        ((WARNINGS++))
    fi

    # 检查是否还有默认密码
    if grep -q "CHANGE_ME" .env.production; then
        echo -e "  └─ ${RED}错误: 配置文件中还有 CHANGE_ME 占位符${NC}"
        echo "     请运行: bash scripts/generate_production_config.sh"
        ((ERRORS++))
    else
        echo "  └─ 配置已设置"
    fi
else
    echo -e "${RED}✗ .env.production 不存在${NC}"
    echo "  运行: bash scripts/generate_production_config.sh"
    ((ERRORS++))
fi
echo ""

# 检查 Dockerfile
if [ -f "Dockerfile.prod" ]; then
    echo "✓ Dockerfile.prod 存在"
else
    echo -e "${RED}✗ Dockerfile.prod 不存在${NC}"
    ((ERRORS++))
fi
echo ""

# 检查 docker-compose
if [ -f "docker-compose.prod.full.yml" ]; then
    echo "✓ docker-compose.prod.full.yml 存在"
else
    echo -e "${YELLOW}⚠ docker-compose.prod.full.yml 不存在（可选）${NC}"
    ((WARNINGS++))
fi
echo ""

# ==================== 检查必需目录 ====================
echo -e "${GREEN}[2/5]${NC} 检查必需目录..."
echo ""

# 检查 config 目录
if [ -d "config" ]; then
    echo "✓ config/ 目录存在"

    # 检查关键配置文件
    if [ -f "config/cameras.yaml" ] || [ -f "config/default.yaml" ]; then
        echo "  └─ 配置文件存在"
    else
        echo -e "  └─ ${YELLOW}警告: config/ 目录为空或缺少关键配置${NC}"
        ((WARNINGS++))
    fi

    # 列出配置文件
    CONFIG_COUNT=$(find config -type f -name "*.yaml" -o -name "*.json" | wc -l | tr -d ' ')
    echo "  └─ 配置文件数量: $CONFIG_COUNT"
else
    echo -e "${RED}✗ config/ 目录不存在${NC}"
    echo "  这是必需的目录，请创建它"
    ((ERRORS++))
fi
echo ""

# 检查 models 目录
if [ -d "models" ]; then
    echo "✓ models/ 目录存在"

    # 检查模型文件
    MODEL_COUNT=$(find models -type f \( -name "*.pt" -o -name "*.pth" -o -name "*.joblib" \) 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MODEL_COUNT" -gt 0 ]; then
        echo "  └─ 模型文件数量: $MODEL_COUNT"

        # 计算模型目录大小
        if command -v du &> /dev/null; then
            MODEL_SIZE=$(du -sh models 2>/dev/null | cut -f1)
            echo "  └─ 模型目录大小: $MODEL_SIZE"

            # 警告：如果模型太大
            MODEL_SIZE_MB=$(du -sm models 2>/dev/null | cut -f1)
            if [ "$MODEL_SIZE_MB" -gt 1000 ]; then
                echo -e "  └─ ${YELLOW}提示: 模型目录较大（${MODEL_SIZE}），传输可能需要较长时间${NC}"
            fi
        fi
    else
        echo -e "  └─ ${YELLOW}警告: models/ 目录为空${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠ models/ 目录不存在（推荐创建）${NC}"
    echo "  如果项目需要模型文件，请创建此目录"
    ((WARNINGS++))
fi
echo ""

# ==================== 检查Docker环境 ====================
echo -e "${GREEN}[3/5]${NC} 检查Docker环境..."
echo ""

# 检查Docker
if command -v docker &> /dev/null; then
    echo "✓ Docker已安装: $(docker --version)"

    # 检查Docker运行状态
    if docker info &> /dev/null; then
        echo "  └─ Docker服务运行中"

        # 检查是否有镜像
        if docker images pyt-backend:latest --format "{{.Repository}}" | grep -q "pyt-backend"; then
            echo "  └─ pyt-backend:latest 镜像已存在"
            IMAGE_SIZE=$(docker images pyt-backend:latest --format "{{.Size}}")
            echo "     镜像大小: $IMAGE_SIZE"
        else
            echo -e "  └─ ${YELLOW}pyt-backend:latest 镜像不存在（部署时会自动构建）${NC}"
        fi
    else
        echo -e "${RED}✗ Docker服务未运行${NC}"
        echo "  请启动Docker Desktop"
        ((ERRORS++))
    fi
else
    echo -e "${RED}✗ Docker未安装${NC}"
    echo "  请安装Docker Desktop"
    ((ERRORS++))
fi
echo ""

# ==================== 检查Registry配置 ====================
echo -e "${GREEN}[4/5]${NC} 检查Registry配置..."
echo ""

REGISTRY_URL="192.168.30.83:5433"

# 测试Registry连接
if curl -sf "http://${REGISTRY_URL}/v2/_catalog" &> /dev/null; then
    echo "✓ Registry可访问 (${REGISTRY_URL})"

    # 检查是否有推送的镜像
    if curl -sf "http://${REGISTRY_URL}/v2/pyt-backend/tags/list" | grep -q "tags"; then
        echo "  └─ pyt-backend 镜像已存在于Registry"
        TAGS=$(curl -sf "http://${REGISTRY_URL}/v2/pyt-backend/tags/list" | grep -o '"tags":\[[^]]*\]' || echo "无法获取")
        echo "     $TAGS"
    else
        echo "  └─ pyt-backend 镜像不存在于Registry（首次部署时会推送）"
    fi
else
    echo -e "${YELLOW}⚠ 无法连接到Registry (${REGISTRY_URL})${NC}"
    echo "  请检查:"
    echo "  1. Registry服务是否运行"
    echo "  2. 网络连接是否正常"
    echo "  3. Docker是否配置信任此Registry"
    echo ""
    echo "  macOS配置方法:"
    echo "  Docker Desktop → Preferences → Docker Engine"
    echo "  添加: \"insecure-registries\": [\"${REGISTRY_URL}\"]"
    ((WARNINGS++))
fi
echo ""

# ==================== 检查部署脚本 ====================
echo -e "${GREEN}[5/5]${NC} 检查部署脚本..."
echo ""

SCRIPTS=(
    "scripts/generate_production_config.sh"
    "scripts/quick_deploy.sh"
    "scripts/push_to_registry.sh"
    "scripts/deploy_from_registry.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "✓ $script (可执行)"
        else
            echo -e "${YELLOW}⚠ $script (不可执行)${NC}"
            echo "  运行: chmod +x $script"
            ((WARNINGS++))
        fi
    else
        echo -e "${RED}✗ $script (不存在)${NC}"
        ((ERRORS++))
    fi
done
echo ""

# ==================== 总结 ====================
echo "========================================================================="
echo -e "${BLUE}检查结果总结${NC}"
echo "========================================================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！可以开始部署！${NC}"
    echo ""
    echo "下一步:"
    echo "  bash scripts/quick_deploy.sh <服务器IP> ubuntu"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 检查完成，有 $WARNINGS 个警告${NC}"
    echo ""
    echo "可以继续部署，但建议先解决警告"
    echo ""
    echo "下一步:"
    echo "  bash scripts/quick_deploy.sh <服务器IP> ubuntu"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 检查失败！发现 $ERRORS 个错误，$WARNINGS 个警告${NC}"
    echo ""
    echo "请先解决上述错误，然后重新运行此脚本"
    echo ""
    echo "常见解决方案:"
    echo "  1. 生成配置: bash scripts/generate_production_config.sh"
    echo "  2. 创建config目录: mkdir -p config"
    echo "  3. 启动Docker: 打开Docker Desktop"
    echo "  4. 设置权限: chmod +x scripts/*.sh"
    echo ""
    exit 1
fi
