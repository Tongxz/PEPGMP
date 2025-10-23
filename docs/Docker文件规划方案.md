# Docker文件规划方案

## 📊 当前状态分析

### 现有文件

#### Docker Compose文件 (4个)
1. `docker-compose.yml` - 开发环境（API + Frontend）
2. `docker-compose.dev-db.yml` - 开发数据库（PostgreSQL + Redis）
3. `docker-compose.prod.yml` - 生产环境（简单版）
4. `docker-compose.prod.full.yml` - 生产环境（完整版）

#### Dockerfile文件 (7个)
1. `Dockerfile` - 默认Dockerfile
2. `Dockerfile.dev` - 开发环境
3. `Dockerfile.prod` - 生产环境（新）
4. `Dockerfile.api` - API专用
5. `Dockerfile.frontend` - 前端专用
6. `Dockerfile.supervisor` - Supervisor专用
7. `backup/Dockerfile.backup` - 备份

---

## 🎯 重新规划方案

### 原则
1. **清晰分离**: 开发环境和生产环境完全分离
2. **简化管理**: 减少冗余文件，统一命名规范
3. **GPU支持**: 生产环境支持GPU和TensorRT
4. **模型管理**: 模型文件使用Docker卷，支持自动转换

---

## 📁 新文件结构

```
Pyt/
├── docker-compose.yml              # 开发环境（API + Frontend）
├── docker-compose.dev-db.yml       # 开发数据库（PostgreSQL + Redis）
├── docker-compose.prod.yml         # 生产环境（完整版，GPU + TensorRT）
│
├── Dockerfile.dev                  # 开发环境Dockerfile
├── Dockerfile.prod                 # 生产环境Dockerfile（GPU + TensorRT）
├── Dockerfile.frontend             # 前端Dockerfile
│
├── .dockerignore                   # Docker忽略文件
│
├── docs/
│   └── Docker文件规划方案.md       # 本文档
│
└── scripts/
    └── deployment/
        ├── build_dev.sh            # 开发环境构建脚本
        └── build_prod.sh           # 生产环境构建脚本
```

---

## 🔧 文件详细说明

### 1. 开发环境

#### `docker-compose.yml`
**用途**: 本地开发环境，包含API和前端

**特点**:
- 使用 `Dockerfile.dev`
- 代码热重载
- 挂载本地代码目录
- 开发数据库连接

**启动命令**:
```bash
docker-compose up -d
```

#### `docker-compose.dev-db.yml`
**用途**: 开发数据库服务

**特点**:
- PostgreSQL 16
- Redis 7
- 开发环境配置
- 数据持久化

**启动命令**:
```bash
docker-compose -f docker-compose.dev-db.yml up -d
```

#### `Dockerfile.dev`
**用途**: 开发环境镜像构建

**特点**:
- 包含开发工具
- 支持热重载
- 包含调试工具
- 较小镜像体积

---

### 2. 生产环境

#### `docker-compose.prod.yml`
**用途**: 生产环境完整部署

**特点**:
- 使用 `Dockerfile.prod`
- GPU支持
- TensorRT自动转换
- 模型文件Docker卷
- 私有镜像仓库
- 健康检查
- 自动重启

**启动命令**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### `Dockerfile.prod`
**用途**: 生产环境镜像构建

**特点**:
- 基于 NVIDIA CUDA 12.4
- 多阶段构建
- 优化镜像大小
- 包含TensorRT支持
- 健康检查
- 安全配置

#### `Dockerfile.frontend`
**用途**: 前端生产镜像构建

**特点**:
- 基于 Nginx
- 静态文件服务
- 压缩优化
- 安全配置

---

## 🗑️ 需要删除的文件

### Docker Compose文件
- ❌ `docker-compose.prod.full.yml` → 重命名为 `docker-compose.prod.yml`

### Dockerfile文件
- ❌ `Dockerfile` → 删除（使用 `Dockerfile.dev` 或 `Dockerfile.prod`）
- ❌ `Dockerfile.api` → 删除（合并到 `Dockerfile.prod`）
- ❌ `Dockerfile.supervisor` → 删除（不需要）
- ❌ `backup/Dockerfile.backup` → 删除（备份文件）

