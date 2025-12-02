# 修复前端页面访问问题

## 问题分析

前端页面无法访问的原因：
1. **Nginx 配置问题** - 当前 nginx.conf 配置了 HTTPS，但没有 SSL 证书
2. **前端服务未启动** - docker-compose.prod.yml 中可能没有前端服务
3. **Nginx 配置错误** - location / 配置为静态文件，但没有前端容器

## 快速诊断

在 WSL2 Ubuntu 中运行：

```bash
cd ~/projects/Pyt

# 检查前端镜像
docker images | grep pepgmp-frontend

# 检查前端容器
docker ps -a | grep pepgmp-frontend

# 检查 docker-compose 配置
grep -A 10 "^  frontend:" docker-compose.prod.yml || echo "Frontend service not found"

# 检查 nginx 配置
cat nginx/nginx.conf | grep -E "listen|server_name|location /"
```

## 解决方案

### 方案 1: 修复 Nginx 配置（推荐 - 如果不需要前端容器）

如果前端是静态文件，更新 nginx 配置为简单的 HTTP 配置：

```bash
cd ~/projects/Pyt

# 备份原配置
cp nginx/nginx.conf nginx/nginx.conf.backup

# 创建简单的 HTTP 配置
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

        # Frontend static files (if frontend container exists)
        location / {
            # Option 1: Proxy to frontend container (if exists)
            # proxy_pass http://frontend:80;
            # proxy_set_header Host $host;
            # proxy_set_header X-Real-IP $remote_addr;
            # proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            # proxy_set_header X-Forwarded-Proto $scheme;

            # Option 2: Serve static files from local directory
            # root /usr/share/nginx/html;
            # try_files $uri $uri/ /index.html;

            # Option 3: Redirect to API docs (temporary)
            return 301 http://$host:8000/docs;
        }
    }
}
EOF

# 重新启动 nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### 方案 2: 添加前端服务（如果前端镜像已导入）

如果前端镜像已导入，添加前端服务到 docker-compose.prod.yml：

```bash
cd ~/projects/Pyt

# 编辑 docker-compose.prod.yml，在 nginx 服务之前添加：
```

```yaml
  # ==================== Frontend 前端（生产） ====================
  frontend:
    image: pepgmp-frontend:${IMAGE_TAG:-latest}
    container_name: pepgmp-frontend-prod
    networks:
      - frontend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

然后更新 nginx 配置，代理到前端容器：

```bash
# 更新 nginx.conf 中的 location / 部分
sed -i 's|# Option 1: Proxy to frontend container|proxy_pass http://frontend:80;|' nginx/nginx.conf
```

### 方案 3: 直接访问 API（临时方案）

如果暂时不需要前端，直接访问 API：

- **API 文档**: `http://localhost:8000/docs`
- **健康检查**: `http://localhost:8000/api/v1/monitoring/health`
- **API 基础路径**: `http://localhost:8000/api/v1/`

## 推荐操作步骤

### 步骤 1: 检查前端镜像

```bash
cd ~/projects/Pyt

# 检查是否有前端镜像
docker images | grep pepgmp-frontend
```

### 步骤 2: 根据情况选择方案

**如果没有前端镜像**：
- 使用方案 1，更新 nginx 配置为简单的 HTTP 配置
- 或者直接访问 API：`http://localhost:8000/docs`

**如果有前端镜像**：
- 使用方案 2，添加前端服务并更新 nginx 配置

### 步骤 3: 重新启动服务

```bash
cd ~/projects/Pyt

# 重新启动 nginx（如果修改了配置）
docker-compose -f docker-compose.prod.yml restart nginx

# 或启动前端服务（如果添加了）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

## 验证访问

```bash
# 测试 nginx
curl http://localhost/api/v1/monitoring/health

# 测试 API 直接访问
curl http://localhost:8000/api/v1/monitoring/health

# 如果配置了前端，访问
curl http://localhost/
```

