# frontend-init 容器失败处理方案

## 📋 问题描述

`frontend-init` 容器启动失败，退出码 255：
```
service "frontend-init" didn't complete successfully: exit 255
```

## 🔍 问题分析

`frontend-init` 是一个**一次性任务容器**，作用是：
1. 从 `pepgmp-frontend` 镜像中提取静态文件
2. 复制到 `./frontend/dist` 目录
3. 设置文件权限
4. 完成后自动退出

**退出码 255** 通常表示：
- 前端镜像不存在或无法访问
- 镜像中没有 `/usr/share/nginx/html` 目录
- 文件权限问题
- 目录创建失败

---

## ✅ 解决方案

### 方案 1: 检查静态文件是否已存在（推荐）

如果静态文件已经存在，可以忽略这个错误：

```bash
# 在 Ubuntu 服务器上执行
cd ~/projects/PEPGMP

# 检查静态文件是否存在
ls -la frontend/dist/

# 如果存在 index.html，说明静态文件已生成
if [ -f "frontend/dist/index.html" ]; then
    echo "✓ 静态文件已存在，可以忽略 frontend-init 错误"
    echo "继续启动其他服务..."
else
    echo "✗ 静态文件不存在，需要修复 frontend-init"
fi
```

**如果静态文件已存在**，可以：
1. 继续使用现有服务（其他服务可能已经启动）
2. 或者修改配置，让 nginx 不依赖 frontend-init（见方案 3）

---

### 方案 2: 查看 frontend-init 日志找出原因

```bash
# 查看 frontend-init 容器的日志
docker logs pepgmp-frontend-init

# 或使用 docker compose
cd ~/projects/PEPGMP
docker compose -f docker-compose.prod.yml --env-file .env.production logs frontend-init
```

**常见错误和解决方法**：

#### 错误 1: 前端镜像不存在

```
Error response from daemon: pull access denied
```

**解决**：
```bash
# 检查前端镜像是否存在
docker images | grep pepgmp-frontend

# 如果不存在，需要导入或构建
docker load -i /tmp/pepgmp-frontend-20251212.tar
```

#### 错误 2: 镜像中没有静态文件

```
cp: cannot stat '/usr/share/nginx/html/*': No such file or directory
```

**解决**：前端镜像可能没有正确构建，需要重新构建前端镜像。

#### 错误 3: 权限问题

```
chown: changing ownership of '/target/...': Operation not permitted
```

**解决**：
```bash
# 检查 HOST_UID 和 HOST_GID 是否正确
grep -E "HOST_UID|HOST_GID" .env.production

# 获取当前用户的 UID/GID
id

# 在 .env.production 中设置正确的值
echo "HOST_UID=$(id -u)" >> .env.production
echo "HOST_GID=$(id -g)" >> .env.production
```

---

### 方案 3: 手动运行 frontend-init 容器

如果自动启动失败，可以手动运行：

```bash
cd ~/projects/PEPGMP

# 获取镜像标签
IMAGE_TAG=$(grep IMAGE_TAG .env.production | cut -d'=' -f2)
IMAGE_TAG=${IMAGE_TAG:-latest}

# 获取用户 UID/GID
HOST_UID=$(id -u)
HOST_GID=$(id -g)

# 确保目录存在
mkdir -p frontend/dist

# 手动运行 frontend-init 容器
docker run --rm \
  -v "$(pwd)/frontend/dist:/target" \
  -e HOST_UID=$HOST_UID \
  -e HOST_GID=$HOST_GID \
  pepgmp-frontend:${IMAGE_TAG} \
  sh -c "
    mkdir -p /target &&
    cp -r /usr/share/nginx/html/* /target/ &&
    chown -R $HOST_UID:$HOST_GID /target &&
    chmod -R 755 /target &&
    echo 'Static files extracted successfully' &&
    ls -la /target/ | head -10
  "

# 验证
ls -la frontend/dist/
```

---

### 方案 4: 修改配置让 nginx 不依赖 frontend-init（如果静态文件已存在）

如果静态文件已经存在，可以修改 `docker-compose.prod.yml`，让 nginx 不等待 frontend-init：

