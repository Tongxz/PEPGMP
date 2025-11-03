#!/bin/bash
# 阶段二灰度发布验证脚本
# 验证新重构的2个端点

BASE_URL="http://127.0.0.1:8000"
ROLLOUT_PERCENT=$1

echo "=========================================="
echo "阶段二灰度发布验证 - ROLLOUT_PERCENT=${ROLLOUT_PERCENT}%"
echo "=========================================="
echo ""

# 1. 最近事件列表
echo "1. 测试 GET /api/v1/events/recent"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/events/recent?limit=10&minutes=60")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c 'length' 2>/dev/null || echo "$BODY" | head -c 50) 条事件"
else
    echo "  ❌ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | head -c 200)"
fi
echo ""

# 2. 实时统计接口
echo "2. 测试 GET /api/v1/statistics/realtime"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/statistics/realtime")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{timestamp, system_status, detection_stats: .detection_stats.total_detections_today}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | head -c 200)"
fi
echo ""

echo "=========================================="
echo "验证完成"
echo "=========================================="
