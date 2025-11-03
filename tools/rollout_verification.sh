#!/bin/bash
# 灰度发布验证脚本
# 验证7个重构端点的功能

BASE_URL="http://127.0.0.1:8000"
ROLLOUT_PERCENT=$1

echo "=========================================="
echo "灰度发布验证 - ROLLOUT_PERCENT=${ROLLOUT_PERCENT}%"
echo "=========================================="
echo ""

# 1. 检测记录列表
echo "1. 测试 GET /api/v1/records/detection-records/cam0"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/records/detection-records/cam0?limit=10&offset=0")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{records_count: .records | length, total: .total}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 2. 违规详情
echo "2. 测试 GET /api/v1/records/violations/1"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/records/violations/1")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    echo "  ✅ 状态码: $HTTP_CODE (404表示记录不存在，正常)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 3. 按天统计
echo "3. 测试 GET /api/v1/statistics/daily"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/statistics/daily?days=7")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c 'length' 2>/dev/null || echo "$BODY" | head -c 50) 天数据"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 4. 事件列表
echo "4. 测试 GET /api/v1/statistics/events"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/statistics/events?limit=10")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{events_count: .events | length, total: .total}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 5. 近期历史
echo "5. 测试 GET /api/v1/statistics/history"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/statistics/history?minutes=60&limit=10")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c 'length' 2>/dev/null || echo "$BODY" | head -c 50) 条记录"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 6. 摄像头列表
echo "6. 测试 GET /api/v1/cameras"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/cameras")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{cameras_count: .cameras | length}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

# 7. 摄像头统计
echo "7. 测试 GET /api/v1/cameras/cam0/stats"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/cameras/cam0/stats")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{camera_id: .camera_id, running: .running}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
fi
echo ""

echo "=========================================="
echo "验证完成"
echo "=========================================="

