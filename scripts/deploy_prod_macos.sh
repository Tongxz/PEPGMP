#!/bin/bash

################################################################################
# macOS Production Deployment Script
# Purpose: Deploy production environment on macOS
# Usage: bash scripts/deploy_prod_macos.sh [DEPLOY_DIR] [VERSION_TAG]
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DEPLOY_DIR="${1:-$HOME/projects/Pyt}"
VERSION_TAG="${2:-$(date +%Y%m%d)}"

echo "========================================================================="
echo -e "${BLUE}macOS Production Deployment${NC}"
echo "========================================================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Deploy directory: $DEPLOY_DIR"
echo "Image version tag: $VERSION_TAG"
echo ""

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

# Step 1: Check Docker
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 1]${NC} Checking Docker environment"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if ! command -v docker &> /dev/null; then
    check_failed "Docker is not installed"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &> /dev/null; then
    check_failed "Docker daemon is not running"
    echo "Please start Docker Desktop and wait for it to fully start"
    exit 1
fi

check_passed "Docker is installed and running"
check_info "Docker version: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    check_failed "Docker Compose is not available"
    exit 1
fi

check_passed "Docker Compose is available"

echo ""

# Step 2: Check port availability
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 2]${NC} Checking port availability"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

PORT_80_IN_USE=$(lsof -i :80 2>/dev/null | grep -v "COMMAND" | wc -l | tr -d ' ')
PORT_8000_IN_USE=$(lsof -i :8000 2>/dev/null | grep -v "COMMAND" | wc -l | tr -d ' ')

if [ "$PORT_80_IN_USE" -gt 0 ]; then
    check_warning "Port 80 is in use"
    check_info "You may need to modify docker-compose.prod.yml to use port 8080"
    echo "  Current usage:"
    lsof -i :80 2>/dev/null | head -3
else
    check_passed "Port 80 is available"
fi

if [ "$PORT_8000_IN_USE" -gt 0 ]; then
    check_warning "Port 8000 is in use"
    echo "  Current usage:"
    lsof -i :8000 2>/dev/null | head -3
else
    check_passed "Port 8000 is available"
fi

echo ""

# Step 3: Prepare deployment directory
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 3]${NC} Preparing deployment directory"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "$DEPLOY_DIR" ]; then
    check_info "Creating deployment directory: $DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"
    check_passed "Directory created"
else
    check_passed "Deployment directory exists"
fi

# Run prepare_minimal_deploy.sh
check_info "Running prepare_minimal_deploy.sh..."
if bash "$PROJECT_ROOT/scripts/prepare_minimal_deploy.sh" "$DEPLOY_DIR" "no"; then
    check_passed "Deployment package prepared"
else
    check_failed "Failed to prepare deployment package"
    exit 1
fi

echo ""

# Step 4: Generate production configuration
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 4]${NC} Generating production configuration"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$DEPLOY_DIR"

if [ ! -f ".env.production" ]; then
    check_info "Generating .env.production..."
    if bash "$PROJECT_ROOT/scripts/generate_production_config.sh" -y; then
        check_passed "Configuration generated"
    else
        check_failed "Failed to generate configuration"
        exit 1
    fi
else
    check_warning ".env.production already exists"
    read -p "Overwrite existing configuration? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        bash "$PROJECT_ROOT/scripts/generate_production_config.sh" -y
        check_passed "Configuration regenerated"
    else
        check_info "Using existing configuration"
    fi
fi

# Update IMAGE_TAG
check_info "Setting IMAGE_TAG to $VERSION_TAG"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed syntax
    sed -i '' "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production
else
    # Linux sed syntax
    sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production
fi

check_passed "IMAGE_TAG updated to $VERSION_TAG"

echo ""

# Step 5: Build production images
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 5]${NC} Building production images"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_ROOT"

check_info "Building images with tag: $VERSION_TAG"
if bash "$PROJECT_ROOT/scripts/build_prod_only.sh" "$VERSION_TAG"; then
    check_passed "Images built successfully"
else
    check_failed "Failed to build images"
    exit 1
fi

# Verify images
check_info "Verifying images..."
# Use --format for more reliable matching
BACKEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-backend:$VERSION_TAG" || echo "0")
if [ "$BACKEND_FOUND" -gt 0 ]; then
    check_passed "Backend image exists (pepgmp-backend:$VERSION_TAG)"
else
    check_failed "Backend image not found (pepgmp-backend:$VERSION_TAG)"
    check_info "Available backend images:"
    docker images --format "{{.Repository}}:{{.Tag}}" | grep "pepgmp-backend" | head -5
    exit 1
fi

FRONTEND_FOUND=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -c "pepgmp-frontend:$VERSION_TAG" || echo "0")
if [ "$FRONTEND_FOUND" -gt 0 ]; then
    check_passed "Frontend image exists (pepgmp-frontend:$VERSION_TAG)"
