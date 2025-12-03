# 前端白屏问题排查

## 问题分析

前端页面显示白屏通常由以下原因导致：
1. **静态文件缺失** - index.html 或 assets 文件不存在
2. **路径问题** - BASE_URL 配置不正确，资源加载失败
3. **代理配置错误** - nginx 代理配置不正确
4. **JavaScript 错误** - 浏览器控制台有错误
5. **CORS 问题** - 跨域请求被阻止

## 快速诊断

运行诊断脚本：

```bash
cd ~/projects/Pyt

# 运行诊断脚本
bash /mnt/f/code/PythonCode/Pyt/scripts/diagnose_frontend_whitescreen.sh
```

## 详细检查步骤

### 步骤 1: 检查前端容器文件

```bash
# 检查前端容器中的文件
docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html

# 检查 index.html
docker exec pepgmp-frontend-prod cat /usr/share/nginx/html/index.html

# 检查 assets 目录
docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html/assets
```

### 步骤 2: 检查前端容器 nginx 配置

```bash
# 查看前端容器内的 nginx 配置
docker exec pepgmp-frontend-prod cat /etc/nginx/conf.d/default.conf

# 测试配置
docker exec pepgmp-frontend-prod nginx -t
```

### 步骤 3: 测试前端容器直接访问

```bash
# 测试前端容器内部访问
docker exec pepgmp-frontend-prod wget -qO- http://localhost/

# 测试健康检查
docker exec pepgmp-frontend-prod wget -qO- http://localhost/health
```

### 步骤 4: 检查反向代理配置

```bash
# 检查反向代理 nginx 配置
docker exec pepgmp-nginx-prod cat /etc/nginx/nginx.conf | grep -A 10 "location /"

# 测试从 nginx 访问前端
docker exec pepgmp-nginx-prod wget -qO- http://frontend:80/
```

### 步骤 5: 检查浏览器控制台

在浏览器中：
1. 按 F12 打开开发者工具
2. 查看 Console 标签页的错误信息
3. 查看 Network 标签页，检查哪些文件加载失败

## 常见问题和解决方案

### 问题 1: index.html 存在但 assets 文件缺失

**症状**: index.html 可以访问，但 JavaScript/CSS 文件 404

**检查**:
```bash
docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html/assets
```

**解决方案**: 重新构建前端镜像

### 问题 2: BASE_URL 配置不正确

**症状**: 资源文件路径错误（如 `/assets/...` 应该是 `/assets/...`）

**检查**:
```bash
# 查看 index.html 中的资源路径
docker exec pepgmp-frontend-prod cat /usr/share/nginx/html/index.html | grep -E 'src=|href='
```

**解决方案**: 检查 `vite.config.ts` 中的 `base` 配置和构建时的 `BASE_URL` 参数

### 问题 3: 代理配置错误

**症状**: 前端容器正常，但通过反向代理访问失败

**检查**:
```bash
# 检查 nginx 配置中的 frontend upstream
docker exec pepgmp-nginx-prod grep -A 5 "upstream frontend" /etc/nginx/nginx.conf

# 检查 location / 配置
docker exec pepgmp-nginx-prod grep -A 10 "location /" /etc/nginx/nginx.conf
```

**解决方案**: 确保 nginx 配置正确代理到 `frontend:80`

### 问题 4: JavaScript 错误

**症状**: 浏览器控制台显示 JavaScript 错误

**检查**: 在浏览器中按 F12，查看 Console 标签页

**常见错误**:
- `Failed to load resource: net::ERR_NAME_NOT_RESOLVED` - 网络问题
- `Uncaught SyntaxError` - JavaScript 语法错误
- `CORS policy` - 跨域问题

### 问题 5: 路径不匹配

**症状**: 资源文件路径不正确

**检查**:
```bash
# 查看 index.html 中的 base 路径
docker exec pepgmp-frontend-prod cat /usr/share/nginx/html/index.html | grep base
```

**解决方案**: 
- 如果前端在根路径 `/`，BASE_URL 应该是 `/`
- 如果前端在子路径 `/app/`，BASE_URL 应该是 `/app/`

## 快速修复

### 修复 1: 重新构建前端镜像

```bash
# 在 Windows 上
cd F:\Code\PythonCode\Pyt
.\scripts\build_prod_only.ps1 20251201

# 导出并导入到 WSL2
.\scripts\export_images_to_wsl.ps1 20251201

# 在 WSL2 中
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-frontend-20251201.tar

# 重启前端服务
cd ~/projects/Pyt
docker-compose -f docker-compose.prod.yml restart frontend
```

### 修复 2: 检查并修复 BASE_URL

```bash
# 检查构建时的 BASE_URL
docker inspect pepgmp-frontend-prod | grep -i base_url

# 如果 BASE_URL 不正确，需要重新构建
```

### 修复 3: 修复 nginx 代理配置

```bash
cd ~/projects/Pyt

# 更新 nginx 配置
bash /mnt/f/code/PythonCode/Pyt/scripts/update_nginx_for_frontend.sh ~/projects/Pyt

# 重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## 验证修复

```bash
# 1. 检查前端容器文件
docker exec pepgmp-frontend-prod ls -la /usr/share/nginx/html

# 2. 测试前端容器直接访问
docker exec pepgmp-frontend-prod wget -qO- http://localhost/ | head -20

# 3. 测试通过反向代理访问
curl http://localhost/ | head -20

# 4. 检查浏览器控制台（手动）
# 打开 http://localhost/ 按 F12 查看
```

