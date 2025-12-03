#!/bin/bash

################################################################################
# 方案 B 完整测试脚本
# Purpose: Test Scheme B (Single Nginx) deployment
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

test_check() {
    if [ $? -eq 0 ]; then
        print_success "$1"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "$1"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "========================================================================="
echo "方案 B 完整测试脚本"
echo "========================================================================="
echo ""

# ============================================================================
# Test 1: Check Container Status
# ============================================================================
print_section "Test 1: 检查容器状态"

print_info "Checking container status..."

NGINX_STATUS=$(docker inspect pepgmp-nginx-prod --format='{{.State.Status}}' 2>/dev/null || echo "not found")
API_STATUS=$(docker inspect pepgmp-api-prod --format='{{.State.Status}}' 2>/dev/null || echo "not found")
DB_STATUS=$(docker inspect pepgmp-postgres-prod --format='{{.State.Status}}' 2>/dev/null || echo "not found")

if [ "$NGINX_STATUS" = "running" ]; then
    print_success "Nginx container is running"
    ((TESTS_PASSED++))
else
    print_error "Nginx container is not running (Status: $NGINX_STATUS)"
    ((TESTS_FAILED++))
fi

if [ "$API_STATUS" = "running" ]; then
    print_success "API container is running"
    ((TESTS_PASSED++))
else
    print_error "API container is not running (Status: $API_STATUS)"
    ((TESTS_FAILED++))
fi

if [ "$DB_STATUS" = "running" ]; then
    print_success "Database container is running"
    ((TESTS_PASSED++))
else
    print_error "Database container is not running (Status: $DB_STATUS)"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 2: Check Nginx Health
# ============================================================================
print_section "Test 2: 检查 Nginx 健康状态"

NGINX_HEALTH=$(docker inspect pepgmp-nginx-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "no healthcheck")
if [ "$NGINX_HEALTH" = "healthy" ]; then
    print_success "Nginx container is healthy"
    ((TESTS_PASSED++))
elif [ "$NGINX_HEALTH" = "starting" ]; then
    print_warning "Nginx container is starting (wait a few seconds)"
else
    print_error "Nginx container is unhealthy (Status: $NGINX_HEALTH)"
    print_info "Check logs: docker logs pepgmp-nginx-prod"
    ((TESTS_FAILED++))
fi

# Test health endpoint
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    print_success "Health endpoint returns 200"
    HEALTH_CONTENT=$(curl -s http://localhost/health)
    print_info "Response: $HEALTH_CONTENT"
    ((TESTS_PASSED++))
else
    print_error "Health endpoint failed (HTTP $HEALTH_RESPONSE)"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 3: Test Static File Access
# ============================================================================
print_section "Test 3: 测试静态文件访问"

ROOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
if [ "$ROOT_RESPONSE" = "200" ]; then
    print_success "Root path returns 200"
    ROOT_CONTENT=$(curl -s http://localhost/ | head -5)
    if echo "$ROOT_CONTENT" | grep -q "DOCTYPE\|html"; then
        print_success "Root path returns HTML content"
        print_info "Preview:"
        echo "$ROOT_CONTENT" | head -3 | sed 's/^/  /'
        ((TESTS_PASSED++))
    else
        print_error "Root path does not return HTML"
        ((TESTS_FAILED++))
    fi
    ((TESTS_PASSED++))
else
    print_error "Root path failed (HTTP $ROOT_RESPONSE)"
    ((TESTS_FAILED++))
fi

INDEX_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/index.html 2>/dev/null || echo "000")
if [ "$INDEX_RESPONSE" = "200" ]; then
    print_success "index.html returns 200"
    ((TESTS_PASSED++))
else
    print_error "index.html failed (HTTP $INDEX_RESPONSE)"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 4: Test Static Resources
# ============================================================================
print_section "Test 4: 测试静态资源文件"

INDEX_HTML=$(curl -s http://localhost/index.html 2>/dev/null || echo "")

if [ -z "$INDEX_HTML" ]; then
    print_error "Cannot fetch index.html"
    ((TESTS_FAILED++))
else
    # Extract JS file
    JS_FILE=$(echo "$INDEX_HTML" | grep -oP 'src="[^"]*\.js[^"]*"' | head -1 | sed 's/src="//;s/"//' || echo "")
    if [ -n "$JS_FILE" ]; then
        JS_URL="http://localhost$JS_FILE"
        JS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$JS_URL" 2>/dev/null || echo "000")
        if [ "$JS_RESPONSE" = "200" ]; then
            print_success "JavaScript file accessible: $JS_FILE"
            ((TESTS_PASSED++))
        else
            print_error "JavaScript file failed (HTTP $JS_RESPONSE): $JS_FILE"
            ((TESTS_FAILED++))
        fi
    else
        print_warning "No JavaScript files found in index.html"
    fi

    # Extract CSS file
    CSS_FILE=$(echo "$INDEX_HTML" | grep -oP 'href="[^"]*\.css[^"]*"' | head -1 | sed 's/href="//;s/"//' || echo "")
    if [ -n "$CSS_FILE" ]; then
        CSS_URL="http://localhost$CSS_FILE"
        CSS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$CSS_URL" 2>/dev/null || echo "000")
        if [ "$CSS_RESPONSE" = "200" ]; then
            print_success "CSS file accessible: $CSS_FILE"
            ((TESTS_PASSED++))
        else
            print_error "CSS file failed (HTTP $CSS_RESPONSE): $CSS_FILE"
            ((TESTS_FAILED++))
        fi
    else
        print_warning "No CSS files found in index.html"
    fi
fi

# ============================================================================
# Test 5: Test API Proxy
# ============================================================================
print_section "Test 5: 测试 API 代理"

API_HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/monitoring/health 2>/dev/null || echo "000")
if [ "$API_HEALTH_RESPONSE" = "200" ]; then
    print_success "API health endpoint returns 200"
    API_HEALTH_CONTENT=$(curl -s http://localhost/api/v1/monitoring/health 2>/dev/null || echo "")
    print_info "Response: $API_HEALTH_CONTENT"
    ((TESTS_PASSED++))
else
    print_error "API health endpoint failed (HTTP $API_HEALTH_RESPONSE)"
    print_info "Check API container: docker logs pepgmp-api-prod"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 6: Test Vue Router History Mode
# ============================================================================
print_section "Test 6: 测试 Vue Router History 模式"

FAKE_PATH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/nonexistent-page 2>/dev/null || echo "000")
if [ "$FAKE_PATH_RESPONSE" = "200" ]; then
    FAKE_PATH_CONTENT=$(curl -s http://localhost/nonexistent-page 2>/dev/null | head -5)
    if echo "$FAKE_PATH_CONTENT" | grep -q "DOCTYPE\|html"; then
        print_success "Vue Router history mode working (fake path returns index.html)"
        ((TESTS_PASSED++))
    else
        print_error "Vue Router history mode not working (fake path does not return HTML)"
        ((TESTS_FAILED++))
    fi
else
    print_error "Vue Router history mode failed (HTTP $FAKE_PATH_RESPONSE)"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 7: Check Container File Mounts
# ============================================================================
print_section "Test 7: 检查容器内文件挂载"

NGINX_HTML=$(docker exec pepgmp-nginx-prod ls -la /usr/share/nginx/html/ 2>/dev/null || echo "")
if [ -n "$NGINX_HTML" ]; then
    print_success "Static files mounted in nginx container"
    FILE_COUNT=$(echo "$NGINX_HTML" | grep -c "^-" || echo "0")
    print_info "File count: $FILE_COUNT"
    ((TESTS_PASSED++))
else
    print_error "Cannot access static files in nginx container"
    ((TESTS_FAILED++))
fi

NGINX_INDEX=$(docker exec pepgmp-nginx-prod test -f /usr/share/nginx/html/index.html 2>/dev/null && echo "exists" || echo "missing")
if [ "$NGINX_INDEX" = "exists" ]; then
    print_success "index.html exists in nginx container"
    ((TESTS_PASSED++))
else
    print_error "index.html missing in nginx container"
    ((TESTS_FAILED++))
fi

# ============================================================================
# Test 8: Performance Test
# ============================================================================
print_section "Test 8: 性能测试"

print_info "Testing response times..."

ROOT_TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost/ 2>/dev/null || echo "0.000")
print_info "Root path: ${ROOT_TIME}s"

API_TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost/api/v1/monitoring/health 2>/dev/null || echo "0.000")
print_info "API health: ${API_TIME}s"

# ============================================================================
# Summary
# ============================================================================
print_section "测试总结"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo "总测试数: $TOTAL_TESTS"
echo "通过: $TESTS_PASSED"
echo "失败: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    print_success "所有测试通过！"
    echo ""
    print_info "下一步："
    echo "  1. 在浏览器中访问: http://localhost/"
    echo "  2. 检查浏览器控制台 (F12) 是否有错误"
    echo "  3. 测试前端功能是否正常"
    exit 0
else
    print_error "部分测试失败，请检查上述错误信息"
    echo ""
    print_info "故障排查："
    echo "  1. 检查容器日志: docker logs pepgmp-nginx-prod"
    echo "  2. 检查静态文件: ls -la frontend/dist/"
    echo "  3. 检查 nginx 配置: docker exec pepgmp-nginx-prod nginx -t"
    exit 1
fi

