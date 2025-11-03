# 生产环境部署指南

## 📋 概述

本指南详细说明如何将项目从 macOS 开发环境部署到 Ubuntu 生产环境。

### 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    开发环境 (macOS)                          │
│                                                              │
│  1. 构建Docker镜像                                           │
│  2. 推送到私有Registry (192.168.30.83:5433)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 网络传输
                       │
┌──────────────────────▼──────────────────────────────────────┐
│               私有Docker Registry                            │
│           http://192.168.30.83:5433                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 拉取镜像
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                生产环境 (Ubuntu)                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  API服务     │  │  PostgreSQL  │  │    Redis     │    │
│  │  (Docker)    │  │  (Docker)    │  │  (Docker)    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                              │
│  可选服务:                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   MLflow     │  │  Prometheus  │  │   Grafana    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始（推荐）

### 方式1: 一键部署（最简单）✨

```bash
# 1. 生成生产环境配置
bash scripts/generate_production_config.sh

# 2. 一键部署（构建 -> 推送 -> 部署）
bash scripts/quick_deploy.sh <生产服务器IP> [SSH用户名]

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**就这么简单！** 脚本会自动完成：
- ✅ 构建Docker镜像
- ✅ 推送到私有Registry
- ✅ 部署到生产服务器
- ✅ 健康检查

---

## 📝 详细部署步骤

如果需要分步骤执行或自定义部署流程，请参考以下详细说明。

### 前置要求

#### 开发环境 (macOS)
- ✅ Docker Desktop已安装
- ✅ SSH密钥配置（可选，推荐）
- ✅ 可访问私有Registry (192.168.30.83:5433)
- ✅ 可SSH连接到生产服务器

#### 生产环境 (Ubuntu)
- ✅ Ubuntu 20.04 LTS 或更高版本
- ✅ 至少 4GB RAM
- ✅ 至少 20GB 磁盘空间
- ✅ root或sudo权限
- ✅ 开放8000端口（API）

### 步骤1: 准备配置文件

#### 方法A: 自动生成（推荐）

```bash
# 自动生成带强随机密码的配置文件
bash scripts/generate_production_config.sh
```

脚本会：
- 生成 `.env.production` 文件
- 自动生成强随机密码
- 创建 `.env.production.credentials` 凭证文件
- 设置正确的文件权限

#### 方法B: 手动创建

```bash
# 从示例创建
cat > .env.production << 'EOF'
ENVIRONMENT=production
API_PORT=8000
LOG_LEVEL=INFO

DATABASE_URL=postgresql://pyt_prod:CHANGE_ME@database:5432/pyt_production
DATABASE_PASSWORD=CHANGE_ME_STRONG_PASSWORD
REDIS_PASSWORD=CHANGE_ME_STRONG_PASSWORD
SECRET_KEY=CHANGE_ME_SECRET_KEY
JWT_SECRET_KEY=CHANGE_ME_JWT_SECRET
ADMIN_USERNAME=admin
ADMIN_PASSWORD=CHANGE_ME_ADMIN_PASSWORD

CORS_ORIGINS=*
USE_DOMAIN_SERVICE=true
REPOSITORY_TYPE=postgresql
ROLLOUT_PERCENT=100
WATCHFILES_FORCE_POLLING=1
EOF

# 设置权限
chmod 600 .env.production

# 修改密码
vim .env.production
```

**生成强密码命令**：
```bash
# Python方法
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL方法
openssl rand -base64 32
```

### 步骤2: 配置Docker信任私有Registry

#### macOS (Docker Desktop)

1. 打开 Docker Desktop
2. 进入 **Preferences** → **Docker Engine**
3. 添加配置：

```json
{
  "insecure-registries": ["192.168.30.83:5433"]
}
```

4. 点击 **Apply & Restart**

#### Ubuntu生产服务器（自动配置）

部署脚本会自动配置，无需手动操作。

### 步骤3: 构建Docker镜像

```bash
# 构建生产镜像
docker build -f Dockerfile.prod -t pyt-backend:latest .

