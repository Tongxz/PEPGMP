#!/bin/bash
# 阶段三灰度发布验证脚本
# 验证新接入的2个端点

BASE_URL="http://127.0.0.1:8000"
ROLLOUT_PERCENT=$1

echo "=========================================="
echo "阶段三灰度发布验证 - ROLLOUT_PERCENT=${ROLLOUT_PERCENT}%"
echo "=========================================="
echo ""

# 1. 统计摘要
echo "1. 测试 GET /api/v1/records/statistics/summary"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/records/statistics/summary?period=7d")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{period, cameras_count: (.cameras | keys | length), total: .total}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | head -c 200)"
fi
echo ""

# 2. 摄像头统计（带force_domain参数）
echo "2. 测试 GET /api/v1/records/statistics/cam0"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}/api/v1/records/statistics/cam0?period=7d")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | jq -c '{camera_id, period, statistics: .statistics.camera_info.id}' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "  ❌ 状态码: $HTTP_CODE"
    echo "  📄 响应: $(echo "$BODY" | head -c 200)"
fi
echo ""

echo "=========================================="
echo "验证完成"
echo "=========================================="
