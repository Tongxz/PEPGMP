# 内网生产环境详细部署指南

## 📋 概述

本文档提供了**内网环境下 Ubuntu 服务器**的详细生产部署步骤，每一步都包含详细的命令、预期输出和验证方法。

**目标环境**:
- ✅ 内网环境（无公网访问）
- ✅ Ubuntu 服务器（Docker 已安装）
- ✅ 内网私有 Registry: `192.168.30.83:5433`
- ✅ 生产服务器 IP: `<SERVER_IP>`（需要替换为实际IP）

**预计时间**: 首次部署 20-30分钟，后续更新 5-10分钟

---

## 🎯 部署前准备清单

### ✅ 开发机器准备（macOS）

#### 1. 确认网络连通性

```bash
# 检查能否访问内网Registry
ping 192.168.30.83

# 检查Registry服务是否可用
curl http://192.168.30.83:5433/v2/_catalog
```

**预期输出**:
```json
{"repositories":[]}
```
或
```json
{"repositories":["pepgmp-backend"]}
```

#### 2. 确认SSH连接

```bash
# 测试SSH连接到生产服务器（替换为实际IP）
ssh ubuntu@<SERVER_IP> "echo 'SSH连接成功'"
```

**预期输出**:
```
SSH连接成功
```

如果失败，需要：
- 检查SSH密钥配置
- 确认服务器IP地址
- 确认SSH端口（默认22）

#### 3. 确认Docker Desktop运行

```bash
# 检查Docker状态
docker info

# 检查Docker Compose版本
docker compose version
```

**预期输出**:
```
Docker Compose version v2.x.x
```

---

## 📝 步骤1: 生成生产环境配置文件

### 1.1 生成配置文件

```bash
# 在项目根目录执行
cd /Users/zhou/Code/Pyt

# 生成生产配置（包含强随机密码）
bash scripts/generate_production_config.sh
```

**交互提示**:
```
请输入配置信息（直接回车使用默认值）:

API端口 [8000]:
管理员用户名 [admin]:
允许的CORS来源 [*]:

正在生成强随机密码...
✓ 密码生成完成
```

**生成的文件**:
- `.env.production` - 生产环境配置文件（敏感信息，已设置权限600）
- `.env.production.credentials` - 凭证信息文件（临时，查看后应删除）

**重要**:
- ⚠️ 立即查看并保存 `.env.production.credentials` 中的密码
- ⚠️ 建议将凭证信息保存到密码管理器
- ⚠️ 确认信息后删除 `.env.production.credentials` 文件

### 1.2 查看生成的凭证

```bash
# 查看凭证文件（首次部署必需）
cat .env.production.credentials
```

**预期输出示例**:
```
========================================================================
生产环境凭证
Production Credentials
========================================================================

生成时间: 2025-11-25 14:30:00

管理员账号:
  用户名: admin
  密码: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

数据库:
  用户名: pepgmp_prod
  数据库: pepgmp_production
  密码: yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

Redis:
  密码: zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz

安全密钥:
  SECRET_KEY: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  JWT_SECRET_KEY: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb

========================================================================
⚠️  重要: 请妥善保管此文件，并在确认信息后删除！
========================================================================
```

**操作**:
- ✅ 将凭证信息保存到安全位置（密码管理器）
- ✅ 确认保存后删除凭证文件: `rm .env.production.credentials`

### 1.3 验证配置文件

```bash
# 验证配置文件格式
python scripts/validate_config.py
```

**预期输出**:
```
✅ 配置文件验证通过
```

如果验证失败，检查 `.env.production` 文件格式是否正确。

---

## 📝 步骤2: 检查部署就绪状态

### 2.1 运行部署就绪检查

```bash
# 全面检查部署前置条件
bash scripts/check_deployment_readiness.sh
```

**检查项**:

1. **必需文件检查**
   ```
   ✓ .env.production 存在
     └─ 文件权限正确 (600)
     └─ 配置已设置
   ✓ Dockerfile.prod 存在
   ```

2. **必需目录检查**
   ```
   ✓ config/ 目录存在
     └─ 配置文件数量: 3
   ✓ models/ 目录存在（如需要）
     └─ 模型文件数量: 5
     └─ 模型目录大小: 2.1G
   ```

