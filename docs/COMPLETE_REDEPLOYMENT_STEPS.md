# 完整重新部署步骤（重新构建后）

## 前提条件

✅ 已在 Windows 重新构建前端和后端镜像

---

## 部署步骤

### 步骤 1: 导出镜像（Windows）

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt

# 获取今天的日期作为版本号
$VERSION = Get-Date -Format "yyyyMMdd"
Write-Host "Version: $VERSION"

# 导出镜像
docker save pepgmp-backend:latest -o "docker-images\pepgmp-backend-$VERSION.tar"
docker save pepgmp-frontend:latest -o "docker-images\pepgmp-frontend-$VERSION.tar"

Write-Host "Images exported to docker-images\"
```

---

### 步骤 2: 导入镜像（WSL2）

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images

# 获取今天的日期
VERSION=$(date +%Y%m%d)
echo "Version: $VERSION"

# 导入镜像
docker load -i pepgmp-backend-$VERSION.tar
docker load -i pepgmp-frontend-$VERSION.tar

# 验证镜像
docker images | grep pepgmp
```

**重要**：检查镜像 ID 是否已变化（与之前的不同）

---

### 步骤 3: 完全清理旧部署（WSL2）

```bash
cd ~/projects/Pyt

# 1. 停止并删除所有容器
docker-compose -f docker-compose.prod.yml down

# 2. 删除旧的静态文件
rm -rf frontend/dist

# 3. 清理旧容器（如果有）
docker ps -a | grep pepgmp | awk '{print $1}' | xargs -r docker rm -f

# 4. 验证清理
docker ps -a | grep pepgmp
# 应该没有输出
```

---

### 步骤 4: 更新配置（WSL2）

```bash
cd ~/projects/Pyt

# 更新版本号
VERSION=$(date +%Y%m%d)
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION/" .env.production

# 验证
grep IMAGE_TAG .env.production
```

---

### 步骤 5: 重新部署（WSL2）

```bash
cd ~/projects/Pyt

# 启动所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 等待服务启动
sleep 20

# 检查容器状态
docker ps -a | grep pepgmp
```

**预期输出**：
```
pepgmp-nginx-prod        Up (healthy)
pepgmp-api-prod          Up (healthy)
pepgmp-postgres-prod     Up (healthy)
pepgmp-redis-prod        Up (healthy)
pepgmp-frontend-init     Exited (0)  ← 正常
```

---

### 步骤 6: 验证部署（WSL2）

```bash
cd ~/projects/Pyt

# 1. 检查 frontend-init 日志
echo "=== Frontend Init Logs ==="
docker logs pepgmp-frontend-init

# 2. 检查静态文件
echo ""
echo "=== Static Files ==="
ls -la frontend/dist/index.html
find frontend/dist -type f | wc -l

# 3. 检查 JS 文件（应该只有一个版本）
echo ""
echo "=== JS Files ==="
ls -la frontend/dist/assets/js/ | grep -E "vue-vendor|index-"

# 4. 测试访问
echo ""
echo "=== Testing Access ==="
curl -s -o /dev/null -w "Frontend: %{http_code}\n" http://localhost/
curl -s -o /dev/null -w "API: %{http_code}\n" http://localhost/api/v1/monitoring/health
curl -s -o /dev/null -w "Nginx: %{http_code}\n" http://localhost/health

# 5. 检查 HTML 中引用的 JS 文件
echo ""
echo "=== HTML JS References ==="
curl -s http://localhost/ | grep -o 'src="/assets/js/[^"]*"' | head -5
```

---

### 步骤 7: 浏览器测试

#### 7.1 清除浏览器缓存

**Chrome/Edge**：
1. 按 `Ctrl + Shift + Delete`
2. 选择"全部时间"
3. 勾选"缓存的图片和文件"
4. 点击"清除数据"

**或使用隐身模式**：
- 按 `Ctrl + Shift + N`
- 在隐身窗口访问

#### 7.2 访问前端

1. 访问 `http://localhost/`
2. 按 `F12` 打开开发者工具
3. 切换到"Console"标签
4. 检查是否有错误

#### 7.3 检查网络请求

1. 切换到"Network"标签
2. 勾选"Disable cache"
3. 刷新页面（F5）
4. 查看所有 JS 文件是否成功加载（状态码 200）

---

## 故障排查

### 问题 1: frontend-init 容器 Exited (1)

```bash
# 查看详细日志
docker logs pepgmp-frontend-init

# 可能原因：镜像版本号不匹配
grep IMAGE_TAG .env.production
docker images | grep pepgmp-frontend
```

---

### 问题 2: 静态文件未提取

```bash
# 检查挂载目录
ls -la frontend/

# 手动重新运行 frontend-init
docker-compose -f docker-compose.prod.yml up -d frontend-init

# 等待完成
sleep 10

# 检查日志
docker logs pepgmp-frontend-init
```

---

### 问题 3: 浏览器仍然报错

**检查步骤**：

```bash
# 1. 确认镜像已更新（IMAGE ID 应该不同）
docker images | grep pepgmp-frontend

# 2. 确认静态文件是新的
ls -la frontend/dist/assets/js/ | head -10

# 3. 确认 HTML 引用正确
curl http://localhost/ | grep vue-vendor
```

**如果仍然报错**：

```bash
# 完全重新部署
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml down
docker rm -f $(docker ps -a | grep pepgmp | awk '{print $1}')
rm -rf frontend/dist
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

### 问题 4: 镜像 ID 未变化

说明镜像未真正重新构建：

```powershell
# Windows: 强制重新构建
cd F:\Code\PythonCode\Pyt

# 删除旧镜像
docker rmi pepgmp-frontend:latest -f

# 清理构建缓存
docker builder prune -f

# 重新构建（不使用缓存）
docker build -f Dockerfile.frontend `
  --no-cache `
  --build-arg VITE_API_BASE=/api/v1 `
  --build-arg BASE_URL=/ `
  --build-arg SKIP_TYPE_CHECK=true `
  -t pepgmp-frontend:latest `
  .
```

---

## 验证清单

- [ ] 镜像 ID 已变化（与旧镜像不同）
- [ ] frontend-init 容器状态为 Exited (0)
- [ ] 静态文件已提取（`frontend/dist/index.html` 存在）
- [ ] JS 文件只有一个版本（无混合文件）
- [ ] 前端页面返回 200
- [ ] API 返回 200
- [ ] 浏览器控制台无错误
- [ ] 前端页面正常显示

---

## 成功标志

### 容器状态
```
pepgmp-frontend-init     Exited (0)
pepgmp-nginx-prod        Up (healthy)
pepgmp-api-prod          Up (healthy)
pepgmp-postgres-prod     Up (healthy)
pepgmp-redis-prod        Up (healthy)
```

### 浏览器控制台
```
无 Uncaught ReferenceError 错误
页面正常加载
```

### 网络请求
```
所有 JS/CSS 文件状态码 200
无 404 错误
```

---

## 下一步

部署成功后，建议：

1. **清理旧镜像**：
   ```bash
   docker image prune -a
   ```

2. **测试功能**：
   - 登录功能
   - API 调用
   - 页面导航

3. **监控日志**：
   ```bash
   docker logs -f pepgmp-nginx-prod
   docker logs -f pepgmp-api-prod
   ```
