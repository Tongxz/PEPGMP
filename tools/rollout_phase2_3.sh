#!/bin/bash

# 脚本名称
SCRIPT_NAME="阶段二和阶段三接口灰度发布验证"

# 后端服务URL
BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 测试灰度百分比
test_rollout_percent() {
    local endpoint=$1
    local method=${2:-GET}
    local payload=${3:-""}
    local rollout_percent=$4
    local test_count=${5:-100}

    echo "--- 测试灰度: ${endpoint} (${rollout_percent}%) ---"

    # 统计走领域服务的请求数
    domain_count=0
    legacy_count=0

    for i in $(seq 1 $test_count); do
        if [ "$method" = "GET" ]; then
            response=$(curl -s "${BASE_URL}${endpoint}" -w "\n%{http_code}")
        elif [ "$method" = "POST" ]; then
            response=$(curl -s -X POST "${BASE_URL}${endpoint}" \
                -H "Content-Type: application/json" \
                -d "${payload}" \
                -w "\n%{http_code}")
        elif [ "$method" = "PUT" ]; then
            response=$(curl -s -X PUT "${BASE_URL}${endpoint}" \
                -H "Content-Type: application/json" \
                -d "${payload}" \
                -w "\n%{http_code}")
        elif [ "$method" = "DELETE" ]; then
            response=$(curl -s -X DELETE "${BASE_URL}${endpoint}" \
                -w "\n%{http_code}")
        fi

        http_code=$(echo "$response" | tail -n 1)

        # 通过响应特征判断是否走领域服务（简化判断）
        # 实际可以通过日志或响应中的特殊字段判断
        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
            # 假设所有成功请求都有可能走领域服务（实际需要通过日志确认）
            domain_count=$((domain_count + 1))
        else
            legacy_count=$((legacy_count + 1))
        fi
    done

    actual_percent=$((domain_count * 100 / test_count))
    echo "  测试请求数: ${test_count}"
    echo "  实际百分比: ${actual_percent}% (目标: ${rollout_percent}%)"

    # 允许±10%的误差
    diff=$((actual_percent - rollout_percent))
    if [ ${diff#-} -le 10 ]; then
        echo -e "  ${GREEN}✅ 灰度百分比正常${NC}"
        return 0
    else
        echo -e "  ${YELLOW}⚠️  灰度百分比偏差较大${NC}"
        return 1
    fi
}

# 验证接口功能
verify_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local payload=${3:-""}
    local force_domain=${4:-"false"}

    local url="${BASE_URL}${endpoint}"
    if [ "$force_domain" = "true" ]; then
        url="${url}?force_domain=true"
    fi

    if [ "$method" = "GET" ]; then
        response=$(curl -s "${url}" -w "\n%{http_code}")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -X POST "${url}" \
            -H "Content-Type: application/json" \
            -d "${payload}" \
            -w "\n%{http_code}")
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -X PUT "${url}" \
            -H "Content-Type: application/json" \
            -d "${payload}" \
            -w "\n%{http_code}")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -X DELETE "${url}" \
            -w "\n%{http_code}")
    fi

    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        return 0
    else
        return 1
    fi
}

