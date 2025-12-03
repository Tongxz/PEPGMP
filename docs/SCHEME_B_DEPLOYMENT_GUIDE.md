# 方案 B 详细部署和测试指南

## 目录

1. [前置条件检查](#前置条件检查)
2. [构建前端静态文件](#构建前端静态文件)
3. [部署步骤](#部署步骤)
4. [详细测试步骤](#详细测试步骤)
5. [故障排查](#故障排查)
6. [回滚步骤](#回滚步骤)

---

## 前置条件检查

### 步骤 1: 检查当前环境

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查当前目录
pwd
# 应该显示: /home/pep/projects/Pyt

# 检查 Docker 是否运行
docker ps

# 检查 Docker Compose 版本
docker-compose --version
# 应该显示: Docker Compose version v2.x.x
```

### 步骤 2: 检查配置文件

```bash
# 检查必要的配置文件是否存在
ls -la docker-compose.prod.yml
ls -la docker-compose.prod.1panel.yml
ls -la nginx/nginx.conf
ls -la .env.production

# 检查 .env.production 中的关键配置
grep IMAGE_TAG .env.production
grep DATABASE_PASSWORD .env.production
grep REDIS_PASSWORD .env.production
```

### 步骤 3: 检查当前服务状态

```bash
# 检查当前运行的服务
docker-compose -f docker-compose.prod.yml ps

# 检查前端容器状态（如果存在）
docker ps -a | grep pepgmp-frontend-prod

# 检查 nginx 容器状态
docker ps -a | grep pepgmp-nginx-prod
```

---

## 构建前端静态文件

### 方式 1: 使用 Docker 构建（推荐）

#### 步骤 1: 在 Windows 上构建前端镜像

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt

# 构建前端镜像（使用当前日期作为标签）
$VERSION_TAG = Get-Date -Format "yyyyMMdd"
.\scripts\build_prod_only.ps1 $VERSION_TAG

# 或者手动构建
docker build -f Dockerfile.frontend `
  --build-arg VITE_API_BASE=/api/v1 `
  --build-arg BASE_URL=/ `
  --build-arg SKIP_TYPE_CHECK=true `
  -t "pepgmp-frontend:$VERSION_TAG" `
  -t "pepgmp-frontend:latest" `
  .
```

#### 步骤 2: 导出镜像到 WSL2（如果需要）

```powershell
# 在 Windows PowerShell 中
.\scripts\export_images_to_wsl.ps1 $VERSION_TAG
```

#### 步骤 3: 在 WSL2 中导入镜像（如果需要）

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images

# 导入前端镜像
docker load -i pepgmp-frontend-*.tar

# 验证镜像
docker images | grep pepgmp-frontend
```

#### 步骤 4: 提取静态文件到主机目录

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 创建临时容器并提取静态文件
docker create --name temp-frontend-extract pepgmp-frontend:latest

# 创建目标目录（如果不存在）
mkdir -p frontend/dist

# 复制静态文件到主机目录
docker cp temp-frontend-extract:/usr/share/nginx/html/. ./frontend/dist/

# 删除临时容器
docker rm temp-frontend-extract

# 验证文件已复制
ls -la frontend/dist/
# 应该看到: index.html, assets/ 等文件
```

### 方式 2: 在主机上直接构建（备选）

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt/frontend

# 检查 Node.js 版本（需要 Node.js 20+）
node --version

# 安装依赖
npm ci

# 构建生产版本
npm run build

# 验证构建产物
ls -la dist/
# 应该看到: index.html, assets/ 等文件

# 返回项目根目录
cd ..
```

### 步骤 5: 验证静态文件

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查静态文件目录结构
tree frontend/dist/ -L 2
# 或者
ls -la frontend/dist/
ls -la frontend/dist/assets/

# 检查 index.html 是否存在
test -f frontend/dist/index.html && echo "✓ index.html exists" || echo "✗ index.html missing"

# 检查 assets 目录是否存在
test -d frontend/dist/assets && echo "✓ assets directory exists" || echo "✗ assets directory missing"

# 查看 index.html 内容（前 20 行）
head -20 frontend/dist/index.html
```

---

## 部署步骤

### 步骤 1: 备份当前配置（重要）

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 创建备份目录
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# 备份配置文件
cp docker-compose.prod.yml "$BACKUP_DIR/"
cp docker-compose.prod.1panel.yml "$BACKUP_DIR/"
cp nginx/nginx.conf "$BACKUP_DIR/"

# 备份 .env.production（如果存在）
[ -f .env.production ] && cp .env.production "$BACKUP_DIR/"

echo "Backup created in: $BACKUP_DIR"
```

### 步骤 2: 更新配置文件（如果从 Windows 复制）

```bash
# 如果配置文件在 Windows 项目目录，需要复制到 WSL2
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 从 Windows 项目目录复制更新的配置文件
cp /mnt/f/code/PythonCode/Pyt/docker-compose.prod.yml .
cp /mnt/f/code/PythonCode/Pyt/docker-compose.prod.1panel.yml .
cp /mnt/f/code/PythonCode/Pyt/nginx/nginx.conf ./nginx/

# 验证文件已更新
head -5 docker-compose.prod.yml
head -5 nginx/nginx.conf
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

# 检查是否有残留容器
docker ps -a | grep pepgmp
```

### 步骤 4: 清理旧的前端容器（可选）

```bash
# 如果前端容器存在但不运行，可以删除
docker rm -f pepgmp-frontend-prod 2>/dev/null || echo "Frontend container not found"

# 验证已删除
docker ps -a | grep pepgmp-frontend-prod
# 应该没有输出
```

### 步骤 5: 验证静态文件挂载点

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查静态文件目录是否存在且可读
if [ -d "frontend/dist" ] && [ -f "frontend/dist/index.html" ]; then
    echo "✓ Static files ready"
    echo "  Files: $(find frontend/dist -type f | wc -l)"
    echo "  Size: $(du -sh frontend/dist | cut -f1)"
else
    echo "✗ Static files missing!"
    echo "  Please build frontend first (see '构建前端静态文件' section)"
    exit 1
fi
```

### 步骤 6: 验证 Nginx 配置

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 使用 nginx 容器测试配置语法
docker run --rm \
  -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  nginx:alpine \
  nginx -t

# 应该显示: "syntax is ok" 和 "test is successful"
```

### 步骤 7: 启动服务

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 启动所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 等待服务启动（约 10-15 秒）
sleep 15

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 8: 检查服务日志

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查 nginx 容器日志
docker logs pepgmp-nginx-prod --tail 50

# 检查 API 容器日志
docker logs pepgmp-api-prod --tail 50

# 检查数据库容器日志（如果有问题）
docker logs pepgmp-postgres-prod --tail 50
```

---

## 详细测试步骤

### 测试 1: 检查容器状态

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

echo "=== 测试 1: 检查容器状态 ==="

# 检查所有容器是否运行
docker-compose -f docker-compose.prod.yml ps

# 检查 nginx 容器状态
NGINX_STATUS=$(docker inspect pepgmp-nginx-prod --format='{{.State.Status}}' 2>/dev/null)
if [ "$NGINX_STATUS" = "running" ]; then
    echo "✓ Nginx container is running"
else
    echo "✗ Nginx container is not running (Status: $NGINX_STATUS)"
fi

# 检查 API 容器状态
API_STATUS=$(docker inspect pepgmp-api-prod --format='{{.State.Status}}' 2>/dev/null)
if [ "$API_STATUS" = "running" ]; then
    echo "✓ API container is running"
else
    echo "✗ API container is not running (Status: $API_STATUS)"
fi

# 检查数据库容器状态
DB_STATUS=$(docker inspect pepgmp-postgres-prod --format='{{.State.Status}}' 2>/dev/null)
if [ "$DB_STATUS" = "running" ]; then
    echo "✓ Database container is running"
else
    echo "✗ Database container is not running (Status: $DB_STATUS)"
fi
```

### 测试 2: 检查 Nginx 健康状态

```bash
echo "=== 测试 2: 检查 Nginx 健康状态 ==="

# 检查 nginx 容器健康状态
NGINX_HEALTH=$(docker inspect pepgmp-nginx-prod --format='{{.State.Health.Status}}' 2>/dev/null)
if [ "$NGINX_HEALTH" = "healthy" ]; then
    echo "✓ Nginx container is healthy"
elif [ "$NGINX_HEALTH" = "starting" ]; then
    echo "⚠ Nginx container is starting (wait a few seconds)"
else
    echo "✗ Nginx container is unhealthy (Status: $NGINX_HEALTH)"
    echo "  Check logs: docker logs pepgmp-nginx-prod"
fi

# 测试健康检查端点
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null)
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✓ Health endpoint returns 200"
    curl -s http://localhost/health
    echo ""
else
    echo "✗ Health endpoint failed (HTTP $HEALTH_RESPONSE)"
fi
```

### 测试 3: 测试静态文件访问

```bash
echo "=== 测试 3: 测试静态文件访问 ==="

# 测试根路径
ROOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null)
if [ "$ROOT_RESPONSE" = "200" ]; then
    echo "✓ Root path returns 200"
    
    # 检查返回内容是否包含 HTML
    ROOT_CONTENT=$(curl -s http://localhost/ | head -5)
    if echo "$ROOT_CONTENT" | grep -q "DOCTYPE\|html"; then
        echo "✓ Root path returns HTML content"
        echo "  Preview:"
        echo "$ROOT_CONTENT" | head -3
    else
        echo "✗ Root path does not return HTML"
        echo "  Content: $ROOT_CONTENT"
    fi
else
    echo "✗ Root path failed (HTTP $ROOT_RESPONSE)"
fi

# 测试 index.html
INDEX_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/index.html 2>/dev/null)
if [ "$INDEX_RESPONSE" = "200" ]; then
    echo "✓ index.html returns 200"
else
    echo "✗ index.html failed (HTTP $INDEX_RESPONSE)"
fi
```

### 测试 4: 测试静态资源文件

```bash
echo "=== 测试 4: 测试静态资源文件 ==="

# 从 index.html 中提取资源路径
INDEX_HTML=$(curl -s http://localhost/index.html)

# 提取 JS 文件路径
JS_FILES=$(echo "$INDEX_HTML" | grep -oP 'src="[^"]*\.js[^"]*"' | head -1 | sed 's/src="//;s/"//')
if [ -n "$JS_FILES" ]; then
    JS_URL="http://localhost$JS_FILES"
    JS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$JS_URL" 2>/dev/null)
    if [ "$JS_RESPONSE" = "200" ]; then
        echo "✓ JavaScript file accessible: $JS_FILES"
    else
        echo "✗ JavaScript file failed (HTTP $JS_RESPONSE): $JS_FILES"
    fi
else
    echo "⚠ No JavaScript files found in index.html"
fi

# 提取 CSS 文件路径
CSS_FILES=$(echo "$INDEX_HTML" | grep -oP 'href="[^"]*\.css[^"]*"' | head -1 | sed 's/href="//;s/"//')
if [ -n "$CSS_FILES" ]; then
    CSS_URL="http://localhost$CSS_FILES"
    CSS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$CSS_URL" 2>/dev/null)
    if [ "$CSS_RESPONSE" = "200" ]; then
        echo "✓ CSS file accessible: $CSS_FILES"
    else
        echo "✗ CSS file failed (HTTP $CSS_RESPONSE): $CSS_FILES"
    fi
else
    echo "⚠ No CSS files found in index.html"
fi
```

### 测试 5: 测试 API 代理

```bash
echo "=== 测试 5: 测试 API 代理 ==="

# 测试 API 健康检查端点
API_HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/monitoring/health 2>/dev/null)
if [ "$API_HEALTH_RESPONSE" = "200" ]; then
    echo "✓ API health endpoint returns 200"
    API_HEALTH_CONTENT=$(curl -s http://localhost/api/v1/monitoring/health)
    echo "  Response: $API_HEALTH_CONTENT"
else
    echo "✗ API health endpoint failed (HTTP $API_HEALTH_RESPONSE)"
fi

# 测试 API 根路径
API_ROOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/ 2>/dev/null)
if [ "$API_ROOT_RESPONSE" = "200" ] || [ "$API_ROOT_RESPONSE" = "404" ]; then
    echo "✓ API root path accessible (HTTP $API_ROOT_RESPONSE)"
else
    echo "✗ API root path failed (HTTP $API_ROOT_RESPONSE)"
fi
```

### 测试 6: 测试 Vue Router History 模式

```bash
echo "=== 测试 6: 测试 Vue Router History 模式 ==="

# 测试一个不存在的路径（应该返回 index.html）
FAKE_PATH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/nonexistent-page 2>/dev/null)
if [ "$FAKE_PATH_RESPONSE" = "200" ]; then
    FAKE_PATH_CONTENT=$(curl -s http://localhost/nonexistent-page | head -5)
    if echo "$FAKE_PATH_CONTENT" | grep -q "DOCTYPE\|html"; then
        echo "✓ Vue Router history mode working (fake path returns index.html)"
    else
        echo "✗ Vue Router history mode not working (fake path does not return HTML)"
    fi
else
    echo "✗ Vue Router history mode failed (HTTP $FAKE_PATH_RESPONSE)"
fi
```

### 测试 7: 检查容器内文件挂载

```bash
echo "=== 测试 7: 检查容器内文件挂载 ==="

# 检查 nginx 容器内的静态文件
NGINX_HTML=$(docker exec pepgmp-nginx-prod ls -la /usr/share/nginx/html/ 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✓ Static files mounted in nginx container"
    echo "  Files:"
    echo "$NGINX_HTML" | head -10
else
    echo "✗ Cannot access static files in nginx container"
fi

# 检查 index.html 是否存在
NGINX_INDEX=$(docker exec pepgmp-nginx-prod test -f /usr/share/nginx/html/index.html 2>/dev/null && echo "exists" || echo "missing")
if [ "$NGINX_INDEX" = "exists" ]; then
    echo "✓ index.html exists in nginx container"
else
    echo "✗ index.html missing in nginx container"
fi
```

### 测试 8: 性能测试

```bash
echo "=== 测试 8: 性能测试 ==="

# 测试响应时间
echo "Testing response times..."

# 根路径响应时间
ROOT_TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost/ 2>/dev/null)
echo "  Root path: ${ROOT_TIME}s"

# API 健康检查响应时间
API_TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost/api/v1/monitoring/health 2>/dev/null)
echo "  API health: ${API_TIME}s"

# 静态资源响应时间（如果找到）
if [ -n "$JS_URL" ]; then
    JS_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$JS_URL" 2>/dev/null)
    echo "  JavaScript: ${JS_TIME}s"
fi
```

### 测试 9: 浏览器测试

```bash
echo "=== 测试 9: 浏览器测试 ==="
echo "Please test in browser:"
echo "  1. Open: http://localhost/"
echo "  2. Check browser console (F12) for errors"
echo "  3. Check Network tab for failed requests"
echo "  4. Test navigation between pages"
echo "  5. Test API calls from frontend"
```

---

## 故障排查

### 问题 1: Nginx 容器无法启动

**症状**：
```bash
docker logs pepgmp-nginx-prod
# 显示配置错误或挂载错误
```

**排查步骤**：
```bash
# 1. 检查 nginx 配置语法
docker run --rm \
  -v "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  nginx:alpine \
  nginx -t

# 2. 检查静态文件目录是否存在
ls -la frontend/dist/

# 3. 检查目录权限
ls -ld frontend/dist/

# 4. 检查挂载路径
docker inspect pepgmp-nginx-prod | grep -A 10 Mounts
```

**解决方案**：
- 如果配置错误：修复 `nginx/nginx.conf`
- 如果静态文件缺失：重新构建前端
- 如果权限问题：`chmod -R 755 frontend/dist`

### 问题 2: 静态文件返回 404

**症状**：
```bash
curl http://localhost/
# 返回 404 Not Found
```

**排查步骤**：
```bash
# 1. 检查静态文件是否存在
ls -la frontend/dist/index.html

# 2. 检查 nginx 容器内的文件
docker exec pepgmp-nginx-prod ls -la /usr/share/nginx/html/

# 3. 检查 nginx 配置中的 root 路径
docker exec pepgmp-nginx-prod cat /etc/nginx/nginx.conf | grep root

# 4. 检查 nginx 错误日志
docker logs pepgmp-nginx-prod | grep error
```

**解决方案**：
- 重新构建前端静态文件
- 检查挂载路径是否正确
- 重启 nginx 容器：`docker-compose restart nginx`

### 问题 3: API 代理失败

**症状**：
```bash
curl http://localhost/api/v1/monitoring/health
# 返回 502 Bad Gateway 或连接失败
```

**排查步骤**：
```bash
# 1. 检查 API 容器是否运行
docker ps | grep pepgmp-api-prod

# 2. 检查 API 容器健康状态
docker inspect pepgmp-api-prod --format='{{.State.Health.Status}}'

# 3. 检查 API 容器日志
docker logs pepgmp-api-prod --tail 50

# 4. 测试直接访问 API
docker exec pepgmp-nginx-prod wget -qO- http://api:8000/api/v1/monitoring/health
```

**解决方案**：
- 检查 API 容器是否正常启动
- 检查网络连接：`docker network inspect pyt_frontend`
- 重启 API 容器：`docker-compose restart api`

### 问题 4: 前端页面白屏

**症状**：
- 浏览器访问 `http://localhost/` 显示白屏
- 浏览器控制台有错误

**排查步骤**：
```bash
# 1. 检查 index.html 是否正确返回
curl http://localhost/ | head -20

# 2. 检查静态资源路径
curl http://localhost/ | grep -E 'src=|href='

# 3. 检查资源文件是否存在
# 从 index.html 中提取资源路径并测试
```

**解决方案**：
- 检查 `BASE_URL` 构建参数是否正确
- 检查资源文件路径是否正确
- 查看浏览器控制台错误信息

---

## 回滚步骤

如果新架构出现问题，可以快速回滚：

### 步骤 1: 停止当前服务

```bash
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml --env-file .env.production down
```

### 步骤 2: 恢复备份配置

```bash
# 找到最新的备份目录
LATEST_BACKUP=$(ls -td backups/*/ | head -1)

# 恢复配置文件
cp "$LATEST_BACKUP/docker-compose.prod.yml" .
cp "$LATEST_BACKUP/docker-compose.prod.1panel.yml" .
cp "$LATEST_BACKUP/nginx/nginx.conf" ./nginx/

# 如果备份了 .env.production
[ -f "$LATEST_BACKUP/.env.production" ] && cp "$LATEST_BACKUP/.env.production" .
```

### 步骤 3: 重新构建前端容器（如果需要）

```bash
# 如果回滚到双重 nginx 架构，需要前端容器运行
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
```

### 步骤 4: 启动服务

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 完整测试脚本

创建一个测试脚本 `scripts/test_scheme_b.sh`：

```bash
#!/bin/bash
# 方案 B 完整测试脚本

set -e

echo "========================================================================="
echo "方案 B 完整测试"
echo "========================================================================="
echo ""

# 运行所有测试
echo "运行测试 1-8..."
# ... (包含上面的所有测试步骤)

echo ""
echo "========================================================================="
echo "测试完成"
echo "========================================================================="
```

---

## 总结

完成以上所有测试步骤后，如果所有测试都通过，说明方案 B 已成功实施。

**关键检查点**：
1. ✅ 静态文件已构建到 `frontend/dist`
2. ✅ Nginx 容器健康运行
3. ✅ 静态文件可以正常访问
4. ✅ API 代理正常工作
5. ✅ Vue Router history 模式正常
6. ✅ 浏览器可以正常访问

如果遇到问题，请参考故障排查部分或查看日志。

