#!/bin/bash
# 完整集成测试脚本

set -e

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TIMEOUT=30

echo "=========================================="
echo "完整集成测试"
echo "=========================================="
echo "测试目标: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL=0
PASSED=0
FAILED=0

# 测试函数
test_endpoint() {
    local method=$1
    local path=$2
    local name=$3
    local params=$4
    local expected_status=${5:-200}

    TOTAL=$((TOTAL + 1))

    echo -n "测试 $TOTAL: $name ... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$path?$params" --max-time $TIMEOUT 2>&1)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$path?$params" \
            -H "Content-Type: application/json" \
            -d "$6" --max-time $TIMEOUT 2>&1)
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$path?$params" \
            -H "Content-Type: application/json" \
            -d "$6" --max-time $TIMEOUT 2>&1)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$path?$params" --max-time $TIMEOUT 2>&1)
    else
        echo -e "${RED}❌ 不支持的HTTP方法: $method${NC}"
        FAILED=$((FAILED + 1))
        return
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ 通过${NC} (状态码: $http_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ 失败${NC} (状态码: $http_code, 期望: $expected_status)"
        echo "   响应: $(echo "$body" | head -c 100)"
        FAILED=$((FAILED + 1))
    fi
}

# ========== 读操作端点 ==========
echo "========== 读操作端点 =========="

test_endpoint "GET" "/api/v1/records/statistics/summary" \
    "获取统计摘要" "period=7d"

test_endpoint "GET" "/api/v1/records/violations" \
    "获取违规记录列表" "limit=10"

test_endpoint "GET" "/api/v1/records/violations/1" \
    "获取违规详情" ""

test_endpoint "GET" "/api/v1/records/statistics/cam0" \
    "获取摄像头统计" ""

test_endpoint "GET" "/api/v1/records/detection-records/cam0" \
    "获取检测记录" "limit=10"

test_endpoint "GET" "/api/v1/statistics/daily" \
    "获取日统计" "days=7"

test_endpoint "GET" "/api/v1/statistics/events" \
    "获取事件历史" "limit=10"

test_endpoint "GET" "/api/v1/statistics/history" \
    "获取历史统计" "period=7d"

test_endpoint "GET" "/api/v1/cameras" \
    "获取摄像头列表" ""

test_endpoint "GET" "/api/v1/cameras/cam0/stats" \
    "获取摄像头统计详情" ""

test_endpoint "GET" "/api/v1/events/recent" \
    "获取最近事件" "limit=10"

test_endpoint "GET" "/api/v1/statistics/realtime" \
    "获取实时统计" ""

test_endpoint "GET" "/api/v1/system/info" \
    "获取系统信息" ""

test_endpoint "GET" "/api/v1/alerts/history-db" \
    "获取告警历史" "limit=10"

test_endpoint "GET" "/api/v1/alerts/rules" \
    "获取告警规则列表" ""

test_endpoint "GET" "/api/v1/monitoring/health" \
    "健康检查" ""

test_endpoint "GET" "/api/v1/monitoring/metrics" \
    "获取监控指标" ""

# ========== 写操作端点 ==========
echo ""
echo "========== 写操作端点 =========="

test_endpoint "PUT" "/api/v1/records/violations/1/status" \
    "更新违规状态" "status=confirmed&notes=集成测试" "200"

test_endpoint "POST" "/api/v1/cameras" \
    "创建摄像头" "" "200" \
    '{"id":"test_camera_integration","name":"集成测试摄像头","source":"rtsp://test.example.com/stream","location":"测试位置","active":true}'

test_endpoint "PUT" "/api/v1/cameras/test_camera_integration" \
    "更新摄像头" "" "200" \
    '{"name":"更新后的摄像头名称"}'

test_endpoint "POST" "/api/v1/alerts/rules" \
    "创建告警规则" "" "200" \
    '{"name":"集成测试规则","rule_type":"violation","conditions":{"threshold":5},"enabled":true}'

# ========== 领域服务验证 ==========
echo ""
echo "========== 领域服务验证 =========="

test_endpoint "GET" "/api/v1/records/violations" \
    "违规记录列表（领域服务）" "limit=10&force_domain=true"

test_endpoint "GET" "/api/v1/statistics/summary" \
    "统计摘要（领域服务）" "period=7d&force_domain=true"

test_endpoint "GET" "/api/v1/cameras" \
    "摄像头列表（领域服务）" "force_domain=true"

# ========== 打印摘要 ==========
echo ""
echo "=========================================="
echo "测试摘要"
echo "=========================================="
echo "总测试数: $TOTAL"
echo -e "${GREEN}通过: $PASSED ✅${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}失败: $FAILED ❌${NC}"
else
    echo "失败: $FAILED"
fi

if [ $TOTAL -gt 0 ]; then
    pass_rate=$(echo "scale=2; $PASSED * 100 / $TOTAL" | bc)
    echo "通过率: ${pass_rate}%"
fi

echo "=========================================="

# 退出码
if [ $FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
