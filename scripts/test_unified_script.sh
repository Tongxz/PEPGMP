#!/bin/bash
# 统一脚本测试脚本
# Test script for unified startup script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "========================================================================="
echo "                     统一脚本测试"
echo "========================================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# 测试函数
test_check() {
    local test_name=$1
    local command=$2
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    echo -n "测试: $test_name ... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 通过${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# ==================== 文件存在性测试 ====================

echo "=== 文件存在性测试 ==="
echo ""

test_check "统一脚本存在" "test -f scripts/start.sh"
test_check "公共函数库 common.sh 存在" "test -f scripts/lib/common.sh"
test_check "公共函数库 env_detection.sh 存在" "test -f scripts/lib/env_detection.sh"
test_check "公共函数库 config_validation.sh 存在" "test -f scripts/lib/config_validation.sh"
test_check "公共函数库 docker_utils.sh 存在" "test -f scripts/lib/docker_utils.sh"
test_check "公共函数库 service_manager.sh 存在" "test -f scripts/lib/service_manager.sh"
test_check "开发环境快捷方式存在" "test -f scripts/start_dev.sh"
test_check "生产环境快捷方式存在" "test -f scripts/start_prod.sh"
test_check "WSL生产环境快捷方式存在" "test -f scripts/start_prod_wsl.sh"

echo ""

# ==================== 脚本语法测试 ====================

echo "=== 脚本语法测试 ==="
echo ""

test_check "统一脚本语法正确" "bash -n scripts/start.sh"
test_check "common.sh 语法正确" "bash -n scripts/lib/common.sh"
test_check "env_detection.sh 语法正确" "bash -n scripts/lib/env_detection.sh"
test_check "config_validation.sh 语法正确" "bash -n scripts/lib/config_validation.sh"
test_check "docker_utils.sh 语法正确" "bash -n scripts/lib/docker_utils.sh"
test_check "service_manager.sh 语法正确" "bash -n scripts/lib/service_manager.sh"
test_check "start_dev.sh 语法正确" "bash -n scripts/start_dev.sh"
test_check "start_prod.sh 语法正确" "bash -n scripts/start_prod.sh"
test_check "start_prod_wsl.sh 语法正确" "bash -n scripts/start_prod_wsl.sh"

echo ""

# ==================== 帮助信息测试 ====================

echo "=== 帮助信息测试 ==="
echo ""

test_check "统一脚本显示帮助信息" "bash scripts/start.sh --help | grep -q '统一启动脚本'"

echo ""

# ==================== 参数解析测试 ====================

echo "=== 参数解析测试 ==="
echo ""

# 测试缺少必需参数
test_check "缺少--env参数时显示错误" "bash scripts/start.sh 2>&1 | grep -q '必须指定环境类型'"

# 测试无效环境类型
test_check "无效环境类型时显示错误" "bash scripts/start.sh --env invalid 2>&1 | grep -q '环境类型必须是 dev 或 prod'"

# 测试帮助参数
test_check "--help参数正常工作" "bash scripts/start.sh --help 2>&1 | grep -q '统一启动脚本'"

echo ""

# ==================== 函数库加载测试 ====================

echo "=== 函数库加载测试 ==="
echo ""

# 测试函数库是否可以正常加载
test_check "common.sh 可以正常加载" "bash -c 'source scripts/lib/common.sh && log_info \"test\" > /dev/null'"
test_check "env_detection.sh 可以正常加载" "bash -c 'source scripts/lib/common.sh && source scripts/lib/env_detection.sh && detect_wsl > /dev/null 2>&1 || true'"

echo ""

# ==================== 快捷方式测试 ====================

echo "=== 快捷方式测试 ==="
echo ""

# 测试快捷方式是否正确调用统一脚本
test_check "start_dev.sh 调用统一脚本" "bash scripts/start_dev.sh --help 2>&1 | grep -q '统一启动脚本'"
test_check "start_prod.sh 调用统一脚本" "bash scripts/start_prod.sh --help 2>&1 | grep -q '统一启动脚本'"
test_check "start_prod_wsl.sh 调用统一脚本" "bash scripts/start_prod_wsl.sh --help 2>&1 | grep -q '统一启动脚本'"

echo ""

# ==================== 测试结果汇总 ====================

echo "========================================================================="
echo "                     测试结果汇总"
echo "========================================================================="
echo ""
echo "总测试数: $TESTS_TOTAL"
echo -e "${GREEN}通过: $TESTS_PASSED${NC}"
echo -e "${RED}失败: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败${NC}"
    exit 1
fi



