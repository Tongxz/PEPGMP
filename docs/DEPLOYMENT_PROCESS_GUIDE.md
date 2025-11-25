# 部署流程指南

## 📋 概述

本文档提供了完整的生产环境部署流程，包括部署前的准备、部署步骤、部署后的验证，以及需要优化调整的内容。

**更新日期**: 2025-11-24  
**目标环境**: Ubuntu 22.04 LTS 内网环境  
**部署方式**: Docker 容器化部署 / Docker Compose / 内网私有Registry  
**预计时间**: 首次部署 10-15分钟，后续更新 3-5分钟

⚠️ **重要**: 本部署方案专为内网环境设计，所有服务部署在内网Ubuntu 22.04服务器上，使用Docker容器化部署。

---

## 🎯 部署流程总览

```
┌─────────────────────────────────────────────────────────────┐
│                    部署前准备（Pre-Deployment）              │
├─────────────────────────────────────────────────────────────┤
│  1. 配置文件准备 (.env.production)                          │
│  2. Docker环境准备                                           │
│  3. 代码质量检查                                             │
│  4. 测试验证                                                 │
│  5. 部署脚本检查                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    部署执行（Deployment）                    │
├─────────────────────────────────────────────────────────────┤
│  方式1: 一键部署（推荐）                                     │
│    bash scripts/quick_deploy.sh <SERVER_IP> ubuntu          │
│                                                              │
│  方式2: 分步部署                                             │
│    1. 构建镜像                                               │
│    2. 推送镜像                                               │
│    3. 部署服务                                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  部署后验证（Post-Deployment）               │
├─────────────────────────────────────────────────────────────┤
│  1. 基础验证（健康检查、容器状态）                           │
│  2. 功能验证（API端点、前端功能）                            │
│  3. 性能验证（响应时间、资源使用）                           │
│  4. 监控验证（日志、指标）                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 一、部署前准备

### 1.1 快速检查清单

在开始部署前，运行以下命令进行快速检查：

```bash
# 运行部署就绪检查
bash scripts/check_deployment_readiness.sh

# 验证配置
python scripts/validate_config.py

# 检查Git状态
git status
```

### 1.2 配置文件准备

#### 步骤1: 生成生产环境配置

```bash
# 自动生成带强随机密码的配置文件
bash scripts/generate_production_config.sh
```

**生成的文件**:
- `.env.production` - 生产环境配置
- `.env.production.credentials` - 凭证信息（使用后应删除）

#### 步骤2: 验证配置

```bash
# 验证配置文件
python scripts/validate_config.py

# 检查密码强度
grep -E "PASSWORD|SECRET" .env.production | grep -v "^#"
```

**检查项目**:
- [ ] 所有密码已设置为强密码（≥ 16字符）
- [ ] `SECRET_KEY` 长度 ≥ 32字符
- [ ] 所有 `CHANGE_ME` 占位符已替换
- [ ] 文件权限正确 (`chmod 600 .env.production`)

#### 步骤3: 检查配置文件

```bash
# 检查必需配置文件
ls -la .env.production
ls -la config/
ls -la models/  # 如需要
```

### 1.3 Docker环境准备

#### 开发环境（macOS）

```bash
# 1. 检查Docker运行状态
docker info

# 2. 配置Docker Registry信任
# Docker Desktop → Preferences → Docker Engine
# 添加: "insecure-registries": ["192.168.30.83:5433"]
# 点击 Apply & Restart

# 3. 验证Registry连接
curl http://192.168.30.83:5433/v2/_catalog
```

#### 生产环境（Ubuntu 22.04 内网环境）

```bash
# 1. 检查Ubuntu版本（必须是22.04）
lsb_release -a

# 2. 检查Docker版本（Ubuntu 22.04 使用Docker Compose V2）
docker --version
docker compose version  # V2命令（推荐）
# 或 docker-compose --version  # V1命令（如已安装）

