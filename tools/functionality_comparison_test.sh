#!/bin/bash
# 功能对比测试 - 对比新旧实现的行为一致性

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "功能对比测试 - 新旧实现行为一致性验证"
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
SKIPPED=0

# 测试函数
compare_endpoints() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    echo -e "${BLUE}----------------------------------------${NC}"
    echo -e "${BLUE}测试: $description${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"

    # 测试新实现（force_domain=true）
    echo ""
    echo -n "  新实现 (force_domain=true) ... "
    if [ "$method" = "GET" ]; then
        if [ -n "$data" ]; then
            new_response=$(curl -s "$BASE_URL$endpoint?force_domain=true&$data" 2>&1) || true
        else
            new_response=$(curl -s "$BASE_URL$endpoint?force_domain=true" 2>&1) || true
        fi
        new_code=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint?force_domain=true" 2>&1 | tail -n1) || echo "000"
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            new_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=true" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            new_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=true" 2>&1) || true
        fi
        new_code=$(echo "$new_response" | tail -n1)
        new_response=$(echo "$new_response" | sed '$d')
    elif [ "$method" = "PUT" ]; then
        if [ -n "$data" ]; then
            new_response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=true" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            new_response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=true" 2>&1) || true
        fi
        new_code=$(echo "$new_response" | tail -n1)
        new_response=$(echo "$new_response" | sed '$d')
    fi

    if [ "$new_code" = "200" ] || [ "$new_code" = "201" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $new_code)"
    else
        echo -e "${YELLOW}⚠ HTTP $new_code${NC}"
        echo "    响应: $(echo "$new_response" | head -c 100)"
    fi

    # 测试旧实现（force_domain=false）
    echo ""
    echo -n "  旧实现 (force_domain=false) ... "
    if [ "$method" = "GET" ]; then
        if [ -n "$data" ]; then
            old_response=$(curl -s "$BASE_URL$endpoint?force_domain=false&$data" 2>&1) || true
        else
            old_response=$(curl -s "$BASE_URL$endpoint?force_domain=false" 2>&1) || true
        fi
        old_code=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint?force_domain=false" 2>&1 | tail -n1) || echo "000"
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            old_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=false" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            old_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=false" 2>&1) || true
        fi
        old_code=$(echo "$old_response" | tail -n1)
        old_response=$(echo "$old_response" | sed '$d')
    elif [ "$method" = "PUT" ]; then
        if [ -n "$data" ]; then
            old_response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=false" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            old_response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=false" 2>&1) || true
        fi
        old_code=$(echo "$old_response" | tail -n1)
        old_response=$(echo "$old_response" | sed '$d')
    fi

    if [ "$old_code" = "200" ] || [ "$old_code" = "201" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $old_code)"
    else
        echo -e "${YELLOW}⚠ HTTP $old_code${NC}"
        echo "    响应: $(echo "$old_response" | head -c 100)"
    fi

    # 对比结果
    echo ""
    echo -n "  对比结果 ... "
    if [ "$new_code" = "$old_code" ]; then
        echo -e "${GREEN}✓ 状态码一致${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 状态码不一致 (新: $new_code, 旧: $old_code)${NC}"
        ((FAILED++))
    fi

    # 如果都是成功，简单对比响应结构（只对比关键字段）
    if [ "$new_code" = "200" ] && [ "$old_code" = "200" ]; then
        # 简单检查：如果响应都包含 "ok" 或 "count" 或 "items"，认为结构可能一致
        new_has_key=$(echo "$new_response" | grep -o '"ok"\|"count"\|"items"\|"status"' | head -1 || echo "")
        old_has_key=$(echo "$old_response" | grep -o '"ok"\|"count"\|"items"\|"status"' | head -1 || echo "")

        if [ -n "$new_has_key" ] && [ -n "$old_has_key" ]; then
            echo -e "  ${GREEN}✓ 响应结构基本一致${NC}"
        else
            echo -e "  ${YELLOW}⚠ 响应结构可能不同（需人工检查）${NC}"
        fi
    fi

    echo ""
}

# 检查服务是否运行
echo "检查后端服务..."
if ! curl -s "$BASE_URL/api/ping" > /dev/null 2>&1; then
    echo -e "${RED}✗ 后端服务未运行，请先启动后端${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 后端服务运行中${NC}"
echo ""

echo "----------------------------------------"
echo "1. 告警规则写操作端点对比"
echo "----------------------------------------"

