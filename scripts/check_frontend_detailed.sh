#!/bin/bash

################################################################################
# Detailed Frontend Container Check
# Purpose: Check frontend container logs, nginx process, and file access
################################################################################

set -e

echo "========================================================================="
echo "Detailed Frontend Container Check"
echo "========================================================================="
echo ""

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

# Check 1: Container health status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Container Health Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HEALTH_STATUS=$(docker inspect pepgmp-frontend-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "no healthcheck")
echo "Health Status: $HEALTH_STATUS"

if [ "$HEALTH_STATUS" = "unhealthy" ]; then
    print_error "Container is unhealthy"
    echo "  Health check details:"
    docker inspect pepgmp-frontend-prod --format='{{json .State.Health}}' | python3 -m json.tool 2>/dev/null || echo "  (Unable to parse)"
elif [ "$HEALTH_STATUS" = "healthy" ]; then
    print_success "Container is healthy"
else
    print_warning "Health status: $HEALTH_STATUS"
fi
echo ""

# Check 2: Container logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Container Logs (last 50 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs pepgmp-frontend-prod --tail 50 2>&1
echo ""

# Check 3: Nginx process
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Nginx Process Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod ps aux | grep -q nginx; then
    print_success "Nginx process is running"
    docker exec pepgmp-frontend-prod ps aux | grep nginx | grep -v grep
else
    print_error "Nginx process is NOT running!"
    echo "  Attempting to start nginx..."
    docker exec pepgmp-frontend-prod nginx -g "daemon off;" &
    sleep 2
    if docker exec pepgmp-frontend-prod ps aux | grep -q nginx; then
        print_success "Nginx started successfully"
    else
        print_error "Failed to start nginx"
    fi
fi
echo ""

# Check 4: Test file access
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Test File Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "Checking if files are accessible..."

# Check index.html
if docker exec pepgmp-frontend-prod test -f /usr/share/nginx/html/index.html; then
    print_success "index.html exists and is readable"
    FILE_SIZE=$(docker exec pepgmp-frontend-prod stat -c%s /usr/share/nginx/html/index.html 2>/dev/null || echo "unknown")
    echo "  Size: $FILE_SIZE bytes"
else
    print_error "index.html does not exist or is not readable"
fi

# Check main JS file
MAIN_JS="/usr/share/nginx/html/assets/js/index-BQJfhJSs.js"
if docker exec pepgmp-frontend-prod test -f "$MAIN_JS"; then
    print_success "Main JS file exists: $MAIN_JS"
    FILE_SIZE=$(docker exec pepgmp-frontend-prod stat -c%s "$MAIN_JS" 2>/dev/null || echo "unknown")
    echo "  Size: $FILE_SIZE bytes"
else
    print_error "Main JS file does not exist: $MAIN_JS"
    echo "  Available JS files:"
    docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html/assets/js/ | head -10
fi

# Check CSS file
MAIN_CSS="/usr/share/nginx/html/assets/css/index-BMBby1Zw.css"
if docker exec pepgmp-frontend-prod test -f "$MAIN_CSS"; then
    print_success "Main CSS file exists: $MAIN_CSS"
else
    print_warning "Main CSS file does not exist: $MAIN_CSS"
    echo "  Available CSS files:"
    docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html/assets/css/ 2>/dev/null || echo "  CSS directory does not exist"
fi
echo ""

# Check 5: Test HTTP access from inside container
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Test HTTP Access from Inside Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if nginx is listening on port 80
if docker exec pepgmp-frontend-prod netstat -tuln 2>/dev/null | grep -q ":80 "; then
    print_success "Nginx is listening on port 80"
    docker exec pepgmp-frontend-prod netstat -tuln | grep ":80 "
else
    print_error "Nginx is NOT listening on port 80"
    echo "  Checking listening ports:"
    docker exec pepgmp-frontend-prod netstat -tuln 2>/dev/null || echo "  netstat not available"
fi

# Try to access via curl or wget
if docker exec pepgmp-frontend-prod which curl >/dev/null 2>&1; then
    print_info "Testing with curl..."
    docker exec pepgmp-frontend-prod curl -s http://localhost/ | head -5 || print_error "curl failed"
elif docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    print_info "Testing with wget..."
    docker exec pepgmp-frontend-prod wget -qO- http://localhost/ 2>&1 | head -5 || print_error "wget failed"
else
    print_warning "Neither curl nor wget available in container"
fi
echo ""

# Check 6: Network and port mapping
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Network and Port Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "Container network configuration:"
docker inspect pepgmp-frontend-prod --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | head -1
echo ""

print_info "Port mappings:"
docker port pepgmp-frontend-prod 2>/dev/null || echo "  No port mappings (expected for internal service)"
echo ""

# Check 7: Test from reverse proxy
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Test from Reverse Proxy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-nginx-prod; then
    print_info "Testing access from reverse proxy nginx..."
    RESPONSE=$(docker exec pepgmp-nginx-prod wget -qO- http://frontend:80/ 2>&1 | head -10)
    if echo "$RESPONSE" | grep -q "DOCTYPE\|html"; then
        print_success "Reverse proxy can access frontend"
        echo "  Response preview:"
        echo "$RESPONSE" | head -5
    else
        print_error "Reverse proxy cannot access frontend properly"
        echo "  Response:"
        echo "$RESPONSE"
    fi
else
    print_warning "Reverse proxy nginx container is not running"
fi
echo ""

echo "========================================================================="
echo "Summary"
echo "========================================================================="
echo ""

if [ "$HEALTH_STATUS" = "unhealthy" ]; then
    print_error "Container is unhealthy - this is likely the root cause"
    echo ""
    echo "Recommended actions:"
    echo "  1. Check container logs: docker logs pepgmp-frontend-prod"
    echo "  2. Restart frontend container: docker-compose restart frontend"
    echo "  3. Check if nginx process is running inside container"
    echo "  4. Verify health check configuration in docker-compose.prod.yml"
fi

echo "========================================================================="

