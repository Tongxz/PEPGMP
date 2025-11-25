# 内网环境部署说明

## 📋 概述

本文档专门针对**内网环境下的 Ubuntu 22.04 Docker 容器化部署**的特殊注意事项和配置说明。

**更新日期**: 2025-11-24  
**目标环境**: Ubuntu 22.04 LTS 内网环境  
**部署方式**: Docker 容器化部署

---

## ⚠️ 内网环境特殊考虑

### 1. 网络环境

#### 1.1 内网特点

- ✅ **无公网访问**: 服务器位于内网，无法访问互联网
- ✅ **私有Registry**: 使用内网私有 Docker Registry (192.168.30.83:5433)
- ✅ **内网服务**: 所有服务（API、数据库、Redis）都在内网环境
- ✅ **网络隔离**: 与公网完全隔离，安全性更高

#### 1.2 网络配置要求

**必需的网络连通性**:
- ✅ 开发机器 → 内网Registry (192.168.30.83:5433)
- ✅ 生产服务器 → 内网Registry (192.168.30.83:5433)
- ✅ 生产服务器内网服务间通信（Docker网络）
- ✅ SSH访问生产服务器（内网）

**网络配置检查**:
```bash
# 1. 检查内网连通性
ping 192.168.30.83

# 2. 检查内网Registry
curl http://192.168.30.83:5433/v2/_catalog

# 3. 检查内网DNS（如使用域名）
nslookup registry.internal  # 如使用域名

# 4. 检查内网路由
ip route
```

### 2. Ubuntu 22.04 特定配置

#### 2.1 Docker Compose V2

**Ubuntu 22.04 默认使用 Docker Compose V2**，命令格式不同：

```bash
# V2 命令（推荐，Ubuntu 22.04 默认）
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down

# V1 命令（如已安装）
docker-compose up -d
docker-compose ps
docker-compose logs -f
docker-compose down
```

**检查版本**:
```bash
# 检查Docker Compose V2
docker compose version

# 检查Docker Compose V1（如安装）
docker-compose --version
```

#### 2.2 Docker Engine 安装（Ubuntu 22.04）

**Ubuntu 22.04 安装 Docker Engine**:

```bash
# 1. 更新软件包索引
sudo apt-get update

# 2. 安装依赖
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 3. 添加Docker官方GPG密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. 添加Docker仓库（Ubuntu 22.04 = jammy）
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 安装Docker Engine
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# 6. 验证安装
sudo docker --version
sudo docker compose version

# 7. 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 8. 将当前用户添加到docker组（避免每次sudo）
sudo usermod -aG docker $USER
newgrp docker  # 或重新登录
```

#### 2.3 内网Registry配置（Ubuntu 22.04）

**配置Docker信任内网Registry**:

```bash
# 1. 创建Docker配置目录
sudo mkdir -p /etc/docker

# 2. 配置内网Registry（Ubuntu 22.04）
sudo tee /etc/docker/daemon.json <<EOF
{
  "insecure-registries": ["192.168.30.83:5433"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# 3. 重启Docker服务
sudo systemctl restart docker

# 4. 验证配置
cat /etc/docker/daemon.json
docker info | grep -A 5 "Insecure Registries"

# 5. 测试内网Registry连接
curl http://192.168.30.83:5433/v2/_catalog
docker pull 192.168.30.83:5433/pyt-backend:latest
```

#### 2.4 防火墙配置（Ubuntu 22.04）

**Ubuntu 22.04 使用 ufw 防火墙**:

```bash
# 1. 检查防火墙状态
sudo ufw status

# 2. 允许SSH（确保不会断开连接）
sudo ufw allow 22/tcp

# 3. 允许API端口
sudo ufw allow 8000/tcp

# 4. 允许Nginx端口（如使用）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 5. 允许内网Registry访问（如在同一内网）
sudo ufw allow from 192.168.0.0/16 to any port 5433

# 6. 启用防火墙
sudo ufw enable

# 7. 验证防火墙规则
sudo ufw status numbered
```

**注意**: Docker容器间通信使用Docker网络，无需在防火墙中配置。

#### 2.5 内网DNS配置（可选）

**如内网有DNS服务器**，配置Ubuntu 22.04使用内网DNS:

```bash
# Ubuntu 22.04 使用 netplan
sudo nano /etc/netplan/00-installer-config.yaml

# 添加DNS配置示例:
# network:
#   version: 2
#   ethernets:
#     eth0:  # 或 ens33, enp0s3 等
#       nameservers:
#         addresses:
#           - 192.168.1.1  # 内网DNS服务器
#           - 192.168.1.2  # 备用DNS
#       dhcp4: true

# 应用配置
sudo netplan apply

# 验证DNS
systemd-resolve --status
# 或
resolvectl status
```

**或使用 /etc/hosts**（简单方法）:

```bash
# 编辑hosts文件
sudo nano /etc/hosts

# 添加内网服务映射
# 192.168.30.83 registry.internal
# 192.168.1.100 api.internal
# 192.168.1.101 database.internal
```

---

## 🐳 Docker 容器化部署特殊配置

