# macOS 生产环境部署指南

## 📋 概述

本指南提供在 macOS 环境下直接部署和测试生产环境的完整步骤。由于使用 Docker 容器化部署，理论上可以在任何支持 Docker 的平台上运行。

**前提条件**：
- macOS 系统
- Docker Desktop 已安装并运行
- 至少 8GB 可用内存（推荐 16GB）
- 至少 20GB 可用磁盘空间

---

## 🚀 快速开始

### 步骤 1: 检查 Docker 环境

```bash
# 检查 Docker 是否运行
docker --version
docker compose version

# 检查 Docker 服务状态
docker info
```

**如果 Docker Desktop 未安装**：
1. 下载并安装 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. 启动 Docker Desktop
3. 等待 Docker 服务完全启动（菜单栏图标显示运行中）

---

### 步骤 2: 准备部署目录

```bash
# 在项目根目录
cd /Users/zhou/Code/Pyt

# 创建部署目录（可选，也可以直接在当前目录部署）
mkdir -p ~/projects/Pyt
DEPLOY_DIR=~/projects/Pyt

# 使用 prepare_minimal_deploy.sh 准备部署包
bash scripts/prepare_minimal_deploy.sh "$DEPLOY_DIR"
```

**注意**：如果直接在当前项目目录部署，可以跳过此步骤，直接使用当前目录。

---

### 步骤 3: 生成生产环境配置

```bash
# 进入部署目录（或项目根目录）
cd "$DEPLOY_DIR"  # 或 cd /Users/zhou/Code/Pyt

# 生成配置文件（非交互模式）
bash /Users/zhou/Code/Pyt/scripts/generate_production_config.sh -y

# 检查生成的配置
cat .env.production | head -20
```

**重要配置项**：
- `IMAGE_TAG`: 镜像版本标签（如 `20251202`）
- `HOST_UID` / `HOST_GID`: 自动检测的 macOS 用户 UID/GID
- `API_PORT`: API 端口（默认 8000，容器内）
- `DATABASE_PASSWORD`: 数据库密码（自动生成）

---

### 步骤 4: 构建生产镜像

```bash
# 返回项目根目录
cd /Users/zhou/Code/Pyt

# 设置镜像版本标签
VERSION_TAG=$(date +%Y%m%d)  # 例如: 20251202
echo "Building images with tag: $VERSION_TAG"

# 构建生产镜像
bash scripts/build_prod_only.sh "$VERSION_TAG"

# 验证镜像
docker images | grep pepgmp
```

**预期输出**：
```
pepgmp-backend:20251202
pepgmp-frontend:20251202
```

**如果构建失败**：
- 检查 Docker Desktop 是否运行
- 检查磁盘空间是否充足
- 查看构建日志中的错误信息

---

### 步骤 5: 更新镜像标签配置

```bash
# 在部署目录中
cd "$DEPLOY_DIR"

# 更新 .env.production 中的 IMAGE_TAG
sed -i '' "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production

# 验证
grep IMAGE_TAG .env.production
```

**macOS 注意**：`sed -i ''` 是 macOS 的语法（Linux 使用 `sed -i`）。

---

### 步骤 6: 处理端口占用（重要）

macOS 上 80 端口可能需要管理员权限。有两种方案：

#### 方案 A: 使用非特权端口（推荐）

修改 `docker-compose.prod.yml` 中的端口映射：

```yaml
nginx:
  ports:
    - "8080:80"  # 改为 8080
    - "443:443"
```

然后访问 `http://localhost:8080/`

#### 方案 B: 使用 80 端口（需要权限）

```bash
# 检查 80 端口占用
sudo lsof -i :80

# 如果被占用，停止占用进程或使用其他端口
```

---

### 步骤 7: 启动服务

```bash
# 在部署目录中
cd "$DEPLOY_DIR"

# 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

**预期状态**：
```
pepgmp-frontend-init     Exited (0)  ← 必须成功
pepgmp-nginx-prod        Up (healthy)
pepgmp-api-prod          Up (healthy)
pepgmp-postgres-prod     Up (healthy)
pepgmp-redis-prod        Up (healthy)
```

---

### 步骤 8: 验证部署

```bash
# 检查容器状态
docker compose -f docker-compose.prod.yml ps

# 检查静态文件
ls -la frontend/dist/index.html

# 测试 HTTP 端点
curl http://localhost/  # 或 http://localhost:8080/（如果修改了端口）
curl http://localhost/api/v1/monitoring/health
curl http://localhost/health

# 使用诊断脚本（如果从项目目录运行）
bash /Users/zhou/Code/Pyt/scripts/diagnose_frontend_whitescreen.sh "$DEPLOY_DIR"
```

---

## 🌐 访问应用

### 浏览器访问

- **前端**: `http://localhost/` 或 `http://localhost:8080/`（如果修改了端口）
- **API**: `http://localhost/api/v1/monitoring/health`
- **健康检查**: `http://localhost/health`

### 如果遇到白屏

