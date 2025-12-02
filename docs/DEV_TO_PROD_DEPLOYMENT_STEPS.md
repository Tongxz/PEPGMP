# 从开发环境到生产环境部署详细步骤

## 📋 概述

本文档提供从**开发环境（macOS）**部署到**内网生产环境（Ubuntu服务器）**的完整详细步骤。

**环境信息**:
- ✅ 开发环境: macOS（当前环境）
- ✅ 生产环境: 内网Ubuntu服务器（Docker已安装）
- ✅ 内网Registry: `192.168.30.83:5433`
- ✅ 部署方式: Docker容器化部署

**预计时间**: 首次部署 20-30分钟

---

## 🎯 部署前准备

### ✅ 检查清单

在开始部署前，请确认：

- [ ] 开发环境代码已提交到Git
- [ ] 生产服务器IP地址已知
- [ ] 可以SSH连接到生产服务器
- [ ] 可以访问内网Registry (192.168.30.83:5433)
- [ ] Docker Desktop在开发机器上运行
- [ ] 生产服务器已安装Docker和Docker Compose

---

## 📝 步骤1: 确认当前环境

### 1.1 确认项目目录

```bash
# 确认当前在项目根目录
pwd
# 应该显示: /Users/zhou/Code/Pyt

# 确认目录结构
ls -la
# 应该看到: scripts/, docs/, src/, docker-compose.prod.full.yml 等
```

### 1.2 确认Git状态

```bash
# 检查是否有未提交的更改
git status

# 如果有未提交的更改，建议先提交
git add .
git commit -m "准备生产部署"
```

### 1.3 确认Docker运行状态

```bash
# 检查Docker Desktop是否运行
docker info

# 检查Docker Compose版本
docker compose version
```

**预期输出**:
```
Docker Compose version v2.x.x
```

---

## 📝 步骤2: 生成生产环境配置文件

### 2.1 生成配置文件

```bash
# 在项目根目录执行
bash scripts/generate_production_config.sh
```

**交互过程**:
```
=========================================================================
生成生产环境配置文件
=========================================================================

警告: .env.production 已存在
是否覆盖现有文件？(yes/no): yes
✓ 已备份现有配置文件

请输入配置信息（直接回车使用默认值）:

API端口 [8000]:
管理员用户名 [admin]:
允许的CORS来源 [*]:

正在生成强随机密码...
✓ 密码生成完成

=========================================================================
配置文件生成成功！
=========================================================================

文件位置: .env.production
文件权限: 600 (仅所有者可读写)

重要信息（请妥善保存）:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

管理员账号:
  用户名: admin
  密码: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

数据库密码: yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
Redis密码: zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  请将以上信息保存到密码管理器！
```

### 2.2 保存凭证信息

```bash
# 查看凭证文件
cat .env.production.credentials
```

**重要操作**:
1. ✅ **立即复制**凭证信息到密码管理器
2. ✅ **确认保存后**删除凭证文件（安全考虑）

```bash
# 确认凭证已保存后，删除凭证文件
rm .env.production.credentials
```

### 2.3 验证配置文件

```bash
# 验证配置文件格式
python scripts/validate_config.py
```

**预期输出**:
```
✅ 配置文件验证通过
```

---

## 📝 步骤3: 配置Docker Registry（开发机器）

### 3.1 检查Registry连接

```bash
# 测试内网Registry是否可访问
ping 192.168.30.83

# 检查Registry服务
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

### 3.2 配置Docker Desktop信任Registry

1. **打开Docker Desktop**
   - 点击菜单栏 Docker 图标
   - 选择 **Preferences**（设置）

2. **进入Docker Engine配置**
   - 左侧菜单选择 **Docker Engine**
   - 在JSON配置编辑器中查看/编辑

3. **添加Registry配置**

   如果配置文件中没有 `insecure-registries`，添加：
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

### 3.3 验证Registry配置

```bash
# 再次测试Registry连接
curl http://192.168.30.83:5433/v2/_catalog
```

---

## 📝 步骤4: 检查部署就绪状态

### 4.1 运行部署就绪检查

```bash
# 全面检查部署前置条件
bash scripts/check_deployment_readiness.sh
```

**检查过程**（约1-2分钟）:

```
=========================================================================
检查部署就绪状态
=========================================================================

