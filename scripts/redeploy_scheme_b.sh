#!/bin/bash

################################################################################
# 方案 B 快速重新部署脚本
# Purpose: Quick redeployment script for Scheme B (Single Nginx)
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

echo "========================================================================="
echo "方案 B 快速重新部署"
echo "========================================================================="
echo ""

# Get deployment directory
DEPLOY_DIR="${1:-$HOME/projects/Pyt}"
cd "$DEPLOY_DIR" || {
    print_error "Cannot access deployment directory: $DEPLOY_DIR"
    exit 1
}

print_info "Deployment directory: $DEPLOY_DIR"
echo ""

# Step 1: Stop current services
print_info "Step 1: Stopping current services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null || true
sleep 3
print_success "Services stopped"
echo ""

# Step 2: Verify frontend image (static files will be auto-extracted)
print_info "Step 2: Verifying frontend image..."

# Check if frontend image exists
if docker images | grep -q "pepgmp-frontend"; then
    print_success "Frontend image found"
    print_info "  → Static files will be auto-extracted when frontend container starts"
else
    print_error "Frontend image not found!"
    echo ""
    print_info "You need to import frontend image:"
    echo "  1. Build in Windows: .\\scripts\\build_prod_only.ps1 20251202"
    echo "  2. Export: .\\scripts\\export_images_to_wsl.ps1 20251202"
    echo "  3. Import in WSL2: docker load -i /mnt/f/code/PythonCode/Pyt/docker-images/pepgmp-frontend-*.tar"
    exit 1
fi
echo ""

# Step 3: Verify configuration files
print_info "Step 3: Verifying configuration files..."

if [ ! -f "docker-compose.prod.yml" ]; then
    print_error "docker-compose.prod.yml not found!"
    exit 1
fi

if [ ! -f "nginx/nginx.conf" ]; then
    print_error "nginx/nginx.conf not found!"
    exit 1
fi

if [ ! -f ".env.production" ]; then
    print_error ".env.production not found!"
    print_info "Run: bash scripts/generate_production_config.sh"
    exit 1
fi

# Verify nginx config syntax
# Note: Testing nginx config outside docker network will show "host not found" for upstream,
# but this is expected and not an error. The config is valid when running in docker-compose.
print_info "Testing nginx configuration syntax..."
NGINX_TEST_OUTPUT=$(docker run --rm \
    -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
    nginx:alpine \
    nginx -t 2>&1)

# Check for syntax errors (not upstream resolution errors)
if echo "$NGINX_TEST_OUTPUT" | grep -q "syntax is ok"; then
    print_success "Nginx configuration syntax is valid"
    # Note: "host not found" warnings are expected when testing outside docker network
    if echo "$NGINX_TEST_OUTPUT" | grep -q "host not found"; then
        print_info "Note: 'host not found' warnings are expected (testing outside docker network)"
    fi
else
    print_error "Nginx configuration has syntax errors!"
    echo "$NGINX_TEST_OUTPUT"
    exit 1
fi

print_success "Configuration files verified"
echo ""

# Step 4: Start services
print_info "Step 4: Starting services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

print_success "Services started"
echo ""

# Step 5: Wait for frontend-init to extract static files
print_info "Step 5: Waiting for frontend-init container to extract static files..."
sleep 10

# Verify static files were extracted
if [ -f "frontend/dist/index.html" ]; then
    STATIC_FILE_COUNT=$(find frontend/dist -type f 2>/dev/null | wc -l)
    print_success "Static files auto-extracted ($STATIC_FILE_COUNT files)"
else
    print_warning "Static files not yet extracted, waiting..."
    sleep 10
    if [ -f "frontend/dist/index.html" ]; then
        STATIC_FILE_COUNT=$(find frontend/dist -type f 2>/dev/null | wc -l)
        print_success "Static files extracted ($STATIC_FILE_COUNT files)"
    else
        print_error "Static files extraction failed or taking too long"
        print_info "Check frontend-init container logs: docker logs pepgmp-frontend-init"
    fi
fi
echo ""

# Step 6: Wait for services to be ready
print_info "Step 6: Waiting for services to be ready..."
sleep 10

# Step 7: Check service status
print_info "Step 7: Checking service status..."
docker-compose -f docker-compose.prod.yml ps
echo ""

# Step 8: Test deployment
print_info "Step 8: Testing deployment..."

# Test health endpoint
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    print_success "Health endpoint: OK (HTTP $HEALTH_RESPONSE)"
else
    print_warning "Health endpoint: Failed (HTTP $HEALTH_RESPONSE)"
fi

# Test frontend
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    print_success "Frontend: OK (HTTP $FRONTEND_RESPONSE)"
else
    print_warning "Frontend: Failed (HTTP $FRONTEND_RESPONSE)"
fi

# Test API
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/monitoring/health 2>/dev/null || echo "000")
if [ "$API_RESPONSE" = "200" ]; then
    print_success "API proxy: OK (HTTP $API_RESPONSE)"
else
    print_warning "API proxy: Failed (HTTP $API_RESPONSE)"
fi

echo ""
echo "========================================================================="
print_success "部署完成！"
echo "========================================================================="
echo ""
print_info "Next steps:"
echo "  1. Open browser: http://localhost/"
echo "  2. Check browser console (F12) for errors"
echo "  3. Run full test: bash /mnt/f/code/PythonCode/Pyt/scripts/test_scheme_b.sh"
echo ""
print_info "Service status:"
echo "  docker-compose -f docker-compose.prod.yml ps"
echo ""
print_info "View logs:"
echo "  docker logs pepgmp-nginx-prod"
echo "  docker logs pepgmp-api-prod"
echo ""

