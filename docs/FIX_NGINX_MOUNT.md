# 修复 Nginx 挂载错误

## 错误信息

```
Error response from daemon: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: error mounting "/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/Ubuntu-22.04/..." to rootfs at "/etc/nginx/nginx.conf": mount ...: not a directory: unknown: Are you trying to mount a directory onto a file (or vice-versa)?
```

## 原因

`docker-compose.prod.yml` 中 nginx 服务尝试挂载 `./nginx/nginx.conf` 文件，但该文件不存在或路径不正确。

## 解决方案

### 方案 1: 禁用 Nginx 服务（如果不需要）

如果不需要 Nginx 反向代理，可以注释掉 nginx 服务：

```bash
cd ~/projects/Pyt

# 编辑 docker-compose.prod.yml，注释掉 nginx 服务
# 或者使用 sed 命令
sed -i '/^  nginx:/,/^  [a-z]/ { /^  nginx:/! { /^  [a-z]/! s/^/#/ } }' docker-compose.prod.yml
```

### 方案 2: 创建 Nginx 配置文件

如果需要 Nginx，创建必要的配置文件：

```bash
cd ~/projects/Pyt

# 创建 nginx 目录
mkdir -p nginx/ssl

# 创建基本的 nginx.conf 文件
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 创建空的 ssl 目录（如果需要 SSL）
touch nginx/ssl/.gitkeep
```

### 方案 3: 修改配置使挂载可选

修改 `docker-compose.prod.yml`，使 nginx 配置挂载可选：

```yaml
nginx:
  image: nginx:alpine
  container_name: pepgmp-nginx-prod
  ports:
    - "80:80"
    - "443:443"
  volumes:
    # 只在文件存在时挂载（需要修改为条件挂载或使用默认配置）
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  # 或者使用 nginx 默认配置，不挂载自定义配置
  # command: ["nginx", "-g", "daemon off;"]
```

## 推荐方案

**如果不需要 Nginx**（API 直接暴露在 8000 端口），使用方案 1，注释掉 nginx 服务。

**如果需要 Nginx**，使用方案 2，创建配置文件。

## 快速修复（禁用 Nginx）

```bash
cd ~/projects/Pyt

# 备份原文件
cp docker-compose.prod.yml docker-compose.prod.yml.backup

# 注释掉 nginx 服务（从 nginx: 到下一个服务之前）
sed -i '/^  nginx:/,/^  [a-z]/ { 
    /^  nginx:/! { 
        /^  [a-z]/! s/^/#/ 
    } 
}' docker-compose.prod.yml

# 或者手动编辑，找到 nginx 服务部分，在每行前加 #
```

## 重新启动服务

```bash
cd ~/projects/Pyt

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 重新启动（nginx 将被跳过）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

