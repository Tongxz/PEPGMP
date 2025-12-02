# 添加前端服务

## 已完成的配置

✅ 已在 `docker-compose.prod.yml` 中添加前端服务配置

## 启动前端服务

### 步骤 1: 检查前端镜像

```bash
cd ~/projects/Pyt

# 检查前端镜像是否存在
docker images | grep pepgmp-frontend

# 应该看到类似：
# pepgmp-frontend    20251201    ...    ...    ...
```

### 步骤 2: 如果前端镜像不存在，需要导入

如果前端镜像不存在，需要从 Windows 导出并导入：

**在 Windows PowerShell 中**:
```powershell
cd F:\Code\PythonCode\Pyt
.\scripts\export_images_to_wsl.ps1 20251201
```

**在 WSL2 Ubuntu 中**:
```bash
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251201.tar

# 验证
docker images | grep pepgmp-frontend
```

### 步骤 3: 更新 Nginx 配置以支持前端

```bash
cd ~/projects/Pyt

# 运行更新脚本（会自动检测前端镜像）
bash /mnt/f/code/PythonCode/Pyt/scripts/update_nginx_for_frontend.sh

# 或者手动更新（如果脚本有问题）
python3 << 'PYEOF'
import os

nginx_conf = """events {
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

    upstream frontend_backend {
        server frontend:80;
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

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        location / {
            proxy_pass http://frontend_backend/;
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
"""

with open('nginx/nginx.conf', 'w') as f:
    f.write(nginx_conf)

os.chmod('nginx/nginx.conf', 0o644)
print("✓ nginx.conf updated with frontend support")
PYEOF
```

### 步骤 4: 启动前端服务

```bash
cd ~/projects/Pyt

# 启动前端服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend

# 等待几秒让前端启动
sleep 5

# 检查前端服务状态
docker-compose -f docker-compose.prod.yml ps frontend
```

### 步骤 5: 重启 Nginx

```bash
cd ~/projects/Pyt

# 重启 nginx 以加载新配置
docker-compose -f docker-compose.prod.yml restart nginx

# 等待几秒
sleep 3

# 检查 nginx 状态
docker-compose -f docker-compose.prod.yml ps nginx

# 测试配置
docker exec pepgmp-nginx-prod nginx -t
```

### 步骤 6: 验证所有服务

```bash
cd ~/projects/Pyt

# 查看所有服务状态
docker-compose -f docker-compose.prod.yml ps

# 应该看到：
# - pepgmp-postgres-prod (healthy)
# - pepgmp-redis-prod (healthy)
# - pepgmp-api-prod (up)
# - pepgmp-frontend-prod (up)
# - pepgmp-nginx-prod (up)
```

## 验证访问

### 测试前端访问

```bash
# 通过 nginx 访问前端
curl http://localhost/

# 通过 nginx 访问 API
curl http://localhost/api/v1/monitoring/health

# 直接访问前端（如果暴露了端口）
# curl http://localhost:8080/
```

### 浏览器访问

- **前端页面**: `http://localhost/`
- **API 文档**: `http://localhost:8000/docs`
- **API 健康检查**: `http://localhost/api/v1/monitoring/health`

## 故障排查

### 如果前端服务启动失败

```bash
# 查看前端日志
docker-compose -f docker-compose.prod.yml logs frontend

# 检查前端镜像
docker images | grep pepgmp-frontend

# 如果镜像不存在，需要导入
```

### 如果 Nginx 报错 "host not found in upstream"

```bash
# 确保前端服务已启动
docker-compose -f docker-compose.prod.yml ps frontend

# 如果前端未启动，先启动前端
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend

# 然后重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### 如果前端页面显示 502 Bad Gateway

```bash
# 检查前端容器是否健康
docker inspect pepgmp-frontend-prod --format='{{.State.Health.Status}}'

# 检查前端日志
docker-compose -f docker-compose.prod.yml logs frontend | tail -50

# 测试前端容器内部
docker exec pepgmp-frontend-prod wget -qO- http://localhost/health
```

## 完整启动命令

```bash
cd ~/projects/Pyt

# 1. 确保前端镜像存在
docker images | grep pepgmp-frontend

# 2. 更新 nginx 配置
bash /mnt/f/code/PythonCode/Pyt/scripts/update_nginx_for_frontend.sh

# 3. 启动所有服务（包括前端）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 4. 等待服务启动
sleep 10

# 5. 检查所有服务状态
docker-compose -f docker-compose.prod.yml ps

# 6. 测试访问
curl http://localhost/api/v1/monitoring/health
curl http://localhost/
```