### 1. 容器网络配置

#### 1.1 Docker网络模式

**内网环境推荐使用bridge网络**（默认）:

```yaml
# docker-compose.prod.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 内部网络，不暴露到外部
```

**优势**:
- ✅ 容器间可直接通信
- ✅ 无需配置防火墙规则
- ✅ 安全性更高

#### 1.2 容器间通信验证

```bash
# 1. 检查Docker网络
docker network ls

# 2. 检查容器网络连接
docker compose -f docker-compose.prod.yml exec api ping -c 3 database
docker compose -f docker-compose.prod.yml exec api ping -c 3 redis

# 3. 检查网络配置
docker network inspect pyt_backend
```

### 2. 内网Registry使用

#### 2.1 从内网Registry拉取镜像

```bash
# 1. 登录内网Registry（如需要认证）
docker login 192.168.30.83:5433

# 2. 拉取镜像
docker pull 192.168.30.83:5433/pyt-backend:latest

# 3. 打标签（便于使用）
docker tag 192.168.30.83:5433/pyt-backend:latest pyt-backend:latest

# 4. 验证镜像
docker images | grep pyt-backend
```

#### 2.2 推送镜像到内网Registry

```bash
# 1. 构建镜像
docker build -f Dockerfile.prod -t pyt-backend:latest .

# 2. 打标签（内网Registry格式）
docker tag pyt-backend:latest 192.168.30.83:5433/pyt-backend:latest

# 3. 推送镜像
docker push 192.168.30.83:5433/pyt-backend:latest

# 4. 验证推送
curl http://192.168.30.83:5433/v2/pyt-backend/tags/list
```

### 3. 容器资源限制

#### 3.1 内网环境资源优化

**内网环境可能资源有限**，建议合理配置资源限制:

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '2.0'
          memory: 2G
```

**检查资源使用**:
```bash
# 检查容器资源使用
docker stats --no-stream

# 检查系统资源
df -h  # 磁盘空间
free -h  # 内存
top  # CPU和内存
```

---

## 🔧 内网环境特殊问题排查

### 问题1: 内网Registry连接失败

**症状**: `Error: Cannot connect to registry` 或 `dial tcp: lookup 192.168.30.83: no such host`

**排查步骤**:
```bash
# 1. 检查内网连通性
ping 192.168.30.83
traceroute 192.168.30.83

# 2. 检查端口是否开放
telnet 192.168.30.83 5433
# 或
nc -zv 192.168.30.83 5433

# 3. 检查防火墙规则
sudo ufw status | grep 5433

# 4. 检查Docker配置
cat /etc/docker/daemon.json

# 5. 检查DNS解析（如使用域名）
nslookup 192.168.30.83
```

**解决方案**:
- ✅ 确保内网网络连通
- ✅ 配置防火墙允许Registry端口
- ✅ 配置Docker `insecure-registries`
- ✅ 如使用域名，配置DNS或/etc/hosts

### 问题2: 容器无法访问内网服务

**症状**: 容器内无法访问内网其他服务

**排查步骤**:
```bash
# 1. 检查容器网络
docker compose -f docker-compose.prod.yml exec api ip addr

# 2. 检查容器DNS
docker compose -f docker-compose.prod.yml exec api cat /etc/resolv.conf

# 3. 测试容器间通信
docker compose -f docker-compose.prod.yml exec api ping -c 3 database

# 4. 检查Docker网络配置
docker network inspect pyt_backend
```

**解决方案**:
- ✅ 确保使用Docker Compose定义的网络
- ✅ 使用服务名称而非IP地址
- ✅ 检查网络模式配置

### 问题3: Docker Compose V2命令不存在

**症状**: `docker compose: command not found`

**解决方案**:
```bash
# Ubuntu 22.04 应该默认安装Docker Compose V2
# 如未安装，重新安装docker-compose-plugin

sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# 验证安装
docker compose version

# 或使用V1（如需要）
sudo apt-get install -y docker-compose
docker-compose --version
```

---

## 📋 内网部署检查清单

### 内网环境准备 ✅

```
□ Ubuntu 22.04 已安装
□ 内网网络连通性正常
□ 内网Registry可访问 (192.168.30.83:5433)
□ Docker Engine已安装
□ Docker Compose V2已安装（或V1）
□ 内网DNS配置正确（如使用域名）
□ 防火墙规则已配置
□ SSH可访问
```

### 内网Registry配置 ✅

```
□ Docker已配置trust内网Registry
□ 内网Registry连接测试通过
□ 镜像推送/拉取测试成功
□ Registry认证配置正确（如需要）
```

### 容器部署配置 ✅

```
□ Docker网络配置正确
□ 容器间通信正常
□ 资源限制配置合理
□ 日志配置正确
□ 数据卷挂载正确
```

---

## 📚 相关文档

- [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md)
- [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md)
- [生产环境部署指南](./production_deployment_guide.md)

---

**状态**: ✅ **内网环境部署说明已完成**  
**目标环境**: Ubuntu 22.04 LTS 内网环境  
**部署方式**: Docker 容器化部署

