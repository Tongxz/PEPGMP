# 数据库容器启动失败故障排查

## 错误信息

```
ErrorContainer pepgmp-redis-prod Errordependency failed to start: container pepgmp-postgres-prod is unhealthy
```

这表明 `pepgmp-postgres-prod` 容器的健康检查失败。

## 故障排查步骤

### 步骤 1: 检查数据库容器日志

```bash
cd ~/projects/Pyt

# 查看数据库容器日志
docker-compose -f docker-compose.prod.yml logs database

# 或查看最后 50 行
docker-compose -f docker-compose.prod.yml logs database | tail -50
```

### 步骤 2: 检查数据库容器状态

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看数据库容器详细信息
docker inspect pepgmp-postgres-prod | grep -A 10 Health
```

### 步骤 3: 检查环境变量配置

```bash
cd ~/projects/Pyt

# 检查数据库密码配置
grep -E 'DATABASE_PASSWORD|POSTGRES_PASSWORD|POSTGRES_USER|POSTGRES_DB' .env.production

# 检查 Docker Compose 配置中的数据库环境变量
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -A 10 "database:"
```

### 步骤 4: 手动测试数据库连接

```bash
# 进入数据库容器
docker exec -it pepgmp-postgres-prod bash

# 在容器内测试连接
psql -U pepgmp_prod -d pepgmp_production

# 如果连接成功，输入 \q 退出
```

### 步骤 5: 检查健康检查配置

健康检查可能配置过于严格或超时时间太短。

## 常见问题和解决方案

### 问题 1: 数据库密码不匹配

**症状**: 日志显示 `password authentication failed`

**解决方案**:
```bash
cd ~/projects/Pyt

# 检查密码是否包含特殊字符需要转义
grep DATABASE_PASSWORD .env.production

# 如果密码包含特殊字符，可能需要重新生成
# 删除旧配置，重新生成
rm .env.production
bash scripts/generate_production_config.sh
```

### 问题 2: 数据库初始化失败

**症状**: 日志显示 `initdb: error` 或 `database initialization failed`

**解决方案**:
```bash
# 停止并删除数据库容器和数据卷
docker-compose -f docker-compose.prod.yml down -v

# 重新启动
docker-compose -f docker-compose.prod.yml up -d database

# 等待数据库完全启动（30-60秒）
sleep 30

# 检查数据库日志
docker-compose -f docker-compose.prod.yml logs database
```

### 问题 3: 健康检查超时

**症状**: 容器启动但健康检查一直失败

**解决方案**: 临时禁用健康检查或增加超时时间

### 问题 4: 端口冲突

**症状**: 日志显示 `port already in use`

**解决方案**:
```bash
# 检查端口占用
sudo netstat -tulpn | grep 5432

# 或使用 lsof
sudo lsof -i :5432

# 停止占用端口的进程或修改 docker-compose.prod.yml 中的端口映射
```

### 问题 5: 数据卷权限问题

**症状**: 日志显示 `permission denied` 或 `cannot create directory`

**解决方案**:
```bash
# 检查数据卷权限
docker volume inspect pyt_postgres_prod_data

# 如果需要，删除数据卷重新创建
docker-compose -f docker-compose.prod.yml down -v
docker volume rm pyt_postgres_prod_data
docker-compose -f docker-compose.prod.yml up -d database
```

## 快速修复命令

### 方法 1: 完全重置数据库

```bash
cd ~/projects/Pyt

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 删除数据卷（⚠️ 会删除所有数据）
docker-compose -f docker-compose.prod.yml down -v

# 重新启动数据库
docker-compose -f docker-compose.prod.yml up -d database

# 等待数据库启动（60秒）
echo "Waiting for database to start..."
sleep 60

# 检查数据库日志
docker-compose -f docker-compose.prod.yml logs database | tail -30

# 如果数据库正常，启动所有服务
docker-compose -f docker-compose.prod.yml up -d
```

### 方法 2: 仅重启数据库服务

```bash
cd ~/projects/Pyt

# 停止数据库服务
docker-compose -f docker-compose.prod.yml stop database

# 删除数据库容器（保留数据卷）
docker-compose -f docker-compose.prod.yml rm -f database

# 重新启动数据库
docker-compose -f docker-compose.prod.yml up -d database

# 等待启动
sleep 30

# 检查状态
docker-compose -f docker-compose.prod.yml ps database
```

## 检查清单

- [ ] 数据库容器日志没有错误
- [ ] 数据库密码配置正确（不是 CHANGE_ME）
- [ ] 数据库用户和数据库名配置正确
- [ ] 端口 5432 没有被占用
- [ ] 数据卷有正确的权限
- [ ] 健康检查通过（等待足够的时间）

## 获取详细错误信息

```bash
# 查看完整的数据库日志
docker-compose -f docker-compose.prod.yml logs database > /tmp/db-log.txt
cat /tmp/db-log.txt

# 查看容器状态
docker inspect pepgmp-postgres-prod --format='{{json .State.Health}}' | python3 -m json.tool
```

## 如果问题仍然存在

请提供以下信息以便进一步诊断：

1. 数据库容器日志（最后 50 行）
2. `.env.production` 中的数据库相关配置（隐藏密码）
3. `docker-compose.prod.yml` 中的数据库服务配置
4. 数据库容器的健康检查状态

