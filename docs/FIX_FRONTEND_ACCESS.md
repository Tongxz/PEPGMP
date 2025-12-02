# 修复前端页面访问问题

## 问题分析

前端页面无法访问的可能原因：
1. **前端服务未启动** - `docker-compose.prod.yml` 中可能没有前端服务配置
2. **前端镜像未导入** - 前端镜像可能没有导入到 WSL2
3. **Nginx 配置不正确** - Nginx 可能没有正确代理前端静态文件
4. **端口冲突** - 前端端口可能被占用

## 检查步骤

### 步骤 1: 检查前端镜像是否存在

```bash
# 在 WSL2 Ubuntu 中
docker images | grep pepgmp-frontend

# 如果没有看到前端镜像，需要导入
```

### 步骤 2: 检查 docker-compose.prod.yml 中是否有前端服务

```bash
cd ~/projects/Pyt

# 检查是否有前端服务配置
grep -A 10 "^  frontend:" docker-compose.prod.yml || echo "Frontend service not found"
```

### 步骤 3: 检查 Nginx 配置

```bash
cd ~/projects/Pyt

# 查看 nginx 配置
cat nginx/nginx.conf | grep -A 10 "location /"
```

## 解决方案

### 方案 1: 添加前端服务到 docker-compose.prod.yml（推荐）

如果前端镜像已构建，添加前端服务：

```yaml
  # ==================== Frontend 前端（生产） ====================
  frontend:
    image: pepgmp-frontend:${IMAGE_TAG:-latest}
    container_name: pepgmp-frontend-prod
    ports:
      - "8080:80"
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

### 方案 2: 更新 Nginx 配置代理前端（如果使用 Nginx）

更新 `nginx/nginx.conf`，添加前端静态文件服务：

```nginx
    # 前端静态文件
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 代理
    location /api/ {
        proxy_pass http://api_backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

### 方案 3: 直接访问前端服务（如果已启动）

如果前端服务已启动，直接访问前端端口：

```bash
# 检查前端服务状态
docker-compose -f docker-compose.prod.yml ps | grep frontend

# 如果前端服务在运行，访问：
# http://localhost:8080（如果端口映射是 8080:80）
```

## 快速修复步骤

### 如果前端镜像已导入

1. **添加前端服务到 docker-compose.prod.yml**:

```bash
cd ~/projects/Pyt

# 编辑 docker-compose.prod.yml，在 nginx 服务之前添加前端服务
# 或者使用 sed 命令（需要根据实际情况调整）
```

2. **重新启动服务**:

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
```

### 如果前端镜像未导入

1. **从 Windows 导出前端镜像**:

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt
.\scripts\export_images_to_wsl.ps1 20251201
```

2. **在 WSL2 中导入前端镜像**:

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251201.tar
```

3. **添加前端服务并启动**:

```bash
cd ~/projects/Pyt
# 添加前端服务配置（见方案1）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
```

## 检查当前状态

```bash
cd ~/projects/Pyt

# 1. 检查所有服务状态
docker-compose -f docker-compose.prod.yml ps

# 2. 检查前端镜像
docker images | grep pepgmp-frontend

# 3. 检查端口占用
sudo netstat -tulpn | grep -E '80|8080|5173'

# 4. 检查 Nginx 配置
cat nginx/nginx.conf
```

## 临时解决方案：直接访问 API

如果暂时不需要前端，可以直接访问 API：

- **API 文档**: `http://localhost:8000/docs`
- **健康检查**: `http://localhost:8000/api/v1/monitoring/health`
- **API 基础路径**: `http://localhost:8000/api/v1/`

