#!/bin/bash
# 灰度发布准备检查清单

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "灰度发布准备检查清单"
echo "========================================="
echo "BASE_URL: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计
PASSED=0
FAILED=0

# 检查函数
check_item() {
    local description=$1
    local command=$2
    
    echo -n "检查: $description ... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "----------------------------------------"
echo "1. 服务健康检查"
echo "----------------------------------------"

# 检查后端服务是否运行
check_item "后端服务运行中" "curl -s $BASE_URL/api/ping | grep -q pong"

# 检查健康检查端点
check_item "健康检查端点可用" "curl -s $BASE_URL/api/v1/monitoring/health | grep -q 'status\|healthy'"

# 检查监控指标端点
check_item "监控指标端点可用" "curl -s $BASE_URL/api/v1/monitoring/metrics | grep -q 'requests\|response_time'"

echo ""
echo "----------------------------------------"
echo "2. 端点功能检查"
echo "----------------------------------------"

# 检查告警规则端点
check_item "告警规则列表端点" "curl -s $BASE_URL/api/v1/alerts/rules | grep -q 'items\|count'"

# 检查摄像头端点（如果有摄像头数据）
cameras_response=$(curl -s "$BASE_URL/api/v1/cameras" 2>&1) || true
camera_id=$(echo "$cameras_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -n "$camera_id" ]; then
    check_item "摄像头状态端点" "curl -s $BASE_URL/api/v1/cameras/$camera_id/status | grep -q 'running\|pid'"
else
    echo -e "${YELLOW}⚠ 未找到摄像头，跳过摄像头端点检查${NC}"
fi

echo ""
echo "----------------------------------------"
echo "3. 灰度开关检查"
echo "----------------------------------------"

# 检查 force_domain 参数
check_item "force_domain=true 参数工作" \
    "curl -s '$BASE_URL/api/v1/alerts/rules?force_domain=true' | grep -q 'items\|count'"

check_item "force_domain=false 参数工作" \
    "curl -s '$BASE_URL/api/v1/alerts/rules?force_domain=false' | grep -q 'items\|count'"

# 检查环境变量（提示）
echo ""
echo "环境变量检查（需要手动验证）:"
echo "  USE_DOMAIN_SERVICE: ${USE_DOMAIN_SERVICE:-未设置}"
echo "  ROLLOUT_PERCENT: ${ROLLOUT_PERCENT:-未设置}"
echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  - 如需启用灰度发布，设置 USE_DOMAIN_SERVICE=true"
echo "  - 如需控制灰度比例，设置 ROLLOUT_PERCENT=10（10%）"
echo "  - 重启后端服务后生效"

echo ""
echo "----------------------------------------"
echo "4. 回滚机制检查"
echo "----------------------------------------"

# 检查回滚能力（设置 force_domain=false 应该使用旧实现）
check_item "回滚机制可用 (force_domain=false)" \
    "curl -s '$BASE_URL/api/v1/alerts/rules?force_domain=false' | grep -q 'items\|count'"

echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  - 回滚方法：设置 USE_DOMAIN_SERVICE=false 并重启服务"
echo "  - 或者：使用 force_domain=false 查询参数强制使用旧实现"

echo ""
echo "----------------------------------------"
echo "5. 监控端点检查"
echo "----------------------------------------"

# 检查监控端点
check_item "健康检查端点" \
    "curl -s $BASE_URL/monitoring/health | grep -q 'status\|healthy'"

check_item "监控指标端点" \
    "curl -s $BASE_URL/monitoring/metrics | grep -q 'requests\|response_time'"

echo ""
echo "========================================="
echo "检查结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过，可以开始灰度发布${NC}"
    echo ""
    echo "建议下一步："
    echo "  1. 设置 USE_DOMAIN_SERVICE=true"
    echo "  2. 设置 ROLLOUT_PERCENT=10（10%灰度）"
    echo "  3. 重启后端服务"
    echo "  4. 观察1-2天后提升到25%"
    exit 0
else
    echo -e "${RED}✗ 部分检查失败，请修复后再开始灰度发布${NC}"
    exit 1
fi

