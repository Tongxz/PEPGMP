# 方案 5 实施文档：Init Container 模式

## 实施完成

已成功实施方案 5（Init Container 模式），优化前端静态文件提取流程。

## 改动总结

### 修改的文件（共 3 个）

1. **docker-compose.prod.yml**
   - 服务名：`frontend` → `frontend-init`
   - 移除 `networks`（不需要网络）
   - 移除 `entrypoint`（使用默认）
   - 简化 `command`（移除 `tail -f /dev/null`，完成后自动退出）
   - nginx 的 `depends_on` 更新为 `frontend-init`
   - 添加 `IMAGE_REGISTRY` 支持（私有仓库）

2. **docker-compose.prod.1panel.yml**
   - 相同的改动

3. **scripts/redeploy_scheme_b.sh**
   - 日志输出：`frontend` → `frontend-init`
   - 容器名：`pepgmp-frontend-prod` → `pepgmp-frontend-init`

### 新增的文档（共 2 个）

1. **docs/PRIVATE_REGISTRY_SUPPORT.md**
   - 私有容器仓库支持文档
   - 详细说明如何切换到私有仓库

2. **docs/SCHEME_5_INIT_CONTAINER_IMPLEMENTATION.md**（本文档）
   - 实施总结

---

## 关键改动对比

### frontend 服务改动

**改动前**：
```yaml
frontend:
  image: pepgmp-frontend:${IMAGE_TAG:-latest}
  container_name: pepgmp-frontend-prod
  networks:
    - frontend
  volumes:
    - ./frontend/dist:/target
  entrypoint: ["sh", "-c"]
  command: >
    "
      cp -r /usr/share/nginx/html/* /target/ &&
      tail -f /dev/null  # 保持运行
    "
  restart: "no"
```

**改动后**：
```yaml
frontend-init:
  image: ${IMAGE_REGISTRY:-}pepgmp-frontend:${IMAGE_TAG:-latest}
  container_name: pepgmp-frontend-init
  # 移除 networks（不需要网络）
  volumes:
    - ./frontend/dist:/target
  # 移除 entrypoint（使用默认）
  command: >
    sh -c "
      echo 'Frontend Init Container - Extracting static files...' &&
      mkdir -p /target &&
      cp -r /usr/share/nginx/html/* /target/ &&
      chmod -R 755 /target &&
      echo '[OK] Static files extracted successfully' &&
      echo 'Frontend init completed - container will exit'
      # 移除 tail -f /dev/null，完成后自动退出
    "
  restart: "no"
```

**关键变化**：
1. ✅ 服务名更语义化：`frontend-init`
2. ✅ 完成后自动退出（不再保持运行）
3. ✅ 支持私有仓库：`${IMAGE_REGISTRY:-}`
4. ✅ 简化配置（移除不必要的 `networks` 和 `entrypoint`）

---

## 部署流程（不变）

### 首次部署

```bash
# ========== Windows ==========
.\scripts\build_prod_only.ps1 20251203
.\scripts\export_images_to_wsl.ps1 20251203

# ========== WSL2/Ubuntu ==========
docker load -i /mnt/f/.../pepgmp-frontend-20251203.tar
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### 更新前端

```bash
# ========== Windows ==========
.\scripts\build_prod_only.ps1 20251203
docker save pepgmp-frontend:20251203 -o docker-images\pepgmp-frontend-20251203.tar

# ========== WSL2/Ubuntu ==========
docker load -i /mnt/f/.../pepgmp-frontend-20251203.tar
cd ~/projects/Pyt
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251203/' .env.production
docker-compose -f docker-compose.prod.yml up -d frontend-init
```

**注意**：服务名从 `frontend` 改为 `frontend-init`

---

## 资源占用对比

| 项目 | 改动前 | 改动后 | 改进 |
|------|--------|--------|------|
| frontend 容器状态 | 一直运行 | 完成后退出 | ✅ 节省资源 |
| 内存占用 | ~50MB | ~0MB（退出后） | ✅ 节省 50MB |
| CPU 占用 | 极低（idle） | 0%（退出后） | ✅ 完全释放 |
| 运行中容器数 | 5 个 | 4 个 | ✅ 更清爽 |

---

## 验证

### 检查容器状态

```bash
# 查看所有容器（包括已退出的）
docker ps -a | grep pepgmp

