# Docker 增量构建优化方案

## 📊 当前 Dockerfile 分析

### 后端 Dockerfile (Dockerfile.prod) 问题分析

**当前结构**：
1. ✅ 基础环境配置（变化少，缓存友好）
2. ✅ 系统依赖安装（变化少，缓存友好）
3. ✅ Python 依赖安装（变化中等，已分离）
4. ❌ **代码复制**：`COPY . /app/`（变化频繁，导致缓存失效）

**问题点**：
- 第76行：`COPY . /app/` 会复制所有文件
- 代码变化时，整个层失效，需要重新构建后续所有层
- 没有充分利用 Docker 层缓存机制

### 前端 Dockerfile (Dockerfile.frontend) 问题分析

**当前结构**：
1. ✅ 依赖安装（已分离 `package*.json`）
2. ❌ **代码复制**：`COPY frontend ./`（变化频繁）

**问题点**：
- 第17行：`COPY frontend ./` 会复制所有前端代码
- 代码变化时，需要重新执行构建步骤

## 🎯 增量构建优化方案

### 方案1: 优化层顺序和文件复制（推荐）

**核心思想**：将变化频繁的代码复制放在最后，充分利用 Docker 层缓存。

#### 后端优化 (Dockerfile.prod)

**优化点**：
1. 分离配置文件复制和代码复制
2. 只复制必要的文件，而不是整个目录
3. 将代码复制放在最后

**修改内容**：

```dockerfile
# ==================== 阶段3: 生产镜像 ====================
FROM base

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/output /app/data /app/models /app/config

# 设置工作目录
WORKDIR /app

# 从builder阶段复制Python包
COPY --from=builder /root/.local /home/appuser/.local

# 确保脚本在PATH中
ENV PATH=/home/appuser/.local/bin:$PATH

# ========== 优化：分离配置文件和代码复制 ==========
# 1. 先复制配置文件（变化少，缓存友好）
COPY --chown=appuser:appuser config/ /app/config/
COPY --chown=appuser:appuser main.py /app/
COPY --chown=appuser:appuser pyproject.toml /app/ 2>/dev/null || true

# 2. 再复制源代码（变化频繁，放在最后）
COPY --chown=appuser:appuser src/ /app/src/

# 设置权限
RUN chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/monitoring/health || exit 1

# 启动命令
CMD ["gunicorn", "src.api.app:app", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--keep-alive", "5", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "50", \
    "--access-logfile", "/app/logs/access.log", \
    "--error-logfile", "/app/logs/error.log", \
    "--log-level", "info"]
```

#### 前端优化 (Dockerfile.frontend)

**优化点**：
1. 分离源代码复制和构建
2. 只复制构建所需的文件

**修改内容**：

```dockerfile
# Frontend production image (Vue3 + Vite build)
ARG NODE_IMAGE=node:20-alpine
ARG NGINX_IMAGE=nginx:1.27-alpine

FROM ${NODE_IMAGE} AS builder

WORKDIR /app

# Install deps (use lockfile if present)
COPY frontend/package*.json ./
COPY frontend/tsconfig*.json ./
COPY frontend/vite.config.ts ./
RUN npm ci

# ========== 优化：分离源代码复制 ==========
# 只复制源代码目录（排除 node_modules, dist 等）
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/index.html ./
COPY frontend/.env* ./ 2>/dev/null || true

# Support build-time env overrides
ARG VITE_API_BASE
ARG BASE_URL
ARG SKIP_TYPE_CHECK=false
ENV VITE_API_BASE=${VITE_API_BASE}
ENV BASE_URL=${BASE_URL}

RUN if [ "$SKIP_TYPE_CHECK" = "true" ]; then \
        npx vite build; \
    else \
        npm run build; \
    fi

# Stage 2: Nginx runtime
FROM ${NGINX_IMAGE}

COPY deployment/nginx/frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 方案2: 使用 BuildKit 缓存挂载（高级优化）

**优势**：
- 利用 BuildKit 的缓存挂载功能
- 进一步加速依赖安装

**后端优化**：

```dockerfile
# 需要启用 BuildKit: DOCKER_BUILDKIT=1
FROM base AS builder