---

## 📝 新文件内容

### 1. docker-compose.yml (开发环境)

```yaml
version: "3.8"

networks:
  pyt-dev-network:
    driver: bridge

services:
  # 后端 API (开发环境)
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: pyt-api-dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./output:/app/output
      - ./data:/app/data
      - ./models:/app/models
    command: python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://pyt_dev:pyt_dev_password@database:5432/pyt_development
      - REDIS_URL=redis://:pyt_dev_redis@redis:6379/0
      - LOG_LEVEL=DEBUG
      - AUTO_CONVERT_TENSORRT=false
    networks:
      - pyt-dev-network
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # 前端 (开发环境)
  frontend:
    image: node:20
    container_name: pyt-frontend-dev
    working_dir: /app
    volumes:
      - ./frontend:/app
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    ports:
      - "5173:5173"
    environment:
      - VITE_API_BASE=/api/v1
      - VITE_PROXY_TARGET=http://api:8000
      - BASE_URL=/
      - NODE_ENV=development
    networks:
      - pyt-dev-network
    depends_on:
      - api
    restart: unless-stopped

  # PostgreSQL 数据库 (开发环境)
  database:
    image: postgres:16-alpine
    container_name: pyt-postgres-dev
    environment:
      POSTGRES_DB: pyt_development
      POSTGRES_USER: pyt_dev
      POSTGRES_PASSWORD: pyt_dev_password
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    networks:
      - pyt-dev-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pyt_dev -d pyt_development"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  # Redis 缓存 (开发环境)
  redis:
    image: redis:7-alpine
    container_name: pyt-redis-dev
    command: >
      redis-server
      --appendonly yes
      --requirepass pyt_dev_redis
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_dev_data:/data
    ports:
      - "6379:6379"
    networks:
      - pyt-dev-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 5s
    restart: unless-stopped

volumes:
  postgres_dev_data:
    driver: local
  redis_dev_data:
    driver: local
```

### 2. docker-compose.prod.yml (生产环境)

```yaml
version: "3.8"

networks:
  pyt-prod-network:
    driver: bridge

volumes:
  postgres_prod_data:
    driver: local
  redis_prod_data:
    driver: local
  models_prod_data:
    driver: local

services:
  # PostgreSQL 数据库 (生产环境)
  database:
    image: 192.168.30.83:5433/postgres:16-alpine
    container_name: pyt-postgres-prod
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-pyt_production}
      POSTGRES_USER: ${POSTGRES_USER:-pyt_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me_in_production}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    networks:
      - pyt-prod-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-pyt_user} -d ${POSTGRES_DB:-pyt_production}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  # Redis 缓存 (生产环境)
  redis:
    image: 192.168.30.83:5433/redis:7-alpine
    container_name: pyt-redis-prod
    command: >
      redis-server
      --appendonly yes
      --requirepass ${REDIS_PASSWORD:-change_me_in_production}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_prod_data:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    networks:
      - pyt-prod-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
    restart: unless-stopped

  # 后端 API (生产环境)
  api:
    image: 192.168.30.83:5433/pyt-api:prod
    container_name: pyt-api-prod
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: ["gpu"]
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${POSTGRES_USER:-pyt_user}:${POSTGRES_PASSWORD:-change_me_in_production}@database:5432/${POSTGRES_DB:-pyt_production}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-change_me_in_production}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY:-change_me_in_production}
      - JWT_SECRET=${JWT_SECRET:-change_me_in_production}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - AUTO_CONVERT_TENSORRT=true
      - TENSORRT_PRECISION=fp16
    ports:
      - "${API_PORT:-8000}:8000"
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./output:/app/output
      - ./data:/app/data
      - models_prod_data:/app/models
    networks:
      - pyt-prod-network
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  # 前端 (生产环境)
  frontend:
    image: 192.168.30.83:5433/pyt-frontend:prod
    container_name: pyt-frontend-prod
    ports:
      - "${FRONTEND_PORT:-8080}:80"
    networks:
      - pyt-prod-network
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
```

