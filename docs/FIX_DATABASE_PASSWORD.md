# 修复数据库密码配置问题

## 问题

`docker-compose.prod.yml` 中的数据库和 Redis 服务缺少 `env_file` 配置，导致无法读取 `.env.production` 中的密码。

## 已修复

已更新 `docker-compose.prod.yml`：
- ✅ 数据库服务添加了 `env_file: - .env.production`
- ✅ Redis 服务添加了 `env_file: - .env.production`

## 验证修复

### 步骤 1: 验证配置

```bash
cd ~/projects/Pyt

# 检查数据库服务配置
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -A 10 "database:" | grep -E 'POSTGRES_PASSWORD|env_file'

# 应该看到：
# POSTGRES_PASSWORD: Z-SB--VS8ha6gWjkZsSalJBn3J9aI8yGL7UkgplQi9w

# 检查 Redis 服务配置
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -A 10 "redis:" | grep -E 'REDIS_PASSWORD|requirepass|env_file'
```

### 步骤 2: 重新部署

```bash
cd ~/projects/Pyt

# 1. 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 2. 如果需要重置数据库（可选，会删除数据）
# docker volume rm pyt_postgres_prod_data

# 3. 重新启动所有服务
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 4. 等待服务启动（60-90秒）
sleep 90

# 5. 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 6. 检查数据库日志
docker-compose -f docker-compose.prod.yml logs database | tail -30
```

### 步骤 3: 验证数据库连接

```bash
# 检查数据库容器健康状态
docker inspect pepgmp-postgres-prod --format='{{.State.Health.Status}}'

# 应该显示：healthy

# 测试数据库连接
docker exec pepgmp-postgres-prod pg_isready -U pepgmp_prod
```

## 在 1Panel 中重新部署

如果使用 1Panel：

1. **停止当前服务**
   - 在 1Panel 中停止 Compose 项目

2. **更新 Compose 文件**
   - 确保 `docker-compose.prod.yml` 已更新（包含 `env_file` 配置）
   - 如果使用 `prepare_minimal_deploy.sh`，重新运行脚本更新文件

3. **重新启动服务**
   - 在 1Panel 中启动 Compose 项目
   - 等待 60-90 秒让服务启动

4. **检查服务状态**
   - 所有服务应该显示为"运行中"或"健康"

## 更新部署目录中的文件

如果部署目录中的 `docker-compose.prod.yml` 是旧版本，需要更新：

```bash
# 方法1: 重新运行准备脚本（推荐）
cd /mnt/f/code/PythonCode/Pyt
bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes

# 方法2: 手动复制更新后的文件
cp /mnt/f/code/PythonCode/Pyt/docker-compose.prod.yml ~/projects/Pyt/docker-compose.prod.yml
```

## 验证清单

- [ ] `docker-compose.prod.yml` 中数据库服务有 `env_file: - .env.production`
- [ ] `docker-compose.prod.yml` 中 Redis 服务有 `env_file: - .env.production`
- [ ] 配置验证显示正确的密码（不是空字符串）
- [ ] 数据库容器健康状态为 `healthy`
- [ ] 所有服务启动成功

