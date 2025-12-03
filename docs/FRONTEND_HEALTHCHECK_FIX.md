# 修复前端容器健康检查问题

## 问题分析

前端容器状态显示为 `unhealthy`，原因是：

1. **wget 命令不可用**: `nginx:alpine` 镜像默认没有 `wget`
2. **健康检查命令错误**: 使用的 `wget` 参数在 alpine 的 busybox wget 中不支持
3. **健康检查路径**: 需要检查 `/health` 端点

## 已修复

### 1. Dockerfile.frontend
- ✅ 添加 `wget` 安装：`RUN apk add --no-cache wget`
- ✅ 修复健康检查命令：使用 `wget --spider` 方式（更轻量）

### 2. docker-compose.prod.yml 和 docker-compose.prod.1panel.yml
- ✅ 修复健康检查命令：使用 `wget --spider` 方式

## 重新构建和部署

### 步骤 1: 重新构建前端镜像

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt
.\scripts\build_prod_only.ps1 20251202
```

### 步骤 2: 导出并导入到 WSL2

```powershell
# 在 Windows PowerShell 中
.\scripts\export_images_to_wsl.ps1 20251202
```

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251202.tar
```

### 步骤 3: 重启前端服务

```bash
cd ~/projects/Pyt

# 停止并删除旧容器
docker-compose -f docker-compose.prod.yml stop frontend
docker-compose -f docker-compose.prod.yml rm -f frontend

# 启动新容器
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend

# 等待健康检查
sleep 15

# 检查状态
docker-compose -f docker-compose.prod.yml ps frontend
```

## 验证修复

```bash
# 1. 检查容器健康状态
docker inspect pepgmp-frontend-prod --format='{{.State.Health.Status}}'
# 应该显示：healthy

# 2. 测试前端容器内部访问
docker exec pepgmp-frontend-prod wget --spider http://localhost/health
# 应该成功

# 3. 测试通过反向代理访问
curl http://localhost/
# 应该返回 HTML 内容

# 4. 检查浏览器访问
# 打开 http://localhost/ 应该不再白屏
```

## 如果仍有问题

### 检查 nginx 是否在运行

```bash
docker exec pepgmp-frontend-prod ps aux | grep nginx
```

### 检查 nginx 日志

```bash
docker exec pepgmp-frontend-prod cat /var/log/nginx/error.log
```

### 手动测试健康检查

```bash
docker exec pepgmp-frontend-prod wget --spider http://localhost/health
docker exec pepgmp-frontend-prod wget --spider http://localhost/
```

## 临时解决方案（如果不想重新构建）

如果暂时不想重新构建镜像，可以：

1. **禁用健康检查**（不推荐，但可以快速验证）:
```yaml
frontend:
  # ... 其他配置 ...
  healthcheck:
    disable: true
```

2. **使用 curl 替代**（如果镜像有 curl）:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
```

但推荐重新构建镜像以彻底解决问题。

