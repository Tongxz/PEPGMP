# Docker Compose 使用指南

## 📚 文件说明

项目中有多个docker-compose配置文件，各有不同用途：

| 文件 | 用途 | 包含服务 |
|------|------|----------|
| `docker-compose.prod.yml` | 生产基础环境 | API + PostgreSQL + Redis |
| `docker-compose.prod.mlops.yml` | MLOps扩展服务 | MLflow + DVC |
| `docker-compose.prod.full.yml` | **完整整合版（推荐）** | 所有服务 + 可选MLOps |
| `docker-compose.dev-db.yml` | 开发环境数据库 | PostgreSQL + Redis（开发用）|

## 🎯 推荐使用方案

### 方案1: 使用整合版（推荐）✨

使用 `docker-compose.prod.full.yml`，支持灵活的服务组合。

#### 场景1: 基础生产环境（最常用）

```bash
# 启动：API + Database + Redis
docker-compose -f docker-compose.prod.full.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.full.yml ps

# 查看日志
docker-compose -f docker-compose.prod.full.yml logs -f api

# 停止服务
docker-compose -f docker-compose.prod.full.yml down
```

**包含服务**:
- ✅ API服务 (pepgmp-backend)
- ✅ PostgreSQL数据库
- ✅ Redis缓存

#### 场景2: 包含MLOps服务

```bash
# 启动：基础服务 + MLflow + DVC
docker-compose -f docker-compose.prod.full.yml --profile mlops up -d

# 访问MLflow
open http://localhost:5000
```

**包含服务**:
- ✅ 所有基础服务
- ✅ MLflow（实验跟踪）
- ✅ DVC（数据版本控制）

#### 场景3: 包含监控服务

```bash
# 启动：基础服务 + Prometheus + Grafana
docker-compose -f docker-compose.prod.full.yml --profile monitoring up -d

# 访问监控
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (默认: admin/admin)
```

#### 场景4: 完整环境（所有服务）

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.full.yml --profile mlops --profile monitoring up -d
```

**包含服务**:
- ✅ API服务
- ✅ PostgreSQL + Redis
- ✅ MLflow + DVC
- ✅ Prometheus + Grafana

### 方案2: 分离的配置文件

适合需要独立管理不同服务的场景。

#### 启动基础环境

```bash
# 1. 启动基础服务
docker-compose -f docker-compose.prod.yml up -d

# 2. 单独启动MLOps服务（可选）
docker-compose -f docker-compose.prod.mlops.yml up -d
```

**注意**: 需要确保网络配置一致。

## 🚀 快速开始

### 步骤1: 准备环境变量

```bash
# 复制环境变量模板
cp .env.production.example .env.production

# 编辑配置（重要！）
vim .env.production
```

**必须配置的变量**:
```env
DATABASE_PASSWORD=your_secure_password
REDIS_PASSWORD=your_secure_password
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
```

### 步骤2: 构建镜像

```bash
# 方式1: 单独构建（已完成）
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 方式2: docker-compose自动构建
docker-compose -f docker-compose.prod.full.yml build
```

### 步骤3: 启动服务

```bash
# 基础环境
docker-compose -f docker-compose.prod.full.yml up -d

# 等待服务启动（约30秒）
sleep 30

# 验证健康状态
curl http://localhost:8000/api/v1/monitoring/health
```

### 步骤4: 验证部署

```bash
# 查看所有容器状态
docker-compose -f docker-compose.prod.full.yml ps

# 查看API日志
docker-compose -f docker-compose.prod.full.yml logs -f api

# 测试API
curl http://localhost:8000/api/v1/statistics/summary
```

## 📊 服务管理

### 查看状态

```bash
# 查看所有服务状态
docker-compose -f docker-compose.prod.full.yml ps

# 查看资源使用
docker stats $(docker-compose -f docker-compose.prod.full.yml ps -q)
```

### 查看日志

```bash
# 所有服务日志
docker-compose -f docker-compose.prod.full.yml logs

# 特定服务日志（实时）
docker-compose -f docker-compose.prod.full.yml logs -f api
docker-compose -f docker-compose.prod.full.yml logs -f database
docker-compose -f docker-compose.prod.full.yml logs -f redis

# 最近100行
docker-compose -f docker-compose.prod.full.yml logs --tail=100
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.prod.full.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.full.yml restart api

