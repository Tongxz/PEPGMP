# 修复 Nginx 权限问题

## 问题

`nginx/nginx.conf` 文件可能由 `sudo` 创建，导致普通用户无法覆盖。

## 快速修复

### 方法 1: 使用修复脚本（推荐）

```bash
cd ~/projects/Pyt

# 运行修复脚本（会自动使用 sudo）
bash /mnt/f/code/PythonCode/Pyt/scripts/fix_nginx_permissions.sh

# 然后重新运行准备脚本
bash /mnt/f/code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes
```

### 方法 2: 手动修复（最简单）

```bash
cd ~/projects/Pyt

# 修复所有权和权限
sudo chown -R $USER:$USER nginx/
chmod 755 nginx
chmod 644 nginx/nginx.conf 2>/dev/null || echo "nginx.conf will be created"

# 重新运行准备脚本
bash /mnt/f/code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes
```

### 方法 3: 完全重置 nginx 目录

```bash
cd ~/projects/Pyt

# 删除整个 nginx 目录（需要 sudo）
sudo rm -rf nginx

# 重新运行准备脚本（会自动创建）
bash /mnt/f/code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes
```

## 验证修复

```bash
cd ~/projects/Pyt

# 检查权限
ls -la nginx/

# 应该看到：
# drwxr-xr-x ... pep pep ... nginx/
# -rw-r--r-- ... pep pep ... nginx.conf (如果存在)

# 检查所有权
stat nginx/nginx.conf | grep Uid

# 应该显示当前用户
```

## 如果仍有问题

如果修复后仍有权限问题，可以手动创建文件：

```bash
cd ~/projects/Pyt

# 确保目录存在
mkdir -p nginx/ssl

# 使用 Python 创建文件（避免权限问题）
python3 << 'PYEOF'
import os

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

os.chmod('nginx/nginx.conf', 0o644)
print("✓ nginx.conf created")
PYEOF

# 验证
ls -la nginx/nginx.conf
```

