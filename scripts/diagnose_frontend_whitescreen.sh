#!/bin/bash

################################################################################
# Diagnose Frontend White Screen Issue
# Purpose: Check frontend container, nginx configuration, and static files
################################################################################

set -e

echo "========================================================================="
echo "Frontend White Screen Diagnosis"
echo "========================================================================="
echo ""

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Check 1: Frontend container status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Frontend Container Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-frontend-prod; then
    print_success "Frontend container is running"
    docker ps | grep pepgmp-frontend-prod
else
    print_error "Frontend container is not running"
    echo "  Checking if container exists..."
    docker ps -a | grep pepgmp-frontend-prod || echo "  Container does not exist"
fi
echo ""

# Check 2: Frontend container files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Frontend Container Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-frontend-prod; then
    print_info "Checking files in frontend container..."
    
    # Check if dist directory exists
    if docker exec pepgmp-frontend-prod test -d /usr/share/nginx/html; then
        print_success "/usr/share/nginx/html directory exists"
        
        # List files
        echo "  Files in /usr/share/nginx/html:"
        docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html | head -20
        
        # Check for index.html
        if docker exec pepgmp-frontend-prod test -f /usr/share/nginx/html/index.html; then
            print_success "index.html exists"
            echo "  index.html content (first 20 lines):"
            docker exec pepgmp-frontend-prod head -20 /usr/share/nginx/html/index.html
        else
            print_error "index.html does not exist!"
        fi
        
        # Check for assets directory
        if docker exec pepgmp-frontend-prod test -d /usr/share/nginx/html/assets; then
            print_success "assets directory exists"
            echo "  Assets files:"
            docker exec pepgmp-frontend-prod find /usr/share/nginx/html/assets -type f | head -10
        else
            print_warning "assets directory does not exist"
        fi
    else
        print_error "/usr/share/nginx/html directory does not exist!"
    fi
else
    print_warning "Frontend container is not running, cannot check files"
fi
echo ""

# Check 3: Frontend container nginx configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Frontend Container Nginx Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-frontend-prod; then
    print_info "Checking nginx configuration in frontend container..."
    
    if docker exec pepgmp-frontend-prod test -f /etc/nginx/conf.d/default.conf; then
        print_success "Nginx configuration file exists"
        echo "  Configuration content:"
        docker exec pepgmp-frontend-prod cat /etc/nginx/conf.d/default.conf
    else
        print_error "Nginx configuration file does not exist!"
    fi
    
    # Test nginx config
    echo ""
    print_info "Testing nginx configuration..."
    if docker exec pepgmp-frontend-prod nginx -t 2>&1; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration has errors!"
    fi
else
    print_warning "Frontend container is not running, cannot check nginx config"
fi
echo ""

# Check 4: Test frontend container directly
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Test Frontend Container Direct Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-frontend-prod; then
    print_info "Testing direct access to frontend container..."
    
    # Get container IP or use service name
    FRONTEND_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pepgmp-frontend-prod 2>/dev/null || echo "")
    
    if [ -n "$FRONTEND_IP" ]; then
        print_info "Frontend container IP: $FRONTEND_IP"
        echo "  Testing HTTP access..."
        docker exec pepgmp-frontend-prod wget -qO- http://localhost/ 2>&1 | head -20 || print_error "Failed to access frontend"
    fi
    
    # Test health endpoint
    echo ""
    print_info "Testing health endpoint..."
    docker exec pepgmp-frontend-prod wget -qO- http://localhost/health 2>&1 || print_warning "Health endpoint not accessible"
else
    print_warning "Frontend container is not running, cannot test access"
fi
echo ""

# Check 5: Reverse proxy nginx configuration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Reverse Proxy Nginx Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-nginx-prod; then
    print_info "Checking reverse proxy nginx configuration..."
    
    if docker exec pepgmp-nginx-prod test -f /etc/nginx/nginx.conf; then
        print_success "Nginx configuration file exists"
        echo "  Frontend proxy configuration:"
        docker exec pepgmp-nginx-prod grep -A 10 "location /" /etc/nginx/nginx.conf | head -15
    else
        print_error "Nginx configuration file does not exist!"
    fi
    
    # Test nginx config
    echo ""
    print_info "Testing nginx configuration..."
    if docker exec pepgmp-nginx-prod nginx -t 2>&1; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration has errors!"
    fi
else
    print_warning "Reverse proxy nginx container is not running"
fi
echo ""

# Check 6: Network connectivity
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Network Connectivity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if docker ps | grep -q pepgmp-nginx-prod && docker ps | grep -q pepgmp-frontend-prod; then
    print_info "Testing connectivity from nginx to frontend..."
    
    # Test if nginx can reach frontend
    if docker exec pepgmp-nginx-prod wget -qO- http://frontend:80/ 2>&1 | head -5; then
        print_success "Nginx can reach frontend container"
    else
        print_error "Nginx cannot reach frontend container!"
        echo "  Checking network..."
        docker exec pepgmp-nginx-prod ping -c 2 frontend 2>&1 || print_warning "Ping test failed"
    fi
else
    print_warning "Cannot test connectivity (containers not running)"
fi
echo ""

# Check 7: Browser console errors (suggestions)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Common Issues and Solutions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
print_info "Common causes of white screen:"
echo "  1. index.html exists but JavaScript/CSS files are missing"
echo "  2. Base URL mismatch (assets loaded from wrong path)"
echo "  3. CORS issues"
echo "  4. JavaScript errors (check browser console)"
echo "  5. Nginx proxy configuration incorrect"
echo ""

print_info "Next steps:"
echo "  1. Check browser console (F12) for JavaScript errors"
echo "  2. Check Network tab to see which files are failing to load"
echo "  3. Verify BASE_URL in vite.config.ts matches deployment path"
echo "  4. Check frontend container logs: docker logs pepgmp-frontend-prod"
echo "  5. Check nginx logs: docker logs pepgmp-nginx-prod"
echo ""

echo "========================================================================="
echo "Diagnosis Complete"
echo "========================================================================="