# 重新构建并重启
docker-compose -f docker-compose.prod.full.yml up -d --build api
```

### 扩展副本

```bash
# 扩展API服务到3个副本
docker-compose -f docker-compose.prod.full.yml up -d --scale api=3

# 配合Nginx负载均衡使用
```

### 停止和清理

```bash
# 停止所有服务（保留数据）
docker-compose -f docker-compose.prod.full.yml stop

# 停止并删除容器（保留数据卷）
docker-compose -f docker-compose.prod.full.yml down

# 停止并删除容器和数据卷（危险！）
docker-compose -f docker-compose.prod.full.yml down -v

# 停止并删除镜像
docker-compose -f docker-compose.prod.full.yml down --rmi all
```

## 🔧 Profile 使用详解

### 什么是Profile？

Profile允许你定义**可选服务**，只在需要时启动。

### 可用的Profile

| Profile | 包含服务 | 用途 |
|---------|----------|------|
| （无） | api, database, redis | 基础生产环境 |
| `mlops` | mlflow, dvc | 机器学习实验跟踪 |
| `monitoring` | prometheus, grafana | 监控和可视化 |
| `nginx` | nginx | 反向代理 |

### 组合使用

```bash
# 基础 + MLOps
docker-compose -f docker-compose.prod.full.yml --profile mlops up -d

# 基础 + 监控
docker-compose -f docker-compose.prod.full.yml --profile monitoring up -d

# 基础 + MLOps + 监控
docker-compose -f docker-compose.prod.full.yml \
  --profile mlops \
  --profile monitoring \
  up -d

# 完整环境（所有服务）
docker-compose -f docker-compose.prod.full.yml \
  --profile mlops \
  --profile monitoring \
  --profile nginx \
  up -d
```

## 🌐 网络配置

### 网络架构

```
┌─────────────────────────────────────────┐
│         frontend (公开网络)              │
│  - API服务                               │
│  - Nginx（可选）                         │
│  - Prometheus（可选）                    │
│  - Grafana（可选）                       │
│  - MLflow（可选）                        │
└─────────────────────────────────────────┘
              │
              │
┌─────────────────────────────────────────┐
│         backend (内部网络)               │
│  - PostgreSQL数据库                      │
│  - Redis缓存                             │
│  - DVC（可选）                           │
└─────────────────────────────────────────┘
```

**安全特性**:
- ✅ backend网络是内部网络（`internal: true`）
- ✅ 数据库和Redis不直接暴露到外部
- ✅ 只有API服务连接两个网络

### 端口映射

| 服务 | 容器端口 | 主机端口 | 访问地址 |
|------|----------|----------|----------|
| API | 8000 | 8000 | http://localhost:8000 |
| PostgreSQL | 5432 | - | 内部访问 |
| Redis | 6379 | - | 内部访问 |
| Nginx | 80/443 | 80/443 | http://localhost |
| Prometheus | 9090 | 9090 | http://localhost:9090 |
| Grafana | 3000 | 3000 | http://localhost:3000 |
| MLflow | 5000 | 5000 | http://localhost:5000 |

## 💾 数据持久化

### 数据卷

| 卷名 | 用途 | 大小估算 |
|------|------|----------|
| `postgres_prod_data` | PostgreSQL数据 | 1-10GB |
| `redis_prod_data` | Redis持久化 | 100MB-1GB |
| `app_logs` | 应用日志 | 1-5GB |
| `app_output` | 输出文件 | 1-10GB |
| `mlflow_prod_data` | MLflow实验数据 | 1-20GB |
| `dvc_prod_cache` | DVC缓存 | 5-50GB |
| `prometheus_data` | 监控指标 | 1-5GB |
| `grafana_data` | Grafana配置 | 100MB |

### 备份数据

```bash
# 备份PostgreSQL
docker-compose -f docker-compose.prod.full.yml exec database \
  pg_dump -U pepgmp_prod pepgmp_production > backup_$(date +%Y%m%d).sql

# 备份Redis
docker-compose -f docker-compose.prod.full.yml exec redis \
  redis-cli --rdb /data/backup.rdb

# 备份所有数据卷
docker run --rm \
  -v postgres_prod_data:/source \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_$(date +%Y%m%d).tar.gz -C /source .
```

### 恢复数据

```bash
# 恢复PostgreSQL
cat backup_20251103.sql | docker-compose -f docker-compose.prod.full.yml exec -T database \
  psql -U pepgmp_prod -d pepgmp_production

