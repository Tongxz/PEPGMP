# 部署架构分析

## 当前架构问题

### 当前结构

```
┌─────────────────────────────────────────────────────────┐
│  浏览器访问 http://localhost/                            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  反向代理 Nginx 容器 (pepgmp-nginx-prod)                 │
│  - 监听主机 80 端口                                        │
│  - 代理 /api/ → api:8000                                 │
│  - 代理 / → frontend:80                                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  前端容器 (pepgmp-frontend-prod)                         │
│  - 运行 Nginx，监听容器内 80 端口                         │
│  - 服务静态文件 /usr/share/nginx/html                    │
└─────────────────────────────────────────────────────────┘
```

### 问题分析

1. **双重 Nginx 架构** ❌
   - 前端容器内运行 nginx
   - 反向代理容器也运行 nginx
   - 请求经过两次 nginx，增加延迟和资源消耗

2. **资源浪费** ❌
   - 两个 nginx 容器都在运行
   - 前端容器的 nginx 只做静态文件服务，功能单一

3. **配置复杂** ❌
   - 需要维护两个 nginx 配置文件
   - `deployment/nginx/frontend.conf` (前端容器内)
   - `nginx/nginx.conf` (反向代理)

4. **维护成本高** ❌
   - 两个容器都需要健康检查
   - 两个容器都需要日志管理
   - 两个容器都需要更新和维护

## 优化方案

### 方案 A：单一 Nginx 容器（推荐）⭐

**架构**：
```
┌─────────────────────────────────────────────────────────┐
│  浏览器访问 http://localhost/                            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  单一 Nginx 容器 (pepgmp-nginx-prod)                     │
│  - 监听主机 80 端口                                        │
│  - 直接服务静态文件（通过 volume mount）                  │
│  - 代理 /api/ → api:8000                                 │
└─────────────────────────────────────────────────────────┘
```

**优点**：
- ✅ 单一 nginx 容器，架构简单
- ✅ 减少资源消耗（只需一个 nginx）
- ✅ 减少网络跳转（请求只经过一次 nginx）
- ✅ 配置集中管理（只需一个 nginx 配置）
- ✅ 性能更好（减少一次代理转发）

**实现方式**：
1. 前端构建时只构建静态文件（不打包 nginx）
2. 反向代理 nginx 通过 volume mount 直接服务静态文件
3. 移除前端容器，或改为仅用于构建

### 方案 B：前端容器直接暴露端口

**架构**：
```
┌─────────────────────────────────────────────────────────┐
│  浏览器访问 http://localhost/                            │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│  Nginx 容器      │  │  前端容器        │
│  - 只代理 API    │  │  - 直接暴露 80   │
│  - /api/ → api  │  │  - 服务静态文件  │
└─────────────────┘  └─────────────────┘
```

**优点**：
- ✅ 前端容器独立，可以单独扩展
- ✅ 前端和 API 分离更清晰

**缺点**：
- ❌ 需要暴露前端容器端口到主机
- ❌ 浏览器需要知道两个不同的端口（或需要 DNS/负载均衡）
- ❌ 仍然有两个 nginx 容器

### 方案 C：保持当前架构但优化

**优化点**：
1. 前端容器只用于构建，运行时通过 volume 挂载到 nginx
2. 或者前端容器改为只提供静态文件服务（不运行 nginx）

## 推荐方案：方案 A（单一 Nginx 容器）

### 实施步骤

#### 步骤 1: 修改前端构建流程

**选项 1：前端只构建，不打包 nginx**

修改 `Dockerfile.frontend`，只构建静态文件，不运行 nginx：

```dockerfile
# 只构建阶段，不运行 nginx
FROM ${NODE_IMAGE} AS builder
WORKDIR /app
# ... 构建步骤 ...
RUN npm run build

# 最终阶段：只复制构建产物，不运行 nginx
FROM scratch
COPY --from=builder /app/dist /dist
```

**选项 2：保持前端容器，但通过 volume 挂载静态文件到 nginx**

前端容器构建后，将静态文件挂载到 nginx 容器。

#### 步骤 2: 修改 docker-compose.prod.yml

```yaml
  # ==================== Frontend 构建（仅构建，不运行） ====================
  frontend-builder:
    image: pepgmp-frontend:${IMAGE_TAG:-latest}
    container_name: pepgmp-frontend-builder
    command: ["sh", "-c", "echo 'Frontend build completed' && sleep infinity"]
    volumes:
      - frontend-dist:/usr/share/nginx/html:ro
    networks:
      - frontend
    restart: "no"  # 只用于挂载，不自动重启

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
      - frontend-builder
    restart: unless-stopped

volumes:
  frontend-dist:
    driver: local
```

#### 步骤 3: 修改 nginx 配置

```nginx
http {
    # ... 其他配置 ...

    server {
        listen 80;
        server_name _;

        # 静态文件根目录（从 volume 挂载）
        root /usr/share/nginx/html;
        index index.html;

        # API 代理
        location /api/ {
            proxy_pass http://api_backend/api/;
            # ... 代理配置 ...
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
    }
}
```

### 方案对比

| 方案 | 容器数 | 资源消耗 | 性能 | 复杂度 | 推荐度 |
|------|-------|---------|------|--------|--------|
| **当前架构** | 2 nginx | 高 | 中 | 高 | ⭐⭐ |
| **方案 A** | 1 nginx | 低 | 高 | 低 | ⭐⭐⭐⭐⭐ |
| **方案 B** | 2 nginx | 高 | 中 | 中 | ⭐⭐⭐ |

## 建议

**立即优化**：采用方案 A（单一 Nginx 容器）

**理由**：
1. 架构更简单，易于维护
2. 性能更好（减少一次代理转发）
3. 资源消耗更低
4. 配置更集中

**实施优先级**：
1. 🔴 **高优先级**：修复当前健康检查问题（已完成）
2. 🟡 **中优先级**：优化架构为单一 nginx（建议实施）
3. 🟢 **低优先级**：性能调优和监控

## 迁移计划

如果决定采用方案 A，可以按以下步骤迁移：

1. **阶段 1**：保持当前架构运行，修复健康检查问题 ✅
2. **阶段 2**：实施方案 A，测试验证
3. **阶段 3**：移除前端容器的 nginx，改为 volume 挂载
4. **阶段 4**：更新文档和部署脚本