---

## 🚀 使用指南

### 开发环境

```bash
# 1. 启动开发环境（包含所有服务）
docker-compose up -d

# 2. 查看日志
docker-compose logs -f api

# 3. 停止服务
docker-compose down

# 4. 只启动数据库
docker-compose -f docker-compose.dev-db.yml up -d
```

### 生产环境

```bash
# 1. 构建并部署
./scripts/deployment/build_prod.sh

# 2. 或者手动步骤
# 构建镜像
docker build -f Dockerfile.prod -t 192.168.30.83:5433/pyt-api:prod .
docker build -f Dockerfile.frontend -t 192.168.30.83:5433/pyt-frontend:prod .

# 推送镜像
docker push 192.168.30.83:5433/pyt-api:prod
docker push 192.168.30.83:5433/pyt-frontend:prod

# 部署服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose -f docker-compose.prod.yml logs -f api

# 4. 停止服务
docker-compose -f docker-compose.prod.yml down
```

---

## 📊 对比表

| 特性 | 开发环境 | 生产环境 |
|------|----------|----------|
| **Docker Compose** | `docker-compose.yml` | `docker-compose.prod.yml` |
| **Dockerfile** | `Dockerfile.dev` | `Dockerfile.prod` |
| **GPU支持** | ❌ 否 | ✅ 是 |
| **TensorRT** | ❌ 否 | ✅ 是（自动转换） |
| **模型卷** | 本地目录 | Docker卷 |
| **代码挂载** | ✅ 是（热重载） | ❌ 否 |
| **日志级别** | DEBUG | INFO |
| **镜像来源** | 本地构建 | 私有仓库 |
| **健康检查** | 简单 | 完整 |
| **自动重启** | unless-stopped | unless-stopped |

---

## ✅ 实施步骤

### 步骤1: 备份现有文件

```bash
# 创建备份目录
mkdir -p docker_backup

# 备份现有文件
cp docker-compose.yml docker_backup/
cp docker-compose.dev-db.yml docker_backup/
cp docker-compose.prod.yml docker_backup/
cp docker-compose.prod.full.yml docker_backup/
cp Dockerfile docker_backup/
cp Dockerfile.dev docker_backup/
cp Dockerfile.api docker_backup/
cp Dockerfile.supervisor docker_backup/
```

### 步骤2: 删除冗余文件

```bash
# 删除不需要的文件
rm docker-compose.prod.full.yml
rm Dockerfile
rm Dockerfile.api
rm Dockerfile.supervisor
rm -rf backup/
```

### 步骤3: 重命名文件

```bash
# 重命名生产环境配置文件
mv docker-compose.prod.full.yml docker-compose.prod.yml
```

### 步骤4: 更新文件内容

按照上述新文件内容更新：
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `Dockerfile.dev`
- `Dockerfile.prod`

### 步骤5: 测试

```bash
# 测试开发环境
docker-compose up -d
docker-compose logs -f

# 测试生产环境
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🎯 总结

### 优化后的结构

- ✅ **4个Docker Compose文件** → **2个** (开发 + 生产)
- ✅ **7个Dockerfile文件** → **3个** (开发 + 生产 + 前端)
- ✅ **清晰分离**: 开发和生产环境完全独立
- ✅ **GPU支持**: 生产环境支持GPU和TensorRT
- ✅ **模型管理**: 使用Docker卷存储模型文件
- ✅ **自动转换**: 生产环境自动转换TensorRT引擎

### 优势

1. **简化管理**: 文件数量减少50%
2. **清晰命名**: 统一命名规范
3. **易于维护**: 减少冗余和混乱
4. **功能完整**: 保留所有必要功能
5. **生产就绪**: 支持GPU和TensorRT

---

**文档版本**: v1.0
**最后更新**: 2025-10-15
**维护者**: 开发团队