WORKDIR /app

# 升级pip（使用缓存挂载）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# 复制依赖文件
COPY requirements.prod.txt /tmp/requirements.txt

# 安装Python依赖（使用缓存挂载）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir -r /tmp/requirements.txt
```

**前端优化**：

```dockerfile
FROM ${NODE_IMAGE} AS builder

WORKDIR /app

# 复制依赖文件
COPY frontend/package*.json ./

# 安装依赖（使用缓存挂载）
RUN --mount=type=cache,target=/root/.npm \
    npm ci
```

### 方案3: 多阶段构建优化（已实现，可进一步优化）

**当前已实现**：
- ✅ 多阶段构建（base → builder → production）
- ✅ 依赖分离

**可进一步优化**：
- 添加依赖层缓存
- 优化文件复制顺序

## 📝 具体修改步骤

### 步骤1: 修改 Dockerfile.prod

1. **分离代码复制**：
   - 将 `COPY . /app/` 拆分为多个 COPY 指令
   - 按变化频率排序：配置文件 → 源代码

2. **优化 .dockerignore**：
   - 确保排除不必要的文件
   - 减少构建上下文大小

### 步骤2: 修改 Dockerfile.frontend

1. **分离源代码复制**：
   - 只复制构建所需的文件
   - 排除 `node_modules`、`dist` 等

### 步骤3: 启用 BuildKit（可选）

在构建脚本中添加：

```powershell
# PowerShell
$env:DOCKER_BUILDKIT=1
docker build ...

# Bash
export DOCKER_BUILDKIT=1
docker build ...
```

### 步骤4: 更新构建脚本

在 `build_prod_only.ps1` 和 `build_prod_only.sh` 中启用 BuildKit：

```powershell
# PowerShell
$env:DOCKER_BUILDKIT=1
docker build ...
```

## 🚀 预期效果

### 优化前
- **代码变化时**：需要重新安装所有依赖，构建时间：~10-15分钟
- **依赖变化时**：需要重新安装依赖，构建时间：~8-12分钟
- **仅代码变化**：仍需要重新安装依赖（因为层失效）

### 优化后
- **代码变化时**：只重新复制代码，构建时间：~1-2分钟 ⚡
- **依赖变化时**：重新安装依赖，构建时间：~8-12分钟
- **仅代码变化**：充分利用缓存，构建时间：~1-2分钟 ⚡

**性能提升**：代码变化时的构建速度提升 **5-10倍**

## 📋 实施检查清单

- [ ] 修改 `Dockerfile.prod`，分离代码复制
- [ ] 修改 `Dockerfile.frontend`，优化文件复制
- [ ] 更新 `.dockerignore`（如需要）
- [ ] 更新构建脚本，启用 BuildKit
- [ ] 测试增量构建效果
- [ ] 验证构建结果正确性
- [ ] 更新文档说明

## 🔍 验证方法

### 测试增量构建

```powershell
# 1. 首次构建（完整构建）
.\scripts\build_prod_only.ps1 20251201

# 2. 修改代码（不修改依赖）
# 例如：修改 src/api/routers/cameras.py

# 3. 再次构建（应该只重新构建代码层）
.\scripts\build_prod_only.ps1 20251201

# 4. 查看构建日志，确认使用了缓存
# 应该看到：CACHED [stage-3 5/7] COPY --chown=appuser:appuser config/ /app/config/
```

### 检查缓存使用情况

```powershell
# 查看构建缓存
docker system df -v

# 查看镜像层
docker history pepgmp-backend:20251201
```

## ⚠️ 注意事项

1. **文件依赖**：确保复制的文件顺序正确，避免运行时找不到文件
2. **权限问题**：确保 `--chown` 参数正确设置
3. **构建上下文**：`.dockerignore` 配置正确，减少构建上下文大小
4. **测试验证**：每次修改后都要测试构建和运行

## 📚 参考资源

- [Docker 最佳实践 - 层缓存](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#leverage-build-cache)
- [BuildKit 缓存挂载](https://docs.docker.com/build/cache/backends/)
- [多阶段构建优化](https://docs.docker.com/develop/develop-images/multistage-build/)