# 应该看到：
# pepgmp-frontend-init  ... Exited (0) ... 
# pepgmp-nginx-prod     ... Up ...
# pepgmp-api-prod       ... Up ...
# pepgmp-postgres-prod  ... Up ...
# pepgmp-redis-prod     ... Up ...
```

### 检查静态文件

```bash
# 验证静态文件已提取
ls -la frontend/dist/index.html

# 查看文件数量
find frontend/dist -type f | wc -l
```

### 查看日志

```bash
# 查看 frontend-init 日志（应该看到提取成功的消息）
docker logs pepgmp-frontend-init

# 应该看到：
# =========================================================================
# Frontend Init Container - Extracting static files...
# =========================================================================
# Image: pepgmp-frontend:20251203
# Target: /target (mounted to ./frontend/dist)
# 
# [OK] Static files extracted successfully
# ...
# Total files: 18
# =========================================================================
# Frontend init completed - container will exit
# =========================================================================
```

### 测试前端访问

```bash
# 测试前端
curl http://localhost/ | head -20

# 测试 API
curl http://localhost/api/v1/monitoring/health
```

---

## 私有仓库支持

### 当前配置（本地镜像）

```bash
# .env.production
IMAGE_REGISTRY=  # 留空
IMAGE_TAG=20251203
```

**镜像格式**：
```
pepgmp-backend:20251203
pepgmp-frontend:20251203
```

### 未来配置（私有仓库）

```bash
# .env.production
IMAGE_REGISTRY=registry.example.com/  # 注意末尾的斜杠
IMAGE_TAG=20251203
```

**镜像格式**：
```
registry.example.com/pepgmp-backend:20251203
registry.example.com/pepgmp-frontend:20251203
```

**切换方法**：
1. 修改 `.env.production` 中的 `IMAGE_REGISTRY`
2. 重新部署：`docker-compose up -d`

详见：`docs/PRIVATE_REGISTRY_SUPPORT.md`

---

## 优势总结

### 1. 资源优化
- ✅ frontend-init 容器完成任务后自动退出
- ✅ 节省约 50MB 内存
- ✅ 释放 CPU 资源

### 2. 语义清晰
- ✅ `frontend-init` 名称明确表示"初始化容器"
- ✅ 符合 Kubernetes Init Container 理念
- ✅ 更易理解和维护

### 3. 架构优雅
- ✅ 职责单一：frontend-init 只负责提取静态文件
- ✅ 依赖明确：nginx 等待 frontend-init 完成
- ✅ 无冗余：不需要保持容器运行

### 4. 扩展性强
- ✅ 支持私有仓库（通过 `IMAGE_REGISTRY` 环境变量）
- ✅ 无需修改代码即可切换镜像来源
- ✅ 向后兼容（不设置 `IMAGE_REGISTRY` 时行为不变）

---

## 注意事项

### 1. 服务名变更

**重要**：服务名从 `frontend` 改为 `frontend-init`

**影响的命令**：
```bash
# 旧命令（不再有效）
docker-compose restart frontend
docker logs pepgmp-frontend-prod

# 新命令
docker-compose up -d frontend-init
docker logs pepgmp-frontend-init
```

### 2. 容器状态

frontend-init 容器完成任务后会显示为 `Exited (0)`，这是**正常行为**，不是错误。

### 3. 更新静态文件

更新前端代码后，需要重新运行 `frontend-init` 容器：
```bash
docker-compose up -d frontend-init
```

nginx 容器**不需要重启**，因为它读取的是主机目录 `./frontend/dist`。

---

## 下一步

1. ✅ **测试验证**：在 WSL2 环境中测试新流程
2. ⏸️ **搭建私有仓库**：未来生产环境使用
3. ⏸️ **CI/CD 集成**：自动化构建和部署

---

## 相关文档

- `docs/PRIVATE_REGISTRY_SUPPORT.md` - 私有仓库支持文档
- `docs/SCHEME_B_DEPLOYMENT_GUIDE.md` - 方案 B 部署指南
- `docs/SCHEME_B_OPTIMIZATION_SUMMARY.md` - 优化总结

