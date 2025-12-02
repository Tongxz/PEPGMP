#!/bin/bash

################################################################################
# Fix Nginx Configuration - Remove Frontend Upstream
# Purpose: Update nginx.conf to work without frontend container
################################################################################

set -e

DEPLOY_DIR="${1:-$(pwd)}"

if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Directory does not exist: $DEPLOY_DIR"
    exit 1
fi

cd "$DEPLOY_DIR"

if [ ! -f "nginx/nginx.conf" ]; then
    echo "ERROR: nginx.conf not found"
    exit 1
fi

# Backup
cp nginx/nginx.conf nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)

# Create configuration without frontend upstream
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

        # Root location - proxy to API
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

chmod 644 nginx/nginx.conf

echo "[OK] nginx.conf updated (removed frontend upstream)"
echo ""
echo "Next step:"
echo "  docker-compose -f docker-compose.prod.yml restart nginx"

