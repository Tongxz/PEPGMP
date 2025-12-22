# Registry 部署方案（网络过渡阶段）

## 📋 网络环境说明

- **Registry 服务器**: `11.25.125.115:5000`
- **当前状态**: Registry 和生产硬件不在同一网络
- **未来状态**: 生产硬件部署后会在同一网络内

---

## 🎯 两阶段部署方案

### 阶段 1: 当前网络隔离阶段

**情况**: Registry 和生产硬件不在同一网络

**推荐方案**:
1. **开发 → Registry**: 在开发机器上构建并推送到 Registry（如果开发机器能访问 Registry）
2. **Registry → 生产**: 暂时使用 tar 传输方案（因为网络隔离）

或者：

3. **开发 → 生产**: 直接使用 tar 传输方案（最简单）

### 阶段 2: 同一网络后（未来）

**情况**: 生产硬件接入后，Registry 和生产在同一网络

**推荐方案**: 完全使用 Registry 方案

---

## 🔧 阶段 1: 当前部署方案

### 方案 A: 混合方案（推荐用于过渡）

**思路**:
- 镜像推送到 Registry（作为版本库）
- 生产环境暂时使用 tar 传输（因为网络隔离）

**优点**:
- ✅ 镜像已存储在 Registry，后续切换方便
- ✅ 版本管理清晰
- ✅ 未来网络打通后，生产环境可以直接从 Registry 拉取

#### 步骤

**1. 开发机器构建并推送到 Registry**

```bash
#!/bin/bash
# 部署脚本：推送到Registry + tar传输到生产（过渡方案）

set -e

# --- 配置 ---
REGISTRY="11.25.125.115:5000"          # Registry地址
IMAGE_NAME="pepgmp-backend"
TAG=$(date +%Y%m%d-%H%M)
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

# 生产服务器（暂时无法访问Registry）
PRODUCTION_IP="192.168.1.100"          # 生产服务器IP（请替换）
PRODUCTION_USER="ubuntu"

echo "========================================================================="
echo "                    混合部署方案（过渡阶段）"
echo "========================================================================="
echo "Registry: $REGISTRY"
echo "镜像: $FULL_IMAGE"
echo "生产服务器: $PRODUCTION_IP"
echo ""

# 步骤1: 构建镜像
echo "[1/4] 构建镜像..."
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    export DOCKER_BUILDKIT=1
    docker buildx build --platform linux/amd64 -f Dockerfile.prod -t $FULL_IMAGE --load .
else
    export DOCKER_BUILDKIT=1
    docker build -f Dockerfile.prod -t $FULL_IMAGE .
fi

# 步骤2: 推送到Registry（作为版本库）
echo ""
echo "[2/4] 推送到Registry（版本库）..."
docker push $FULL_IMAGE
echo "✓ 镜像已推送到Registry: $FULL_IMAGE"

# 步骤3: 导出为tar文件（用于生产服务器）
echo ""
echo "[3/4] 导出镜像为tar文件（用于生产服务器）..."
TAR_FILE="/tmp/pepgmp-backend-$TAG.tar.gz"
docker save $FULL_IMAGE | gzip > $TAR_FILE
echo "✓ 镜像已导出: $TAR_FILE"
ls -lh $TAR_FILE

# 步骤4: 传输到生产服务器
echo ""
echo "[4/4] 传输到生产服务器..."
scp $TAR_FILE $PRODUCTION_USER@$PRODUCTION_IP:/tmp/

# 步骤5: 在生产服务器导入并部署
echo ""
echo "[5/5] 在生产服务器部署..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    cd /home/ubuntu/projects/PEPGMP

    # 导入镜像
    echo "导入镜像..."
    docker load < /tmp/pepgmp-backend-$TAG.tar.gz

    # 标签为本地镜像（因为无法访问Registry）
    docker tag $FULL_IMAGE pepgmp-backend:$TAG

    # 更新版本号（使用本地镜像格式）
    if grep -q "^IMAGE_REGISTRY=" .env.production; then
        sed -i 's|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=|' .env.production
    fi
    if grep -q "^IMAGE_TAG=" .env.production; then
        sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$TAG|" .env.production
    else
        echo "IMAGE_TAG=$TAG" >> .env.production
    fi

    # 重启服务
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api

    # 清理临时文件
    rm -f /tmp/pepgmp-backend-$TAG.tar.gz

    echo "✓ 部署完成"
    docker compose -f docker-compose.prod.yml ps api
EOF

# 清理本地临时文件
rm -f $TAR_FILE

echo ""
echo "========================================================================="
echo "部署完成！"
echo "========================================================================="
echo "Registry镜像: $FULL_IMAGE"
echo "本地镜像标签: pepgmp-backend:$TAG"
echo ""
echo "注意: 当生产硬件接入同一网络后，可以切换到Registry方案"
echo ""
```

### 方案 B: 纯 tar 传输（当前最简单）

如果开发机器也无法访问 Registry，使用纯 tar 传输方案（参考 `COMPLETE_DEPLOYMENT_GUIDE.md` 中的方案）

---

## 🚀 阶段 2: 同一网络后的方案

### 完整 Registry 部署方案

**前提条件**:
1. ✅ 生产硬件已接入网络，可以访问 `11.25.125.115:5000`
2. ✅ 生产服务器已配置信任 Registry（HTTP需要）

#### 步骤 1: 修改 docker-compose.prod.yml 支持 Registry

```yaml
# docker-compose.prod.yml
services:
  api:
    # 支持 Registry: ${IMAGE_REGISTRY:-} 如果未设置则为空
    image: ${IMAGE_REGISTRY:-}pepgmp-backend:${IMAGE_TAG:-latest}
    # ... 其他配置
```

