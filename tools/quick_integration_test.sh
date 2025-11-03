#!/bin/bash
# 快速集成测试 - 验证新集成的端点

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "快速集成测试 - 新端点验证"
echo "========================================="
echo "BASE_URL: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查服务是否运行
echo "检查后端服务..."
if ! curl -s "$BASE_URL/api/ping" > /dev/null 2>&1; then
    echo -e "${RED}✗ 后端服务未运行，请先启动后端${NC}"
    echo "启动命令示例:"
    echo "  cd /Users/zhou/Code/Pyt && source venv/bin/activate && export DATABASE_URL=\"postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development\" && python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload"
    exit 1
fi
echo -e "${GREEN}✓ 后端服务运行中${NC}"
echo ""

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
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>&1) || true
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=true" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint?force_domain=true" 2>&1) || true
        fi
    elif [ "$method" = "PUT" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=true" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1) || true
        else
            response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint?force_domain=true" 2>&1) || true
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
        if [ -n "$body" ]; then
            echo "  响应: $(echo "$body" | head -c 100)"
        fi
        ((FAILED++))
        return 1
    fi
}

echo "----------------------------------------"
echo "1. 告警规则写操作端点"
echo "----------------------------------------"

# 测试创建告警规则
test_endpoint "POST" "/api/v1/alerts/rules" \
    '{"name":"测试规则_'"$(date +%s)"'","rule_type":"violation","conditions":{"threshold":5}}' \
    "200" \
    "创建告警规则"

# 获取刚创建的规则ID（如果有返回）
if [ $? -eq 0 ]; then
    # 尝试从响应中提取规则ID
    rule_id=$(echo "$body" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2 || echo "")
    if [ -n "$rule_id" ] && [ "$rule_id" != "" ]; then
        echo "  创建的规则ID: $rule_id"
        
        # 测试更新告警规则
        echo ""
        test_endpoint "PUT" "/api/v1/alerts/rules/$rule_id" \
            '{"enabled":false}' \
            "200" \
            "更新告警规则"
    else
        echo -e "${YELLOW}⚠ 无法提取规则ID，跳过更新测试${NC}"
    fi
fi

echo ""
echo "----------------------------------------"
echo "2. 摄像头操作端点（只读操作）"
echo "----------------------------------------"

# 获取第一个摄像头ID（用于测试）
echo ""
echo "获取摄像头列表..."
cameras_response=$(curl -s "$BASE_URL/api/v1/cameras?force_domain=true" 2>&1) || true
camera_id=$(echo "$cameras_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -z "$camera_id" ]; then
    echo -e "${YELLOW}⚠ 未找到摄像头，跳过摄像头操作测试${NC}"
else
    echo "  使用摄像头ID: $camera_id"
    
    # 测试获取摄像头状态（只读，安全）
    echo ""
    test_endpoint "GET" "/api/v1/cameras/$camera_id/status?force_domain=true" "" "200" "获取摄像头状态"
    
    # 测试批量状态查询
    echo ""
    test_endpoint "POST" "/api/v1/cameras/batch-status?force_domain=true" \
        "{\"camera_ids\":[\"$camera_id\"]}" \
        "200" \
        "批量查询摄像头状态"
    
    # 测试刷新所有摄像头
    echo ""
    test_endpoint "POST" "/api/v1/cameras/refresh?force_domain=true" "" "200" "刷新所有摄像头"
    
    echo ""
    echo -e "${YELLOW}⚠ 以下操作会实际控制摄像头，已跳过：${NC}"
    echo -e "${YELLOW}   - 启动/停止/重启摄像头${NC}"
    echo -e "${YELLOW}   - 激活/停用摄像头${NC}"
    echo -e "${YELLOW}   - 切换自动启动${NC}"
    echo -e "${YELLOW}   - 获取日志${NC}"
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