3. **Docker环境检查**
   ```
   ✓ Docker已安装: Docker version 24.x.x
     └─ Docker服务运行中
     └─ pepgmp-backend:latest 镜像已存在（可选）
   ```

4. **Registry配置检查**
   ```
   ✓ Registry可访问 (192.168.30.83:5433)
     └─ pepgmp-backend 镜像已存在于Registry（可选）
   ```

5. **部署脚本检查**
   ```
   ✓ scripts/generate_production_config.sh (可执行)
   ✓ scripts/quick_deploy.sh (可执行)
   ✓ scripts/push_to_registry.sh (可执行)
   ✓ scripts/deploy_from_registry.sh (可执行)
   ```

**如果检查失败**:
- ❌ 错误: 需要先解决错误
- ⚠️ 警告: 可以继续，但建议先解决

**预期最终输出**:
```
========================================================================
检查结果总结
========================================================================

✅ 所有检查通过！可以开始部署！

下一步:
  bash scripts/quick_deploy.sh <服务器IP> ubuntu
```

---

## 📝 步骤3: 配置开发机器Docker Registry

### 3.1 配置Docker Desktop信任内网Registry（macOS）

1. **打开Docker Desktop**
   - 点击菜单栏 Docker 图标
   - 选择 **Preferences**（或 **设置**）

2. **进入Docker Engine配置**
   - 左侧菜单选择 **Docker Engine**
   - 在JSON配置编辑器中添加配置

3. **添加Registry配置**

   找到或创建 `daemon.json` 配置，添加以下内容：
   ```json
   {
     "insecure-registries": ["192.168.30.83:5433"]
   }
   ```

   **完整配置示例**:
   ```json
   {
     "builder": {
       "gc": {
         "defaultKeepStorage": "20GB",
         "enabled": true
       }
     },
     "experimental": false,
     "insecure-registries": [
       "192.168.30.83:5433"
     ]
   }
   ```

4. **应用并重启**
   - 点击 **Apply & Restart**
   - 等待Docker重启完成（约30秒）

### 3.2 验证Registry配置

```bash
# 测试Registry连接
curl http://192.168.30.83:5433/v2/_catalog

# 查看Registry中的镜像（如已推送）
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list
```

**预期输出**:
```json
{"repositories":[]}
```
或（如已有镜像）
```json
{"name":"pepgmp-backend","tags":["latest","v1.0.0"]}
```

---

## 📝 步骤4: 准备生产服务器

### 4.1 SSH连接到生产服务器

```bash
# 替换 <SERVER_IP> 为实际服务器IP
ssh ubuntu@<SERVER_IP>
```

**示例**:
```bash
ssh ubuntu@192.168.1.100
```

**如果首次连接**，会提示确认主机密钥:
```
The authenticity of host '192.168.1.100 (192.168.1.100)' can't be established.
ECDSA key fingerprint is SHA256:xxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```
输入 `yes` 确认。

### 4.2 验证Docker安装

```bash
# 检查Docker版本
docker --version
```

**预期输出**:
```
Docker version 24.0.x, build xxxxxxx
```

### 4.3 检查Docker Compose版本

```bash
# 检查Docker Compose V2（Ubuntu 22.04默认）
docker compose version
```

**预期输出**:
```
Docker Compose version v2.24.x
```

**如果没有输出**，检查是否安装了docker-compose:
```bash
# 检查V1版本（兼容性）
docker-compose --version
```

如果都没有，需要安装Docker Compose（见下节）。

### 4.4 安装Docker Compose（如需要）

```bash
# 下载Docker Compose V2
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 设置执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

**注意**: 内网环境可能需要手动下载并传输文件。

### 4.5 创建部署目录

```bash
# 创建部署目录
sudo mkdir -p /opt/pyt

# 设置目录所有者
sudo chown ubuntu:ubuntu /opt/pyt

# 验证权限
ls -ld /opt/pyt
```

**预期输出**:
```
drwxr-xr-x 2 ubuntu ubuntu 4096 Nov 25 14:30 /opt/pyt
```

### 4.6 配置生产服务器Docker信任Registry

```bash
# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 检查现有配置
cat /etc/docker/daemon.json 2>/dev/null || echo "文件不存在，将创建新配置"
```

**如果文件不存在，创建配置**:
```bash
# 创建daemon.json
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": ["192.168.30.83:5433"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
```

**如果文件已存在，添加Registry配置**:
```bash
# 备份现有配置
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup

