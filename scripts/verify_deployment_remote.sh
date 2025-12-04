#!/bin/bash

################################################################################
# Remote Deployment Verification Script
# Purpose: Verify WSL2 deployment from macOS (via SSH or WSL access)
# Usage: bash scripts/verify_deployment_remote.sh [WSL_USER@]WSL_HOST [DEPLOY_DIR]
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

WSL_TARGET="${1:-}"
DEPLOY_DIR="${2:-$HOME/projects/PEPGMP"

echo "========================================================================="
echo -e "${BLUE}Remote Deployment Verification${NC}"
echo "========================================================================="
echo ""

if [ -z "$WSL_TARGET" ]; then
    echo "Usage: $0 [WSL_USER@]WSL_HOST [DEPLOY_DIR]"
    echo ""
    echo "Examples:"
    echo "  # Direct WSL access (if WSL is accessible)"
    echo "  bash $0"
    echo ""
    echo "  # Via SSH"
    echo "  bash $0 user@wsl-ip"
    echo ""
    echo "  # With custom deploy directory"
    echo "  bash $0 user@wsl-ip /home/user/projects/PEPGMP"
    exit 1
fi

# Function to run command on remote
run_remote() {
    if [ -z "$WSL_TARGET" ]; then
        # Direct WSL access (same machine)
        wsl bash -c "$1"
    else
        # SSH access
        ssh "$WSL_TARGET" "$1"
    fi
}

# Function to copy file from remote
copy_from_remote() {
    local remote_file="$1"
    local local_file="$2"

    if [ -z "$WSL_TARGET" ]; then
        # Direct WSL access
        wsl cat "$remote_file" > "$local_file"
    else
        # SSH access
        scp "$WSL_TARGET:$remote_file" "$local_file"
    fi
}

echo "Target: $WSL_TARGET"
echo "Deploy directory: $DEPLOY_DIR"
echo ""

# Step 1: Check container status
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 1]${NC} Checking container status"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

run_remote "cd $DEPLOY_DIR && docker compose -f docker-compose.prod.yml ps"

echo ""

# Step 2: Check frontend static files
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 2]${NC} Checking frontend static files"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

run_remote "cd $DEPLOY_DIR && ls -la frontend/dist/ 2>/dev/null | head -10 || echo 'frontend/dist not found'"
run_remote "cd $DEPLOY_DIR && find frontend/dist -type f 2>/dev/null | wc -l || echo '0'"

echo ""

# Step 3: Check frontend-init logs
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 3]${NC} Checking frontend-init logs"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

run_remote "docker logs pepgmp-frontend-init-prod 2>&1 | tail -30"

echo ""

# Step 4: Test HTTP endpoints
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 4]${NC} Testing HTTP endpoints"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get WSL IP
WSL_IP=$(run_remote "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "localhost")

echo "WSL IP: $WSL_IP"
echo ""

# Test endpoints
echo "Testing frontend (http://$WSL_IP/):"
curl -s -o /dev/null -w "HTTP Code: %{http_code}\n" "http://$WSL_IP/" 2>/dev/null || echo "Cannot connect"

echo ""
echo "Testing API (http://$WSL_IP/api/v1/monitoring/health):"
curl -s "http://$WSL_IP/api/v1/monitoring/health" 2>/dev/null || echo "Cannot connect"
echo ""

echo "Testing Nginx health (http://$WSL_IP/health):"
curl -s "http://$WSL_IP/health" 2>/dev/null || echo "Cannot connect"
echo ""

# Step 5: Download and check HTML
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 5]${NC} Checking HTML content"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

HTML_FILE="/tmp/frontend_check_$$.html"
curl -s "http://$WSL_IP/" > "$HTML_FILE" 2>/dev/null || {
    echo "Cannot fetch HTML"
    exit 1
}

if [ -f "$HTML_FILE" ]; then
    if grep -q "<!DOCTYPE html>" "$HTML_FILE"; then
        echo -e "${GREEN}[✓]${NC} HTML is valid"

        SCRIPT_COUNT=$(grep -c "<script" "$HTML_FILE" || echo "0")
        echo "Script tags: $SCRIPT_COUNT"

        echo ""
        echo "Script sources:"
        grep -o 'src="[^"]*"' "$HTML_FILE" | head -5

        # Check for errors in HTML
        if grep -qi "error\|exception\|undefined" "$HTML_FILE"; then
            echo ""
            echo -e "${YELLOW}[!]${NC} Found potential errors in HTML:"
            grep -i "error\|exception\|undefined" "$HTML_FILE" | head -3
        fi
    else
        echo -e "${RED}[✗]${NC} HTML is not valid"
        echo "First 200 characters:"
        head -c 200 "$HTML_FILE"
        echo ""
    fi

    rm -f "$HTML_FILE"
fi

echo ""
echo "========================================================================="
