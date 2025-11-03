#!/bin/bash
# 回滚机制验证脚本

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "回滚机制验证"
echo "========================================="
echo "BASE_URL: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local params=$3
    local description=$4
    
    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}测试: $description${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"
    
    if [ "$method" = "GET" ]; then
        if [ -n "$params" ]; then
            response=$(curl -s "$BASE_URL$endpoint?$params" 2>&1) || true
            code=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint?$params" 2>&1 | tail -n1) || echo "000"
        else
            response=$(curl -s "$BASE_URL$endpoint" 2>&1) || true
            code=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>&1 | tail -n1) || echo "000"
        fi
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$params" 2>&1) || true
        code=$(echo "$response" | tail -n1)
        response=$(echo "$response" | sed '$d')
    fi
    
    echo ""
    echo -n "  响应状态码 ... "
    if [ "$code" = "200" ] || [ "$code" = "201" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $code)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $code)"
        echo "    响应: $(echo "$response" | head -c 200)"
        ((FAILED++))
    fi
    
    echo ""
}

echo "检查后端服务..."
if ! curl -s "$BASE_URL/api/ping" > /dev/null 2>&1; then
    echo -e "${RED}✗ 后端服务未运行，请先启动后端${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 后端服务运行中${NC}"
echo ""

echo "----------------------------------------"
echo "1. 回滚方法一：force_domain=false 参数"
echo "----------------------------------------"
echo ""
echo "使用 force_domain=false 查询参数强制使用旧实现（即时生效）"
echo ""

# 测试告警规则列表（只读，安全）
test_endpoint "GET" "/api/v1/alerts/rules" "force_domain=false" "告警规则列表（旧实现）"

# 测试告警规则列表（新实现对比）
echo ""
echo "对比：新实现 (force_domain=true)"
test_endpoint "GET" "/api/v1/alerts/rules" "force_domain=true" "告警规则列表（新实现）"

echo ""
echo "----------------------------------------"
echo "2. 回滚方法二：USE_DOMAIN_SERVICE=false 环境变量"
echo "----------------------------------------"
echo ""
echo -e "${YELLOW}⚠ 注意: 此方法需要重启后端服务才能生效${NC}"
echo ""
echo "设置方法:"
echo "  export USE_DOMAIN_SERVICE=false"
echo "  export ROLLOUT_PERCENT=0"
echo "  # 然后重启后端服务"
echo ""

# 检查当前环境变量
echo "当前环境变量状态:"
if [ -n "$USE_DOMAIN_SERVICE" ]; then
    echo "  USE_DOMAIN_SERVICE: $USE_DOMAIN_SERVICE"
else
    echo "  USE_DOMAIN_SERVICE: 未设置（使用默认值）"
fi

if [ -n "$ROLLOUT_PERCENT" ]; then
    echo "  ROLLOUT_PERCENT: $ROLLOUT_PERCENT"
else
    echo "  ROLLOUT_PERCENT: 未设置（使用默认值）"
fi

echo ""
echo "----------------------------------------"
echo "3. 回滚验证检查清单"
echo "----------------------------------------"
echo ""
echo "回滚前检查:"
echo "  [ ] 确认旧实现正常工作"
echo "  [ ] 确认新实现正常工作"
echo "  [ ] 确认回滚方法可用"
echo "  [ ] 准备回滚脚本"
echo ""

echo "回滚步骤:"
echo "  1. 设置 USE_DOMAIN_SERVICE=false"
echo "  2. 设置 ROLLOUT_PERCENT=0"
echo "  3. 重启后端服务"
echo "  4. 验证所有端点使用旧实现"
echo "  5. 监控错误率和性能"
echo ""

echo "回滚后验证:"
echo "  [ ] 所有端点功能正常"
echo "  [ ] 响应格式一致"
echo "  [ ] 错误率正常"
echo "  [ ] 性能正常"
echo ""

echo "----------------------------------------"
echo "4. 快速回滚脚本"
echo "----------------------------------------"
echo ""

cat > /tmp/quick_rollback.sh << 'EOF'
#!/bin/bash
# 快速回滚脚本

echo "========================================="
echo "快速回滚到旧实现"
echo "========================================="
echo ""

# 设置环境变量
export USE_DOMAIN_SERVICE=false
export ROLLOUT_PERCENT=0

echo "环境变量已设置:"
echo "  USE_DOMAIN_SERVICE=false"
echo "  ROLLOUT_PERCENT=0"
echo ""
echo -e "${YELLOW}⚠ 警告: 请重启后端服务使配置生效${NC}"
echo ""
echo "重启后，所有端点将使用旧实现"
echo ""
EOF

chmod +x /tmp/quick_rollback.sh

echo -e "${GREEN}✓ 快速回滚脚本已生成: /tmp/quick_rollback.sh${NC}"
echo ""
echo "使用方法:"
echo "  source /tmp/quick_rollback.sh"
echo "  # 然后重启后端服务"
echo ""

echo "========================================="
echo "验证结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 回滚机制验证通过${NC}"
    echo ""
    echo "回滚方法:"
    echo "  1. 使用 force_domain=false 查询参数（即时生效）"
    echo "  2. 设置 USE_DOMAIN_SERVICE=false 并重启服务（全局生效）"
    exit 0
else
    echo -e "${RED}✗ 部分验证失败${NC}"
    exit 1
fi

