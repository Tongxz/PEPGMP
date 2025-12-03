# 方案 B 重新部署步骤

## 前置检查清单

在重新部署前，请确认以下内容：

- [ ] 所有配置文件已更新（docker-compose.prod.yml, nginx/nginx.conf）
- [ ] 前端静态文件已构建或可以构建
- [ ] 已备份当前配置（如果需要回滚）
- [ ] 了解方案 B 架构变化（单一 Nginx，直接服务静态文件）

## 重新部署步骤

### 步骤 1: 构建前端静态文件（必须）

**如果静态文件已存在**：
```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查静态文件是否存在
ls -la frontend/dist/index.html
```

**如果静态文件不存在，需要构建**：

**方式 1: 使用 Docker 构建（推荐）**

```bash
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt

# 构建前端镜像
.\scripts\build_prod_only.ps1 20251202

# 或者手动构建
docker build -f Dockerfile.frontend `
  --build-arg VITE_API_BASE=/api/v1 `
  --build-arg BASE_URL=/ `
  --build-arg SKIP_TYPE_CHECK=true `
  -t pepgmp-frontend:latest .
```

**方式 2: 提取静态文件到部署目录**

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 如果镜像在 WSL2 中
docker create --name temp-frontend-extract pepgmp-frontend:latest
mkdir -p frontend/dist
docker cp temp-frontend-extract:/usr/share/nginx/html/. ./frontend/dist/
docker rm temp-frontend-extract

# 验证文件已提取
ls -la frontend/dist/index.html
ls -la frontend/dist/assets/
```

### 步骤 2: 更新部署目录（如果使用 prepare_minimal_deploy.sh）

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt

# 运行部署准备脚本（会自动处理前端静态文件）
bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes
```

### 步骤 3: 停止当前服务

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 停止所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production down

# 等待服务完全停止
sleep 5

# 验证服务已停止
docker-compose -f docker-compose.prod.yml ps
# 应该显示: "No containers"
```

### 步骤 4: 验证配置文件

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查 docker-compose 配置
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -A 5 "nginx:"
# 应该看到: volumes: - ./frontend/dist:/usr/share/nginx/html:ro

# 检查 nginx 配置
grep -A 3 "root /usr/share/nginx/html" nginx/nginx.conf
# 应该看到: root /usr/share/nginx/html;

# 检查前端静态文件
test -f frontend/dist/index.html && echo "✓ Static files ready" || echo "✗ Static files missing"
```

### 步骤 5: 启动新服务

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 启动所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 等待服务启动（约 15-20 秒）
sleep 20

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 6: 验证部署

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 运行自动化测试脚本
bash /mnt/f/code/PythonCode/Pyt/scripts/test_scheme_b.sh

# 或者手动验证
echo "=== 验证 Nginx 健康状态 ==="
docker inspect pepgmp-nginx-prod --format='{{.State.Health.Status}}'

echo "=== 测试健康检查端点 ==="
curl http://localhost/health

echo "=== 测试前端静态文件 ==="
curl -s http://localhost/ | head -10

echo "=== 测试 API 代理 ==="
curl http://localhost/api/v1/monitoring/health
```

### 步骤 7: 浏览器验证

1. 打开浏览器访问：`http://localhost/`
2. 按 F12 打开开发者工具
3. 检查 Console 标签页是否有错误
4. 检查 Network 标签页，确认所有资源文件都成功加载（状态码 200）
5. 测试前端功能是否正常

## 快速部署命令（一键执行）

如果所有准备工作已完成，可以使用以下命令快速部署：

```bash
#!/bin/bash
# 快速重新部署脚本

cd ~/projects/Pyt

echo "=== 步骤 1: 停止当前服务 ==="
docker-compose -f docker-compose.prod.yml --env-file .env.production down

echo "=== 步骤 2: 验证静态文件 ==="
if [ ! -f "frontend/dist/index.html" ]; then
    echo "错误: 前端静态文件不存在！"
    echo "请先构建前端: docker build -f Dockerfile.frontend -t pepgmp-frontend:latest ."
    echo "然后提取: docker create --name temp pepgmp-frontend:latest && docker cp temp:/usr/share/nginx/html ./frontend/dist && docker rm temp"
    exit 1
fi

echo "=== 步骤 3: 启动服务 ==="
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

echo "=== 步骤 4: 等待服务启动 ==="
sleep 20

echo "=== 步骤 5: 检查服务状态 ==="
docker-compose -f docker-compose.prod.yml ps

echo "=== 步骤 6: 测试部署 ==="
curl -s http://localhost/health && echo " - Health check OK"
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost/
curl -s -o /dev/null -w "API: %{http_code}\n" http://localhost/api/v1/monitoring/health

echo ""
echo "=== 部署完成 ==="
echo "访问: http://localhost/"
```

## 常见问题

### 问题 1: 前端静态文件不存在

**症状**：
```
错误: 前端静态文件不存在！
```

**解决方案**：
```bash
# 构建前端镜像
docker build -f Dockerfile.frontend -t pepgmp-frontend:latest .

# 提取静态文件
docker create --name temp pepgmp-frontend:latest
mkdir -p frontend/dist
docker cp temp:/usr/share/nginx/html/. ./frontend/dist/
docker rm temp
```

### 问题 2: Nginx 容器无法启动

**症状**：
```
pepgmp-nginx-prod exited with code 1
```

**排查**：
```bash
# 检查 nginx 配置
docker run --rm -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t

# 检查日志
docker logs pepgmp-nginx-prod
```

### 问题 3: 前端页面白屏

**排查**：
```bash
# 检查静态文件是否挂载
docker exec pepgmp-nginx-prod ls -la /usr/share/nginx/html/

# 检查 index.html
docker exec pepgmp-nginx-prod cat /usr/share/nginx/html/index.html | head -10

# 检查浏览器控制台错误（F12）
```

## 回滚方案

如果新部署出现问题，可以快速回滚：

```bash
cd ~/projects/Pyt

# 停止新服务
docker-compose -f docker-compose.prod.yml --env-file .env.production down

# 恢复备份配置（如果有）
# cp backups/YYYYMMDD_HHMMSS/docker-compose.prod.yml .
# cp backups/YYYYMMDD_HHMMSS/nginx/nginx.conf ./nginx/

# 启动旧服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## 验证清单

部署完成后，请确认：

- [ ] Nginx 容器健康状态为 `healthy`
- [ ] 健康检查端点返回 200：`curl http://localhost/health`
- [ ] 前端页面可以访问：`curl http://localhost/` 返回 HTML
- [ ] API 代理正常工作：`curl http://localhost/api/v1/monitoring/health`
- [ ] 浏览器可以正常访问前端页面
- [ ] 浏览器控制台没有错误
- [ ] 前端功能正常工作

## 总结

方案 B 重新部署的关键点：

1. **前端静态文件必须存在**：`frontend/dist/index.html`
2. **Nginx 配置已更新**：单一 Nginx，直接服务静态文件
3. **Docker Compose 配置已更新**：volume 挂载 `./frontend/dist:/usr/share/nginx/html:ro`
4. **前端容器不再运行服务**：设置为 `restart: "no"`

完成以上步骤后，即可成功部署方案 B 架构。

