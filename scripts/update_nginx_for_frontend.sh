#!/bin/bash

################################################################################
# Update Nginx Configuration for Frontend Access
# Purpose: Update nginx.conf to properly serve frontend and proxy API
################################################################################

set -e

# Get deploy directory from parameter, or use current directory, or use default
if [ -n "$1" ]; then
    DEPLOY_DIR="$1"
elif [ -d "$HOME/projects/Pyt" ]; then
    DEPLOY_DIR="$HOME/projects/Pyt"
elif [ -d "./nginx" ] || [ -f "./docker-compose.prod.yml" ]; then
    DEPLOY_DIR="$(pwd)"
else
    DEPLOY_DIR="${HOME}/projects/Pyt"
fi

echo "========================================================================="
echo "Update Nginx Configuration for Frontend"
echo "========================================================================="
echo ""
echo "Deploy directory: $DEPLOY_DIR"
echo ""

# Check if deploy directory exists
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deploy directory does not exist: $DEPLOY_DIR"
    echo ""
    echo "Usage: bash update_nginx_for_frontend.sh [DEPLOY_DIR]"
    echo "Example: bash update_nginx_for_frontend.sh ~/projects/Pyt"
    echo "Or run from the deploy directory: cd ~/projects/Pyt && bash update_nginx_for_frontend.sh"
    exit 1
fi

cd "$DEPLOY_DIR"

# Check if nginx directory exists
if [ ! -d "nginx" ]; then
    echo "ERROR: nginx directory does not exist"
    exit 1
fi

# Backup current configuration
if [ -f "nginx/nginx.conf" ]; then
    cp nginx/nginx.conf nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "[OK] Backed up current nginx.conf"
fi

# Check if frontend container exists
FRONTEND_EXISTS=$(docker ps -a 2>/dev/null | grep -c pepgmp-frontend || echo "0")
FRONTEND_IMAGE_EXISTS=$(docker images 2>/dev/null | grep -c pepgmp-frontend || echo "0")

# Clean up any newlines
FRONTEND_EXISTS=$(echo "$FRONTEND_EXISTS" | tr -d '\n' | head -1)
FRONTEND_IMAGE_EXISTS=$(echo "$FRONTEND_IMAGE_EXISTS" | tr -d '\n' | head -1)

echo "Frontend container exists: $FRONTEND_EXISTS"
echo "Frontend image exists: $FRONTEND_IMAGE_EXISTS"
echo ""

# Create nginx configuration
if [ "${FRONTEND_EXISTS:-0}" -gt 0 ] || [ "${FRONTEND_IMAGE_EXISTS:-0}" -gt 0 ]; then
    echo "Creating nginx configuration with frontend support..."
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

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        # API proxy
        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        # Root location - proxy to API (frontend can be added later)
        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF
else
    echo "Creating nginx configuration without frontend (API only)..."
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

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        # API proxy
        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        # Root location - redirect to API docs
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
fi

chmod 644 nginx/nginx.conf

echo ""
echo "[OK] nginx.conf updated"
echo ""
echo "Configuration summary:"
if [ "${FRONTEND_EXISTS:-0}" -gt 0 ] || [ "${FRONTEND_IMAGE_EXISTS:-0}" -gt 0 ]; then
    echo "  - Frontend proxy: Enabled (proxies to frontend:80)"
else
    echo "  - Frontend proxy: Disabled (no frontend container/image found)"
fi
echo "  - API proxy: Enabled (proxies to api:8000)"
echo ""
echo "Next steps:"
echo "  1. Restart nginx:"
echo "     docker-compose -f docker-compose.prod.yml restart nginx"
echo ""
echo "  2. If frontend image exists but container not running, add frontend service:"
echo "     # Edit docker-compose.prod.yml and add frontend service"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend"
echo ""
echo "========================================================================="

