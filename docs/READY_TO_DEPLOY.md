# 准备部署检查清单

## ✅ 已完成的步骤

1. ✅ **镜像已导入到 WSL2**
   - `pepgmp-backend:20251201` ✓
   - `pepgmp-backend:latest` ✓

2. ✅ **配置文件已生成**
   - `.env.production` 在 `~/projects/Pyt/` ✓
   - `IMAGE_TAG=20251201` ✓

## 🔍 最终验证步骤

### 步骤 1: 验证镜像标签匹配

```bash
cd ~/projects/Pyt

# 检查配置文件中的镜像标签
grep IMAGE_TAG .env.production

# 应该显示：IMAGE_TAG=20251201
```

### 步骤 2: 验证 Docker Compose 配置

```bash
cd ~/projects/Pyt

# 验证配置（使用 --env-file 明确指定环境变量文件）
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'image:|IMAGE_TAG|DATABASE_PASSWORD|REDIS_PASSWORD'
```

**预期结果**：
- `image: pepgmp-backend:20251201`（不再是 latest）
- `DATABASE_PASSWORD: 实际的强随机密码`（不是 CHANGE_ME）
- `REDIS_PASSWORD: 实际的强随机密码`（不是 CHANGE_ME）

### 步骤 3: 检查文件完整性

```bash
cd ~/projects/Pyt

# 检查必要文件是否存在
ls -la docker-compose.prod.yml .env.production config/ models/ scripts/
```

## 🚀 在 1Panel 中部署

### 准备工作

1. **确认工作目录**：
   ```bash
   cd ~/projects/Pyt
   pwd
   # 应该显示：/home/pep/projects/Pyt
   ```

2. **确认 Compose 文件**：
   ```bash
   ls -la docker-compose.prod.yml
   ```

### 在 1Panel 中创建 Compose 项目

1. **登录 1Panel**
   - 打开浏览器访问 1Panel
   - 使用用户名和密码登录

2. **进入 Compose 管理**
   - 点击左侧菜单 **"容器"**
   - 点击 **"Compose"**

3. **创建新项目**
   - 点击 **"创建"** 或 **"新建"** 按钮
   - 填写以下信息：
     - **项目名称**: `pepgmp-production`
     - **工作目录**: `/home/pep/projects/Pyt`
     - **Compose 文件**: `docker-compose.prod.yml`
     - **环境变量文件**: `.env.production`（1Panel 会自动加载）

4. **启动服务**
   - 点击 **"启动"** 或 **"部署"** 按钮
   - 等待 60-90 秒让所有服务启动完成

5. **检查服务状态**
   - 在 Compose 项目列表中，查看服务状态
   - 所有服务应该显示为 **"运行中"** 或 **"健康"**

## 🔍 部署后验证

### 检查容器状态

```bash
cd ~/projects/Pyt

# 查看所有容器状态
docker-compose -f docker-compose.prod.yml ps

# 应该看到：
# - pepgmp-api-prod (运行中)
# - pepgmp-database-prod (运行中)
# - pepgmp-redis-prod (运行中)
```

### 检查服务日志

```bash
# API 服务日志
docker-compose -f docker-compose.prod.yml logs api | tail -50

# 数据库服务日志
docker-compose -f docker-compose.prod.yml logs database | tail -20

# Redis 服务日志
docker-compose -f docker-compose.prod.yml logs redis | tail -20
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 或访问 API 文档
# 浏览器打开：http://localhost:8000/docs
```

## ⚠️ 常见问题

### Q1: 1Panel 中找不到工作目录？

**A**: 确保使用绝对路径：
```bash
# 查看实际路径
cd ~/projects/Pyt && pwd
# 输出：/home/pep/projects/Pyt
```

在 1Panel 中使用这个完整路径。

### Q2: 服务启动失败？

**A**: 检查日志：
```bash
docker-compose -f docker-compose.prod.yml logs
```

常见原因：
- 数据库密码不匹配
- Redis 密码不匹配
- 镜像标签不正确
- 端口被占用

### Q3: 镜像标签仍然是 latest？

**A**: 确保使用了 `--env-file` 参数：
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production config
```

在 1Panel 中，确保工作目录正确，1Panel 会自动加载 `.env.production`。

### Q4: 数据库连接失败？

**A**: 检查密码是否正确：
```bash
grep DATABASE_PASSWORD .env.production
```

确保密码不是 `CHANGE_ME`，而是实际的强随机密码。

## 📋 部署检查清单

- [ ] 镜像已导入到 WSL2（`pepgmp-backend:20251201`）
- [ ] 配置文件已生成（`.env.production`）
- [ ] 镜像标签匹配（`IMAGE_TAG=20251201`）
- [ ] Docker Compose 配置验证通过
- [ ] 在 1Panel 中创建了 Compose 项目
- [ ] 所有服务启动成功
- [ ] API 健康检查通过

## 🎉 部署完成

如果所有检查都通过，恭喜！你的应用已经成功部署。

下一步：
- 访问 API 文档：`http://localhost:8000/docs`
- 使用管理员账户登录（用户名和密码在 `.env.production.credentials` 中）