# 使用编辑器修改（推荐）
sudo nano /etc/docker/daemon.json
```

在JSON中添加 `insecure-registries`:
```json
{
  "existing-config": "...",
  "insecure-registries": ["192.168.30.83:5433"]
}
```

**重启Docker服务**:
```bash
# 重启Docker
sudo systemctl restart docker

# 验证Docker运行状态
sudo systemctl status docker
```

**预期输出**:
```
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since ...
```

### 4.7 验证Registry连接

```bash
# 测试从Registry拉取镜像（不需要镜像存在）
curl http://192.168.30.83:5433/v2/_catalog
```

**预期输出**:
```json
{"repositories":[]}
```
或包含已有镜像的列表。

**退出SSH连接**:
```bash
exit
```

---

## 📝 步骤5: 构建并推送镜像

### 5.1 构建生产镜像

```bash
# 在开发机器项目根目录
cd /Users/zhou/Code/Pyt

# 构建生产镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .
```

**构建过程**（首次构建需要5-10分钟）:
```
[+] Building 120.5s (25/25) FINISHED
 => [internal] load build definition from Dockerfile.prod
 => => transferring dockerfile: 2.15kB
 => [internal] load .dockerignore
 ...
 => => writing image sha256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 => => naming to docker.io/library/pepgmp-backend:latest
```

**验证镜像**:
```bash
# 查看镜像
docker images pepgmp-backend:latest
```

**预期输出**:
```
REPOSITORY          TAG       IMAGE ID       CREATED         SIZE
pepgmp-backend      latest    xxxxxxxxxxxx   2 minutes ago   2.5GB
```

### 5.2 推送镜像到Registry

```bash
# 推送到内网Registry
bash scripts/push_to_registry.sh latest v1.0.0
```

**推送过程**:
```
=========================================================================
推送镜像到私有Registry
=========================================================================

Registry地址: 192.168.30.83:5433
镜像名称: pepgmp-backend
标签: latest
版本: v1.0.0

[步骤1/3] 打标签...
✓ 标签已添加

[步骤2/3] 推送镜像...
The push refers to repository [192.168.30.83:5433/pepgmp-backend]
...
latest: digest: sha256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx size: xxxxx

[步骤3/3] 验证推送...
✓ 镜像推送成功
```

### 5.3 验证镜像在Registry中

```bash
# 检查Registry中的镜像标签
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list
```

**预期输出**:
```json
{"name":"pepgmp-backend","tags":["latest","v1.0.0"]}
```

---

## 📝 步骤6: 一键部署到生产服务器

### 6.1 执行一键部署

```bash
# 在开发机器上执行（替换为实际IP）
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**部署过程**（首次部署需要15-20分钟）:

#### 步骤1: 检查Registry连接
```
[步骤1/4] 构建Docker镜像...
（如果镜像已构建，此步骤会跳过）
```

#### 步骤2: 推送镜像到Registry
```
[步骤2/4] 推送镜像到Registry...
✓ 镜像推送成功
```

#### 步骤3: 部署到生产服务器
```
[步骤3/4] 部署到生产服务器...

从私有Registry部署到生产环境
=========================================================================

Registry地址: 192.168.30.83:5433
目标服务器: 192.168.1.100
SSH用户: ubuntu
镜像标签: latest
部署目录: /opt/pyt

警告: 即将部署到生产环境！
=========================================================================
确认要部署到 192.168.1.100 吗？(yes/no): yes

[步骤1/6] 检查Registry连接...
✓ Registry连接成功
✓ 镜像 pepgmp-backend:latest 存在于Registry

[步骤2/6] 检查SSH连接...
✓ SSH连接可用

[步骤3/6] 传输配置文件...
创建远程部署目录...
传输docker-compose配置...
传输环境变量配置...
传输配置目录...
传输模型目录（如果有）...
✓ 配置文件传输完成

[步骤4/6] 配置生产服务器Docker环境...
✓ Docker已安装: Docker version 24.0.x
✓ docker-compose已安装: Docker Compose version v2.24.x
✓ Registry配置已存在
✓ Docker环境配置完成

[步骤5/6] 拉取镜像并部署...
更新docker-compose.yml使用Registry镜像...
停止旧容器（如果存在）...
拉取最新镜像...
latest: Pulling from pepgmp-backend
...
Status: Downloaded newer image for 192.168.30.83:5433/pepgmp-backend:latest

启动容器...
[+] Running 4/4
 ✔ Network pyt_default      Created
 ✔ Container pepgmp-redis-prod    Started
 ✔ Container pepgmp-postgres-prod Started
 ✔ Container pepgmp-api-prod      Started

等待服务启动...
等待数据库初始化（首次部署需要60-70秒）...
```

