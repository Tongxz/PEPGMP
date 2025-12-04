#!/bin/bash

################################################################################
# macOS Deployment Verification Script
# Purpose: Verify WSL2 deployment from macOS (via WSL command)
# Usage: bash scripts/verify_deployment_macos.sh [DEPLOY_DIR]
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

DEPLOY_DIR="${1:-$HOME/projects/PEPGMP"

echo "========================================================================="
echo -e "${BLUE}macOS Deployment Verification (WSL2)${NC}"
echo "========================================================================="
echo ""

# Check if WSL is available
if ! command -v wsl &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} WSL command not found. Please install WSL2 or use SSH."
    exit 1
fi

# Function to run command in WSL
run_wsl() {
    wsl bash -c "$1"
}

# Function to check result
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

# Step 1: Get WSL IP
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 1]${NC} Getting WSL2 IP address"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

WSL_IP=$(run_wsl "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "")

if [ -n "$WSL_IP" ]; then
    check_passed "WSL2 IP: $WSL_IP"
    echo ""
    echo "You can access the application at:"
    echo "  - http://$WSL_IP/"
    echo "  - http://$WSL_IP/api/v1/monitoring/health"
    echo ""
else
    check_failed "Cannot get WSL2 IP address"
    exit 1
fi

# Step 2: Check container status
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 2]${NC} Checking container status"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CONTAINER_STATUS=$(run_wsl "cd $DEPLOY_DIR && docker compose -f docker-compose.prod.yml ps 2>/dev/null" || echo "")

if [ -n "$CONTAINER_STATUS" ]; then
    echo "$CONTAINER_STATUS"
    echo ""

    # Check specific containers
    if echo "$CONTAINER_STATUS" | grep -q "pepgmp-nginx-prod.*Up"; then
        check_passed "Nginx container is running"
    else
        check_failed "Nginx container is not running"
    fi

    if echo "$CONTAINER_STATUS" | grep -q "pepgmp-frontend-init.*Exited.*0"; then
        check_passed "Frontend-init container completed successfully"
    else
        check_failed "Frontend-init container did not complete successfully"
    fi

    if echo "$CONTAINER_STATUS" | grep -q "pepgmp-api-prod.*Up"; then
        check_passed "API container is running"
    else
        check_failed "API container is not running"
    fi
else
    check_failed "Cannot get container status"
fi

echo ""

# Step 3: Check frontend static files
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 3]${NC} Checking frontend static files"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FILE_CHECK=$(run_wsl "cd $DEPLOY_DIR && ls -la frontend/dist/index.html 2>/dev/null && echo 'EXISTS' || echo 'NOT_FOUND'")

if echo "$FILE_CHECK" | grep -q "EXISTS"; then
    check_passed "index.html exists"

    FILE_SIZE=$(run_wsl "cd $DEPLOY_DIR && stat -c%s frontend/dist/index.html 2>/dev/null || echo '0'")
    if [ "$FILE_SIZE" -gt 100 ]; then
        check_passed "index.html size: $FILE_SIZE bytes"
    else
        check_failed "index.html is too small: $FILE_SIZE bytes"
    fi

    FILE_COUNT=$(run_wsl "cd $DEPLOY_DIR && find frontend/dist -type f 2>/dev/null | wc -l")
    check_info "Total files in frontend/dist: $FILE_COUNT"
else
    check_failed "index.html not found"
fi

echo ""

# Step 4: Test HTTP endpoints
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 4]${NC} Testing HTTP endpoints from macOS"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test frontend
echo "Testing frontend (http://$WSL_IP/):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$WSL_IP/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check_passed "Frontend returns 200"
else
    check_failed "Frontend returns $HTTP_CODE"
fi

# Test API
echo ""
echo "Testing API (http://$WSL_IP/api/v1/monitoring/health):"
API_RESPONSE=$(curl -s "http://$WSL_IP/api/v1/monitoring/health" 2>/dev/null || echo "")
if [ -n "$API_RESPONSE" ]; then
    check_passed "API is accessible"
    check_info "API response: $API_RESPONSE"
else
    check_failed "API is not accessible"
fi

# Test Nginx health
echo ""
echo "Testing Nginx health (http://$WSL_IP/health):"
HEALTH_RESPONSE=$(curl -s "http://$WSL_IP/health" 2>/dev/null || echo "")
if [ -n "$HEALTH_RESPONSE" ]; then
    check_passed "Nginx health check is accessible"
    check_info "Health response: $HEALTH_RESPONSE"
else
    check_failed "Nginx health check is not accessible"
fi

echo ""

# Step 5: Check HTML content
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 5]${NC} Checking HTML content"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

HTML_FILE="/tmp/frontend_check_$$.html"
curl -s "http://$WSL_IP/" > "$HTML_FILE" 2>/dev/null || {
    check_failed "Cannot fetch HTML content"
    exit 1
}

if [ -f "$HTML_FILE" ]; then
    if grep -q "<!DOCTYPE html>" "$HTML_FILE"; then
        check_passed "HTML is valid"

        SCRIPT_COUNT=$(grep -c "<script" "$HTML_FILE" || echo "0")
        if [ "$SCRIPT_COUNT" -gt 0 ]; then
            check_passed "Found $SCRIPT_COUNT script tags"

            echo ""
            check_info "Script sources:"
            grep -o 'src="[^"]*"' "$HTML_FILE" | head -5 | while read -r src; do
                echo "  - $src"
            done
        else
            check_failed "No script tags found"
        fi

        # Check for Vue app mount point
        if grep -q 'id="app"' "$HTML_FILE"; then
            check_passed "Vue app mount point found"
        else
            check_warning "Vue app mount point not found"
        fi

        # Check for errors
        if grep -qi "error\|exception\|undefined" "$HTML_FILE"; then
            echo ""
            check_warning "Found potential errors in HTML:"
            grep -i "error\|exception\|undefined" "$HTML_FILE" | head -3
        fi
    else
        check_failed "HTML is not valid"
        echo "First 200 characters:"
        head -c 200 "$HTML_FILE"
        echo ""
    fi

    rm -f "$HTML_FILE"
fi

echo ""

# Step 6: Check frontend-init logs
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 6]${NC} Checking frontend-init logs"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FRONTEND_INIT_LOGS=$(run_wsl "docker logs pepgmp-frontend-init 2>&1 | tail -20" || echo "")

if [ -n "$FRONTEND_INIT_LOGS" ]; then
    echo "$FRONTEND_INIT_LOGS"

    if echo "$FRONTEND_INIT_LOGS" | grep -q "Static files extracted successfully"; then
        check_passed "Frontend-init completed successfully"
    else
        check_warning "Frontend-init may not have completed successfully"
    fi
else
    check_failed "Cannot get frontend-init logs"
fi

echo ""

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Access URLs:"
echo "  Frontend: http://$WSL_IP/"
echo "  API:      http://$WSL_IP/api/v1/monitoring/health"
echo "  Health:   http://$WSL_IP/health"
echo ""
echo "Next steps:"
echo "  1. Open http://$WSL_IP/ in your browser"
echo "  2. Press F12 to open developer tools"
echo "  3. Check Console and Network tabs for errors"
echo ""
echo "If you see a white screen:"
echo "  1. Run the diagnostic script in WSL2:"
echo "     bash scripts/diagnose_frontend_whitescreen.sh $DEPLOY_DIR"
echo "  2. Check the troubleshooting guide:"
echo "     docs/前端白屏问题排查指南.md"
echo ""
echo "========================================================================="