#### 步骤 2: 生产服务器配置 Docker 信任 Registry

```bash
# 在生产服务器上执行
sudo mkdir -p /etc/docker

# 如果使用HTTP Registry，需要配置为insecure-registries
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": ["11.25.125.115:5000"]
}
EOF

# 重启Docker
sudo systemctl restart docker

# 验证
docker info | grep -A 5 "Insecure Registries"
```

#### 步骤 3: 配置 .env.production

```bash
# 在生产服务器上
cd /home/ubuntu/projects/PEPGMP

# 更新配置，使用Registry
sed -i 's|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=11.25.125.115:5433/|' .env.production
```

#### 步骤 4: 使用 Registry 部署脚本

```bash
#!/bin/bash
# Registry 部署脚本（同一网络后使用）

set -e

# --- 配置 ---
REGISTRY="11.25.125.115:5000"          # Registry地址
IMAGE_NAME="pepgmp-backend"
TAG="${1:-$(date +%Y%m%d-%H%M)}"
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

PRODUCTION_IP="${2:-192.168.1.100}"    # 生产服务器IP
PRODUCTION_USER="ubuntu"
DEPLOY_DIR="/home/ubuntu/projects/PEPGMP"

echo "========================================================================="
echo "                    Registry 部署（同一网络）"
echo "========================================================================="
echo "Registry: $REGISTRY"
echo "镜像: $FULL_IMAGE"
echo "生产服务器: $PRODUCTION_IP"
echo ""

# 1. 构建镜像
echo "[1/4] 构建镜像..."
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    export DOCKER_BUILDKIT=1
    docker buildx build --platform linux/amd64 -f Dockerfile.prod -t $FULL_IMAGE --load .
else
    export DOCKER_BUILDKIT=1
    docker build -f Dockerfile.prod -t $FULL_IMAGE .
fi

# 2. 推送到Registry
echo ""
echo "[2/4] 推送到Registry..."
docker push $FULL_IMAGE

# 3. 在生产服务器拉取并部署
echo ""
echo "[3/4] 在生产服务器拉取并部署..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    cd $DEPLOY_DIR

    # 更新配置
    if grep -q "^IMAGE_REGISTRY=" .env.production; then
        sed -i 's|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=$REGISTRY/|' .env.production
    else
        echo "IMAGE_REGISTRY=$REGISTRY/" >> .env.production
    fi

    sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$TAG|" .env.production

    # 拉取镜像
    docker compose -f docker-compose.prod.yml --env-file .env.production pull api

    # 更新服务
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api

    # 健康检查
    sleep 10
    curl -sf http://localhost/api/v1/monitoring/health && echo "✓ 健康检查通过"
EOF

echo ""
echo "========================================================================="
echo "部署完成！"
echo "========================================================================="
```

---

## 📊 方案对比

| 阶段 | 方案 | 优点 | 缺点 |
|------|------|------|------|
| **阶段1** | 混合方案（推送到Registry + tar传输） | 镜像已存储，后续切换方便 | 需要两次操作 |
| **阶段1** | 纯tar传输 | 最简单直接 | 未来需要重新部署到Registry |
| **阶段2** | 纯Registry | 快速、自动化、版本管理好 | 需要网络打通 |

---

## 🔄 从阶段1切换到阶段2

### 切换步骤

当生产硬件接入同一网络后：

**1. 验证网络连通性**

```bash
# 在生产服务器上测试
curl http://11.25.125.115:5000/v2/_catalog

# 测试拉取镜像
docker pull 11.25.125.115:5000/pepgmp-backend:20251215-1430
```

**2. 配置生产服务器**

```bash
# 配置Docker信任Registry
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "insecure-registries": ["11.25.125.115:5000"]
}
EOF

sudo systemctl restart docker
```

**3. 更新 .env.production**

```bash
cd /home/ubuntu/projects/PEPGMP

# 从本地镜像切换到Registry
sed -i 's|^IMAGE_REGISTRY=.*|IMAGE_REGISTRY=11.25.125.115:5433/|' .env.production

# 验证配置
cat .env.production | grep IMAGE_REGISTRY
```

**4. 测试部署**

```bash
# 拉取并启动（使用Registry镜像）
docker compose -f docker-compose.prod.yml --env-file .env.production pull api
docker compose -f docker-compose.prod.yml --env-file .env.production up -d api
```

---

## ⚠️ 注意事项

### 1. Registry 端口确认

请确认 Registry 的端口号：
- 标准端口: `5000`
- 如果不同，请修改脚本中的端口

### 2. HTTP vs HTTPS

- **HTTP Registry**: 需要配置 `insecure-registries`
- **HTTPS Registry**: 需要配置 TLS 证书

### 3. 网络访问

**当前阶段**:
- 如果开发机器可以访问 Registry（11.25.125.115），可以使用混合方案
- 如果开发机器也无法访问，使用纯 tar 传输

**未来阶段**:
- 生产服务器需要能访问 Registry（11.25.125.115:5000）

---

## 🎯 推荐流程

### 当前阶段（网络隔离）

```bash
# 使用混合方案：推送到Registry + tar传输
bash deploy_mixed.sh  # 需要创建此脚本
```

### 未来阶段（同一网络）

```bash
# 使用纯Registry方案
bash deploy_via_registry.sh 11.25.125.115:5000 20251215-1430 192.168.1.100
```

---

## 📝 总结

1. **当前**: 使用混合方案或纯 tar 传输
2. **未来**: 切换到纯 Registry 方案
3. **切换**: 只需修改 `.env.production` 中的 `IMAGE_REGISTRY` 配置

**关键点**:
- Registry 已搭建在 `11.25.125.115:5000`
- 当前网络隔离，暂时用 tar 传输
- 未来网络打通后，无缝切换到 Registry