# 验证镜像
docker images pyt-backend:latest
```

### 步骤4: 推送镜像到私有Registry

```bash
# 推送到Registry
bash scripts/push_to_registry.sh

# 或指定标签和版本
bash scripts/push_to_registry.sh latest v1.0.0
```

**验证推送成功**：
```bash
# 查看Registry中的镜像
curl http://192.168.30.83:5433/v2/_catalog
curl http://192.168.30.83:5433/v2/pyt-backend/tags/list
```

### 步骤5: 部署到生产服务器

```bash
# 从Registry部署
bash scripts/deploy_from_registry.sh <生产服务器IP> [SSH用户名] [镜像标签]

# 示例
bash scripts/deploy_from_registry.sh 192.168.1.100 ubuntu latest
```

### 步骤6: 验证部署

```bash
# SSH到生产服务器
ssh ubuntu@192.168.1.100

# 检查容器状态
docker ps

# 查看日志
docker-compose -f /opt/pyt/docker-compose.yml logs -f

# 测试API
curl http://localhost:8000/api/v1/monitoring/health
curl http://localhost:8000/api/v1/system/info
```

## 🛠️ 部署脚本说明

项目提供了多个部署脚本，适应不同场景：

| 脚本 | 用途 | 使用场景 |
|------|------|----------|
| `quick_deploy.sh` | 一键完整部署 | **最常用**，构建+推送+部署 |
| `push_to_registry.sh` | 推送镜像到Registry | 只更新镜像 |
| `deploy_from_registry.sh` | 从Registry部署 | 部署或回滚 |
| `deploy_to_production.sh` | 传统部署（tar传输） | 无Registry时使用 |
| `generate_production_config.sh` | 生成配置文件 | 首次部署前 |

### quick_deploy.sh - 一键部署 ✨

**最推荐的方式**，自动完成全流程：

```bash
bash scripts/quick_deploy.sh <服务器IP> [SSH用户]

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**执行流程**：
1. ✅ 构建Docker镜像
2. ✅ 推送到Registry
3. ✅ 部署到生产服务器
4. ✅ 健康检查
5. ✅ 记录部署历史

### push_to_registry.sh - 推送镜像

仅推送镜像到Registry，不部署：

```bash
# 推送latest标签
bash scripts/push_to_registry.sh

# 推送指定标签和版本
bash scripts/push_to_registry.sh v1.0.0 20251103_120000
```

### deploy_from_registry.sh - 从Registry部署

从Registry拉取镜像并部署：

```bash
# 部署latest版本
bash scripts/deploy_from_registry.sh 192.168.1.100 ubuntu latest

# 部署特定版本
bash scripts/deploy_from_registry.sh 192.168.1.100 ubuntu v1.0.0
```

### generate_production_config.sh - 生成配置

生成带强随机密码的生产环境配置：

```bash
bash scripts/generate_production_config.sh
```

生成的文件：
- `.env.production` - 生产环境变量
- `.env.production.credentials` - 凭证信息（使用后应删除）

## 🔄 更新和回滚

### 更新到新版本

#### 方法1: 快速更新

```bash
# 一键更新
bash scripts/quick_deploy.sh <服务器IP>
```

#### 方法2: 分步更新

```bash
# 1. 构建新镜像
docker build -f Dockerfile.prod -t pyt-backend:latest .

# 2. 推送到Registry
bash scripts/push_to_registry.sh latest v1.1.0

# 3. 在生产服务器上更新
ssh ubuntu@<服务器IP>
cd /opt/pyt
docker-compose pull
docker-compose up -d
```

### 回滚到之前版本

```bash
# 查看可用版本
curl http://192.168.30.83:5433/v2/pyt-backend/tags/list

# 回滚到特定版本
bash scripts/deploy_from_registry.sh <服务器IP> ubuntu v1.0.0
```

### 零停机更新（可选）

