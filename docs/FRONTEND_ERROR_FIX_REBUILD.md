# 前端错误修复：重新构建

## 问题分析

### 错误信息
```
vue-vendor-oq9SroqG.js:13  Uncaught ReferenceError: Cannot access 'ql' before initialization
```

### 根本原因

1. **镜像未重新构建**：
   - `pepgmp-frontend:20251202` 和 `pepgmp-frontend:20251203` 是同一个镜像（IMAGE ID 相同）
   - 之前修复 `vite.config.ts` 后没有重新构建镜像

2. **静态文件混合**：
   - 部署目录中同时存在旧版本和新版本的 JS 文件
   - HTML 引用新版本，但模块加载顺序问题仍然存在

### 验证

```bash
# 检查镜像 ID
docker images | grep pepgmp-frontend
# 输出：
# pepgmp-frontend  20251202  a8f64541b45b  ← 相同 ID
# pepgmp-frontend  20251203  a8f64541b45b  ← 相同 ID
```

---

## 解决方案

### 步骤 1: 重新构建前端镜像（Windows）

```powershell
# 在 Windows PowerShell 中
cd F:\Code\PythonCode\Pyt

# 重新构建前端镜像（使用新版本号）
.\scripts\build_prod_only.ps1 20251203-fix

# 或者只构建前端
docker build -f Dockerfile.frontend `
  --build-arg VITE_API_BASE=/api/v1 `
  --build-arg BASE_URL=/ `
  --build-arg SKIP_TYPE_CHECK=true `
  -t pepgmp-frontend:20251203-fix `
  -t pepgmp-frontend:latest `
  .
```

**重要**：使用新的版本号（如 `20251203-fix`）以区分旧镜像

---

### 步骤 2: 导出镜像（Windows）

```powershell
# 导出新镜像
docker save pepgmp-frontend:20251203-fix -o docker-images\pepgmp-frontend-20251203-fix.tar
```

---

### 步骤 3: 导入镜像（WSL2）

```bash
# 在 WSL2 Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251203-fix.tar

# 验证镜像 ID 已变化
docker images | grep pepgmp-frontend
```

---

### 步骤 4: 清理并重新部署（WSL2）

```bash
cd ~/projects/Pyt

# 1. 停止服务
docker-compose -f docker-compose.prod.yml down

# 2. 完全删除旧的静态文件
rm -rf frontend/dist

# 3. 更新版本号
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251203-fix/' .env.production

# 4. 重新启动服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 5. 等待 frontend-init 完成
sleep 15

# 6. 验证
docker logs pepgmp-frontend-init
ls -la frontend/dist/assets/js/ | head -20
```

---

### 步骤 5: 验证修复

```bash
# 检查静态文件（应该只有一个版本）
cd ~/projects/Pyt/frontend/dist/assets/js
ls -la | grep vue-vendor
# 应该只有一个 vue-vendor-*.js 文件

# 测试前端
curl http://localhost/ | grep vue-vendor
```

**在浏览器中测试**：
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 访问 `http://localhost/`
3. 打开控制台（F12）
4. 检查是否还有 `Uncaught ReferenceError` 错误

---

## 快速修复（临时方案）

如果不想重新构建，可以尝试清理静态文件：

```bash
cd ~/projects/Pyt

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 删除旧静态文件
rm -rf frontend/dist

# 重新启动（使用现有镜像）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 验证
docker logs pepgmp-frontend-init
curl http://localhost/
```

**注意**：这只是清理混合文件，但如果镜像本身有问题，仍需重新构建。

---

## 为什么之前测试能正常显示？

可能的原因：

1. **之前使用的是更早的镜像**（20251201 或更早）
   - 那时的 `vite.config.ts` 可能没有复杂的 chunk 分割
   - 或者使用的是不同的构建配置

2. **浏览器缓存**
   - 之前测试时浏览器缓存了旧版本的 JS 文件
   - 新部署后缓存失效，暴露了问题

3. **静态文件来源不同**
   - 之前可能是手动复制的 `dist` 目录
   - 现在是从镜像中提取的

---

## 验证 vite.config.ts 修复是否生效

重新构建后，检查生成的 JS 文件：

```bash
# 在 Windows 中构建后
cd frontend\dist\assets\js
dir | findstr vue-vendor

# 应该看到 vue-vendor-*.js 文件
# 这个文件应该包含 vue、vue-router、@vicons/* 等
```

---

## 总结

**根本原因**：前端镜像未重新构建，`vite.config.ts` 的修复未生效

**解决方法**：
1. ✅ 重新构建前端镜像（推荐）
2. ⏸️ 清理静态文件（临时方案）

**验证标准**：
- ✅ 镜像 ID 已变化
- ✅ 静态文件目录中只有一个版本的 JS 文件
- ✅ 浏览器控制台无 `Uncaught ReferenceError` 错误
- ✅ 前端页面正常显示

