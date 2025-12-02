# 验证 Nginx 配置就绪

## 当前状态

✅ nginx 目录权限正确（pep:pep）
✅ nginx.conf 文件存在

## 修复文件权限（可选）

```bash
cd ~/projects/Pyt

# 修复 nginx.conf 权限（应该是 644，不是 755）
chmod 644 nginx/nginx.conf

# 验证
ls -la nginx/nginx.conf
# 应该显示：-rw-r--r-- ... nginx.conf
```

## 验证配置

### 步骤 1: 检查配置内容

```bash
cd ~/projects/Pyt

# 查看配置前几行
head -20 nginx/nginx.conf

# 检查是否有 frontend upstream（如果有前端镜像）
grep -A 2 "upstream frontend" nginx/nginx.conf || echo "No frontend upstream (OK if no frontend)"
```

### 步骤 2: 检查 Docker Compose 配置

```bash
cd ~/projects/Pyt

# 检查前端服务是否已添加
grep -A 10 "^  frontend:" docker-compose.prod.yml || echo "Frontend service not found in docker-compose.prod.yml"

# 检查 nginx 依赖
grep -A 5 "depends_on:" docker-compose.prod.yml | grep -A 5 "nginx:"
```

### 步骤 3: 启动服务

```bash
cd ~/projects/Pyt

# 如果前端镜像存在，启动前端服务
docker images | grep pepgmp-frontend

# 如果有前端镜像，启动前端
if docker images | grep -q pepgmp-frontend; then
    echo "Frontend image found, starting frontend service..."
    docker-compose -f docker-compose.prod.yml --env-file .env.production up -d frontend
    sleep 5
fi

# 重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx

# 等待几秒
sleep 3

# 检查所有服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 4: 验证访问

```bash
# 测试 nginx 配置
docker exec pepgmp-nginx-prod nginx -t

# 测试 API 访问
curl http://localhost/api/v1/monitoring/health

# 如果前端已启动，测试前端
curl http://localhost/
```

## 如果前端镜像不存在

如果前端镜像不存在，nginx 配置应该不包含 `frontend_backend` upstream。当前配置应该可以正常工作（只代理 API）。

## 下一步

1. ✅ nginx 配置已就绪
2. 修复文件权限（可选）：`chmod 644 nginx/nginx.conf`
3. 启动前端服务（如果前端镜像存在）
4. 重启 nginx
5. 验证访问