[1/5] 检查必需文件...
✓ .env.production 存在
  └─ 文件权限正确 (600)
  └─ 配置已设置
✓ Dockerfile.prod 存在

[2/5] 检查必需目录...
✓ config/ 目录存在
  └─ 配置文件数量: 3
✓ models/ 目录存在
  └─ 模型文件数量: 5
  └─ 模型目录大小: 2.1G

[3/5] 检查Docker环境...
✓ Docker已安装: Docker version 24.x.x
  └─ Docker服务运行中
  └─ pepgmp-backend:latest 镜像已存在（可选）

[4/5] 检查Registry配置...
✓ Registry可访问 (192.168.30.83:5433)
  └─ pepgmp-backend 镜像已存在于Registry（可选）

[5/5] 检查部署脚本...
✓ scripts/generate_production_config.sh (可执行)
✓ scripts/quick_deploy.sh (可执行)
✓ scripts/push_to_registry.sh (可执行)
✓ scripts/deploy_from_registry.sh (可执行)

=========================================================================
检查结果总结
=========================================================================

✅ 所有检查通过！可以开始部署！

下一步:
  bash scripts/quick_deploy.sh <服务器IP> ubuntu
```

**如果检查失败**:
- ❌ **错误**: 必须解决所有错误才能继续
- ⚠️ **警告**: 可以继续，但建议先解决

---

## 📝 步骤5: 准备生产服务器（首次部署）

### 5.1 SSH连接到生产服务器

```bash
# 替换 <SERVER_IP> 为实际生产服务器IP
ssh ubuntu@<SERVER_IP>

# 示例
ssh ubuntu@192.168.1.100
```

**首次连接提示**:
```
The authenticity of host '192.168.1.100 (192.168.1.100)' can't be established.
ECDSA key fingerprint is SHA256:xxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
```

### 5.2 验证Docker环境

```bash
# 检查Docker版本
docker --version
```

**预期输出**:
```
Docker version 24.0.x, build xxxxxxx
```

```bash
# 检查Docker Compose版本
docker compose version
```

**预期输出**:
```
Docker Compose version v2.24.x
```

### 5.3 创建部署目录

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

### 5.4 配置Docker信任Registry

```bash
# 创建Docker配置目录（如不存在）
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

**如果文件已存在，编辑配置**:
```bash
# 备份现有配置
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup

# 编辑配置
sudo nano /etc/docker/daemon.json
```

在JSON中添加或确认 `insecure-registries`:
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

### 5.5 验证Registry连接

```bash
# 测试从Registry连接
curl http://192.168.30.83:5433/v2/_catalog
```

**预期输出**:
```json
{"repositories":[]}
```

### 5.6 退出SSH连接

```bash
# 返回开发机器
exit
```

---

## 📝 步骤6: 构建并推送镜像

### 6.1 构建生产镜像

```bash
# 在开发机器项目根目录
cd /Users/zhou/Code/Pyt

# 构建生产镜像（首次构建需要5-10分钟）
docker build -f Dockerfile.prod -t pepgmp-backend:latest .
```

**构建过程**（首次构建）:
```
[+] Building 120.5s (25/25) FINISHED
 => [internal] load build definition from Dockerfile.prod
 => => transferring dockerfile: 2.15kB
 => [internal] load .dockerignore
 => => transferring context: 2.15kB
 => [internal] load metadata for docker.io/library/python:3.10-slim
 => [1/20] FROM docker.io/library/python:3.10-slim
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

### 6.2 推送镜像到Registry

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

### 6.3 验证镜像在Registry中

```bash
# 检查Registry中的镜像标签
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list
```

**预期输出**:
```json
{"name":"pepgmp-backend","tags":["latest","v1.0.0"]}
```

---

## 📝 步骤7: 一键部署到生产服务器

### 7.1 执行一键部署

```bash
# 在开发机器上执行（替换为实际生产服务器IP）
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**部署过程**（首次部署需要15-20分钟）:

