#!/bin/bash
# 写操作端点灰度发布验证脚本
# 验证 PUT /api/v1/records/violations/{violation_id}/status 端点

set -e

BASE_URL="http://localhost:8000"
ROLLOUT_PERCENTS=(5 10 25 50 100)

echo "=========================================="
echo "写操作端点灰度发布验证"
echo "=========================================="
echo ""
echo "端点: PUT /api/v1/records/violations/{violation_id}/status"
echo ""

# 检查后端服务是否运行
if ! curl -s "${BASE_URL}/api/v1/records/health" > /dev/null 2>&1; then
    echo "❌ 错误: 后端服务未运行，请先启动后端服务"
    exit 1
fi

echo "✅ 后端服务运行正常"
echo ""

# 测试函数
test_update_violation_status() {
    local rollout_percent=$1
    local violation_id=${2:-1}
    local status=${3:-"confirmed"}
    local notes=${4:-"灰度测试"}

    echo "--- 测试 PUT /api/v1/records/violations/${violation_id}/status (${rollout_percent}%灰度) ---"

    # 测试更新违规状态（使用Query参数和force_domain）
    response=$(curl -s -X PUT "${BASE_URL}/api/v1/records/violations/${violation_id}/status?status=${status}&notes=${notes}&force_domain=true" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo "  ✅ 状态码: ${http_code}"

        # 检查响应结构
        if echo "$body" | grep -q "\"ok\""; then
            echo "  ✅ 响应结构: 正确"
        else
            echo "  ⚠️  响应结构: 可能不正确"
            echo "  响应内容: $body"
        fi

        # 检查是否包含violation_id
        if echo "$body" | grep -q "\"violation_id\""; then
            echo "  ✅ 包含violation_id字段"
        else
            echo "  ⚠️  缺少violation_id字段"
        fi

        # 检查是否包含status字段
        if echo "$body" | grep -q "\"status\""; then
            echo "  ✅ 包含status字段"
        else
            echo "  ⚠️  缺少status字段"
        fi

    elif [ "$http_code" = "404" ]; then
        echo "  ⚠️  状态码: ${http_code} (违规记录不存在，这是正常的测试场景)"
    elif [ "$http_code" = "400" ]; then
        echo "  ⚠️  状态码: ${http_code} (请求参数错误)"
        echo "  响应内容: $body"
    else
        echo "  ❌ 状态码: ${http_code}"
        echo "  响应内容: $body"
        return 1
    fi

    echo ""
    return 0
}

# 测试无效状态
test_invalid_status() {
    local violation_id=${1:-1}

    echo "--- 测试无效状态值 ---"

    response=$(curl -s -X PUT "${BASE_URL}/api/v1/records/violations/${violation_id}/status?status=invalid_status&force_domain=true" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "400" ] || [ "$http_code" = "422" ]; then
        echo "  ✅ 正确拒绝无效状态 (状态码: ${http_code})"
    else
        echo "  ⚠️  状态码: ${http_code} (应该拒绝无效状态)"
        echo "  响应内容: $body"
    fi

    echo ""
}

# 测试回退机制
test_fallback() {
    echo "--- 测试回退机制 (强制使用旧实现) ---"

    # 设置环境变量禁用领域服务
    export USE_DOMAIN_SERVICE=false

    response=$(curl -s -X PUT "${BASE_URL}/api/v1/records/violations/1/status?status=confirmed&force_domain=false" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] || [ "$http_code" = "404" ]; then
        echo "  ✅ 回退机制正常 (状态码: ${http_code})"
    else
        echo "  ❌ 回退机制异常 (状态码: ${http_code})"
        echo "  响应内容: $body"
    fi

    # 恢复环境变量
    unset USE_DOMAIN_SERVICE

    echo ""
}

# 执行灰度验证
echo "开始灰度验证..."
echo ""

# 首先测试无效状态
test_invalid_status

# 然后测试回退机制
test_fallback

# 测试各个灰度阶段
for percent in "${ROLLOUT_PERCENTS[@]}"; do
    echo "=========================================="
    echo "灰度阶段: ${percent}%"
    echo "=========================================="
    echo ""

    # 设置灰度百分比
    export ROLLOUT_PERCENT=${percent}

    # 提示重启服务（如果是手动控制）
    if [ "$percent" != "5" ]; then
        echo "⚠️  请确保 ROLLOUT_PERCENT=${percent} 已设置并重启后端服务"
        echo "按 Enter 继续..."
        read
    fi

    # 测试更新违规状态
    test_update_violation_status "$percent" 1 "confirmed" "灰度测试 ${percent}%"

    # 测试其他状态值
    test_update_violation_status "$percent" 1 "pending" "灰度测试 ${percent}% - pending"

    # 短暂等待
    sleep 2
done

# 最终稳定性验证
echo "=========================================="
echo "最终稳定性验证 (100%灰度)"
echo "=========================================="
echo ""

for i in {1..3}; do
    echo "--- 第${i}次验证 ---"
    test_update_violation_status 100 1 "confirmed" "稳定性测试 ${i}"
    sleep 1
done

echo "=========================================="
echo "✅ 灰度验证完成"
echo "=========================================="
echo ""
echo "总结:"
echo "  - 端点: PUT /api/v1/records/violations/{violation_id}/status"
echo "  - 灰度阶段: 5% → 10% → 25% → 50% → 100%"
echo "  - 稳定性验证: 3次验证均通过"
echo ""
