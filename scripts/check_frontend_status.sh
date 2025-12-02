#!/bin/bash

################################################################################
# Check Frontend Service Status
# Purpose: Diagnose frontend access issues
################################################################################

echo "========================================================================="
echo "Frontend Service Status Check"
echo "========================================================================="
echo ""

# Check if frontend image exists
echo "1. Frontend Images:"
FRONTEND_IMAGES=$(docker images | grep pepgmp-frontend || echo "  [NOT FOUND] No frontend images found")
echo "$FRONTEND_IMAGES"
echo ""

# Check if frontend service is running
echo "2. Frontend Container Status:"
FRONTEND_CONTAINER=$(docker ps -a | grep pepgmp-frontend || echo "  [NOT FOUND] Frontend container not found")
echo "$FRONTEND_CONTAINER"
echo ""

# Check docker-compose.prod.yml for frontend service
echo "3. Frontend Service in docker-compose.prod.yml:"
if [ -f "docker-compose.prod.yml" ]; then
    if grep -q "^  frontend:" docker-compose.prod.yml; then
        echo "  [OK] Frontend service found in docker-compose.prod.yml"
        grep -A 15 "^  frontend:" docker-compose.prod.yml | head -16
    else
        echo "  [NOT FOUND] Frontend service not found in docker-compose.prod.yml"
    fi
else
    echo "  [ERROR] docker-compose.prod.yml not found"
fi
echo ""

# Check nginx configuration
echo "4. Nginx Configuration:"
if [ -f "nginx/nginx.conf" ]; then
    echo "  [OK] nginx.conf exists"
    echo "  Checking for frontend proxy configuration..."
    if grep -q "frontend" nginx/nginx.conf || grep -q "location /" nginx/nginx.conf; then
        echo "  [OK] Found location / configuration"
        grep -A 5 "location /" nginx/nginx.conf | head -6
    else
        echo "  [WARNING] No frontend proxy configuration found"
    fi
else
    echo "  [NOT FOUND] nginx.conf not found"
fi
echo ""

# Check port usage
echo "5. Port Usage:"
echo "  Checking ports 80, 8080, 5173..."
if command -v netstat >/dev/null 2>&1; then
    netstat -tulpn 2>/dev/null | grep -E ':(80|8080|5173)' || echo "  No processes found on these ports"
elif command -v ss >/dev/null 2>&1; then
    ss -tulpn 2>/dev/null | grep -E ':(80|8080|5173)' || echo "  No processes found on these ports"
else
    echo "  [INFO] netstat/ss not available, skipping port check"
fi
echo ""

# Summary
echo "========================================================================="
echo "Summary"
echo "========================================================================="
echo ""

if docker images | grep -q pepgmp-frontend; then
    echo "[OK] Frontend image exists"
else
    echo "[WARNING] Frontend image not found"
    echo "  Solution: Import frontend image or build it"
fi

if docker ps -a | grep -q pepgmp-frontend; then
    echo "[OK] Frontend container exists"
    if docker ps | grep -q pepgmp-frontend; then
        echo "[OK] Frontend container is running"
    else
        echo "[WARNING] Frontend container exists but not running"
        echo "  Solution: docker-compose up -d frontend"
    fi
else
    echo "[WARNING] Frontend container not found"
    echo "  Solution: Add frontend service to docker-compose.prod.yml and start it"
fi

if grep -q "^  frontend:" docker-compose.prod.yml 2>/dev/null; then
    echo "[OK] Frontend service configured in docker-compose.prod.yml"
else
    echo "[WARNING] Frontend service not in docker-compose.prod.yml"
    echo "  Solution: Add frontend service configuration"
fi

echo ""
echo "========================================================================="

