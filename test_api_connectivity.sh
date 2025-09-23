#!/bin/bash

echo "=== API连通性测试 ==="
echo

BASE_URL="http://localhost:8000"

# 测试系统健康状态
echo "1. 测试系统健康状态..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/system/health" | head -1
echo

# 测试摄像头接口
echo "2. 测试摄像头接口..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/cameras" | head -1
echo

# 测试区域管理接口
echo "3. 测试区域管理接口..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/management/regions" | head -1
echo

# 测试统计摘要接口
echo "4. 测试统计摘要接口..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/statistics/summary" | head -1
echo

# 测试每日统计接口
echo "5. 测试每日统计接口..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/statistics/daily" | head -1
echo

# 测试事件接口
echo "6. 测试事件接口..."
curl -s -w "状态码: %{http_code}\n" "$BASE_URL/api/v1/statistics/events" | head -1
echo

echo "=== 测试完成 ==="
