# 方案 5 重新部署步骤

## 当前状态

- ✅ 部署目录已更新（`docker-compose.prod.yml` 包含 `frontend-init` 服务）
- ⚠️ 旧容器仍在运行（使用旧配置）

## 重新部署步骤

### 步骤 1: 停止旧服务

```bash
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml down
```

**说明**：停止并删除所有旧容器（包括旧的 `pepgmp-frontend-prod`）

---

### 步骤 2: 清理旧的静态文件（可选）

```bash
# 备份旧静态文件（可选）
mv frontend/dist frontend/dist.backup.$(date +%Y%m%d_%H%M%S)

# 或直接删除
rm -rf frontend/dist
```

**说明**：确保使用新镜像提取的静态文件

---

### 步骤 3: 更新镜像版本号

```bash
# 检查当前版本
grep IMAGE_TAG .env.production

# 更新为新版本（如果需要）
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251203/' .env.production

# 验证
grep IMAGE_TAG .env.production
```

---

### 步骤 4: 启动新服务

```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**预期输出**：
```
[+] Running 6/6
 ✔ Network pyt_frontend             Created
 ✔ Network pyt_backend              Created
 ✔ Container pepgmp-postgres-prod   Healthy
 ✔ Container pepgmp-redis-prod      Healthy
 ✔ Container pepgmp-frontend-init   Started  ← 注意这里是 frontend-init
 ✔ Container pepgmp-api-prod        Started
 ✔ Container pepgmp-nginx-prod      Started
```

---

### 步骤 5: 验证部署

#### 5.1 检查容器状态

```bash
docker ps -a | grep pepgmp
```

**预期输出**：
```
pepgmp-nginx-prod        ... Up ...
pepgmp-api-prod          ... Up ...
pepgmp-postgres-prod     ... Up ...
pepgmp-redis-prod        ... Up ...
pepgmp-frontend-init     ... Exited (0) ...  ← 这是正常的！
```

**关键点**：
- ✅ `pepgmp-frontend-init` 状态为 `Exited (0)` 是**正常的**
- ✅ 表示静态文件提取完成后容器自动退出
- ❌ 如果是 `Exited (1)` 或其他非 0 状态，说明有错误

#### 5.2 检查静态文件

```bash
# 检查静态文件是否存在
ls -la frontend/dist/index.html

# 查看文件数量
find frontend/dist -type f | wc -l
```

**预期输出**：
```
-rw-r--r-- 1 pep pep 1234 Dec  3 10:00 frontend/dist/index.html
18  ← 文件数量
```

#### 5.3 查看 frontend-init 日志

```bash
docker logs pepgmp-frontend-init
```

**预期输出**：
```
=========================================================================
Frontend Init Container - Extracting static files...
=========================================================================
Image: pepgmp-frontend:20251203
Target: /target (mounted to ./frontend/dist)

[OK] Static files extracted successfully
total 123
drwxr-xr-x  3 root root  4096 Dec  3 10:00 .
drwxr-xr-x  3 root root  4096 Dec  3 10:00 ..
-rw-r--r--  1 root root  1234 Dec  3 10:00 index.html
...

Total files: 18
=========================================================================
Frontend init completed - container will exit
=========================================================================
```

#### 5.4 测试前端访问

```bash
# 测试前端首页
curl -I http://localhost/

# 测试 API 健康检查
curl http://localhost/api/v1/monitoring/health

# 测试 Nginx 健康检查
curl http://localhost/health
```

**预期输出**：
```
# 前端首页
HTTP/1.1 200 OK
Content-Type: text/html

# API 健康检查
{"status":"healthy",...}

# Nginx 健康检查
healthy
```

---

## 完整命令（一键执行）

```bash
cd ~/projects/Pyt

# 停止旧服务
docker-compose -f docker-compose.prod.yml down

# 更新版本号（如果需要）
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251203/' .env.production

# 启动新服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 等待服务启动
sleep 15

# 验证
echo "=== 容器状态 ==="
docker ps -a | grep pepgmp

echo ""
echo "=== 静态文件 ==="
ls -la frontend/dist/index.html 2>/dev/null && echo "✓ 静态文件存在" || echo "✗ 静态文件不存在"

echo ""
echo "=== frontend-init 日志 ==="
docker logs pepgmp-frontend-init | tail -5

echo ""
echo "=== 测试访问 ==="
curl -s -o /dev/null -w "前端: %{http_code}\n" http://localhost/
curl -s -o /dev/null -w "API: %{http_code}\n" http://localhost/api/v1/monitoring/health
curl -s -o /dev/null -w "Nginx: %{http_code}\n" http://localhost/health
```

---

## 故障排查

### 问题 1: frontend-init 容器状态为 Exited (1)

**检查日志**：
```bash
docker logs pepgmp-frontend-init
```

**可能原因**：
- 镜像不存在或版本号错误
- 挂载目录权限问题
- 镜像内静态文件路径错误

**解决方法**：
```bash
# 检查镜像是否存在
docker images | grep pepgmp-frontend

# 检查版本号
grep IMAGE_TAG .env.production

# 检查目录权限
ls -la frontend/
```

---

### 问题 2: 静态文件未提取

**检查**：
```bash
ls -la frontend/dist/
```

**解决方法**：
```bash
# 手动重新运行 frontend-init
docker-compose -f docker-compose.prod.yml up -d frontend-init

# 等待完成
sleep 10

# 检查日志
docker logs pepgmp-frontend-init
```

---

### 问题 3: Nginx 容器 unhealthy

**检查日志**：
```bash
docker logs pepgmp-nginx-prod
```

**可能原因**：
- 静态文件未提取
- nginx.conf 配置错误
- API 服务未启动

**解决方法**：
```bash
# 检查 nginx 配置
docker exec pepgmp-nginx-prod nginx -t

# 检查静态文件挂载
docker exec pepgmp-nginx-prod ls -la /usr/share/nginx/html/

# 重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 与旧版本的区别

| 项目 | 旧版本 (方案 B) | 新版本 (方案 5) |
|------|----------------|----------------|
| 服务名 | `frontend` | `frontend-init` |
| 容器名 | `pepgmp-frontend-prod` | `pepgmp-frontend-init` |
| 容器状态 | `Up` (一直运行) | `Exited (0)` (完成后退出) |
| 内存占用 | ~50MB | ~0MB (退出后) |
| 重启命令 | `docker-compose restart frontend` | `docker-compose up -d frontend-init` |

---

## 下次更新前端

```bash
# 1. Windows: 构建新镜像
.\scripts\build_prod_only.ps1 20251204

# 2. Windows: 导出镜像
docker save pepgmp-frontend:20251204 -o docker-images\pepgmp-frontend-20251204.tar

# 3. WSL2: 导入镜像
docker load -i /mnt/f/code/PythonCode/Pyt/docker-images/pepgmp-frontend-20251204.tar

# 4. WSL2: 更新版本号
cd ~/projects/Pyt
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251204/' .env.production

# 5. WSL2: 重新运行 frontend-init
docker-compose -f docker-compose.prod.yml up -d frontend-init

# 6. 验证
docker logs pepgmp-frontend-init
ls -la frontend/dist/index.html
curl http://localhost/
```

**注意**：nginx 容器**不需要重启**！

