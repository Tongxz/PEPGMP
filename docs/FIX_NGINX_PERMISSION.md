# 修复 Nginx 权限问题

## 错误信息

```
-bash: nginx/nginx.conf: Permission denied
```

## 原因

nginx 目录或文件的权限不正确，导致无法创建或修改文件。

## 解决方案

### 步骤 1: 检查当前权限

```bash
cd ~/projects/Pyt

# 检查 nginx 目录权限
ls -la nginx/

# 检查目录权限
ls -ld nginx/
```

### 步骤 2: 修复权限

```bash
cd ~/projects/Pyt

# 删除错误的目录结构（如果存在）
rm -rf nginx/nginx.conf

# 确保 nginx 目录存在且有正确权限
mkdir -p nginx/ssl
chmod 755 nginx

# 创建 nginx.conf 文件
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 设置文件权限
chmod 644 nginx/nginx.conf

# 验证
ls -la nginx/nginx.conf
```

### 步骤 3: 如果仍然有权限问题

```bash
cd ~/projects/Pyt

# 完全删除 nginx 目录并重新创建
rm -rf nginx

# 重新创建
mkdir -p nginx/ssl
chmod 755 nginx
chmod 755 nginx/ssl

# 使用 echo 或 printf 创建文件（如果 cat 有问题）
cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 设置权限
chmod 644 nginx/nginx.conf
```

### 步骤 4: 使用 Python 创建文件（如果 bash 有问题）

```bash
cd ~/projects/Pyt

# 使用 Python 创建文件
python3 << 'PYTHON_EOF'
import os

# 确保目录存在
os.makedirs('nginx/ssl', exist_ok=True)

# 创建 nginx.conf
nginx_conf = """events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""

with open('nginx/nginx.conf', 'w') as f:
    f.write(nginx_conf)

# 设置权限
os.chmod('nginx/nginx.conf', 0o644)
os.chmod('nginx', 0o755)
os.chmod('nginx/ssl', 0o755)

print("nginx.conf created successfully")
PYTHON_EOF

# 验证
ls -la nginx/nginx.conf
```

## 快速修复命令（推荐）

```bash
cd ~/projects/Pyt

# 完全重置 nginx 目录
rm -rf nginx
mkdir -p nginx/ssl

# 使用 Python 创建文件（最可靠）
python3 << 'PYEOF'
import os
os.makedirs('nginx/ssl', exist_ok=True)
conf = """events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""
with open('nginx/nginx.conf', 'w') as f:
    f.write(conf)
os.chmod('nginx/nginx.conf', 0o644)
print("✓ nginx.conf created")
PYEOF

# 验证
ls -la nginx/
```

## 验证

```bash
cd ~/projects/Pyt

# 检查文件是否存在且是文件（不是目录）
ls -la nginx/nginx.conf

# 应该显示：-rw-r--r-- ... nginx.conf（文件）
# 不应该显示：drwxr-xr-x ... nginx.conf（目录）

# 检查文件内容
head -5 nginx/nginx.conf
```

## 重新启动服务

```bash
cd ~/projects/Pyt

# 重新启动服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

