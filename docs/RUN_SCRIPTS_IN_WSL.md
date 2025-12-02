# 在 WSL 中运行脚本

## 脚本位置

所有脚本都在项目根目录的 `scripts/` 目录中：
- **Windows 路径**: `F:\Code\PythonCode\Pyt\scripts\`
- **WSL 路径**: `/mnt/f/code/PythonCode/Pyt/scripts/`

## 运行方式

### 方式 1: 直接运行（推荐）

在 WSL 中直接运行，使用 WSL 路径：

```bash
# 在 WSL Ubuntu 中
bash /mnt/f/code/PythonCode/Pyt/scripts/fix_nginx_structure.sh
```

### 方式 2: 先进入项目目录

```bash
# 在 WSL Ubuntu 中
cd /mnt/f/code/PythonCode/Pyt
bash scripts/fix_nginx_structure.sh
```

### 方式 3: 复制到 WSL（不推荐）

如果脚本需要频繁修改或执行，可以复制到 WSL：

```bash
# 复制脚本到 WSL 的部署目录
cp /mnt/f/code/PythonCode/Pyt/scripts/fix_nginx_structure.sh ~/projects/Pyt/scripts/

# 然后运行
cd ~/projects/Pyt
bash scripts/fix_nginx_structure.sh
```

## 推荐方式

**推荐使用方式 1 或方式 2**，因为：
- ✅ 不需要复制文件
- ✅ 始终使用最新版本的脚本
- ✅ 脚本修改后立即生效

## 当前问题的快速修复

对于 nginx 结构问题，直接在 WSL 中运行：

```bash
# 方法1: 直接运行（推荐）
bash /mnt/f/code/PythonCode/Pyt/scripts/fix_nginx_structure.sh ~/projects/Pyt

# 方法2: 进入项目目录后运行
cd /mnt/f/code/PythonCode/Pyt
bash scripts/fix_nginx_structure.sh ~/projects/Pyt

# 方法3: 手动修复（最简单）
cd ~/projects/Pyt
rm -rf nginx/nginx.conf
mkdir -p nginx/ssl
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
```

## 注意事项

1. **脚本权限**: 如果脚本没有执行权限，使用 `bash` 命令运行（不需要 `chmod +x`）
2. **路径**: 脚本中的路径都是相对于脚本所在目录或传入的参数
3. **行尾符**: 脚本已经修复为 LF（Unix 格式），可以在 WSL 中直接运行