# 3. 配置内网Docker Registry信任
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "insecure-registries": ["192.168.30.83:5433"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF
sudo systemctl restart docker

# 4. 验证内网Registry连接（确保内网连通）
ping 192.168.30.83
curl http://192.168.30.83:5433/v2/_catalog

# 5. 配置Docker用户组（避免每次sudo）
sudo usermod -aG docker $USER
newgrp docker  # 或重新登录
```

### 1.4 代码质量检查

```bash
# 1. 检查Git状态
git status
# 确保工作目录干净，所有更改已提交

# 2. 检查当前分支
git branch --show-current
# 建议在 develop 或 main 分支部署

# 3. 检查无硬编码敏感信息
grep -r "password\|secret" src/ --exclude-dir=__pycache__ | grep -v "#"
```

### 1.5 测试验证

```bash
# 1. 运行单元测试
pytest tests/unit/ -v

# 2. 运行集成测试（需要先启动开发服务器）
bash scripts/start_dev.sh &
sleep 10
python tests/integration/test_api_integration.py
pkill -f "uvicorn"

# 3. 测试Docker Compose配置
docker-compose -f docker-compose.prod.yml config
```

---

## 🚀 二、部署执行

### 方式1: 一键部署（推荐）✨

**最简单快速的方式，适合大多数场景**:

```bash
# 一键部署（构建 -> 推送 -> 部署）
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**执行流程**:
1. ✅ 构建Docker镜像
2. ✅ 推送到Registry
3. ✅ 部署到生产服务器
4. ✅ 健康检查
5. ✅ 记录部署历史

**优点**:
- 操作简单，一键完成
- 自动化程度高
- 减少人为错误

**缺点**:
- 无法细粒度控制
- 适合标准部署场景

### 方式2: 分步部署

**适合需要自定义部署流程的场景**:

#### 步骤1: 构建镜像

```bash
# 在开发机器上构建生产镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 验证镜像
docker images pepgmp-backend:latest
```

#### 步骤2: 推送镜像

```bash
# 推送到Registry
bash scripts/push_to_registry.sh latest v1.0.0

# 验证推送
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list
```

#### 步骤3: 准备生产服务器

```bash
# SSH到生产服务器
ssh ubuntu@<SERVER_IP>

# 创建部署目录
sudo mkdir -p /opt/pyt
sudo chown $USER:$USER /opt/pyt
cd /opt/pyt
```

#### 步骤4: 部署配置文件

**在开发机器上**:
```bash
# 打包配置文件（不包含.env.production）
tar czf deploy_config.tar.gz \
    docker-compose.prod.yml \
    Dockerfile.prod \
    config/ \
    scripts/ \
    nginx/

# 传输到生产服务器
scp deploy_config.tar.gz ubuntu@<SERVER_IP>:/opt/pyt/
scp .env.production ubuntu@<SERVER_IP>:/opt/pyt/
```

**在生产服务器上**:
```bash
# 解压配置文件
cd /opt/pyt
tar xzf deploy_config.tar.gz
chmod 600 .env.production
```

#### 步骤5: 部署服务（Ubuntu 22.04 内网环境）

**在Ubuntu 22.04生产服务器上**:
```bash
cd /opt/pyt

# 1. 从内网Registry拉取镜像
docker pull 192.168.30.83:5433/pepgmp-backend:latest
docker tag 192.168.30.83:5433/pepgmp-backend:latest pepgmp-backend:latest

# 2. 启动服务（Ubuntu 22.04 使用 Docker Compose V2）
docker compose -f docker-compose.prod.yml up -d
# 或使用 V1 命令（如已安装）: docker-compose -f docker-compose.prod.yml up -d

# 3. 验证部署
docker compose -f docker-compose.prod.yml ps
# 或: docker-compose -f docker-compose.prod.yml ps

# 4. 验证服务健康
curl http://localhost:8000/api/v1/monitoring/health

# 5. 查看日志
docker compose -f docker-compose.prod.yml logs -f api
# 或: docker-compose -f docker-compose.prod.yml logs -f api
```

**注意事项**:
- ✅ Ubuntu 22.04 默认使用 Docker Compose V2，命令为 `docker compose`（无连字符）
- ✅ 如使用 V1，确保已安装 `docker-compose`（带连字符）
- ✅ 内网环境需要确保所有服务可在内网访问
- ✅ 容器间通信使用 Docker 网络，无需配置防火墙规则

---

## ✅ 三、部署后验证

### 3.1 基础验证

```bash
# 1. 检查容器状态（Ubuntu 22.04 使用 docker compose）
docker ps
# 或使用: docker compose -f docker-compose.prod.yml ps
# 所有容器状态应为 "Up"

# 2. 健康检查（内网访问）
curl http://localhost:8000/api/v1/monitoring/health
# 应返回: {"status": "healthy"}

# 3. 系统信息
curl http://localhost:8000/api/v1/system/info
# 应返回系统信息JSON

# 4. 查看日志（Ubuntu 22.04 使用 docker compose）
docker compose -f docker-compose.prod.yml logs --tail=100 api
# 或使用: docker-compose -f docker-compose.prod.yml logs --tail=100 api
# 应无错误信息

# 5. 检查内网网络连通性（容器间）
docker compose -f docker-compose.prod.yml exec api ping -c 3 database
docker compose -f docker-compose.prod.yml exec api ping -c 3 redis
```

### 3.2 功能验证

```bash
# 1. 测试摄像头列表
curl http://localhost:8000/api/v1/cameras

# 2. 测试检测记录
curl http://localhost:8000/api/v1/records/violations?limit=10

# 3. 测试实时统计 ⭐
curl http://localhost:8000/api/v1/statistics/detection-realtime

# 4. 测试告警历史（分页）⭐
curl "http://localhost:8000/api/v1/alerts/history-db?limit=10&offset=0&sort_by=created_at&sort_order=desc"

# 5. 测试告警规则（分页）⭐
curl "http://localhost:8000/api/v1/alerts/rules?limit=10&offset=0"

# 6. 测试前端访问
curl http://localhost:8000/
```

### 3.3 前端验证

**在浏览器中访问**:
```
http://<SERVER_IP>:8000
```

**检查项目**:
- [ ] 首页加载正常
- [ ] 实时统计显示正常 ⭐
- [ ] 实时监控视频流正常
- [ ] 检测记录页面正常
- [ ] 告警中心分页正常 ⭐
- [ ] 统计数据图表显示
- [ ] 无JavaScript错误（打开浏览器控制台）

### 3.4 性能验证

```bash
# 1. 响应时间测试
time curl http://localhost:8000/api/v1/monitoring/health

# 2. 资源使用监控
docker stats

# 3. 压力测试（可选）
ab -n 1000 -c 10 http://localhost:8000/api/v1/monitoring/health
```

**性能指标**:
- [ ] 健康检查响应时间 < 50ms
- [ ] API响应时间 < 1s
- [ ] CPU使用率 < 80%
- [ ] 内存使用 < 4GB

### 3.5 监控验证

```bash
# 1. 查看日志（Ubuntu 22.04 使用 docker compose）
docker compose -f docker-compose.prod.yml logs -f
# 或使用: docker-compose -f docker-compose.prod.yml logs -f

# 2. 检查日志轮转（Ubuntu 22.04）
ls -lh /var/lib/docker/containers/*/*-json.log

# 3. 检查监控指标（如配置Prometheus，内网访问）
curl http://localhost:9090/api/v1/query?query=up

# 4. 检查Docker系统资源使用
docker system df
docker stats --no-stream

# 5. 检查容器网络（内网环境）
docker network ls
docker network inspect <network_name>
```

---

## 🔧 四、需要优化调整的内容

### 4.1 安全优化 ✅

#### SSL/TLS配置（推荐）

**当前状态**: 未配置HTTPS  
**建议**: 配置HTTPS以提高安全性

**实施步骤**:
1. 准备SSL证书（Let's Encrypt 或自签名）
2. 配置Nginx HTTPS
3. 更新API配置支持HTTPS

**配置文件**: `nginx/nginx.conf`

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://api:8000;
        # ...
    }
}
```

#### 安全头配置（推荐）

**当前状态**: 未配置安全头  
**建议**: 添加安全头以提高安全性

**配置文件**: `nginx/nginx.conf`

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000" always;
```