参考 [前端白屏问题排查指南](./前端白屏问题排查指南.md)

---

## 🔧 macOS 特定注意事项

### 1. 文件权限

macOS 和 Linux 的 UID/GID 可能不同，但容器内会自动处理：

```bash
# 检查当前用户 UID/GID
id -u  # macOS 通常是 501
id -g  # macOS 通常是 20

# 这些会自动写入 .env.production
grep HOST_UID .env.production
```

### 2. Docker Desktop 资源限制

**推荐配置**（Docker Desktop Settings）：
- **Memory**: 至少 8GB（推荐 16GB）
- **CPUs**: 至少 4 核
- **Disk**: 至少 60GB

**检查资源使用**：
```bash
docker stats
```

### 3. 端口冲突

macOS 上常见端口占用：
- **80**: AirPlay Receiver（可在系统设置中关闭）
- **8000**: 可能被其他应用占用

**检查端口占用**：
```bash
# 检查 80 端口
sudo lsof -i :80

# 检查 8000 端口
lsof -i :8000
```

### 4. 路径差异

macOS 使用 `/Users/` 而不是 `/home/`，但脚本已自动处理：

```bash
# prepare_minimal_deploy.sh 会自动使用 $HOME
# macOS: $HOME = /Users/username
# Linux: $HOME = /home/username
```

### 5. sed 命令差异

macOS 的 `sed` 需要 `-i ''` 而不是 `-i`：

```bash
# macOS
sed -i '' 's/old/new/' file

# Linux
sed -i 's/old/new/' file
```

脚本已自动处理此差异。

---

## 🛠️ 故障排查

### 问题 1: Docker Desktop 未运行

**症状**：
```
Cannot connect to the Docker daemon
```

**解决**：
1. 打开 Docker Desktop
2. 等待完全启动（菜单栏图标显示运行中）
3. 重新运行命令

### 问题 2: 端口被占用

**症状**：
```
Error: bind: address already in use
```

**解决**：
```bash
# 查找占用进程
sudo lsof -i :80
sudo lsof -i :8000

# 停止进程或修改 docker-compose.prod.yml 中的端口
```

### 问题 3: 内存不足

**症状**：
```
Container killed (out of memory)
```

**解决**：
1. 增加 Docker Desktop 内存限制（Settings → Resources）
2. 关闭其他占用内存的应用
3. 重启 Docker Desktop

### 问题 4: 磁盘空间不足

**症状**：
```
No space left on device
```

**解决**：
```bash
# 清理 Docker 资源
docker system prune -a

# 检查磁盘空间
df -h
```

### 问题 5: 前端白屏

参考 [前端白屏问题排查指南](./前端白屏问题排查指南.md)

---

## 📊 性能优化

### Docker Desktop 设置

1. **启用 VirtioFS**（如果可用）：
   - Settings → General → Use VirtioFS for file sharing
   - 提高文件 I/O 性能

2. **调整资源限制**：
   - Settings → Resources
   - 根据 Mac 配置调整内存和 CPU

3. **使用 Docker BuildKit**：
   ```bash
   export DOCKER_BUILDKIT=1
   export COMPOSE_DOCKER_CLI_BUILD=1
   ```

---

## 🔄 更新部署

### 更新镜像

```bash
# 1. 构建新镜像
cd /Users/zhou/Code/Pyt
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh "$VERSION_TAG"

# 2. 更新配置
cd "$DEPLOY_DIR"
sed -i '' "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production

# 3. 重启服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate
```

### 更新配置

```bash
cd "$DEPLOY_DIR"

# 修改 .env.production
nano .env.production

# 重启服务
docker compose -f docker-compose.prod.yml --env-file .env.production restart
```

---

## 🛑 停止和清理

### 停止服务

```bash
cd "$DEPLOY_DIR"
docker compose -f docker-compose.prod.yml down
```

### 清理数据（谨慎）

```bash
# 停止并删除容器、网络
docker compose -f docker-compose.prod.yml down -v

# 删除镜像
docker rmi pepgmp-backend:20251202 pepgmp-frontend:20251202

# 清理未使用的资源
docker system prune -a
```

---

## 📚 相关文档

- [前端白屏问题排查指南](./前端白屏问题排查指南.md)
- [完整部署方案说明](./完整部署方案说明.md)
- [WSL2 生产部署详细步骤](./WSL2生产部署详细步骤.md)

---

## ✅ 检查清单

部署前：
- [ ] Docker Desktop 已安装并运行
- [ ] 至少 8GB 可用内存
- [ ] 至少 20GB 可用磁盘空间
- [ ] 端口 80/8080 未被占用

部署中：
- [ ] 镜像构建成功
- [ ] 配置文件生成成功
- [ ] 所有容器启动成功
- [ ] frontend-init 成功退出（Exit 0）

部署后：
- [ ] 前端页面可访问
- [ ] API 健康检查返回 200
- [ ] 浏览器控制台无错误
- [ ] 静态文件正确加载

---

**最后更新**: 2025-12-02
