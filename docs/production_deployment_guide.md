# 生产环境部署指南

## 概述

当前的配置管理改进**完全支持生产环境部署**，但需要针对生产环境进行一些额外的配置和优化。

## 生产环境适用性评估

### ✅ 已支持的特性

1. **配置管理** ✅
   - 使用.env文件
   - 支持多环境配置（.env.production）
   - 环境变量优先级
   - 配置验证

2. **安全性** ✅
   - 密码不暴露在命令行
   - 敏感信息不提交到Git
   - 支持密钥管理服务集成

3. **可扩展性** ✅
   - 支持Docker部署
   - 支持多workers
   - 支持负载均衡

### ⚠️ 需要改进的部分

1. **Docker配置** ⚠️
   - Dockerfile.prod需要支持.env文件
   - docker-compose需要适配新的配置系统
   - 需要secrets管理

2. **启动脚本** ⚠️
   - 需要生产环境启动脚本
   - 需要支持Gunicorn
   - 需要健康检查

3. **监控和日志** ⚠️
   - 需要集成日志聚合
   - 需要性能监控
   - 需要告警系统

## 生产环境部署改进方案

### 1. Dockerfile.prod改进

**问题**:
- ❌ 当前Dockerfile.prod未使用.env文件
- ❌ 使用硬编码的启动命令
- ❌ 使用uvicorn而非Gunicorn

**改进方案**: 创建新的Dockerfile.prod

### 2. docker-compose.yml改进

**问题**:
- ❌ 当前docker-compose.yml主要用于开发
- ❌ 未使用Docker secrets
- ❌ 未使用健康检查

**改进方案**: 创建docker-compose.prod.yml

### 3. 生产环境配置

**创建文件**:
- `.env.production.example` - 生产配置模板
- `scripts/start_prod.sh` - 生产启动脚本
- `scripts/deploy_prod.sh` - 部署脚本

## 生产环境文件结构

```
project/
├── .env.example                    # 开发配置模板
├── .env                            # 开发配置（不提交）
├── .env.production.example         # 生产配置模板
├── .env.production                 # 生产配置（不提交）
├── Dockerfile.dev                  # 开发环境镜像
├── Dockerfile.prod                 # 生产环境镜像（改进）
├── docker-compose.yml              # 开发环境编排
├── docker-compose.prod.yml         # 生产环境编排（新建）
├── scripts/
│   ├── start_dev.sh               # 开发启动
│   ├── start_prod.sh              # 生产启动（新建）
│   └── deploy_prod.sh             # 部署脚本（新建）
└── docs/
    └── production_deployment_guide.md  # 本文档
```

## 部署架构

### 开发环境

```
Developer Machine
├── .env (本地配置)
├── venv (虚拟环境)
└── ./scripts/start_dev.sh
    └── uvicorn with --reload
```

### 生产环境

```
Production Server
├── Docker Container
│   ├── .env.production (挂载为secrets)
│   ├── Gunicorn
│   │   └── Uvicorn Workers (4+)
│   └── 健康检查
├── Nginx (反向代理)
├── PostgreSQL (独立容器/服务)
├── Redis (独立容器/服务)
└── 监控系统
    ├── Prometheus
    ├── Grafana
    └── ELK Stack
```

## 部署流程

### 第一步：准备生产配置

```bash
# 1. 创建生产配置
cp .env.production.example .env.production

# 2. 编辑生产配置
nano .env.production

# 3. 设置强密码
# DATABASE_PASSWORD=<strong-password>
# REDIS_PASSWORD=<strong-password>
# ADMIN_PASSWORD=<strong-password>
# SECRET_KEY=<64-char-random-key>

# 4. 限制文件权限
chmod 600 .env.production
```

### 第二步：构建生产镜像

```bash
# 使用改进的Dockerfile.prod
docker build -f Dockerfile.prod -t pyt-api:latest .
```

### 第三步：部署

**使用Docker Compose**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**使用Kubernetes**:
```bash
kubectl apply -f k8s/
```

### 第四步：验证

```bash
# 健康检查
curl https://your-domain.com/api/v1/monitoring/health

# 性能测试
ab -n 1000 -c 10 https://your-domain.com/api/v1/monitoring/health
```

## 安全最佳实践

### 1. 密钥管理

**不推荐** ❌:
```bash
# 直接在.env.production中存储密码
DATABASE_PASSWORD=plain_text_password
```

**推荐** ✅:

**选项1: Docker Secrets**
```bash
# 创建secrets
echo "strong_password" | docker secret create db_password -

# 在docker-compose中引用
secrets:
  - db_password
```

**选项2: 环境变量（从外部注入）**
```bash
# 从密钥管理服务获取
export DATABASE_PASSWORD=$(aws secretsmanager get-secret-value --secret-id prod/db/password --query SecretString --output text)
```

