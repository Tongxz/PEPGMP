#!/bin/bash

################################################################################
# Fix Nginx Directory Structure Issue
# Purpose: Fix incorrect nginx.conf directory structure
################################################################################

set -e

DEPLOY_DIR="${1:-$HOME/projects/Pyt}"

echo "========================================================================="
echo "Fix Nginx Directory Structure"
echo "========================================================================="
echo ""
echo "Deploy directory: $DEPLOY_DIR"
echo ""

# Check if deploy directory exists
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deploy directory does not exist: $DEPLOY_DIR"
    exit 1
fi

cd "$DEPLOY_DIR"

# Check if nginx.conf is incorrectly a directory
if [ -d "nginx/nginx.conf" ]; then
    echo "WARNING: Found directory at nginx/nginx.conf (should be a file)"
    echo "Removing incorrect directory structure..."
    rm -rf nginx/nginx.conf
    echo "[OK] Removed incorrect directory"
fi

# Ensure nginx directory exists
if [ ! -d "nginx" ]; then
    echo "Creating nginx directory..."
    mkdir -p nginx/ssl
    echo "[OK] Created nginx directory"
fi

# Create nginx.conf file if it doesn't exist
if [ ! -f "nginx/nginx.conf" ]; then
    echo "Creating nginx.conf..."
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
    echo "[OK] Created nginx.conf"
else
    echo "[OK] nginx.conf already exists (as a file)"
fi

# Ensure ssl directory exists
if [ ! -d "nginx/ssl" ]; then
    echo "Creating nginx/ssl directory..."
    mkdir -p nginx/ssl
    touch nginx/ssl/.gitkeep
    echo "[OK] Created nginx/ssl directory"
fi

echo ""
echo "========================================================================="
echo "Nginx Structure Fixed"
echo "========================================================================="
echo ""
echo "Verifying structure:"
ls -la nginx/
echo ""
if [ -f "nginx/nginx.conf" ]; then
    echo "[OK] nginx.conf is a file (correct)"
else
    echo "[ERROR] nginx.conf is not a file"
    exit 1
fi
echo ""
echo "Next steps:"
echo "  1. Re-run prepare script:"
echo "     bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes"
echo ""
echo "  2. Or restart services:"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo "========================================================================="

