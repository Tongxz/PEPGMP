#!/bin/bash

################################################################################
# Fix Nginx Mount Issue
# Purpose: Create nginx directory and configuration file if missing
################################################################################

set -e

DEPLOY_DIR="${1:-$HOME/projects/Pyt}"

echo "========================================================================="
echo "Fix Nginx Mount Issue"
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

# Create nginx directory if it doesn't exist
if [ ! -d "nginx" ]; then
    echo "Creating nginx directory..."
    mkdir -p nginx/ssl
    echo "[OK] Created nginx directory"
else
    echo "[OK] nginx directory already exists"
fi

# Create nginx.conf if it doesn't exist
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
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    # Upstream API server
    upstream api_backend {
        server api:8000;
    }

    # HTTP server
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

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        # Default location
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
    echo "[OK] nginx.conf already exists"
fi

# Create ssl directory if it doesn't exist
if [ ! -d "nginx/ssl" ]; then
    echo "Creating nginx/ssl directory..."
    mkdir -p nginx/ssl
    touch nginx/ssl/.gitkeep
    echo "[OK] Created nginx/ssl directory"
else
    echo "[OK] nginx/ssl directory already exists"
fi

echo ""
echo "========================================================================="
echo "Nginx Configuration Ready"
echo "========================================================================="
echo ""
echo "Files created:"
ls -la nginx/
echo ""
echo "Next steps:"
echo "  1. Restart services:"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo "  2. Or if nginx is not needed, comment out nginx service in docker-compose.prod.yml"
echo ""
echo "========================================================================="