```bash
# 在生产服务器上
cd /opt/pyt

# 拉取新镜像
docker-compose pull

# 滚动更新（逐个重启容器）
docker-compose up -d --no-deps --build api

# 验证
curl http://localhost:8000/api/v1/monitoring/health
```

## 🔍 故障排查

### 问题1: Registry连接失败

**症状**：
```
Error: Cannot connect to registry
```

**解决方案**：
```bash
# 1. 检查Registry可访问性
curl http://192.168.30.83:5433/v2/_catalog

# 2. 检查Docker配置
# macOS: Docker Desktop -> Preferences -> Docker Engine
# Ubuntu: /etc/docker/daemon.json

# 3. 配置示例
{
  "insecure-registries": ["192.168.30.83:5433"]
}

# 4. 重启Docker
# macOS: Docker Desktop -> Restart
# Ubuntu: sudo systemctl restart docker
```

### 问题2: SSH连接失败

**症状**：
```
Permission denied (publickey)
```

**解决方案**：
```bash
# 方法1: 使用SSH密钥（推荐）
ssh-copy-id ubuntu@<服务器IP>

# 方法2: 脚本会提示输入密码
# 直接运行，按提示输入

# 方法3: 临时指定密钥
ssh -i ~/.ssh/your_key ubuntu@<服务器IP>
```

### 问题3: 容器启动失败

**症状**：
```
Container exited with code 1
```

**解决方案**：
```bash
# 1. 查看日志
ssh ubuntu@<服务器IP>
cd /opt/pyt
docker-compose logs api

# 2. 检查环境变量
cat .env

# 3. 检查配置文件
ls -la config/

# 4. 手动启动查看详细错误
docker-compose up api
```

### 问题4: 数据库连接失败

**症状**：
```
Connection to database failed
```

**解决方案**：
```bash
# 1. 检查数据库容器
docker ps | grep postgres

# 2. 检查数据库日志
docker-compose logs database

# 3. 测试连接
docker exec pyt-postgres-prod pg_isready -U pyt_prod

# 4. 检查密码配置
grep DATABASE_PASSWORD .env
```

### 问题5: 健康检查失败

**症状**：
```
Health check failed
```

**解决方案**：
```bash
# 1. 手动测试健康检查
curl -v http://localhost:8000/api/v1/monitoring/health

# 2. 检查API日志
docker-compose logs api

# 3. 检查依赖服务
docker-compose ps

# 4. 重启服务
docker-compose restart api
```

## 📊 监控和维护

### 日志管理

```bash
# 查看实时日志
ssh ubuntu@<服务器IP>
cd /opt/pyt
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f database
docker-compose logs -f redis

# 查看最近100行
docker-compose logs --tail=100 api

# 导出日志
docker-compose logs api > api_logs_$(date +%Y%m%d).log
```

### 资源监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看Docker磁盘使用
docker system df

# 清理未使用的资源
docker system prune -a
```

### 数据备份

```bash
# 备份PostgreSQL
docker exec pyt-postgres-prod pg_dump -U pyt_prod pyt_production > backup_$(date +%Y%m%d).sql

# 备份Redis
docker exec pyt-redis-prod redis-cli --rdb /data/backup.rdb

# 备份配置文件
tar czf config_backup_$(date +%Y%m%d).tar.gz /opt/pyt/config /opt/pyt/.env

# 定期备份脚本（crontab）
0 2 * * * /opt/pyt/scripts/backup.sh
```

### 安全更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新Docker
sudo apt install docker-ce docker-ce-cli containerd.io

# 更新docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🔐 安全最佳实践

### 1. 保护敏感文件

```bash
# 设置正确的文件权限
chmod 600 .env.production
chmod 600 /opt/pyt/.env
chmod 700 /opt/pyt/config

# 不要提交到Git
git status  # 确保 .env.production 被忽略
```

### 2. 使用强密码

```bash
# 定期更新密码（每90天）
bash scripts/generate_production_config.sh