# 恢复Redis
docker-compose -f docker-compose.prod.full.yml exec redis \
  redis-cli --rdb /data/dump.rdb < backup.rdb
```

## 🔍 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 查看完整日志
docker-compose -f docker-compose.prod.full.yml logs

# 查看特定服务详细日志
docker-compose -f docker-compose.prod.full.yml logs api --tail=100

# 检查容器状态
docker-compose -f docker-compose.prod.full.yml ps
```

#### 2. 数据库连接失败

```bash
# 检查数据库健康状态
docker-compose -f docker-compose.prod.full.yml exec database pg_isready -U pepgmp_prod

# 查看数据库日志
docker-compose -f docker-compose.prod.full.yml logs database

# 手动连接测试
docker-compose -f docker-compose.prod.full.yml exec database \
  psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"
```

#### 3. Redis连接失败

```bash
# 测试Redis连接
docker-compose -f docker-compose.prod.full.yml exec redis \
  redis-cli -a ${REDIS_PASSWORD} ping

# 查看Redis日志
docker-compose -f docker-compose.prod.full.yml logs redis
```

#### 4. API健康检查失败

```bash
# 手动测试健康检查
docker-compose -f docker-compose.prod.full.yml exec api \
  curl -f http://localhost:8000/api/v1/monitoring/health

# 查看API日志
docker-compose -f docker-compose.prod.full.yml logs api --tail=50
```

#### 5. 网络问题

```bash
# 查看网络配置
docker network ls
docker network inspect pyt_frontend
docker network inspect pyt_backend

# 重建网络
docker-compose -f docker-compose.prod.full.yml down
docker-compose -f docker-compose.prod.full.yml up -d
```

## 🔐 安全最佳实践

### 1. 使用Secrets

```bash
# 创建secrets目录
mkdir -p secrets

# 生成密钥文件
echo "your_secure_db_password" > secrets/db_password.txt
echo "your_secure_redis_password" > secrets/redis_password.txt
echo "your_admin_password" > secrets/admin_password.txt
echo "your_secret_key" > secrets/secret_key.txt

# 设置权限
chmod 600 secrets/*
```

### 2. 限制资源

配置文件中已包含资源限制：
- CPU限制：防止服务占用过多CPU
- 内存限制：防止OOM

### 3. 日志管理

配置文件中已包含日志轮转：
- 最大文件大小：10MB
- 保留文件数：3个

### 4. 网络隔离

- backend网络设置为内部网络
- 数据库和Redis不直接暴露

## 📈 性能优化

### 1. 调整副本数

```bash
# 根据负载调整API副本数
docker-compose -f docker-compose.prod.full.yml up -d --scale api=3
```

### 2. 资源限制调整

编辑 `docker-compose.prod.full.yml`：

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '8.0'      # 增加CPU限制
        memory: 8G        # 增加内存限制
```

### 3. 数据库优化

```bash
# 调整PostgreSQL配置
docker-compose -f docker-compose.prod.full.yml exec database \
  psql -U pepgmp_prod -d pepgmp_production -c "SHOW all;"
```

## 📝 总结

### Dockerfile vs docker-compose

| 方面 | Dockerfile | docker-compose |
|------|-----------|----------------|
| 用途 | 构建单个镜像 | 编排多个容器 |
| 命令 | `docker build` | `docker-compose up` |
| 配置 | 镜像构建步骤 | 服务、网络、卷 |
| 使用场景 | 创建应用镜像 | 运行完整环境 |

### 推荐工作流

```bash
# 1. 构建镜像（可选，docker-compose也能自动构建）
docker build -f Dockerfile.prod -t pepgmp-backend:latest .

# 2. 启动完整环境
docker-compose -f docker-compose.prod.full.yml up -d

# 3. 如需MLOps
docker-compose -f docker-compose.prod.full.yml --profile mlops up -d

# 4. 验证
curl http://localhost:8000/api/v1/monitoring/health

# 5. 查看日志
docker-compose -f docker-compose.prod.full.yml logs -f
```

### 文件选择建议

| 场景 | 推荐文件 |
|------|----------|
| **生产部署（推荐）** | `docker-compose.prod.full.yml` |
| 基础环境 | `docker-compose.prod.yml` |
| 只要MLOps | `docker-compose.prod.mlops.yml` |
| 开发环境 | `docker-compose.dev-db.yml` |

---

**更新日期**: 2025-11-03
**作者**: AI Assistant
