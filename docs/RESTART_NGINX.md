# 重启 Nginx 并验证配置

## 重启 Nginx

```bash
cd ~/projects/Pyt

# 重启 nginx 容器
docker-compose -f docker-compose.prod.yml restart nginx

# 或者重新加载配置（如果支持）
docker exec pepgmp-nginx-prod nginx -s reload
```

## 验证配置

### 步骤 1: 检查 Nginx 容器状态

```bash
docker-compose -f docker-compose.prod.yml ps nginx

# 应该显示 "Up" 状态
```

### 步骤 2: 检查 Nginx 配置语法

```bash
docker exec pepgmp-nginx-prod nginx -t

# 应该显示：nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 步骤 3: 测试 API 访问

```bash
# 通过 nginx 代理访问
curl http://localhost/api/v1/monitoring/health

# 直接访问 API
curl http://localhost:8000/api/v1/monitoring/health

# 访问 API 文档（浏览器）
# http://localhost:8000/docs
```

### 步骤 4: 查看 Nginx 日志

```bash
# 查看访问日志
docker-compose -f docker-compose.prod.yml logs nginx | tail -20

# 查看错误日志
docker exec pepgmp-nginx-prod tail -20 /var/log/nginx/error.log
```

## 如果 Nginx 启动失败

### 检查错误日志

```bash
docker-compose -f docker-compose.prod.yml logs nginx | tail -50
```

### 常见问题

1. **配置语法错误**:
   ```bash
   docker exec pepgmp-nginx-prod nginx -t
   ```

2. **端口被占用**:
   ```bash
   sudo netstat -tulpn | grep :80
   ```

3. **文件权限问题**:
   ```bash
   ls -la nginx/nginx.conf
   ```

## 完整验证流程

```bash
cd ~/projects/Pyt

# 1. 重启 nginx
docker-compose -f docker-compose.prod.yml restart nginx

# 2. 等待几秒
sleep 3

# 3. 检查状态
docker-compose -f docker-compose.prod.yml ps nginx

# 4. 测试配置
docker exec pepgmp-nginx-prod nginx -t

# 5. 测试访问
curl http://localhost/api/v1/monitoring/health

# 6. 查看日志
docker-compose -f docker-compose.prod.yml logs nginx | tail -10
```

