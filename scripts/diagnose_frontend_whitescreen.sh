#!/bin/bash

################################################################################
# Frontend White Screen Diagnostic Script
# Purpose: Diagnose frontend white screen issues in production deployment
# Usage: bash scripts/diagnose_frontend_whitescreen.sh [DEPLOY_DIR]
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DEPLOY_DIR="${1:-$HOME/projects/Pyt}"

echo "========================================================================="
echo -e "${BLUE}Frontend White Screen Diagnostic${NC}"
echo "========================================================================="
echo ""
echo "Deploy directory: $DEPLOY_DIR"
echo ""

cd "$DEPLOY_DIR" || {
    echo -e "${RED}[ERROR]${NC} Cannot access deploy directory: $DEPLOY_DIR"
    exit 1
}

# Check functions
check_passed() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_failed() {
    echo -e "${RED}[✗]${NC} $1"
}

check_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Step 1: Check container status
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 1]${NC} Checking container status"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "docker-compose.prod.yml" ]; then
    docker compose -f docker-compose.prod.yml ps
    echo ""

    # Check specific containers
    if docker ps --format "{{.Names}}" | grep -q "pepgmp-nginx-prod"; then
        check_passed "Nginx container is running"
    else
        check_failed "Nginx container is not running"
    fi

    if docker ps -a --format "{{.Names}}" | grep -q "pepgmp-frontend-init"; then
        FRONTEND_INIT_STATUS=$(docker inspect --format='{{.State.Status}}' pepgmp-frontend-init 2>/dev/null || echo "not found")
        if [ "$FRONTEND_INIT_STATUS" = "exited" ]; then
            EXIT_CODE=$(docker inspect --format='{{.State.ExitCode}}' pepgmp-frontend-init 2>/dev/null || echo "unknown")
            if [ "$EXIT_CODE" = "0" ]; then
                check_passed "Frontend-init container completed successfully (Exit code: 0)"
            else
                check_failed "Frontend-init container exited with error (Exit code: $EXIT_CODE)"
            fi
        else
            check_warning "Frontend-init container status: $FRONTEND_INIT_STATUS"
        fi
    else
        check_failed "Frontend-init container not found"
    fi

    if docker ps --format "{{.Names}}" | grep -q "pepgmp-api-prod"; then
        check_passed "API container is running"
    else
        check_failed "API container is not running"
    fi
else
    check_failed "docker-compose.prod.yml not found"
fi

echo ""

# Step 2: Check frontend static files
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 2]${NC} Checking frontend static files"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d "frontend/dist" ]; then
    check_passed "frontend/dist directory exists"

    if [ -f "frontend/dist/index.html" ]; then
        check_passed "index.html exists"

        # Check file size
        FILE_SIZE=$(stat -f%z "frontend/dist/index.html" 2>/dev/null || stat -c%s "frontend/dist/index.html" 2>/dev/null || echo "0")
        if [ "$FILE_SIZE" -gt 100 ]; then
            check_passed "index.html size: $FILE_SIZE bytes"
        else
            check_failed "index.html is too small: $FILE_SIZE bytes"
        fi

        # Check HTML content
        if grep -q "<!DOCTYPE html>" "frontend/dist/index.html" 2>/dev/null; then
            check_passed "index.html contains valid HTML"
        else
            check_failed "index.html does not contain valid HTML"
        fi
    else
        check_failed "index.html not found"
    fi

    # Check assets directory
    if [ -d "frontend/dist/assets" ]; then
        check_passed "assets directory exists"

        JS_COUNT=$(find frontend/dist/assets -name "*.js" 2>/dev/null | wc -l | tr -d ' ')
        CSS_COUNT=$(find frontend/dist/assets -name "*.css" 2>/dev/null | wc -l | tr -d ' ')

        if [ "$JS_COUNT" -gt 0 ]; then
            check_passed "Found $JS_COUNT JavaScript files"
        else
            check_failed "No JavaScript files found"
        fi

        if [ "$CSS_COUNT" -gt 0 ]; then
            check_passed "Found $CSS_COUNT CSS files"
        else
            check_warning "No CSS files found"
        fi

        # List JS files
        echo ""
        check_info "JavaScript files:"
        find frontend/dist/assets -name "*.js" 2>/dev/null | head -5 | while read -r file; do
            echo "  - $(basename "$file")"
        done
    else
        check_failed "assets directory not found"
    fi

    # Check file permissions
    echo ""
    check_info "File permissions:"
    ls -ld frontend/dist 2>/dev/null || check_failed "Cannot check permissions"
    ls -la frontend/dist/index.html 2>/dev/null | head -1

    # Count total files
    TOTAL_FILES=$(find frontend/dist -type f 2>/dev/null | wc -l | tr -d ' ')
    check_info "Total files in frontend/dist: $TOTAL_FILES"

else
    check_failed "frontend/dist directory does not exist"
fi

echo ""

# Step 3: Check frontend-init logs
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 3]${NC} Checking frontend-init container logs"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if docker ps -a --format "{{.Names}}" | grep -q "pepgmp-frontend-init"; then
    echo "Frontend-init logs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker logs pepgmp-frontend-init 2>&1 | tail -30
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    check_failed "Frontend-init container not found"
fi

echo ""

