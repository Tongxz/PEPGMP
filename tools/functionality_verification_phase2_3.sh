#!/bin/bash

# 脚本名称
SCRIPT_NAME="阶段二和阶段三接口功能验证"

# 后端服务URL
BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查后端服务是否运行
check_backend_status() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")
    if [ "$response" -eq 200 ]; then
        echo -e "${GREEN}✅ 后端服务运行正常${NC}"
        return 0
    else
        echo -e "${RED}❌ 后端服务未运行或不可达 (HTTP状态码: $response)${NC}"
        return 1
    fi
}

# 测试系统信息接口
test_system_info() {
    echo "--- 测试 GET /api/v1/system/info ---"
    
    # 测试默认（可能走旧实现）
    response=$(curl -s "${BASE_URL}/api/v1/system/info" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 检查响应结构
        if echo "$body" | jq -e '.timestamp' > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 响应结构: 正确${NC}"
        else
            echo -e "  ${YELLOW}⚠️  响应结构: 可能不正确${NC}"
        fi
        
        # 测试强制使用领域服务
        response_domain=$(curl -s "${BASE_URL}/api/v1/system/info?force_domain=true" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            return 1
        fi
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        return 1
    fi
}

# 测试告警历史接口
test_alert_history() {
    echo "--- 测试 GET /api/v1/alerts/history-db ---"
    
    # 测试默认
    response=$(curl -s "${BASE_URL}/api/v1/alerts/history-db?limit=10" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 检查响应结构
        if echo "$body" | jq -e '.count' > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 响应结构: 正确${NC}"
        else
            echo -e "  ${YELLOW}⚠️  响应结构: 可能不正确${NC}"
        fi
        
        # 测试强制使用领域服务
        response_domain=$(curl -s "${BASE_URL}/api/v1/alerts/history-db?limit=10&force_domain=true" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            return 1
        fi
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        return 1
    fi
}

# 测试告警规则接口
test_alert_rules() {
    echo "--- 测试 GET /api/v1/alerts/rules ---"
    
    # 测试默认
    response=$(curl -s "${BASE_URL}/api/v1/alerts/rules" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 检查响应结构
        if echo "$body" | jq -e '.count' > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 响应结构: 正确${NC}"
        else
            echo -e "  ${YELLOW}⚠️  响应结构: 可能不正确${NC}"
        fi
        
        # 测试强制使用领域服务
        response_domain=$(curl -s "${BASE_URL}/api/v1/alerts/rules?force_domain=true" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            return 1
        fi
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        return 1
    fi
}

# 测试创建摄像头接口（写操作，需要谨慎）
test_create_camera() {
    echo "--- 测试 POST /api/v1/cameras ---"
    
    # 生成唯一的摄像头ID
    TEST_CAMERA_ID="test_cam_$(date +%s)"
    
    # 测试数据
    payload=$(cat <<EOF
{
  "id": "${TEST_CAMERA_ID}",
  "name": "测试摄像头",
  "source": "0",
  "location": "测试位置",
  "active": true
}
EOF
)
    
    # 测试默认（可能走旧实现）
    response=$(curl -s -X POST "${BASE_URL}/api/v1/cameras" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 检查响应结构
        if echo "$body" | jq -e '.ok // .camera' > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 响应结构: 正确${NC}"
        else
            echo -e "  ${YELLOW}⚠️  响应结构: 可能不正确${NC}"
        fi
        
        # 清理：删除测试摄像头
        curl -s -X DELETE "${BASE_URL}/api/v1/cameras/${TEST_CAMERA_ID}" > /dev/null 2>&1
        
        # 测试强制使用领域服务
        response_domain=$(curl -s -X POST "${BASE_URL}/api/v1/cameras?force_domain=true" \
            -H "Content-Type: application/json" \
            -d "${payload}" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ] || [ "$http_code_domain" = "201" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            
            # 清理
            curl -s -X DELETE "${BASE_URL}/api/v1/cameras/${TEST_CAMERA_ID}" > /dev/null 2>&1
            
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            echo "  响应内容: $body"
            return 1
        fi
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        echo "  响应内容: $body"
        return 1
    fi
}

# 测试更新摄像头接口（写操作，需要谨慎）
test_update_camera() {
    echo "--- 测试 PUT /api/v1/cameras/{camera_id} ---"
    
    # 使用已知的摄像头ID（如果存在）
    CAMERA_ID="cam0"
    
    # 测试数据
    payload='{"name": "更新后的名称"}'
    
    # 测试默认（可能走旧实现）
    response=$(curl -s -X PUT "${BASE_URL}/api/v1/cameras/${CAMERA_ID}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 检查响应结构
        if echo "$body" | jq -e '.status // .ok' > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅ 响应结构: 正确${NC}"
        else
            echo -e "  ${YELLOW}⚠️  响应结构: 可能不正确${NC}"
        fi
        
        # 测试强制使用领域服务
        response_domain=$(curl -s -X PUT "${BASE_URL}/api/v1/cameras/${CAMERA_ID}?force_domain=true" \
            -H "Content-Type: application/json" \
            -d "${payload}" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            return 1
        fi
    elif [ "$http_code" = "404" ]; then
        echo -e "  ${YELLOW}⚠️  摄像头不存在（需要先创建）: ${CAMERA_ID}${NC}"
        return 1
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        return 1
    fi
}

# 测试删除摄像头接口（写操作，需要非常谨慎）
test_delete_camera() {
    echo "--- 测试 DELETE /api/v1/cameras/{camera_id} ---"
    
    # 先创建一个测试摄像头
    TEST_CAMERA_ID="test_delete_$(date +%s)"
    
    payload=$(cat <<EOF
{
  "id": "${TEST_CAMERA_ID}",
  "name": "测试删除摄像头",
  "source": "0",
  "location": "测试位置",
  "active": true
}
EOF
)
    
    # 先创建
    curl -s -X POST "${BASE_URL}/api/v1/cameras" \
        -H "Content-Type: application/json" \
        -d "${payload}" > /dev/null 2>&1
    
    sleep 1
    
    # 测试默认（可能走旧实现）
    response=$(curl -s -X DELETE "${BASE_URL}/api/v1/cameras/${TEST_CAMERA_ID}" \
        -w "\n%{http_code}")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "  ${GREEN}✅ 状态码: ${http_code}${NC}"
        
        # 再次创建用于领域服务测试
        curl -s -X POST "${BASE_URL}/api/v1/cameras" \
            -H "Content-Type: application/json" \
            -d "${payload}" > /dev/null 2>&1
        
        sleep 1
        
        # 测试强制使用领域服务
        response_domain=$(curl -s -X DELETE "${BASE_URL}/api/v1/cameras/${TEST_CAMERA_ID}?force_domain=true" \
            -w "\n%{http_code}")
        http_code_domain=$(echo "$response_domain" | tail -n 1)
        
        if [ "$http_code_domain" = "200" ]; then
            echo -e "  ${GREEN}✅ 领域服务分支: 正常${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  领域服务分支: 状态码 ${http_code_domain}${NC}"
            return 1
        fi
    else
        echo -e "  ${RED}❌ 状态码: ${http_code}${NC}"
        return 1
    fi
}

# 主执行逻辑
echo "=========================================="
echo "$SCRIPT_NAME"
echo "=========================================="
echo ""

if ! check_backend_status; then
    exit 1
fi

echo ""
echo "开始功能验证..."
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

# 阶段二接口验证
test_system_info && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""
test_alert_history && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""
test_alert_rules && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""

# 阶段三写操作接口验证（谨慎测试）
test_create_camera && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""
test_update_camera && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""
test_delete_camera && SUCCESS_COUNT=$((SUCCESS_COUNT + 1)) || FAIL_COUNT=$((FAIL_COUNT + 1))
echo ""

echo "=========================================="
echo "验证结果汇总"
echo "=========================================="
echo -e "成功: ${GREEN}${SUCCESS_COUNT}${NC}"
echo -e "失败: ${RED}${FAIL_COUNT}${NC}"
echo "总计: $((SUCCESS_COUNT + FAIL_COUNT))"

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 所有接口功能验证通过！${NC}"
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠️  部分接口验证失败，请检查日志${NC}"
    exit 1
fi

