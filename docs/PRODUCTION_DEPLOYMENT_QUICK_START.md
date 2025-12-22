# 生产部署快速指南

## 🚀 快速部署（3步完成）

### 步骤1: 生成生产配置

```bash
# 自动生成带强随机密码的配置文件
bash scripts/generate_production_config.sh
```

**重要**：
- 脚本会生成 `.env.production` 文件
- 会创建 `.env.production.credentials` 凭证文件
- **请妥善保存凭证信息！**

### 步骤2: 检查部署就绪

```bash
# 检查所有部署前置条件
bash scripts/check_deployment_readiness.sh
```

**检查项**：
- ✅ 配置文件是否存在
- ✅ Docker环境是否正常
- ✅ Registry是否可访问
- ✅ 部署脚本是否可执行

### 步骤3: 生产部署（仅保留两条主线）

```bash
# 方式1：混合部署（网络隔离：导出/传输镜像 tar，现状推荐）
bash scripts/deploy_mixed_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP

# 方式2：Registry 部署（同一网络：生产机可访问 Registry）
bash scripts/deploy_via_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP
```

---

## 📋 详细部署步骤

### 前置要求

#### 开发环境 (macOS)
- ✅ Docker Desktop已安装并运行
- ✅ 可访问私有 Registry (11.25.125.115:5433)
- ✅ 可SSH连接到生产服务器
- ✅ SSH密钥已配置（推荐）

#### 生产服务器 (Ubuntu)
- ✅ Ubuntu 20.04 LTS 或更高版本
- ✅ 至少 4GB RAM
- ✅ 至少 20GB 磁盘空间
- ✅ Docker 和 Docker Compose 已安装
- ✅ 开放8000端口（API）

---

## 🔧 部署前准备

### 1. 配置Docker信任私有Registry

**macOS (Docker Desktop)**:

1. 打开 Docker Desktop
2. 进入 **Preferences** → **Docker Engine**
3. 添加配置：
```json
{
  "insecure-registries": ["11.25.125.115:5433"]
}
```
4. 点击 **Apply & Restart**

### 2. 准备生产服务器

```bash
# SSH到生产服务器
ssh ubuntu@<SERVER_IP>

# 部署目录（主线脚本会自动创建）
mkdir -p /home/ubuntu/projects/PEPGMP
cd /home/ubuntu/projects/PEPGMP
```

---

## 🚀 部署执行

### 方式1: 混合部署（推荐）✨

```bash
# 在开发机器上执行
bash scripts/deploy_mixed_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP
```

### 方式2: Registry 部署（同一网络）

```bash
# 在开发机器上执行
bash scripts/deploy_via_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP
```

### 方式2: 分步部署

#### 步骤1: 构建镜像

```bash
# 构建生产镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .
```

#### 步骤2: 准备生产服务器

```bash
# 传输最小部署包（推荐使用 prepare_minimal_deploy.sh 生成）
scp -r ./config ubuntu@<SERVER_IP>:/home/ubuntu/projects/PEPGMP/
scp docker-compose.prod.yml ubuntu@<SERVER_IP>:/home/ubuntu/projects/PEPGMP/
scp .env.production ubuntu@<SERVER_IP>:/home/ubuntu/projects/PEPGMP/.env.production
```

#### 步骤4: 部署服务

```bash
# 在生产服务器上
cd /home/ubuntu/projects/PEPGMP

# 解压配置
tar xzf deploy_config.tar.gz
chmod 600 .env.production

# 启动服务
docker compose -f docker-compose.prod.yml up -d

# ⚠️ 重要：等待数据库初始化（首次部署需要60-70秒）
echo "等待数据库初始化..."
sleep 60

# 验证数据库初始化
bash scripts/check_database_init.sh pepgmp-postgres-prod pepgmp_prod pepgmp_production
```

---

## ✅ 部署后验证

### 1. 检查容器状态

```bash
# 在生产服务器上
docker compose -f docker-compose.prod.yml ps
```

**预期输出**：
- `pepgmp-api-prod` - 运行中
- `pepgmp-postgres-prod` - 运行中
- `pepgmp-redis-prod` - 运行中

### 2. 健康检查

```bash
# 检查API健康状态
curl http://localhost:8000/api/v1/monitoring/health

# 检查系统信息
curl http://localhost:8000/api/v1/system/info
```

**预期响应**：
```json
{
  "status": "healthy",
  "timestamp": "2025-11-25T12:00:00Z",
  "version": "1.0.0"
}
```

### 3. 查看日志

```bash
# 查看API日志
docker compose -f docker-compose.prod.yml logs -f api

# 查看所有服务日志
docker compose -f docker-compose.prod.yml logs -f
```

### 4. 功能验证

```bash
# 测试摄像头列表
curl http://localhost:8000/api/v1/cameras

# 测试检测记录
curl http://localhost:8000/api/v1/detection/records?limit=10
```

---

## 🔄 更新部署

### 快速更新

```bash
# 混合部署更新（现状推荐）
bash scripts/deploy_mixed_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP

# 同网 Registry 更新
bash scripts/deploy_via_registry.sh <SERVER_IP> ubuntu /home/ubuntu/projects/PEPGMP
```

### 仅更新镜像

```bash
# 1. 构建新镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 2. 在生产服务器上重启（假设镜像已在目标机可用）
ssh ubuntu@<SERVER_IP> << 'EOF'
cd /home/ubuntu/projects/PEPGMP
docker compose -f docker-compose.prod.yml up -d --no-deps api
EOF
```

---

## 🛠️ 故障排查

### 问题1: 无法连接到Registry

**症状**：
```
Error: Get "http://11.25.125.115:5433/v2/": dial tcp: connect: connection refused
```

**解决方案**：
1. 检查Registry服务是否运行
2. 检查网络连接
3. 确认Docker已配置信任Registry（见"部署前准备"）

### 问题2: 数据库连接失败

**症状**：
```
FATAL: password authentication failed for user "pepgmp_prod"
```

**解决方案**：
```bash
# 在生产服务器上检查数据库容器
docker compose -f docker-compose.prod.yml logs postgres

# 验证.env.production中的数据库密码
cat .env.production | grep DATABASE_PASSWORD

# 检查数据库初始化
bash scripts/check_database_init.sh pepgmp-postgres-prod pepgmp_prod pepgmp_production
```

### 问题3: 容器无法启动

**症状**：
```
Error: container failed to start
```

**解决方案**：
```bash
# 查看详细错误日志
docker compose -f docker-compose.prod.yml logs api

# 检查配置文件
python scripts/validate_config.py

# 检查端口占用
sudo netstat -tulpn | grep 8000
```

---

## 📝 常用命令

### 服务管理

```bash
# 启动服务
docker compose -f docker-compose.prod.yml up -d

# 停止服务
docker compose -f docker-compose.prod.yml down

# 重启服务
docker compose -f docker-compose.prod.yml restart

# 查看状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

### 数据库管理

```bash
# 备份数据库
bash scripts/backup_db.sh

# 恢复数据库
bash scripts/restore_db.sh <备份文件路径>

# 检查数据库初始化
bash scripts/check_database_init.sh
```

---

## 🔗 相关文档

- [部署流程指南](./DEPLOYMENT_PROCESS_GUIDE.md) - 完整部署流程
- [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md) - 详细检查清单
- [生产环境部署指南](./production_deployment_guide.md) - 详细部署文档

---

**最后更新**: 2025-11-25