else
    check_failed "Frontend image not found (pepgmp-frontend:$VERSION_TAG)"
    check_info "Available frontend images:"
    docker images --format "{{.Repository}}:{{.Tag}}" | grep "pepgmp-frontend" | head -5
    exit 1
fi

echo ""

# Step 6: Clean up old containers (if any)
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 6]${NC} Cleaning up old containers"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$DEPLOY_DIR"

# Check for existing containers with same names
check_info "Checking for existing containers..."
EXISTING_CONTAINERS=$(docker ps -a --filter "name=pepgmp-" --format "{{.Names}}" 2>/dev/null || echo "")

if [ -n "$EXISTING_CONTAINERS" ]; then
    check_warning "Found existing containers:"
    echo "$EXISTING_CONTAINERS" | while read -r container; do
        echo "  - $container"
    done

    # Stop and remove old containers from this compose file
    check_info "Stopping and removing old containers..."
    if docker compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null; then
        check_passed "Old containers cleaned up"
    else
        check_warning "Some containers may not have been cleaned up (this is OK if they're from different compose files)"
    fi
else
    check_info "No existing containers found"
fi

echo ""

# Step 7: Start services
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 7]${NC} Starting services"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_info "Starting Docker Compose services..."
if docker compose -f docker-compose.prod.yml --env-file .env.production up -d; then
    check_passed "Services started"
else
    check_failed "Failed to start services"
    check_info "Trying to get more details..."
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d 2>&1 | tail -20
    exit 1
fi

# Wait for services to be ready
check_info "Waiting for services to be ready..."
sleep 10

# Check service status
check_info "Service status:"
docker compose -f docker-compose.prod.yml ps

echo ""

# Step 8: Verify deployment
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[Step 8]${NC} Verifying deployment"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check frontend-init
FRONTEND_INIT_STATUS=$(docker inspect --format='{{.State.Status}}' pepgmp-frontend-init 2>/dev/null || echo "not found")
if [ "$FRONTEND_INIT_STATUS" = "exited" ]; then
    EXIT_CODE=$(docker inspect --format='{{.State.ExitCode}}' pepgmp-frontend-init 2>/dev/null || echo "unknown")
    if [ "$EXIT_CODE" = "0" ]; then
        check_passed "Frontend-init completed successfully"
    else
        check_failed "Frontend-init exited with code $EXIT_CODE"
        check_info "Check logs: docker logs pepgmp-frontend-init"
    fi
else
    check_warning "Frontend-init status: $FRONTEND_INIT_STATUS"
fi

# Check static files
if [ -f "frontend/dist/index.html" ]; then
    check_passed "Static files exist"
else
    check_failed "Static files not found"
fi

# Test HTTP endpoints
echo ""
check_info "Testing HTTP endpoints..."

# Determine port (check if 80 is used, fallback to 8080)
HTTP_PORT=80
if [ "$PORT_80_IN_USE" -gt 0 ]; then
    HTTP_PORT=8080
    check_warning "Using port 8080 instead of 80"
fi

# Test frontend
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$HTTP_PORT/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    check_passed "Frontend is accessible (HTTP $HTTP_CODE)"
else
    check_failed "Frontend returned HTTP $HTTP_CODE"
fi

# Test API
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$HTTP_PORT/api/v1/monitoring/health" 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
    check_passed "API is accessible (HTTP $API_CODE)"
else
    check_failed "API returned HTTP $API_CODE"
fi

echo ""

# Summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Deployment Summary${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Deployment directory: $DEPLOY_DIR"
echo "Image version: $VERSION_TAG"
echo ""
echo "Access URLs:"
if [ "$PORT_80_IN_USE" -gt 0 ]; then
    echo "  Frontend: http://localhost:8080/"
    echo "  API:      http://localhost:8080/api/v1/monitoring/health"
    echo "  Health:   http://localhost:8080/health"
    echo ""
    check_warning "Port 80 was in use, using port 8080 instead"
    check_info "You can modify docker-compose.prod.yml to use a different port"
else
    echo "  Frontend: http://localhost/"
    echo "  API:      http://localhost/api/v1/monitoring/health"
    echo "  Health:   http://localhost/health"
fi
echo ""
echo "Useful commands:"
echo "  View logs:    docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:         docker compose -f docker-compose.prod.yml down"
echo "  Restart:     docker compose -f docker-compose.prod.yml restart"
echo "  Status:       docker compose -f docker-compose.prod.yml ps"
echo ""
echo "Diagnostic script:"
echo "  bash $PROJECT_ROOT/scripts/diagnose_frontend_whitescreen.sh $DEPLOY_DIR"
echo ""
echo "========================================================================="
