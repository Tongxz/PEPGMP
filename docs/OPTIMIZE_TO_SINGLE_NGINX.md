# 优化为单一 Nginx 容器架构

## 当前问题

当前架构存在**双重 Nginx**：
- 前端容器内运行 nginx（服务静态文件）
- 反向代理容器运行 nginx（代理请求）

这导致：
- 资源浪费（两个 nginx 容器）
- 性能开销（请求经过两次 nginx）
- 配置复杂（需要维护两个配置）

## 优化方案：单一 Nginx 容器

### 架构对比

**当前架构**：
```
浏览器 → 反向代理 Nginx → 前端容器 Nginx → 静态文件
```

**优化后架构**：
```
浏览器 → 单一 Nginx → 静态文件（volume 挂载）+ API 代理
```

## 实施步骤

### 步骤 1: 修改前端构建（可选）

如果采用 volume 挂载方式，前端容器可以只构建，不运行 nginx。

### 步骤 2: 修改 docker-compose.prod.yml

创建优化版本的配置：

```yaml
  # ==================== Frontend 前端（仅用于挂载静态文件） ====================
  frontend:
    image: pepgmp-frontend:${IMAGE_TAG:-latest}
    container_name: pepgmp-frontend-prod
    networks:
      - frontend
    restart: "no"  # 只用于 volume 挂载，不自动重启
    # 通过 volume 挂载静态文件到 nginx
    volumes:
      - frontend-dist:/usr/share/nginx/html:ro
    # 不暴露端口，不运行服务

  # ==================== Nginx 反向代理（统一服务） ====================
  nginx:
    image: nginx:alpine
    container_name: pepgmp-nginx-prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - frontend-dist:/usr/share/nginx/html:ro  # 挂载前端静态文件
    networks:
      - frontend
    depends_on:
      - api
      - frontend
    restart: unless-stopped

volumes:
  frontend-dist:
    driver: local
```

### 步骤 3: 修改 nginx 配置

更新 `nginx/nginx.conf`，直接服务静态文件：

```nginx
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

        # 静态文件根目录（从 volume 挂载）
        root /usr/share/nginx/html;
        index index.html;

        # API 代理
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

        # 前端静态文件（支持 Vue Router history 模式）
        location / {
            try_files $uri $uri/ /index.html;

            # 静态资源缓存
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # 错误页面
        error_page 404 /index.html;
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
}
```

## 注意事项

### 方案 A：使用 Volume 挂载（推荐）

**优点**：
- ✅ 前端容器只构建，不运行 nginx
- ✅ 单一 nginx 容器，架构简单
- ✅ 静态文件通过 volume 共享

**缺点**：
- ⚠️ 需要确保前端容器先启动（构建静态文件）
- ⚠️ Volume 需要正确初始化

### 方案 B：直接挂载构建产物目录

如果前端构建产物在主机上，可以直接挂载：

```yaml
nginx:
  volumes:
    - ./frontend/dist:/usr/share/nginx/html:ro
```

**优点**：
- ✅ 不需要前端容器运行
- ✅ 更简单直接

**缺点**：
- ⚠️ 需要确保构建产物在主机上存在
- ⚠️ 部署时需要先构建前端

## 推荐实施方式

**阶段 1（当前）**：保持现有架构，修复健康检查问题 ✅

**阶段 2（优化）**：采用方案 B（直接挂载构建产物）

1. 前端构建时，将产物保存到 `frontend/dist`
2. Nginx 直接挂载 `./frontend/dist`
3. 移除前端容器的 nginx 运行

**阶段 3（进一步优化）**：如果使用 CI/CD，可以在构建阶段生成静态文件，部署时直接挂载

## 迁移检查清单

- [ ] 备份当前配置
- [ ] 修改 docker-compose.prod.yml
- [ ] 修改 nginx/nginx.conf
- [ ] 测试静态文件服务
- [ ] 测试 API 代理
- [ ] 测试 Vue Router history 模式
- [ ] 更新部署文档
- [ ] 更新健康检查配置

