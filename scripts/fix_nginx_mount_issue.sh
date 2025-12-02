#!/bin/bash

################################################################################
# Fix Nginx Mount Issue
# Purpose: Fix nginx.conf mount issue by recreating container
################################################################################

set -e

DEPLOY_DIR="${1:-$HOME/projects/Pyt}"

echo "========================================================================="
echo "Fix Nginx Mount Issue"
echo "========================================================================="
echo ""
echo "Deploy directory: $DEPLOY_DIR"
echo ""

cd "$DEPLOY_DIR"

# Check if nginx.conf exists
if [ ! -f "nginx/nginx.conf" ]; then
    echo "ERROR: nginx.conf does not exist"
    exit 1
fi

echo "[OK] nginx.conf exists"
echo ""

# Stop and remove nginx container
echo "Stopping and removing nginx container..."
docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true
docker-compose -f docker-compose.prod.yml rm -f nginx 2>/dev/null || true

echo "[OK] Nginx container removed"
echo ""

# Verify nginx.conf path
NGINX_CONF_PATH=$(realpath nginx/nginx.conf)
echo "nginx.conf path: $NGINX_CONF_PATH"
echo ""

# Check file permissions
ls -la nginx/nginx.conf
echo ""

# Recreate nginx container
echo "Recreating nginx container..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d nginx

echo ""
echo "[OK] Nginx container recreated"
echo ""

# Wait a few seconds
sleep 3

# Check nginx status
echo "Checking nginx status..."
docker-compose -f docker-compose.prod.yml ps nginx

echo ""
echo "========================================================================="
echo "Fix Complete"
echo "========================================================================="
echo ""
echo "Next steps:"
echo "  1. Check nginx logs: docker-compose -f docker-compose.prod.yml logs nginx"
echo "  2. Test nginx config: docker exec pepgmp-nginx-prod nginx -t"
echo "  3. Test access: curl http://localhost/api/v1/monitoring/health"
echo ""
echo "========================================================================="

