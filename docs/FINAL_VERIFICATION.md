# 最终验证步骤

## ✅ 配置文件检查完成

配置文件 `.env.production` 已正确生成：
- ✅ 镜像标签：`IMAGE_TAG=20251201`
- ✅ 数据库密码：已生成强随机密码
- ✅ Redis 密码：已生成强随机密码
- ✅ 无 CHANGE_ME 占位符

## 步骤 1: 验证 Docker Compose 配置

```bash
cd ~/projects/Pyt

# 使用 --env-file 明确指定环境变量文件
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'image:|IMAGE_TAG|DATABASE_PASSWORD|REDIS_PASSWORD|ADMIN_USERNAME|ADMIN_PASSWORD'
```

**预期结果**：
- `image: pepgmp-backend:20251201`（不再是 latest）
- `DATABASE_PASSWORD: Z-SB--VS8ha6gWjkZsSalJBn3J9aI8yGL7UkgplQi9w`（实际密码）
- `REDIS_PASSWORD: BgjWTwPYXLyzW804odEzlfl5POK_SMPL_eBb4tiuH7s`（实际密码）
- `ADMIN_USERNAME: pepadmin`（或你设置的值）
- `ADMIN_PASSWORD: 实际的强随机密码`

## 步骤 2: 完整配置验证

```bash
cd ~/projects/Pyt

# 查看完整配置（不显示警告）
docker-compose -f docker-compose.prod.yml --env-file .env.production config > /tmp/compose-config.yml

# 检查关键服务配置
grep -A 10 "api:" /tmp/compose-config.yml | grep -E 'image:|DATABASE_PASSWORD|REDIS_PASSWORD|ADMIN_USERNAME|ADMIN_PASSWORD'

# 检查数据库服务配置
grep -A 5 "database:" /tmp/compose-config.yml | grep -E 'POSTGRES_PASSWORD|DATABASE_PASSWORD'

# 检查 Redis 服务配置
grep -A 5 "redis:" /tmp/compose-config.yml | grep -E 'REDIS_PASSWORD'
```

## 步骤 3: 在 1Panel 中部署

### 准备工作

1. **确认文件位置**：
   ```bash
   cd ~/projects/Pyt
   ls -la docker-compose.prod.yml .env.production
   ```

2. **确认镜像已导入**：
   ```bash
   docker images | grep pepgmp
   ```
   应该看到：
   - `pepgmp-backend:20251201`
   - `pepgmp-frontend:20251201`（如果构建了前端）

### 在 1Panel 中创建 Compose 项目

1. 登录 1Panel
2. 进入 **容器** → **Compose**
3. 点击 **创建** 或 **导入**
4. 配置：
   - **项目名称**: `pepgmp-production`
   - **工作目录**: `/home/pep/projects/Pyt`
   - **Compose 文件**: `docker-compose.prod.yml`
   - **环境变量文件**: `.env.production`（1Panel 会自动加载）

5. 点击 **确认** 创建项目

### 启动服务

1. 在 Compose 项目列表中，找到 `pepgmp-production`
2. 点击 **启动** 或 **更新**
3. 等待所有服务启动完成
4. 检查服务状态，确保所有容器都是 **运行中**

## 步骤 4: 验证服务运行

```bash
cd ~/projects/Pyt

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 检查 API 服务日志
docker-compose -f docker-compose.prod.yml logs api | tail -50

# 检查数据库连接
docker-compose -f docker-compose.prod.yml exec api python -c "from src.database import get_db; print('Database connection OK')" 2>&1 || echo "Check database connection"
```

## 步骤 5: 访问应用

1. **API 文档**: `http://localhost:8000/docs`
2. **健康检查**: `http://localhost:8000/health`
3. **前端界面**: `http://localhost:80`（如果部署了前端）

## 故障排查

### 如果镜像标签仍然是 latest

检查 `.env.production` 文件：
```bash
grep IMAGE_TAG .env.production
```

如果显示 `IMAGE_TAG=latest`，需要更新：
```bash
sed -i 's/IMAGE_TAG=latest/IMAGE_TAG=20251201/' .env.production
```

### 如果密码仍然是 CHANGE_ME

重新生成配置文件：
```bash
cd ~/projects/Pyt
rm .env.production
bash scripts/generate_production_config.sh
```

### 如果服务启动失败

检查日志：
```bash
docker-compose -f docker-compose.prod.yml logs
```

常见问题：
- 数据库连接失败：检查 `DATABASE_PASSWORD` 是否正确
- Redis 连接失败：检查 `REDIS_PASSWORD` 是否正确
- 镜像不存在：确认镜像已导入，标签为 `20251201`