# 创建一个测试规则用于更新测试
echo "创建测试规则用于更新测试..."
create_response=$(curl -s -X POST "$BASE_URL/api/v1/alerts/rules?force_domain=true" \
    -H "Content-Type: application/json" \
    -d '{"name":"对比测试规则_'"$(date +%s)"'","rule_type":"violation","conditions":{"threshold":5}}' 2>&1) || true

rule_id=$(echo "$create_response" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2 || echo "")

if [ -n "$rule_id" ] && [ "$rule_id" != "" ]; then
    echo "  创建的规则ID: $rule_id"
    echo ""

    # 对比创建告警规则
    compare_endpoints "POST" "/api/v1/alerts/rules" \
        '{"name":"对比测试规则_'"$(date +%s)"'","rule_type":"violation","conditions":{"threshold":5}}' \
        "创建告警规则"

    # 对比更新告警规则
    if [ -n "$rule_id" ]; then
        compare_endpoints "PUT" "/api/v1/alerts/rules/$rule_id" \
            '{"enabled":false}' \
            "更新告警规则"
    fi
else
    echo -e "${YELLOW}⚠ 无法创建测试规则，跳过告警规则端点对比${NC}"
    ((SKIPPED++))
fi

echo ""
echo "----------------------------------------"
echo "2. 摄像头操作端点对比（只读操作）"
echo "----------------------------------------"

# 获取第一个摄像头ID（用于测试）
echo ""
echo "获取摄像头列表..."
cameras_response=$(curl -s "$BASE_URL/api/v1/cameras?force_domain=true" 2>&1) || true
camera_id=$(echo "$cameras_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -z "$camera_id" ]; then
    echo -e "${YELLOW}⚠ 未找到摄像头，跳过摄像头操作端点对比${NC}"
    ((SKIPPED++))
else
    echo "  使用摄像头ID: $camera_id"
    echo ""

    # 对比获取摄像头状态（只读，安全）
    compare_endpoints "GET" "/api/v1/cameras/$camera_id/status" "" "获取摄像头状态"

    # 对比批量状态查询
    compare_endpoints "POST" "/api/v1/cameras/batch-status" \
        "{\"camera_ids\":[\"$camera_id\"]}" \
        "批量查询摄像头状态"

    echo ""
    echo -e "${YELLOW}⚠ 以下操作会实际控制摄像头，已跳过：${NC}"
    echo -e "${YELLOW}   - 启动/停止/重启摄像头${NC}"
    echo -e "${YELLOW}   - 激活/停用摄像头${NC}"
    echo -e "${YELLOW}   - 切换自动启动${NC}"
    echo -e "${YELLOW}   - 获取日志${NC}"
    ((SKIPPED++))
fi

echo ""
echo "----------------------------------------"
echo "3. 灰度开关验证"
echo "----------------------------------------"

echo ""
echo "测试灰度开关功能..."

# 测试 USE_DOMAIN_SERVICE 环境变量（需要重启服务才能生效，这里只做检查）
echo ""
echo -n "  检查 USE_DOMAIN_SERVICE 环境变量 ... "
if [ -n "$USE_DOMAIN_SERVICE" ]; then
    echo -e "${GREEN}✓ 已设置: $USE_DOMAIN_SERVICE${NC}"
else
    echo -e "${YELLOW}⚠ 未设置（默认值会生效）${NC}"
fi

echo ""
echo -n "  检查 ROLLOUT_PERCENT 环境变量 ... "
if [ -n "$ROLLOUT_PERCENT" ]; then
    echo -e "${GREEN}✓ 已设置: $ROLLOUT_PERCENT${NC}"
else
    echo -e "${YELLOW}⚠ 未设置（默认值会生效）${NC}"
fi

# 测试 force_domain 查询参数
echo ""
echo "  测试 force_domain=true 参数 ..."
test_response=$(curl -s "$BASE_URL/api/v1/alerts/rules?force_domain=true" 2>&1) || true
if echo "$test_response" | grep -q "items\|count"; then
    echo -e "    ${GREEN}✓ force_domain=true 正常工作${NC}"
else
    echo -e "    ${YELLOW}⚠ force_domain=true 响应异常${NC}"
fi

echo ""
echo "  测试 force_domain=false 参数 ..."
test_response=$(curl -s "$BASE_URL/api/v1/alerts/rules?force_domain=false" 2>&1) || true
if echo "$test_response" | grep -q "items\|count"; then
    echo -e "    ${GREEN}✓ force_domain=false 正常工作${NC}"
else
    echo -e "    ${YELLOW}⚠ force_domain=false 响应异常${NC}"
fi

echo ""
echo "========================================="
echo "测试结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo -e "${YELLOW}跳过: $SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有对比测试通过${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分对比测试失败${NC}"
    exit 1
fi
