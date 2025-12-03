#!/bin/bash

################################################################################
# Verify Frontend Fix
# Purpose: Verify frontend container health after rebuild
################################################################################

set -e

echo "========================================================================="
echo "Verify Frontend Container Fix"
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

# Check if frontend container exists
if ! docker ps -a | grep -q pepgmp-frontend-prod; then
    print_error "Frontend container does not exist"
    echo "  Please start it first:"
    echo "    docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend"
    exit 1
fi

# Check 1: Container status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Container Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CONTAINER_STATUS=$(docker inspect pepgmp-frontend-prod --format='{{.State.Status}}' 2>/dev/null)
HEALTH_STATUS=$(docker inspect pepgmp-frontend-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "no healthcheck")

echo "Container Status: $CONTAINER_STATUS"
echo "Health Status: $HEALTH_STATUS"

if [ "$CONTAINER_STATUS" != "running" ]; then
    print_error "Container is not running"
    echo "  Starting container..."
    docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
    sleep 5
fi

if [ "$HEALTH_STATUS" = "unhealthy" ]; then
    print_warning "Container is unhealthy"
    echo "  This may be due to:"
    echo "    1. Old image without wget installed"
    echo "    2. Nginx not started properly"
    echo ""
    echo "  Solution: Rebuild frontend image with fixed Dockerfile.frontend"
elif [ "$HEALTH_STATUS" = "healthy" ]; then
    print_success "Container is healthy"
else
    print_info "Health status: $HEALTH_STATUS (may be starting)"
fi
echo ""

# Check 2: Wget availability
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Wget Availability"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    print_success "wget is available"
    WGET_VERSION=$(docker exec pepgmp-frontend-prod wget --version 2>&1 | head -1)
    echo "  $WGET_VERSION"
else
    print_error "wget is NOT available"
    echo "  This means the image was built with the old Dockerfile.frontend"
    echo "  Solution: Rebuild frontend image"
fi
echo ""

# Check 3: Nginx process
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Nginx Process"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod ps aux | grep -q "[n]ginx"; then
    print_success "Nginx process is running"
    docker exec pepgmp-frontend-prod ps aux | grep "[n]ginx" | head -3
else
    print_error "Nginx process is NOT running"
    echo "  Checking nginx logs..."
    docker logs pepgmp-frontend-prod --tail 20
fi
echo ""

# Check 4: Port listening
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Port 80 Listening"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod netstat -tuln 2>/dev/null | grep -q ":80 "; then
    print_success "Port 80 is listening"
    docker exec pepgmp-frontend-prod netstat -tuln | grep ":80 "
else
    print_warning "Cannot verify port 80 (netstat may not be available)"
    echo "  Trying alternative check..."
    if docker exec pepgmp-frontend-prod sh -c "nc -z localhost 80" 2>/dev/null; then
        print_success "Port 80 is accessible"
    else
        print_error "Port 80 is not accessible"
    fi
fi
echo ""

# Check 5: Health endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Health Endpoint Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    if docker exec pepgmp-frontend-prod wget --spider --no-verbose http://localhost/health 2>&1 | grep -q "200 OK\|200"; then
        print_success "Health endpoint is accessible"
    else
        print_error "Health endpoint is not accessible"
        echo "  Response:"
        docker exec pepgmp-frontend-prod wget --spider --no-verbose http://localhost/health 2>&1 || true
    fi
else
    print_warning "Cannot test health endpoint (wget not available)"
fi
echo ""

# Check 6: Root endpoint
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Root Endpoint Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    RESPONSE=$(docker exec pepgmp-frontend-prod wget -qO- http://localhost/ 2>&1 | head -5)
    if echo "$RESPONSE" | grep -q "DOCTYPE\|html"; then
        print_success "Root endpoint returns HTML"
        echo "  Response preview:"
        echo "$RESPONSE"
    else
        print_error "Root endpoint does not return HTML"
        echo "  Response:"
        echo "$RESPONSE"
    fi
else
    print_warning "Cannot test root endpoint (wget not available)"
fi
echo ""

# Check 7: Reverse proxy access
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Reverse Proxy Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-nginx-prod; then
    RESPONSE=$(docker exec pepgmp-nginx-prod wget -qO- http://frontend:80/ 2>&1 | head -5)
    if echo "$RESPONSE" | grep -q "DOCTYPE\|html"; then
        print_success "Reverse proxy can access frontend"
        echo "  Response preview:"
        echo "$RESPONSE"
    else
        print_error "Reverse proxy cannot access frontend properly"
        echo "  Response:"
        echo "$RESPONSE"
    fi
else
    print_warning "Reverse proxy nginx container is not running"
fi
echo ""

# Summary
echo "========================================================================="
echo "Summary"
echo "========================================================================="
echo ""

if [ "$HEALTH_STATUS" = "healthy" ] && docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    print_success "Frontend container is working correctly!"
    echo ""
    echo "Next steps:"
    echo "  1. Access frontend: http://localhost/"
    echo "  2. Check browser console (F12) for any JavaScript errors"
    echo "  3. Verify API calls are working"
elif [ "$HEALTH_STATUS" = "unhealthy" ] || ! docker exec pepgmp-frontend-prod which wget >/dev/null 2>&1; then
    print_error "Frontend container needs to be rebuilt"
    echo ""
    echo "Required actions:"
    echo "  1. Rebuild frontend image with fixed Dockerfile.frontend:"
    echo "     cd /mnt/f/code/PythonCode/Pyt"
    echo "     bash scripts/build_prod_only.sh 20251202"
    echo ""
    echo "  2. Export and import to WSL2:"
    echo "     # In Windows PowerShell:"
    echo "     .\\scripts\\export_images_to_wsl.ps1 20251202"
    echo ""
    echo "     # In WSL2 Ubuntu:"
    echo "     cd /mnt/f/code/PythonCode/Pyt/docker-images"
    echo "     docker load -i pepgmp-frontend-20251202.tar"
    echo ""
    echo "  3. Restart frontend container:"
    echo "     cd ~/projects/Pyt"
    echo "     docker-compose -f docker-compose.prod.yml stop frontend"
    echo "     docker-compose -f docker-compose.prod.yml rm -f frontend"
    echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend"
else
    print_warning "Frontend container status is unclear"
    echo "  Check logs: docker logs pepgmp-frontend-prod"
fi

echo "========================================================================="