#### API访问控制（推荐）

**当前状态**: 基本认证  
**建议**: 增强认证机制

**优化内容**:
- [ ] JWT Token过期时间配置
- [ ] 刷新Token机制
- [ ] 访问频率限制（Rate Limiting）
- [ ] IP白名单（如需要）

### 4.2 性能优化 ✅

#### Gunicorn Workers配置

**当前配置**: 4 workers（硬编码在Dockerfile.prod）  
**建议**: 根据CPU核心数动态配置

**优化方案**:
1. 使用环境变量配置workers数量
2. 公式: `(2 × CPU核心数) + 1`

**配置文件**: `Dockerfile.prod` 或 `docker-compose.prod.yml`

```yaml
environment:
  - GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
```

#### 数据库连接池（推荐）

**当前状态**: 使用默认连接池  
**建议**: 优化连接池配置

**优化内容**:
- [ ] 调整连接池大小
- [ ] 优化查询语句
- [ ] 添加数据库索引（如需要）
- [ ] 配置连接超时

#### Redis缓存策略（推荐）

**当前状态**: 基本缓存配置  
**建议**: 优化缓存策略

**优化内容**:
- [ ] 配置缓存过期时间
- [ ] 优化缓存键名
- [ ] 监控缓存命中率
- [ ] 配置缓存预热