#### 步骤1: 构建镜像（如未构建）
```
[步骤1/4] 构建Docker镜像...
（如果镜像已构建，此步骤会跳过）
```

#### 步骤2: 推送镜像
```
[步骤2/4] 推送镜像到Registry...
✓ 镜像推送成功
```

#### 步骤3: 部署到生产服务器
```
[步骤3/4] 部署到生产服务器...

=========================================================================
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

**⚠️ 重要**: 首次部署时，数据库初始化需要60-70秒，请耐心等待。

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

### 7.2 部署完成

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

## 📝 步骤8: 验证部署

### 8.1 检查容器状态

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
pepgmp-postgres-prod    postgres:16-alpine                         "docker-entrypoint.s…"   database            2 minutes ago   Up 2 minutes        5432/tcp
pepgmp-redis-prod       redis:7-alpine                             "docker-entrypoint.s…"   redis               2 minutes ago   Up 2 minutes        6379/tcp
```

**检查要点**:
- ✅ 所有容器状态为 `Up`
- ✅ API容器端口映射正确 `0.0.0.0:8000->8000/tcp`
- ✅ 没有容器重启（`STATUS` 中没有 `Restarting`）

### 8.2 检查健康状态

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

### 8.3 检查系统信息

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

### 8.4 查看日志

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

### 8.5 从开发机器访问（验证外部访问）

```bash
# 从开发机器访问（替换为实际IP）
curl http://<SERVER_IP>:8000/api/v1/monitoring/health

# 访问API文档
open http://<SERVER_IP>:8000/docs
```

---

## 🔍 常见问题排查

### 问题1: Registry连接失败

**症状**:
```
错误: 无法连接到Registry
curl: (7) Failed to connect to 192.168.30.83 port 5433: Connection refused
```

**解决方案**:
1. 检查网络连通性: `ping 192.168.30.83`
2. 检查防火墙规则
3. 确认Registry服务运行中
4. 检查Docker `insecure-registries` 配置

### 问题2: SSH连接失败

**症状**:
```
ssh: connect to host 192.168.1.100 port 22: Connection refused
```

**解决方案**:
1. 检查SSH服务状态（在生产服务器上）
2. 检查防火墙规则
3. 确认服务器IP地址正确

### 问题3: 数据库初始化失败

**症状**:
```
FATAL: password authentication failed for user "pepgmp_prod"
```

**解决方案**:
1. 确认 `.env` 文件中的数据库密码正确
2. 等待数据库完全初始化（首次部署需要60-70秒）
3. 检查数据库容器日志: `docker compose logs database`

### 问题4: 容器无法启动

**症状**:
```
Error response from daemon: driver failed programming external connectivity
```

**解决方案**:
1. 查看详细错误日志: `docker compose logs api`
2. 检查端口占用: `sudo netstat -tulpn | grep :8000`
3. 检查配置文件: `python scripts/validate_config.py`

---

## 📋 部署完成检查清单

- [ ] 配置文件已生成（`.env.production`）
- [ ] 凭证信息已保存到密码管理器
- [ ] Docker Registry配置完成（开发机器和生产服务器）
- [ ] 镜像已构建并推送到Registry
- [ ] 配置文件已传输到生产服务器
- [ ] 容器已启动并运行正常
- [ ] 健康检查通过
- [ ] API可以正常访问（本地和外部）
- [ ] 日志无错误信息

---

## 🚀 后续更新部署

当需要更新生产环境时，只需执行：

```bash
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

或使用一键部署：
```bash
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu
```

---

**最后更新**: 2025-11-25