**重要**: 首次部署时，数据库初始化需要60-70秒，请耐心等待。

#### 步骤4: 健康检查
```
[步骤4/4] 健康检查...

等待服务完全启动（30秒）...
执行健康检查...
{
  "status": "healthy",
  "timestamp": "2025-11-25T14:45:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}

✓ 健康检查通过
```

### 6.2 部署完成

**最终输出**:
```
=========================================================================
部署完成！
=========================================================================

部署信息:
  - Registry: 192.168.30.83:5433
  - 镜像: pepgmp-backend:latest
  - 服务器: 192.168.1.100
  - 部署目录: /opt/pyt
  - API地址: http://192.168.1.100:8000

常用命令:

  1. 查看日志:
     ssh ubuntu@192.168.1.100 'cd /opt/pyt && docker compose logs -f api'

  2. 查看所有容器状态:
     ssh ubuntu@192.168.1.100 'cd /opt/pyt && docker compose ps'

  3. 重启服务:
     ssh ubuntu@192.168.1.100 'cd /opt/pyt && docker compose restart api'

  4. 更新到新版本:
     bash scripts/push_to_registry.sh
     ssh ubuntu@192.168.1.100 'cd /opt/pyt && docker compose pull && docker compose up -d'

  5. 访问API文档:
     http://192.168.1.100:8000/docs
```

---

## 📝 步骤7: 验证部署

### 7.1 检查容器状态

```bash
# SSH到生产服务器
ssh ubuntu@<SERVER_IP>

# 进入部署目录
cd /opt/pyt

# 查看容器状态
docker compose ps
```

**预期输出**:
```
NAME                      IMAGE                                      COMMAND                  SERVICE             CREATED         STATUS              PORTS
pepgmp-api-prod         192.168.30.83:5433/pepgmp-backend:latest   "gunicorn src.api.ap…"   api                 2 minutes ago   Up 2 minutes        0.0.0.0:8000->8000/tcp
pepgmp-postgres-prod    postgres:15-alpine                         "docker-entrypoint.s…"   database            2 minutes ago   Up 2 minutes        5432/tcp
pepgmp-redis-prod       redis:7-alpine                             "docker-entrypoint.s…"   redis               2 minutes ago   Up 2 minutes        6379/tcp
```

**检查要点**:
- ✅ 所有容器状态为 `Up`
- ✅ API容器端口映射正确 `0.0.0.0:8000->8000/tcp`
- ✅ 没有容器重启（`STATUS` 中没有 `Restarting`）

### 7.2 检查健康状态

```bash
# 在生产服务器上执行
curl http://localhost:8000/api/v1/monitoring/health
```

**预期输出**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T14:45:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

### 7.3 检查系统信息

```bash
# 检查系统信息
curl http://localhost:8000/api/v1/system/info
```

**预期输出**:
```json
{
  "environment": "production",
  "version": "1.0.0",
  "python_version": "3.10.x",
  "docker": true
}
```

### 7.4 查看日志

```bash
# 查看API服务日志
docker compose logs -f api
```

**预期输出示例**:
```
pepgmp-api-prod  | INFO:     Started server process [1]
pepgmp-api-prod  | INFO:     Waiting for application startup.
pepgmp-api-prod  | INFO:     Application startup complete.
pepgmp-api-prod  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**按 `Ctrl+C` 退出日志查看**。

### 7.5 测试API端点

```bash
# 测试摄像头列表（如已配置）
curl http://localhost:8000/api/v1/cameras

# 测试检测记录
curl http://localhost:8000/api/v1/detection/records?limit=10
```

### 7.6 从外部访问（如需要）

```bash
# 从开发机器访问（替换为实际IP）
curl http://<SERVER_IP>:8000/api/v1/monitoring/health