### 4.3 监控和日志优化 ✅

#### Prometheus监控（可选）

**当前状态**: 配置已存在但未启用  
**建议**: 在生产环境启用监控

**启用方法**:
```bash
docker-compose -f docker-compose.prod.full.yml --profile monitoring up -d
```

**验证**:
```bash
# Prometheus
curl http://localhost:9090/api/v1/query?query=up

# Grafana
curl http://localhost:3000
```

#### 日志聚合（可选）

**当前状态**: 本地日志文件  
**建议**: 配置日志聚合系统

**可选方案**:
- ELK Stack (Elasticsearch + Logstash + Kibana)
- Loki + Grafana
- CloudWatch (AWS)
- Azure Monitor (Azure)

### 4.4 备份和恢复优化 ✅

#### 自动备份（推荐）

**当前状态**: 手动备份脚本  
**建议**: 配置自动定时备份

**配置方法**:
```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天凌晨2点备份）
0 2 * * * /opt/pyt/scripts/backup_db.sh
```

#### 备份验证（推荐）

**当前状态**: 无备份验证  
**建议**: 添加备份验证机制

**优化内容**:
- [ ] 备份后验证文件完整性
- [ ] 定期测试恢复流程
- [ ] 监控备份成功/失败
- [ ] 配置备份告警

### 4.5 高可用优化（可选）✅

#### 多实例部署（可选）

**当前状态**: 单实例部署  
**建议**: 配置多实例部署提高可用性

**配置方法**:
```bash
# 启动多个API实例
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

**要求**:
- 配置Nginx负载均衡
- 配置共享存储（如需要）
- 配置会话共享（Redis）

#### 健康检查和自动恢复（推荐）

**当前状态**: 基本健康检查  
**建议**: 增强健康检查和自动恢复

**优化内容**:
- [ ] 配置自动重启策略
- [ ] 配置健康检查间隔
- [ ] 配置故障转移
- [ ] 配置告警通知

---

## 📋 五、部署检查清单（执行版）

### 部署前检查 ✅

```
□ .env.production 已创建并配置
□ 所有密码已设置为强密码（≥ 16字符）
□ config/ 目录存在且包含必需配置
□ models/ 目录存在（如需要）
□ Docker环境已准备
□ Registry连接正常
□ 生产服务器环境已准备
□ 代码已提交到Git
□ 单元测试通过
□ 集成测试通过
□ Docker Compose测试通过
□ 部署脚本可执行
```

### 部署中检查 ✅

```
□ 镜像构建成功
□ 镜像大小合理（< 1GB）
□ 镜像推送成功
□ Registry中镜像可访问
□ 生产服务器可访问
□ 配置文件已传输
□ 服务已启动
□ 所有容器状态为 "Up"
```

### 部署后检查 ✅

```
□ 健康检查通过
□ 系统信息正常返回
□ API端点可访问
□ 功能验证通过
□ 前端访问正常
□ 日志无错误信息
□ 性能指标正常
□ 监控系统正常（如配置）
```

---

## 🔄 六、更新和回滚

### 更新到新版本

#### 方式1: 快速更新（推荐）

```bash
# 一键更新
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu
```

#### 方式2: 分步更新

```bash
# 1. 构建新镜像
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 2. 推送到Registry
bash scripts/push_to_registry.sh latest v1.1.0

# 3. 在生产服务器上更新
ssh ubuntu@<SERVER_IP>
cd /opt/pyt
docker-compose pull
docker-compose up -d
```

### 回滚到之前版本

```bash
# 1. 查看可用版本
curl http://192.168.30.83:5433/v2/pepgmp-backend/tags/list

