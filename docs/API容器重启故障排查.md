# API 容器重启故障排查

## 📋 问题描述

API 容器 `pepgmp-api-prod` 持续重启，退出码 255：
```
STATUS: Restarting (255) 47 seconds ago
```

---

## 🔍 故障排查步骤

### 步骤 1: 查看 API 容器日志

```bash
# 查看最近的日志
docker logs pepgmp-api-prod --tail 100

# 查看所有日志
docker logs pepgmp-api-prod

# 实时查看日志
docker logs -f pepgmp-api-prod
```

**重点关注**：
- 启动错误信息
- 数据库连接错误
- Redis 连接错误
- 配置文件错误
- 依赖缺失错误

---

### 步骤 2: 检查容器启动命令

```bash
# 查看容器的启动命令和配置
docker inspect pepgmp-api-prod | grep -A 20 "Args\|Cmd\|Env"

# 或使用 docker compose
cd ~/projects/PEPGMP
docker compose -f docker-compose.prod.yml --env-file .env.production config | grep -A 30 "api:"
```

---

### 步骤 3: 检查环境变量配置

```bash
cd ~/projects/PEPGMP

# 检查 .env.production 文件
cat .env.production

# 检查关键配置
grep -E "DATABASE_URL|REDIS_URL|SECRET_KEY|IMAGE_TAG" .env.production
```

---

### 步骤 4: 检查数据库和 Redis 连接

```bash
# 检查数据库容器是否健康
docker ps | grep postgres

# 测试数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"

# 检查 Redis 连接
docker exec pepgmp-redis-prod redis-cli ping
```

---

### 步骤 5: 手动运行 API 容器测试

```bash
cd ~/projects/PEPGMP

# 使用相同的配置手动运行容器
docker run --rm -it \
  --env-file .env.production \
  --network pepgmp-prod-network \
  pepgmp-backend:20251212 \
  /app/docker-entrypoint.sh

# 这会显示详细的启动信息
```

---

## 🚨 常见原因和解决方案

### 原因 1: 数据库连接失败

**错误信息**：
```
ConnectionError: could not connect to server
```

**解决方案**：
```bash
# 检查 .env.production 中的数据库配置
grep DATABASE_URL .env.production

# 确保配置正确：
# DATABASE_URL=postgresql://pepgmp_prod:password@pepgmp-postgres-prod:5432/pepgmp_production

# 测试数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"
```

### 原因 2: Redis 连接失败

**错误信息**：
```
Connection refused
Redis connection failed
```

**解决方案**：
```bash
# 检查 Redis 配置
grep REDIS_URL .env.production

# 测试 Redis 连接
docker exec pepgmp-redis-prod redis-cli ping

# 应该返回: PONG
```

### 原因 3: 缺少必要的环境变量

**错误信息**：
```
Required environment variable not set
```

**解决方案**：
```bash
# 检查必要的环境变量
cd ~/projects/PEPGMP

# 确保以下变量已设置：
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY
# - IMAGE_TAG

grep -E "DATABASE_URL|REDIS_URL|SECRET_KEY|IMAGE_TAG" .env.production
```

### 原因 4: 应用启动脚本错误

**错误信息**：
```
/bin/sh: /app/docker-entrypoint.sh: not found
```

**解决方案**：
```bash
# 检查镜像中是否有入口脚本
docker run --rm pepgmp-backend:20251212 ls -la /app/docker-entrypoint.sh

# 如果不存在，检查 Dockerfile.prod 是否正确复制了脚本
```

### 原因 5: Python 依赖缺失或错误

**错误信息**：
```
ModuleNotFoundError: No module named 'xxx'
ImportError
```

**解决方案**：
```bash
# 检查镜像是否正确构建
docker images | grep pepgmp-backend

# 如果怀疑镜像有问题，重新构建
# 在开发机器上：
# bash scripts/build_prod_only.sh 20251212
```

### 原因 6: 端口冲突

**错误信息**：
```
Address already in use
Port 8000 is already in use
```

**解决方案**：
```bash
# 检查端口占用
sudo netstat -tulpn | grep 8000

# 或使用 ss
ss -tulpn | grep 8000

# 停止占用端口的进程或修改配置
```

---

## 🔧 快速修复脚本

```bash
#!/bin/bash
cd ~/projects/PEPGMP

echo "=== API 容器故障排查 ==="
echo ""

# 1. 查看日志
echo "[1] API 容器日志（最近 50 行）:"
echo "----------------------------------------"
docker logs pepgmp-api-prod --tail 50
echo ""

# 2. 检查环境变量
echo "[2] 检查关键环境变量:"
echo "----------------------------------------"
grep -E "DATABASE_URL|REDIS_URL|SECRET_KEY|IMAGE_TAG" .env.production
echo ""

# 3. 测试数据库连接
echo "[3] 测试数据库连接:"
echo "----------------------------------------"
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;" 2>&1
echo ""

# 4. 测试 Redis 连接
echo "[4] 测试 Redis 连接:"
echo "----------------------------------------"
docker exec pepgmp-redis-prod redis-cli ping 2>&1
echo ""

# 5. 检查容器状态
echo "[5] 容器状态:"
echo "----------------------------------------"
docker compose -f docker-compose.prod.yml --env-file .env.production ps
echo ""

echo "=== 排查完成 ==="
```

---

## 📝 诊断命令参考

### 查看完整启动日志

```bash
# 查看最近的错误日志
docker logs pepgmp-api-prod --tail 200

# 实时跟踪日志
docker logs -f pepgmp-api-prod

# 查看容器退出前的最后日志
docker logs pepgmp-api-prod 2>&1 | tail -100
```

### 进入容器调试（如果容器能短暂启动）

```bash
# 如果容器能短暂启动，可以尝试进入容器
docker exec -it pepgmp-api-prod /bin/bash

# 检查环境变量
env | grep -E "DATABASE|REDIS|SECRET"

# 检查配置文件
ls -la /app/
cat /app/.env 2>/dev/null || echo "No .env file"
```

### 检查网络连接

```bash
# 从 API 容器测试数据库连接
docker exec pepgmp-api-prod ping -c 2 pepgmp-postgres-prod

# 测试 Redis 连接
docker exec pepgmp-api-prod ping -c 2 pepgmp-redis-prod
```

---

## ✅ 建议的操作流程

1. **查看日志**：`docker logs pepgmp-api-prod --tail 100`
2. **检查环境变量**：确认 `.env.production` 配置正确
3. **测试连接**：验证数据库和 Redis 连接
4. **检查镜像**：确认镜像正确构建
5. **查看详细错误**：根据日志中的具体错误信息进行修复

---

## 🚀 快速诊断

```bash
# 一键诊断
cd ~/projects/PEPGMP

echo "=== 快速诊断 ==="
echo ""
echo "1. API 日志:"
docker logs pepgmp-api-prod --tail 50
echo ""
echo "2. 容器状态:"
docker compose -f docker-compose.prod.yml --env-file .env.production ps
echo ""
echo "3. 数据库连接:"
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;" 2>&1
echo ""
echo "4. Redis 连接:"
docker exec pepgmp-redis-prod redis-cli ping 2>&1
```

---

请先执行 `docker logs pepgmp-api-prod --tail 100` 查看详细错误信息，然后我们可以根据具体错误进行修复。