# Step 4: Check Nginx configuration
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 4]${NC} Checking Nginx configuration"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "nginx/nginx.conf" ]; then
    check_passed "nginx.conf exists"

    # Check if using Scheme B (single Nginx)
    if grep -q "root /usr/share/nginx/html" nginx/nginx.conf; then
        check_passed "Nginx config uses Scheme B (single Nginx)"
    else
        check_failed "Nginx config does not use Scheme B"
    fi

    # Check for Scheme A remnants
    if grep -q "frontend_backend" nginx/nginx.conf; then
        check_failed "Nginx config contains 'frontend_backend' (Scheme A remnant)"
    else
        check_passed "Nginx config does not contain Scheme A remnants"
    fi

    # Test Nginx config syntax
    if docker ps --format "{{.Names}}" | grep -q "pepgmp-nginx-prod"; then
        if docker exec pepgmp-nginx-prod nginx -t 2>&1 | grep -q "successful"; then
            check_passed "Nginx configuration syntax is valid"
        else
            check_failed "Nginx configuration syntax error"
            docker exec pepgmp-nginx-prod nginx -t 2>&1
        fi
    fi
else
    check_failed "nginx/nginx.conf not found"
fi

echo ""

# Step 5: Check Nginx logs
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 5]${NC} Checking Nginx logs"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if docker ps --format "{{.Names}}" | grep -q "pepgmp-nginx-prod"; then
    echo "Recent Nginx access logs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker logs pepgmp-nginx-prod 2>&1 | grep -E "(GET|POST|error)" | tail -20
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    check_failed "Nginx container not running"
fi

echo ""

# Step 6: Test HTTP endpoints
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 6]${NC} Testing HTTP endpoints"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test frontend
echo "Testing frontend (http://localhost/):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check_passed "Frontend returns 200"
else
    check_failed "Frontend returns $HTTP_CODE"
fi

# Test API
echo ""
echo "Testing API (http://localhost/api/v1/monitoring/health):"
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/monitoring/health 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
    check_passed "API returns 200"
    API_RESPONSE=$(curl -s http://localhost/api/v1/monitoring/health 2>/dev/null)
    check_info "API response: $API_RESPONSE"
else
    check_failed "API returns $API_CODE"
fi

# Test Nginx health
echo ""
echo "Testing Nginx health (http://localhost/health):"
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [ "$HEALTH_CODE" = "200" ]; then
    check_passed "Nginx health returns 200"
else
    check_failed "Nginx health returns $HEALTH_CODE"
fi

echo ""

# Step 7: Check HTML content
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 7]${NC} Checking HTML content"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

HTML_CONTENT=$(curl -s http://localhost/ 2>/dev/null || echo "")
if [ -n "$HTML_CONTENT" ]; then
    if echo "$HTML_CONTENT" | grep -q "<!DOCTYPE html>"; then
        check_passed "HTML content is valid"

        # Check for script tags
        SCRIPT_COUNT=$(echo "$HTML_CONTENT" | grep -c "<script" || echo "0")
        if [ "$SCRIPT_COUNT" -gt 0 ]; then
            check_passed "Found $SCRIPT_COUNT script tags"

            # Check script sources
            echo ""
            check_info "Script sources:"
            echo "$HTML_CONTENT" | grep -o 'src="[^"]*"' | head -5 | while read -r src; do
                SCRIPT_PATH=$(echo "$src" | sed 's/src="//;s/"//')
                echo "  - $SCRIPT_PATH"
            done
        else
            check_failed "No script tags found in HTML"
        fi

        # Check for Vue app mount point
        if echo "$HTML_CONTENT" | grep -q "id=\"app\""; then
            check_passed "Vue app mount point found"
        else
            check_warning "Vue app mount point not found"
        fi
    else
        check_failed "HTML content is not valid"
        echo "First 200 characters:"
        echo "$HTML_CONTENT" | head -c 200
        echo ""
    fi
else
    check_failed "Cannot fetch HTML content"
fi

echo ""

# Step 8: Check Docker Compose configuration
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 8]${NC} Checking Docker Compose configuration"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "docker-compose.prod.yml" ]; then
    # Check depends_on
    if grep -A 5 "nginx:" docker-compose.prod.yml | grep -q "frontend-init"; then
        check_passed "Nginx depends_on frontend-init (correct)"
    elif grep -A 5 "nginx:" docker-compose.prod.yml | grep -q "frontend:"; then
        check_failed "Nginx depends_on frontend (incorrect, should be frontend-init)"
    else
        check_warning "Cannot determine nginx depends_on configuration"
    fi

    # Check volumes
    if grep -A 10 "nginx:" docker-compose.prod.yml | grep -q "./frontend/dist:/usr/share/nginx/html"; then
        check_passed "Nginx volume mount is correct"
    else
        check_failed "Nginx volume mount is incorrect"
    fi
fi

echo ""

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Diagnostic Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "  1. If frontend-init failed, check logs: docker logs pepgmp-frontend-init"
echo "  2. If static files missing, re-run: docker compose -f docker-compose.prod.yml up -d frontend-init"
echo "  3. If Nginx config error, check: nginx/nginx.conf"
echo "  4. If still white screen, check browser console (F12)"
echo ""
echo "========================================================================="
