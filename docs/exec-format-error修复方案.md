# exec format error 修复方案

## 📋 问题描述

API 容器启动失败，错误信息：
```
exec /app/docker-entrypoint.sh: exec format error
```

## 🔍 问题原因

`exec format error` 通常表示：

1. **架构不匹配**：镜像架构与运行环境架构不一致
   - macOS (ARM64/M1) 构建的镜像在 x86_64 Ubuntu 上运行
   - 或反之

2. **脚本格式问题**：脚本文件可能有格式问题（虽然可能性较小）

3. **文件损坏**：镜像中的脚本文件可能损坏

---

## ✅ 解决方案

### 方案 1: 检查并修复架构问题（最可能）

#### 步骤 1: 检查镜像架构

```bash
# 在 Ubuntu 服务器上检查镜像架构
docker inspect pepgmp-backend:20251212 | grep -i arch

# 或使用 manifest
docker manifest inspect pepgmp-backend:20251212
```

#### 步骤 2: 检查运行环境架构

```bash
# 在 Ubuntu 服务器上
uname -m
# 应该显示: x86_64 或 aarch64

# 检查 Docker 架构
docker version
```

#### 步骤 3: 重新构建镜像（在正确的架构上）

**如果是在 macOS (ARM) 上构建，需要在 x86_64 上重新构建：**

```bash
# 在 macOS 上，使用 buildx 构建多架构镜像
docker buildx create --use --name multiarch
docker buildx build --platform linux/amd64 -f Dockerfile.prod -t pepgmp-backend:20251212 --load .
```

**或者直接在 Ubuntu 服务器上构建：**

```bash
# 在 Ubuntu 服务器上
cd ~/projects/PEPGMP
bash scripts/build_prod_only.sh 20251212
```

---

### 方案 2: 修复脚本格式问题

#### 检查脚本换行符

```bash
# 在开发机器上检查
cd /Users/zhou/Code/PEPGMP
file scripts/docker-entrypoint.sh

# 检查是否有 Windows 换行符
cat -A scripts/docker-entrypoint.sh | head -5
# 如果看到 ^M$，说明有 Windows 换行符
```

#### 修复换行符（如果需要）

```bash
# 转换为 Unix 格式
dos2unix scripts/docker-entrypoint.sh

# 或使用 sed
sed -i 's/\r$//' scripts/docker-entrypoint.sh
```

---

### 方案 3: 临时解决方案 - 直接使用命令启动

如果无法立即修复镜像，可以临时修改 docker-compose 配置：

```bash
cd ~/projects/PEPGMP

# 备份配置
cp docker-compose.prod.yml docker-compose.prod.yml.backup

# 编辑 docker-compose.prod.yml，找到 api 服务
# 临时修改 entrypoint 和 command
```

**临时修改示例**（不推荐长期使用）：

```yaml
api:
  # 注释掉 entrypoint
  # entrypoint: ["/app/docker-entrypoint.sh"]

  # 直接使用命令
  command: >
    sh -c "
      echo 'Waiting for database...' &&
      sleep 10 &&
      gunicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
    "
```

---

### 方案 4: 在 Ubuntu 服务器上重新构建镜像（推荐）

**最可靠的解决方案**：在 Ubuntu 服务器上直接构建镜像

```bash
# 在 Ubuntu 服务器上
cd ~/projects/PEPGMP

# 1. 确保有源代码（如果还没有）
# 如果代码已通过 rsync 传输，应该已经有了

# 2. 构建镜像
bash scripts/build_prod_only.sh 20251212

# 3. 验证镜像
docker images | grep pepgmp-backend

# 4. 重新启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d api
```

---

## 🚀 快速修复步骤

### 推荐方案：在 Ubuntu 上重新构建

```bash
# 在 Ubuntu 服务器上执行

cd ~/projects/PEPGMP

# 1. 检查当前镜像架构
docker inspect pepgmp-backend:20251212 --format '{{.Architecture}}' 2>/dev/null || echo "无法获取架构"

# 2. 检查系统架构
uname -m

# 3. 如果架构不匹配，重新构建
# 确保有源代码和 Dockerfile
ls -la Dockerfile.prod

# 4. 构建镜像（在正确的架构上）
docker build -f Dockerfile.prod -t pepgmp-backend:20251212 .

# 5. 重新启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d api

# 6. 查看日志
docker logs -f pepgmp-api-prod
```

---

## 🔍 诊断命令

```bash
# 在 Ubuntu 服务器上执行

echo "=== 架构诊断 ==="
echo ""
echo "1. 系统架构:"
uname -m
echo ""
echo "2. Docker 信息:"
docker version --format 'Server: {{.Server.Version}} ({{.Server.Arch}})' 2>/dev/null
echo ""
echo "3. 镜像架构:"
docker inspect pepgmp-backend:20251212 --format 'Architecture: {{.Architecture}}' 2>/dev/null || echo "镜像不存在或无法检查"
echo ""
echo "4. 镜像详细信息:"
docker inspect pepgmp-backend:20251212 | grep -E "Architecture|Os" | head -5
echo ""
echo "5. 检查 entrypoint 脚本:"
docker run --rm pepgmp-backend:20251212 ls -la /app/docker-entrypoint.sh 2>&1 | head -5
```

---

## 📝 根本解决方案

### 在 macOS 上构建时指定平台

```bash
# 在 macOS 开发机器上
cd /Users/zhou/Code/PEPGMP

# 使用 buildx 构建 Linux amd64 镜像
docker buildx create --use --name multiarch 2>/dev/null || true
docker buildx build --platform linux/amd64 -f Dockerfile.prod -t pepgmp-backend:20251212 --load .
```

### 修改构建脚本支持多架构

可以在 `scripts/build_prod_only.sh` 中添加平台参数：

```bash
# 添加平台参数
PLATFORM="${PLATFORM:-linux/amd64}"

# 构建时指定平台
docker build --platform $PLATFORM -f Dockerfile.prod -t pepgmp-backend:$VERSION_TAG .
```

---

## ✅ 验证修复

修复后验证：

```bash
# 1. 检查容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 2. 查看日志（应该不再有 exec format error）
docker logs pepgmp-api-prod --tail 50

# 3. 测试健康检查
curl http://localhost:8000/api/v1/monitoring/health
```

---

## 📚 相关文档

- [API 容器重启故障排查](./API容器重启故障排查.md)
- [Docker 多架构构建指南](https://docs.docker.com/build/building/multi-platform/)