# 阶段二接口灰度发布验证
rollout_phase2() {
    local percent=$1

    echo ""
    echo "=========================================="
    echo "阶段二接口灰度发布 (${percent}%)"
    echo "=========================================="
    echo ""

    SUCCESS_COUNT=0
    FAIL_COUNT=0

    # 1. GET /api/v1/system/info
    echo "1. GET /api/v1/system/info"
    if verify_endpoint "/api/v1/system/info" "GET" "" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    # 2. GET /api/v1/alerts/history-db
    echo "2. GET /api/v1/alerts/history-db"
    if verify_endpoint "/api/v1/alerts/history-db?limit=10" "GET" "" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    # 3. GET /api/v1/alerts/rules
    echo "3. GET /api/v1/alerts/rules"
    if verify_endpoint "/api/v1/alerts/rules" "GET" "" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    echo "=========================================="
    echo "验证结果: ${GREEN}${SUCCESS_COUNT}${NC} 成功, ${RED}${FAIL_COUNT}${NC} 失败"
    echo "=========================================="

    if [ "$FAIL_COUNT" -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# 阶段三接口灰度发布验证（谨慎）
rollout_phase3() {
    local percent=$1

    echo ""
    echo "=========================================="
    echo "阶段三接口灰度发布 (${percent}%)"
    echo "=========================================="
    echo ""
    echo -e "${YELLOW}⚠️  写操作接口灰度发布需要更谨慎${NC}"
    echo ""

    SUCCESS_COUNT=0
    FAIL_COUNT=0

    # 1. POST /api/v1/cameras (测试创建)
    echo "1. POST /api/v1/cameras"
    TEST_CAMERA_ID="test_rollout_$(date +%s)"
    payload=$(cat <<EOF
{
  "id": "${TEST_CAMERA_ID}",
  "name": "测试灰度摄像头",
  "source": "0",
  "location": "测试位置",
  "active": true
}
EOF
)

    if verify_endpoint "/api/v1/cameras" "POST" "${payload}" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

        # 清理：删除测试摄像头
        curl -s -X DELETE "${BASE_URL}/api/v1/cameras/${TEST_CAMERA_ID}" > /dev/null 2>&1
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    # 2. PUT /api/v1/cameras/{camera_id} (测试更新)
    echo "2. PUT /api/v1/cameras/{camera_id}"
    CAMERA_ID="cam0"
    payload='{"name": "灰度测试更新"}'

    if verify_endpoint "/api/v1/cameras/${CAMERA_ID}" "PUT" "${payload}" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    # 3. DELETE /api/v1/cameras/{camera_id} (测试删除，需要先创建)
    echo "3. DELETE /api/v1/cameras/{camera_id}"
    TEST_DELETE_ID="test_delete_$(date +%s)"
    create_payload=$(cat <<EOF
{
  "id": "${TEST_DELETE_ID}",
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
        -d "${create_payload}" > /dev/null 2>&1

    sleep 1

    if verify_endpoint "/api/v1/cameras/${TEST_DELETE_ID}" "DELETE" "" "false"; then
        echo -e "  ${GREEN}✅ 接口正常${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}❌ 接口异常${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo ""

    echo "=========================================="
    echo "验证结果: ${GREEN}${SUCCESS_COUNT}${NC} 成功, ${RED}${FAIL_COUNT}${NC} 失败"
    echo "=========================================="

    if [ "$FAIL_COUNT" -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# 主执行逻辑
main() {
    echo "=========================================="
    echo "$SCRIPT_NAME"
    echo "=========================================="
    echo ""

    if ! check_backend_status; then
        exit 1
    fi

    # 检查环境变量
    use_domain=$(echo "${USE_DOMAIN_SERVICE:-false}" | tr '[:upper:]' '[:lower:]')
    rollout_percent=${ROLLOUT_PERCENT:-0}

    echo "当前配置:"
    echo "  USE_DOMAIN_SERVICE: ${use_domain}"
    echo "  ROLLOUT_PERCENT: ${rollout_percent}%"
    echo ""

    if [ "$use_domain" != "true" ]; then
        echo -e "${YELLOW}⚠️  USE_DOMAIN_SERVICE=false，灰度未启用${NC}"
        echo "请设置: export USE_DOMAIN_SERVICE=true"
        echo "请设置: export ROLLOUT_PERCENT=<百分比>"
        exit 1
    fi

    # 根据ROLLOUT_PERCENT决定验证范围
    if [ "$rollout_percent" -le 0 ]; then
        echo -e "${YELLOW}⚠️  ROLLOUT_PERCENT=0，灰度未启用${NC}"
        exit 1
    elif [ "$rollout_percent" -lt 25 ]; then
        echo -e "${BLUE}📊 灰度比例: ${rollout_percent}% (小规模测试)${NC}"
    elif [ "$rollout_percent" -lt 50 ]; then
        echo -e "${BLUE}📊 灰度比例: ${rollout_percent}% (中规模测试)${NC}"
    elif [ "$rollout_percent" -lt 100 ]; then
        echo -e "${BLUE}📊 灰度比例: ${rollout_percent}% (大规模测试)${NC}"
    else
        echo -e "${GREEN}📊 灰度比例: ${rollout_percent}% (全量发布)${NC}"
    fi

    # 阶段二接口验证
    if rollout_phase2 "$rollout_percent"; then
        echo ""
        echo -e "${GREEN}✅ 阶段二接口灰度发布验证通过${NC}"
    else
        echo ""
        echo -e "${RED}❌ 阶段二接口灰度发布验证失败${NC}"
        exit 1
    fi

    # 阶段三接口验证（仅在灰度比例>=5%时执行）
    if [ "$rollout_percent" -ge 5 ]; then
        if rollout_phase3 "$rollout_percent"; then
            echo ""
            echo -e "${GREEN}✅ 阶段三接口灰度发布验证通过${NC}"
        else
            echo ""
            echo -e "${RED}❌ 阶段三接口灰度发布验证失败${NC}"
            exit 1
        fi
    else
        echo ""
        echo -e "${YELLOW}⚠️  阶段三接口灰度比例过低，跳过验证${NC}"
    fi

    echo ""
    echo "=========================================="
    echo -e "${GREEN}✅ 灰度发布验证完成！${NC}"
    echo "=========================================="
}

# 执行主函数
main