```bash
cd ~/projects/PEPGMP

# 备份原文件
cp docker-compose.prod.yml docker-compose.prod.yml.backup

# 修改 nginx 的 depends_on，移除 frontend-init 依赖
# 编辑 docker-compose.prod.yml，找到 nginx 服务的 depends_on 部分
# 删除或注释掉 frontend-init 的依赖
```

**或者**，如果静态文件已存在，直接启动其他服务：

```bash
cd ~/projects/PEPGMP

# 只启动核心服务（不启动 frontend-init）
docker compose -f docker-compose.prod.yml --env-file .env.production up -d database redis api nginx

# 查看状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

---

### 方案 5: 临时禁用 frontend-init（如果不需要更新静态文件）

如果静态文件已经存在且不需要更新，可以临时禁用：

```bash
cd ~/projects/PEPGMP

# 方式 1: 注释掉 frontend-init 服务
# 编辑 docker-compose.prod.yml，在 frontend-init 服务前添加注释

# 方式 2: 使用 profiles 功能（Docker Compose V2）
# 在 frontend-init 服务中添加：
# profiles: ["init"]  # 默认不启动
# 需要时手动启动：docker compose --profile init up frontend-init
```

---

## 🚀 快速排查步骤

```bash
# 1. 检查静态文件是否存在
cd ~/projects/PEPGMP
ls -la frontend/dist/index.html 2>/dev/null && echo "✓ 静态文件已存在" || echo "✗ 静态文件不存在"

# 2. 查看 frontend-init 日志
docker logs pepgmp-frontend-init 2>/dev/null || echo "容器不存在或已删除"

# 3. 检查前端镜像
docker images | grep pepgmp-frontend

# 4. 检查其他服务状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 5. 如果静态文件已存在，测试前端访问
curl http://localhost/ 2>/dev/null | head -20
```

---

## 📝 推荐操作流程

### 如果静态文件已存在

```bash
cd ~/projects/PEPGMP

# 1. 验证静态文件
if [ -f "frontend/dist/index.html" ]; then
    echo "✓ 静态文件已存在，可以继续使用"

    # 2. 检查其他服务状态
    docker compose -f docker-compose.prod.yml --env-file .env.production ps

    # 3. 如果其他服务正常，可以忽略 frontend-init 错误
    echo "其他服务应该已经正常启动"
else
    echo "需要修复 frontend-init 或手动提取静态文件"
fi
```

### 如果静态文件不存在

```bash
cd ~/projects/PEPGMP

# 1. 检查前端镜像
docker images | grep pepgmp-frontend

# 2. 如果镜像不存在，导入镜像
VERSION_TAG=20251212  # 替换为实际版本
docker load -i /tmp/pepgmp-frontend-${VERSION_TAG}.tar

# 3. 手动运行 frontend-init（使用上面的方案 3）

# 4. 验证静态文件
ls -la frontend/dist/
```

---

## ✅ 验证清单

- [ ] 静态文件是否存在：`ls -la frontend/dist/index.html`
- [ ] 前端镜像是否存在：`docker images | grep pepgmp-frontend`
- [ ] frontend-init 日志：`docker logs pepgmp-frontend-init`
- [ ] 其他服务状态：`docker compose ps`
- [ ] 前端访问：`curl http://localhost/`

---

## 🔧 常见问题

### Q: frontend-init 失败会影响其他服务吗？

**A**: 取决于配置：
- 如果 nginx 的 `depends_on` 中有 `frontend-init: condition: service_completed_successfully`，nginx 不会启动
- 如果静态文件已存在，可以修改配置移除这个依赖

### Q: 如何更新静态文件？

**A**:
1. 更新前端镜像
2. 重新运行 frontend-init 容器（手动或自动）
3. 或使用方案 3 手动提取

### Q: 可以跳过 frontend-init 吗？

**A**: 可以，如果：
- 静态文件已经存在
- 不需要更新静态文件
- 修改 nginx 的 depends_on 配置

---

## 📚 相关文档

- [部署包解压后操作步骤](./部署包解压后操作步骤.md)
- [前端构建流程分析](./前端构建流程分析.md)
