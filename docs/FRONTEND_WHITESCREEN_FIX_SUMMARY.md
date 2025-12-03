# 前端白屏问题修复总结

## 问题诊断结果

根据诊断脚本的输出，前端容器存在以下问题：

1. ✅ **文件完整**: `index.html` 和 `assets` 文件都存在
2. ✅ **nginx 配置正确**: 前端容器内的 nginx 配置正常
3. ❌ **容器状态 unhealthy**: 健康检查失败
4. ❌ **wget 不可用**: `nginx:alpine` 镜像默认没有 `wget`

## 已修复的问题

### 1. Dockerfile.frontend
- ✅ 添加 `wget` 安装：`RUN apk add --no-cache wget`
- ✅ 修复健康检查命令：使用 `wget --spider` 方式

### 2. docker-compose.prod.yml
- ✅ 修复健康检查命令：使用 `wget --spider` 方式

### 3. docker-compose.prod.1panel.yml
- ✅ 修复健康检查命令：使用 `wget --spider` 方式

## 下一步操作

### 步骤 1: 重新构建前端镜像

在 Windows PowerShell 中：

```powershell
cd F:\Code\PythonCode\Pyt

# 使用新的版本标签（例如：20251202）
.\scripts\build_prod_only.ps1 20251202
```

### 步骤 2: 导出镜像到 WSL2

在 Windows PowerShell 中：

```powershell
.\scripts\export_images_to_wsl.ps1 20251202
```

### 步骤 3: 在 WSL2 中导入镜像

在 WSL2 Ubuntu 中：

```bash
cd /mnt/f/code/PythonCode/Pyt/docker-images

# 导入前端镜像
docker load -i pepgmp-frontend-20251202.tar

# 验证镜像
docker images | grep pepgmp-frontend
```

### 步骤 4: 更新部署目录并重启

在 WSL2 Ubuntu 中：

```bash
cd ~/projects/Pyt

# 更新部署文件（如果需要）
bash /mnt/f/code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes

# 停止并删除旧容器
docker-compose -f docker-compose.prod.yml stop frontend
docker-compose -f docker-compose.prod.yml rm -f frontend

# 更新 .env.production 中的 IMAGE_TAG
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251202/' .env.production

# 启动新容器
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend

# 等待健康检查（约 15 秒）
sleep 15

# 验证容器状态
docker-compose -f docker-compose.prod.yml ps frontend
```

### 步骤 5: 验证修复

```bash
# 1. 检查容器健康状态
docker inspect pepgmp-frontend-prod --format='{{.State.Health.Status}}'
# 应该显示：healthy

# 2. 测试健康检查端点
docker exec pepgmp-frontend-prod wget --spider http://localhost/health

# 3. 测试前端访问
curl http://localhost/ | head -10

# 4. 运行验证脚本
bash /mnt/f/code/PythonCode/Pyt/scripts/verify_frontend_fix.sh
```

### 步骤 6: 浏览器验证

1. 打开浏览器访问：`http://localhost/`
2. 按 F12 打开开发者工具
3. 查看 Console 标签页是否有错误
4. 查看 Network 标签页，确认所有资源文件都成功加载（状态码 200）

## 如果仍有问题

### 检查浏览器控制台

如果页面仍然白屏，请检查：

1. **Console 错误**: 是否有 JavaScript 错误
2. **Network 404**: 是否有资源文件加载失败
3. **CORS 错误**: 是否有跨域问题

### 常见问题

1. **资源路径错误**: 检查 `BASE_URL` 是否正确设置为 `/`
2. **API 连接失败**: 检查 API 服务是否正常运行
3. **nginx 代理错误**: 检查反向代理配置

### 进一步诊断

```bash
# 检查前端容器日志
docker logs pepgmp-frontend-prod --tail 50

# 检查反向代理 nginx 日志
docker logs pepgmp-nginx-prod --tail 50

# 检查前端容器内的文件
docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html/assets/js/

# 测试前端容器内部访问
docker exec pepgmp-frontend-prod wget -qO- http://localhost/ | head -20
```

## 相关文档

- `docs/FRONTEND_HEALTHCHECK_FIX.md` - 健康检查修复详情
- `docs/FRONTEND_WHITESCREEN_TROUBLESHOOTING.md` - 白屏问题排查指南
- `scripts/diagnose_frontend_whitescreen.sh` - 诊断脚本
- `scripts/verify_frontend_fix.sh` - 验证脚本