**选项3: 密钥管理服务**
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

### 2. 网络安全

```yaml
# docker-compose.prod.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 内网，不暴露到外部
```

### 3. 容器安全

```dockerfile
# 使用非root用户
RUN useradd -m -u 1000 appuser
USER appuser
```

### 4. HTTPS

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://api:8000;
    }
}
```

## 性能优化

### 1. Gunicorn配置

```bash
# 生产环境使用Gunicorn + Uvicorn Workers
gunicorn src.api.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log
```

### 2. Workers数量

```python
# 推荐公式
workers = (2 * CPU_CORES) + 1

# 示例
# 4核CPU: workers = 9
# 8核CPU: workers = 17
```

### 3. 数据库连接池

```python
# src/config/env_config.py
@property
def database_pool_size(self) -> int:
    """数据库连接池大小."""
    return int(os.getenv("DATABASE_POOL_SIZE", "20"))

@property
def database_max_overflow(self) -> int:
    """数据库连接池溢出."""
    return int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
```

### 4. Redis连接池

```python
@property
def redis_pool_size(self) -> int:
    """Redis连接池大小."""
    return int(os.getenv("REDIS_POOL_SIZE", "10"))
```

## 监控和日志

### 1. 日志聚合

**使用ELK Stack**:
```yaml
# docker-compose.prod.yml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
```

### 2. 性能监控

**使用Prometheus + Grafana**:
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana:latest
```

### 3. APM（应用性能监控）

**选项**:
- New Relic
- Datadog
- Sentry
- Elastic APM

## 高可用性

### 1. 负载均衡

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
      
  nginx:
    image: nginx:alpine
    depends_on:
      - api
```

### 2. 数据库主从复制

```yaml
services:
  postgres-master:
    image: postgres:16-alpine
    
  postgres-replica:
    image: postgres:16-alpine
    environment:
      POSTGRES_MASTER_HOST: postgres-master
```

### 3. Redis哨兵模式

```yaml
services:
  redis-master:
    image: redis:7-alpine
    
  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
```

## 备份策略

### 1. 数据库备份

```bash
# 每日备份脚本
#!/bin/bash
docker exec postgres-master pg_dump -U user dbname > backup_$(date +%Y%m%d).sql

# 保留最近30天
find /backups -name "*.sql" -mtime +30 -delete
```

### 2. 配置备份

```bash
# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    .env.production \
    config/*.yaml \
    docker-compose.prod.yml
```

## 故障恢复

### 1. 健康检查

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/monitoring/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 2. 自动重启

```yaml
restart: unless-stopped
```

### 3. 滚动更新

```bash
# 无停机更新
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
```

## CI/CD集成

### GitHub Actions示例

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -f Dockerfile.prod -t pyt-api:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag pyt-api:${{ github.sha }} registry.example.com/pyt-api:latest
          docker push registry.example.com/pyt-api:latest
      
      - name: Deploy
        run: |
          ssh user@prod-server "cd /app && docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d"
```

## 成本优化

### 1. 资源限制

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 2. 镜像优化

```dockerfile
# 使用多阶段构建
FROM python:3.10-slim AS builder
# 构建依赖

FROM python:3.10-slim
# 复制构建产物
COPY --from=builder /app /app
```

### 3. 缓存优化

```yaml
services:
  redis:
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
```

## 检查清单

### 部署前

- [ ] 创建.env.production配置
- [ ] 设置强密码
- [ ] 配置SSL证书
- [ ] 设置防火墙规则
- [ ] 配置备份策略
- [ ] 设置监控告警

### 部署时

- [ ] 构建生产镜像
- [ ] 运行集成测试
- [ ] 验证配置
- [ ] 执行数据库迁移
- [ ] 部署到生产环境
- [ ] 验证健康检查

### 部署后

- [ ] 验证所有API端点
- [ ] 检查日志
- [ ] 监控性能指标
- [ ] 配置告警规则
- [ ] 文档更新
- [ ] 团队通知

## 总结

### ✅ 当前方案的优势

1. **配置管理** - 使用.env文件，支持多环境
2. **安全性** - 密码不暴露，支持secrets管理
3. **可扩展性** - 支持Docker、Kubernetes
4. **标准化** - 符合12-Factor App原则

### 🔧 需要的改进

1. **Docker文件** - 需要适配新的配置系统
2. **部署脚本** - 需要生产环境脚本
3. **监控集成** - 需要完整的监控方案
4. **文档完善** - 需要详细的部署文档

### 📋 下一步行动

1. 创建改进的Dockerfile.prod
2. 创建docker-compose.prod.yml
3. 创建生产启动脚本
4. 创建部署脚本
5. 配置监控和日志
6. 编写运维文档

---

**状态**: 生产环境部署方案  
**优先级**: 高  
**影响**: 确保生产环境安全、稳定、高性能

