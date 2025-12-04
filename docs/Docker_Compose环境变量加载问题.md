# Docker Compose 环境变量加载问题

## 📋 问题现象

执行 `docker compose -f docker-compose.prod.yml up -d` 时：

```
WARN[0000] The "DATABASE_PASSWORD" variable is not set. Defaulting to a blank string.
WARN[0000] The "REDIS_PASSWORD" variable is not set. Defaulting to a blank string.
```

**结果**：
- 数据库容器启动失败：`Error: Database is uninitialized and superuser password is not specified.`
- Redis 容器启动失败：`FATAL CONFIG FILE ERROR`

---

## 🔍 根本原因

**Docker Compose 不会自动加载 `.env.production` 文件**

虽然 `docker-compose.prod.yml` 中配置了：
```yaml
env_file:
  - .env.production
```

但 `env_file` 只是将文件内容加载到**容器内部**的环境变量，**不会**用于 Docker Compose 自身的变量替换（如 `${DATABASE_PASSWORD}`）。

**Docker Compose 变量替换规则**：
1. 从当前 shell 环境变量读取
2. 从 `.env` 文件读取（**不是** `.env.production`）
3. 如果找不到，使用空字符串

---

## ✅ 解决方案

### 方案 1：使用 `--env-file` 参数（推荐）

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**优点**：
- ✅ 显式指定环境文件
- ✅ 不需要修改配置文件
- ✅ 清晰明确

**缺点**：
- ⚠️ 每次都需要指定 `--env-file` 参数

### 方案 2：创建 `.env` 文件（或符号链接）

```bash
# 创建符号链接
ln -s .env.production .env

# 或复制文件
cp .env.production .env
```

**优点**：
- ✅ Docker Compose 会自动加载 `.env` 文件
- ✅ 不需要每次指定参数

**缺点**：
- ⚠️ 需要维护两个文件（或符号链接）
- ⚠️ 可能混淆开发和生产环境配置

### 方案 3：在启动前导出环境变量

```bash
# 导出环境变量
export $(grep -v '^#' .env.production | xargs)

# 启动服务
docker compose -f docker-compose.prod.yml up -d
```

**优点**：
- ✅ 环境变量在 shell 中可用
- ✅ 可以用于其他脚本

**缺点**：
- ⚠️ 需要每次导出
- ⚠️ 可能污染 shell 环境

---

## 🎯 推荐方案

**推荐使用方案 1**：使用 `--env-file` 参数

**原因**：
1. 明确指定环境文件，不会混淆
2. 不需要修改文件系统
3. 适合 CI/CD 自动化

**使用示例**：

```bash
# 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 停止服务
docker compose -f docker-compose.prod.yml --env-file .env.production down

# 查看日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 查看状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

---

## 📝 更新部署脚本

如果使用部署脚本，需要更新脚本以包含 `--env-file` 参数：

```bash
# 在 deploy_prod_macos.sh 或其他部署脚本中
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 🔧 验证修复

修复后验证：

```bash
# 1. 检查配置是否正确加载
docker compose -f docker-compose.prod.yml --env-file .env.production config | grep POSTGRES_PASSWORD
# 应该显示实际的密码值，而不是空字符串

# 2. 检查容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps
# 所有容器应该是 healthy 或 running

# 3. 测试数据库连接
docker exec -e PGPASSWORD='<密码>' \
  pepgmp-api-prod psql -h database -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"
```

---

## 📚 相关文档

- Docker Compose 环境变量文档：https://docs.docker.com/compose/environment-variables/
- `.env` 文件说明：https://docs.docker.com/compose/env-file/

---

**问题发现日期**: 2025-12-04
**状态**: ✅ 已解决（使用 `--env-file` 参数）