# 访问API文档
open http://<SERVER_IP>:8000/docs
```

---

## 🔍 故障排查

### 问题1: Registry连接失败

**症状**:
```
错误: 无法连接到Registry
curl: (7) Failed to connect to 192.168.30.83 port 5433: Connection refused
```

**排查步骤**:

1. **检查网络连通性**
   ```bash
   ping 192.168.30.83
   ```

2. **检查端口是否开放**
   ```bash
   telnet 192.168.30.83 5433
   # 或
   nc -zv 192.168.30.83 5433
   ```

3. **检查防火墙规则**
   ```bash
   # 在Registry服务器上
   sudo ufw status | grep 5433
   ```

**解决方案**:
- ✅ 确保Registry服务运行中
- ✅ 检查防火墙规则，开放5433端口
- ✅ 检查网络路由和VPN连接

### 问题2: SSH连接失败

**症状**:
```
ssh: connect to host 192.168.1.100 port 22: Connection refused
```

**排查步骤**:

1. **检查SSH服务状态**（在生产服务器上）
   ```bash
   sudo systemctl status ssh
   ```

2. **检查端口占用**
   ```bash
   sudo netstat -tulpn | grep :22
   ```

3. **检查防火墙**
   ```bash
   sudo ufw status | grep 22
   ```

**解决方案**:
- ✅ 启动SSH服务: `sudo systemctl start ssh`
- ✅ 开放SSH端口: `sudo ufw allow 22/tcp`
- ✅ 检查SSH配置: `/etc/ssh/sshd_config`

### 问题3: 数据库初始化失败

**症状**:
```
FATAL: password authentication failed for user "pepgmp_prod"
FATAL: role "pepgmp_prod" does not exist
```

**排查步骤**:

1. **检查数据库容器日志**
   ```bash
   docker compose logs database
   ```

2. **检查环境变量配置**
   ```bash
   cat /opt/pyt/.env | grep DATABASE
   ```

3. **手动检查数据库初始化**
   ```bash
   bash scripts/check_database_init.sh pepgmp-postgres-prod pepgmp_prod pepgmp_production
   ```

**解决方案**:
- ✅ 确认 `.env` 文件中的数据库密码正确
- ✅ 等待数据库完全初始化（首次部署需要60-70秒）
- ✅ 检查 `init_db.sql` 是否正确执行

### 问题4: 容器无法启动

**症状**:
```
Error response from daemon: driver failed programming external connectivity
Container exited with code 1
```

**排查步骤**:

1. **查看详细错误日志**
   ```bash
   docker compose logs api
   ```

2. **检查端口占用**
   ```bash
   sudo netstat -tulpn | grep :8000
   ```

3. **检查配置文件**
   ```bash
   python scripts/validate_config.py
   ```

**解决方案**:
- ✅ 检查端口是否被占用，释放端口或修改配置
- ✅ 检查配置文件格式和内容
- ✅ 查看容器日志中的具体错误信息

---

## 📋 部署后维护

### 更新部署

```bash
# 在开发机器上
# 1. 构建新镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 2. 推送镜像
bash scripts/push_to_registry.sh latest v1.0.1

# 3. 在生产服务器上更新
ssh ubuntu@<SERVER_IP> << 'EOF'
cd /opt/pyt
docker compose pull
docker compose up -d
docker compose ps
EOF
```

### 备份数据库

```bash
# 在生产服务器上
cd /opt/pyt

# 创建备份目录
mkdir -p backups

# 执行备份
docker compose exec -T database pg_dump -U pepgmp_prod pepgmp_production | gzip > backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 验证备份
ls -lh backups/
```

### 查看日志

```bash
# 查看API日志
docker compose logs -f api

# 查看所有服务日志
docker compose logs -f

# 查看最近100行日志
docker compose logs --tail=100 api
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart api

# 停止所有服务
docker compose down

# 启动所有服务
docker compose up -d
```

---

## ✅ 部署完成检查清单

- [ ] 配置文件已生成（`.env.production`）
- [ ] 凭证信息已保存
- [ ] Docker Registry配置完成
- [ ] 生产服务器Docker环境配置完成
- [ ] 镜像已构建并推送到Registry
- [ ] 配置文件已传输到生产服务器
- [ ] 容器已启动并运行正常
- [ ] 健康检查通过
- [ ] API可以正常访问
- [ ] 日志无错误信息

---

**最后更新**: 2025-11-25
