# 方案 B 简化部署流程（已优化）

## 优化说明

**问题**：之前的部署流程太复杂
- 需要构建 → 导出 → 导入 → 手动提取 → 挂载（5步）

**优化后**：自动化部署流程
- 构建 → 导入 → 启动（3步，启动时自动提取）

## 新架构

```
前端容器启动 → 自动提取静态文件到 ./frontend/dist → Nginx 挂载该目录
```

## 关键改进

### 1. 前端容器自动提取静态文件

**docker-compose.prod.yml 配置**：
```yaml
frontend:
  image: pepgmp-frontend:${IMAGE_TAG:-latest}
  volumes:
    - ./frontend/dist:/target  # 挂载主机目录
  entrypoint: ["sh", "-c"]
  command: >
    "
      cp -r /usr/share/nginx/html/* /target/ &&
      tail -f /dev/null
    "
  restart: "no"
```

**效果**：
- ✅ 前端容器启动时自动提取静态文件
- ✅ 无需手动操作
- ✅ Nginx 直接使用提取的文件

### 2. Nginx 依赖前端容器

```yaml
nginx:
  depends_on:
    - api
    - frontend  # 确保静态文件已提取
```

**效果**：
- ✅ Nginx 启动前，前端容器已完成静态文件提取
- ✅ 保证静态文件可用

## 简化后的部署流程

### 步骤 1: 构建前端镜像（Windows）

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt

# 构建前端镜像
.\scripts\build_prod_only.ps1 20251202
```

### 步骤 2: 导出并导入镜像（Windows → WSL2）

```powershell
# 在 Windows PowerShell 中
.\scripts\export_images_to_wsl.ps1 20251202
```

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251202.tar
```

### 步骤 3: 启动服务（自动提取静态文件）

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 使用快速部署脚本（已优化）
bash /mnt/f/code/PythonCode/Pyt/scripts/redeploy_scheme_b.sh

# 或者手动启动
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**自动完成**：
- ✅ 前端容器启动
- ✅ 自动提取静态文件到 `./frontend/dist`
- ✅ Nginx 自动挂载静态文件
- ✅ 服务就绪

## 流程对比

### 之前（5步，手动操作多）

1. 构建前端镜像
2. 导出镜像
3. 导入镜像到 WSL2
4. **手动提取静态文件**（复杂）
5. 启动服务

### 现在（3步，全自动）

1. 构建前端镜像
2. 导入镜像到 WSL2
3. **启动服务（自动提取）**（简单）

## 更新静态文件

**更新前端代码后**：

```bash
# 1. 重新构建前端镜像（Windows）
.\scripts\build_prod_only.ps1 20251202

# 2. 重新导入镜像（WSL2）
docker load -i /mnt/f/code/PythonCode/Pyt/docker-images/pepgmp-frontend-20251202.tar

# 3. 重启前端容器（自动重新提取）
docker-compose -f docker-compose.prod.yml restart frontend

# 或者重新启动所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
```

**优势**：
- ✅ 只需重启前端容器
- ✅ 自动重新提取最新静态文件
- ✅ 无需手动操作

## 验证

```bash
# 检查静态文件是否已提取
ls -la frontend/dist/index.html

# 检查前端容器日志（应该看到提取成功的消息）
docker logs pepgmp-frontend-prod

# 测试前端访问
curl http://localhost/ | head -20
```

## 优势总结

1. **自动化**：无需手动提取静态文件
2. **简化**：从5步减少到3步
3. **高效**：更新时只需重启容器
4. **可靠**：docker-compose 确保依赖顺序

## 注意事项

1. **首次部署**：需要导入前端镜像
2. **更新前端**：重新导入镜像后重启前端容器即可
3. **静态文件位置**：`./frontend/dist`（自动管理）