# 2. 回滚到特定版本
bash scripts/deploy_from_registry.sh <SERVER_IP> ubuntu v1.0.0
```

---

## 🚨 七、故障排查

### 常见问题

#### 问题1: 内网Registry连接失败

**症状**: `Error: Cannot connect to registry` 或 `dial tcp: lookup 192.168.30.83: no such host`

**解决方案** (Ubuntu 22.04 内网环境):
```bash
# 1. 检查内网连通性
ping 192.168.30.83
# 如无法ping通，检查内网网络配置

# 2. 检查内网Registry可访问性
curl http://192.168.30.83:5433/v2/_catalog
# 如无法访问，检查内网防火墙规则

# 3. 检查Docker配置（Ubuntu 22.04）
cat /etc/docker/daemon.json
# 确保包含: "insecure-registries": ["192.168.30.83:5433"]

# 4. 检查内网DNS（如使用域名）
nslookup registry.internal  # 如使用域名
# 或配置 /etc/hosts:
# echo "192.168.30.83 registry.internal" | sudo tee -a /etc/hosts

# 重启Docker
sudo systemctl restart docker
```

#### 问题2: 容器启动失败（Ubuntu 22.04）

**症状**: `Container exited with code 1` 或 `docker compose` 命令不存在

**解决方案** (Ubuntu 22.04 内网环境):
```bash
# 1. 检查Docker Compose版本（Ubuntu 22.04 默认使用V2）
docker compose version
# 如不存在，使用: docker-compose --version

# 2. 查看日志（Ubuntu 22.04 使用 docker compose）
docker compose -f docker-compose.prod.yml logs api
# 或使用: docker-compose -f docker-compose.prod.yml logs api

# 3. 检查环境变量
docker compose -f docker-compose.prod.yml config
# 或使用: docker-compose -f docker-compose.prod.yml config

# 4. 检查内网网络连通性（容器间）
docker compose -f docker-compose.prod.yml exec api ping -c 3 database
docker compose -f docker-compose.prod.yml exec api ping -c 3 redis

# 5. 检查Docker服务状态
sudo systemctl status docker

# 6. 检查磁盘空间（内网环境可能空间有限）
df -h
docker system df

# 检查文件权限
ls -la .env.production
```

#### 问题3: 数据库连接失败

**症状**: `Connection to database failed`

**解决方案**:
```bash
# 检查数据库容器
docker ps | grep postgres

# 检查数据库日志
docker-compose -f docker-compose.prod.yml logs database

# 测试连接
docker exec pepgmp-postgres-prod pg_isready -U pepgmp_prod
```

#### 问题4: 健康检查失败

**症状**: `Health check failed`

**解决方案**:
```bash
# 手动测试健康检查
curl -v http://localhost:8000/api/v1/monitoring/health

# 检查API日志
docker-compose -f docker-compose.prod.yml logs api

# 检查依赖服务
docker-compose -f docker-compose.prod.yml ps
```

---

## 📊 八、部署记录模板

### 部署记录

```yaml
部署日期: 2025-11-24
部署版本: v1.0.0
部署人员: <姓名>
部署方式: Docker Compose
服务器IP: <IP>
Git Commit: <commit-hash>

部署前检查:
  - [ ] 配置检查通过
  - [ ] 测试通过
  - [ ] 代码审查通过

部署步骤:
  1. 构建镜像: ✅
  2. 推送镜像: ✅
  3. 部署服务: ✅
  4. 验证功能: ✅

部署后验证:
  - [ ] 健康检查通过
  - [ ] 功能验证通过
  - [ ] 性能指标正常

问题记录:
  - 无

备注:
  - 无
```

---

## 📚 相关文档

- [部署前准备工作清单](./DEPLOYMENT_PREPARATION_CHECKLIST.md)
- [部署测试计划](./DEPLOYMENT_TEST_PLAN.md)
- [生产环境部署指南](./production_deployment_guide.md)
- [生产环境部署实施报告](./production_deployment_implementation.md)
- [Docker Compose使用指南](./docker_compose_usage_guide.md)

---

**状态**: ✅ **部署流程指南已完成**  
**下一步**: 根据流程指南执行部署  
**预计时间**: 首次部署 10-15分钟，后续更新 3-5分钟