# 使用密码管理器保存
# 推荐: 1Password, Bitwarden, LastPass
```

### 3. 限制网络访问

```bash
# 配置防火墙
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # API
sudo ufw status
```

### 4. 定期安全审计

```bash
# 检查容器安全
docker scan pyt-backend:latest

# 检查漏洞
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image pyt-backend:latest

# 检查配置
docker inspect pyt-api-prod
```

## 📈 性能优化

### 调整资源限制

编辑 `docker-compose.prod.full.yml`:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '8.0'      # 增加CPU
        memory: 8G        # 增加内存
      reservations:
        cpus: '4.0'
        memory: 4G
```

### 扩展副本数

```bash
# 启动多个API实例
cd /opt/pyt
docker-compose up -d --scale api=3

# 配合Nginx负载均衡
```

### 数据库优化

```bash
# 调整PostgreSQL配置
docker exec -it pyt-postgres-prod bash
psql -U pyt_prod -d pyt_production

# 常用优化查询
SHOW shared_buffers;
SHOW work_mem;
SHOW maintenance_work_mem;
```

## 🎯 高级主题

### CI/CD集成

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and Push
        run: |
          docker build -f Dockerfile.prod -t pyt-backend:latest .
          bash scripts/push_to_registry.sh

      - name: Deploy
        run: |
          bash scripts/deploy_from_registry.sh ${{ secrets.PRODUCTION_HOST }} ubuntu
```

### 蓝绿部署

```bash
# 准备蓝环境
docker-compose -f docker-compose.blue.yml up -d

# 测试蓝环境
curl http://localhost:8001/api/v1/monitoring/health

# 切换流量（更新Nginx配置）
sudo nginx -s reload

# 停止绿环境
docker-compose -f docker-compose.green.yml down
```

### 多环境部署

```bash
# 测试环境
bash scripts/deploy_from_registry.sh test.example.com ubuntu latest

# 预生产环境
bash scripts/deploy_from_registry.sh staging.example.com ubuntu latest

# 生产环境
bash scripts/deploy_from_registry.sh prod.example.com ubuntu v1.0.0
```

## 📚 相关文档

- [Docker Compose使用指南](./docker_compose_usage_guide.md)
- [Docker快速命令参考](./docker_quick_reference.md)
- [配置快速开始](./configuration_quick_start.md)
- [API文档](./API_文档.md)

## 💡 常见问题

### Q: 如何选择部署方式？

**A**: 推荐使用私有Registry方式：
- ✅ **有Registry**: 使用 `quick_deploy.sh`（推荐）
- ❌ **无Registry**: 使用 `deploy_to_production.sh`

### Q: 部署需要多长时间？

**A**:
- 首次部署: 约10-15分钟
- 后续更新: 约3-5分钟
- 一键部署: 约5-8分钟

### Q: 如何验证部署成功？

**A**:
```bash
# 1. 检查容器
docker ps

# 2. 测试API
curl http://localhost:8000/api/v1/monitoring/health

# 3. 查看日志
docker-compose logs api
```

### Q: 支持哪些操作系统？

**A**:
- **开发环境**: macOS, Linux, Windows (WSL2)
- **生产环境**: Ubuntu 20.04+, CentOS 7+, Debian 10+

### Q: 如何获取帮助？

**A**:
```bash
# 查看脚本帮助
bash scripts/quick_deploy.sh --help

# 查看日志
docker-compose logs -f

# 联系团队
```

---

## 📝 总结

本指南提供了完整的生产环境部署方案：

| 步骤 | 命令 | 耗时 |
|------|------|------|
| 1. 生成配置 | `generate_production_config.sh` | 1分钟 |
| 2. 一键部署 | `quick_deploy.sh <IP>` | 5-8分钟 |
| 3. 验证部署 | 自动执行 | 1分钟 |

**推荐流程**：
```bash
bash scripts/generate_production_config.sh
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**就这么简单！** 🎉

---

**更新日期**: 2025-11-03
**版本**: 1.0
**作者**: AI Assistant
