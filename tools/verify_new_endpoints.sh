#!/bin/bash
# 验证新集成的端点功能
# 包括：告警规则写操作和摄像头操作端点

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
FORCE_DOMAIN="${FORCE_DOMAIN:-true}"

echo "========================================="
echo "新端点功能验证"
echo "========================================="
echo "BASE_URL: $BASE_URL"
echo "FORCE_DOMAIN: $FORCE_DOMAIN"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    
    echo -n "测试: $description ... "
    
    if [ "$method" = "GET" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint?$data" 2>&1) || true
        else
            response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>&1) || true
        fi
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=$FORCE_DOMAIN" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=$FORCE_DOMAIN" 2>&1) || true
        fi
    elif [ "$method" = "PUT" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=$FORCE_DOMAIN" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=$FORCE_DOMAIN" 2>&1) || true
        fi
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (期望 HTTP $expected_status, 实际 HTTP $http_code)"
        echo "  响应: $body"
        ((FAILED++))
        return 1
    fi
}

echo "----------------------------------------"
echo "1. 告警规则写操作端点"
echo "----------------------------------------"

# 测试创建告警规则
echo ""
test_endpoint "POST" "/api/v1/alerts/rules" \
    '{"name":"测试规则","rule_type":"violation","conditions":{"threshold":5}}' \
    "200" \
    "创建告警规则"

# 获取刚创建的规则ID（如果有返回）
if [ $? -eq 0 ]; then
    rule_id=$(echo "$body" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    if [ -n "$rule_id" ]; then
        echo "  创建的规则ID: $rule_id"
        
        # 测试更新告警规则
        echo ""
        test_endpoint "PUT" "/api/v1/alerts/rules/$rule_id" \
            '{"enabled":false}' \
            "200" \
            "更新告警规则"
    fi
fi

echo ""
echo "----------------------------------------"
echo "2. 摄像头操作端点"
echo "----------------------------------------"

# 获取第一个摄像头ID（用于测试）
echo ""
echo "获取摄像头列表..."
cameras_response=$(curl -s "$BASE_URL/api/v1/cameras" 2>&1) || true
camera_id=$(echo "$cameras_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$camera_id" ]; then
    echo -e "${YELLOW}⚠ 警告: 未找到摄像头，跳过摄像头操作测试${NC}"
else
    echo "  使用摄像头ID: $camera_id"
    
    # 测试获取摄像头状态
    echo ""
    test_endpoint "GET" "/api/v1/cameras/$camera_id/status" "force_domain=$FORCE_DOMAIN" "200" "获取摄像头状态"
    
    # 测试批量状态查询
    echo ""
    test_endpoint "POST" "/api/v1/cameras/batch-status" \
        "{\"camera_ids\":[\"$camera_id\"]}" \
        "200" \
        "批量查询摄像头状态"
    
    # 测试获取摄像头日志
    echo ""
    test_endpoint "GET" "/api/v1/cameras/$camera_id/logs" "lines=10&force_domain=$FORCE_DOMAIN" "200" "获取摄像头日志"
    
    # 测试刷新所有摄像头
    echo ""
    test_endpoint "POST" "/api/v1/cameras/refresh" "" "200" "刷新所有摄像头"
    
    echo ""
    echo -e "${YELLOW}⚠ 注意: 以下操作会实际控制摄像头，请谨慎测试${NC}"
    echo -e "${YELLOW}   - 启动/停止/重启摄像头${NC}"
    echo -e "${YELLOW}   - 激活/停用摄像头${NC}"
    echo -e "${YELLOW}   - 切换自动启动${NC}"
    
    read -p "是否继续测试摄像头控制操作? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 测试激活摄像头（相对安全）
        echo ""
        test_endpoint "POST" "/api/v1/cameras/$camera_id/activate" "" "200" "激活摄像头"
        
        # 测试切换自动启动
        echo ""
        test_endpoint "PUT" "/api/v1/cameras/$camera_id/auto-start" "auto_start=false" "200" "切换自动启动"
        
        # 测试停用摄像头
        echo ""
        test_endpoint "POST" "/api/v1/cameras/$camera_id/deactivate" "" "200" "停用摄像头"
    fi
fi

echo ""
echo "========================================="
echo "测试结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败${NC}"
    exit 1
fi

