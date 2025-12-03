# 方案 B 部署脚本更新说明

## 更新概述

已更新 `scripts/prepare_minimal_deploy.sh` 脚本，使其完全适配方案 B（单一 Nginx 架构）。

## 主要更新内容

### 1. 前端静态文件检查和复制

**位置**：第 484-578 行

**更新内容**：
- ✅ 添加了前端静态文件的检查和复制逻辑
- ✅ 自动检测 `frontend/dist` 目录
- ✅ 如果不存在，尝试从前端镜像中提取
- ✅ 复制到部署目录 `$DEPLOY_DIR/frontend/dist`

**关键代码**：
```bash
# Check and prepare frontend static files (Scheme B requirement)
print_step "Checking frontend static files (Scheme B)"

# 检查项目根目录中的 frontend/dist
# 如果不存在，尝试从镜像中提取
# 复制到部署目录
```

### 2. Nginx 配置更新

**位置**：第 268-482 行

**更新内容**：
- ✅ 更新 nginx 配置生成逻辑，使用方案 B 配置
- ✅ 移除 `upstream frontend_backend`
- ✅ 添加 `root /usr/share/nginx/html` 配置
- ✅ 添加 Vue Router history 模式支持
- ✅ 添加静态资源缓存配置
- ✅ 添加健康检查端点

**关键代码**：
```bash
# Scheme B: Single Nginx architecture - no frontend upstream needed
# Static files are served directly from volume mount ./frontend/dist
```

### 3. 架构验证

**位置**：第 709-730 行

**更新内容**：
- ✅ 添加方案 B 架构验证逻辑
- ✅ 检查 nginx 配置是否符合方案 B
- ✅ 检查 docker-compose 是否有正确的 volume 挂载
- ✅ 检查前端服务配置

**验证项**：
1. Nginx 配置包含 `root /usr/share/nginx/html`
2. Nginx 配置不包含 `upstream frontend_backend`
3. Docker Compose 包含 `frontend/dist:/usr/share/nginx/html:ro` volume 挂载
4. 前端服务配置为 `restart: "no"`（可选）

### 4. 部署总结更新

**位置**：第 777-791 行

**更新内容**：
- ✅ 添加前端静态文件状态显示
- ✅ 显示文件数量和 index.html 存在性
- ✅ 如果缺失，显示警告信息

**显示内容**：
```
✓ frontend/dist/ (frontend static files) - X files
  → index.html exists
```

### 5. 下一步指引更新

**位置**：第 796-831 行

**更新内容**：
- ✅ 添加前端静态文件验证步骤
- ✅ 添加测试命令（健康检查、前端、API）
- ✅ 更新步骤编号

**新增步骤**：
```
2. Verify frontend static files (Scheme B requirement)
   ✓ Frontend static files ready
   OR
   ⚠ Frontend static files missing!
   → Build frontend: docker build -f Dockerfile.frontend ...
   → Extract files: docker create --name temp ...

6. Test deployment (Scheme B):
   curl http://localhost/health
   curl http://localhost/
   curl http://localhost/api/v1/monitoring/health
```

### 6. 架构说明

**位置**：第 833-840 行

**更新内容**：
- ✅ 添加方案 B 架构说明
- ✅ 说明 Nginx 直接服务静态文件
- ✅ 说明前端容器的作用（仅用于构建）
- ✅ 说明静态文件必须在部署前构建

**说明内容**：
```
Architecture: Scheme B (Single Nginx)
  • Nginx serves static files directly from ./frontend/dist
  • Frontend container is optional (only for building static files)
  • Static files must be built before deployment
```

## 脚本功能完整性

### ✅ 已实现的功能

1. **前端静态文件处理**
   - 自动检测 `frontend/dist` 目录
   - 从镜像中提取静态文件（如果不存在）
   - 复制到部署目录
   - 验证文件完整性

2. **Nginx 配置生成**
   - 根据前端镜像存在性生成不同配置
   - 方案 B 配置（单一 Nginx）
   - API 专用配置（无前端）

3. **架构验证**
   - 验证 Docker Compose 配置
   - 验证 Nginx 配置
   - 验证前端静态文件

4. **部署指引**
   - 清晰的步骤说明
   - 测试命令
   - 故障排查提示

### 📋 脚本使用流程

1. **运行脚本**
   ```bash
   bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt
   ```

2. **脚本自动执行**
   - 检查前端镜像
   - 生成/更新 nginx 配置
   - 检查/提取/复制前端静态文件
   - 复制其他必要文件
   - 验证配置

3. **用户操作**
   - 根据提示生成 `.env.production`（如果需要）
   - 确保前端静态文件已构建
   - 启动服务

## 与方案 B 的完全集成

### ✅ 架构一致性

- **Nginx 配置**：完全符合方案 B（单一 Nginx，直接服务静态文件）
- **Docker Compose**：支持方案 B 的 volume 挂载配置
- **前端处理**：自动处理前端静态文件的提取和复制

### ✅ 工作流程一致性

1. **构建阶段**：前端镜像构建（脚本可以提取）
2. **部署阶段**：静态文件复制到部署目录
3. **运行阶段**：Nginx 直接挂载静态文件

### ✅ 文档一致性

- 脚本输出包含方案 B 架构说明
- 提示信息符合方案 B 要求
- 测试命令符合方案 B 架构

## 总结

`prepare_minimal_deploy.sh` 脚本已完全更新，与方案 B 架构完全集成：

1. ✅ **自动处理前端静态文件**：检测、提取、复制
2. ✅ **生成正确的 Nginx 配置**：方案 B 单一 Nginx 配置
3. ✅ **验证架构一致性**：确保配置符合方案 B
4. ✅ **提供清晰的指引**：包含架构说明和测试命令

脚本现在完全符合软件工程要求，与项目架构保持一致，不再有独立的部署脚本。

