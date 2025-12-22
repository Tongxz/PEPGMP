# 生产环境部署完整指南

## 📋 部署场景分类

本指南区分两种部署场景，提供不同的部署流程。

---

## 🆕 场景 1: 首次全新部署

**适用场景**:
- 新购服务器，全新环境
- 重大版本迁移
- 灾难恢复后的重建

**包含内容**:
- ✅ 完整项目文件（config、models、scripts、nginx等）
- ✅ Docker镜像
- ✅ 数据库初始化
- ✅ 环境配置生成
- ✅ 服务器环境准备

### 首次部署流程

#### 步骤 1: 本地构建镜像

```bash
# 在开发机器（macOS）上
cd /Users/zhou/Code/PEPGMP

# 构建GPU镜像（使用日期版本号）
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 确认镜像构建成功
docker images | grep pepgmp
# 输出示例:
# pepgmp-backend    20251215    xxx    5.0GB
# pepgmp-frontend   20251215    xxx    50MB
```

#### 步骤 2: 导出镜像

```bash
# 创建镜像目录
mkdir -p docker-images

# 导出镜像（压缩以节省空间和传输时间）
docker save pepgmp-backend:$VERSION_TAG | gzip > docker-images/pepgmp-backend-$VERSION_TAG.tar.gz
docker save pepgmp-frontend:$VERSION_TAG | gzip > docker-images/pepgmp-frontend-$VERSION_TAG.tar.gz

# 确认导出成功
ls -lh docker-images/
# 预期大小: backend ~2-3GB (压缩后), frontend ~20MB
```

#### 步骤 3: 准备部署包

```bash
# 准备最小化部署包（不包含镜像）
bash scripts/prepare_minimal_deploy.sh ~/deploy-temp/$VERSION_TAG no

# 部署包包含:
# - docker-compose.prod.yml (1Panel版本，无build段)
# - config/ (配置文件)
# - models/ (AI模型，可选)
# - nginx/ (Nginx配置)
# - scripts/ (部署脚本)
# - frontend/dist/ (静态文件挂载目录)
```

#### 步骤 4: 准备生产服务器环境

**选项 A: 自动准备（推荐）**
```bash
# 远程执行环境准备脚本
bash scripts/deploy_mixed_registry.sh <生产IP> ubuntu /home/ubuntu/projects/PEPGMP

# 该脚本会:
# - 安装必要的工具（rsync等）
# - 创建部署目录
# - 设置正确的权限
```

**选项 B: 手动准备**
```bash
# SSH到生产服务器
ssh ubuntu@<生产IP>

# 创建部署目录
sudo mkdir -p /home/ubuntu/projects/PEPGMP
sudo chown ubuntu:ubuntu /home/ubuntu/projects/PEPGMP

# 安装必要工具
sudo apt update
sudo apt install -y docker.io docker-compose
```

#### 步骤 5: 传输到生产服务器

**整合传输方式（推荐）**:
```bash
PRODUCTION_IP="192.168.1.100"
PRODUCTION_USER="ubuntu"

# 传输部署包
scp -r ~/deploy-temp/$VERSION_TAG/* $PRODUCTION_USER@$PRODUCTION_IP:/home/ubuntu/projects/PEPGMP/

# 传输镜像文件
scp docker-images/pepgmp-backend-$VERSION_TAG.tar.gz $PRODUCTION_USER@$PRODUCTION_IP:/tmp/
scp docker-images/pepgmp-frontend-$VERSION_TAG.tar.gz $PRODUCTION_USER@$PRODUCTION_IP:/tmp/
```

#### 步骤 6: 生产服务器部署

```bash
# SSH到生产服务器
ssh $PRODUCTION_USER@$PRODUCTION_IP

# 进入部署目录
cd /home/ubuntu/projects/PEPGMP

# 导入Docker镜像
docker load < /tmp/pepgmp-backend-$VERSION_TAG.tar.gz
docker load < /tmp/pepgmp-frontend-$VERSION_TAG.tar.gz

# 清理临时文件
rm -f /tmp/pepgmp-*.tar.gz

# 生成生产配置
bash scripts/generate_production_config.sh

# 更新镜像版本号
bash scripts/update_image_version.sh $VERSION_TAG

# 验证配置
docker compose -f docker-compose.prod.yml --env-file .env.production config

# 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

#### 步骤 7: 验证部署

```bash
# 等待服务启动（30-60秒）
sleep 30

# 健康检查
curl http://localhost/health
curl http://localhost/api/v1/monitoring/health

# 查看容器状态
docker compose -f docker-compose.prod.yml ps

# 查看服务日志
docker compose -f docker-compose.prod.yml logs api --tail 100
```

---

## 🔄 场景 2: 增量更新部署

**适用场景**:
- 代码更新
- Bug修复
- 功能迭代
- 配置调整

**更新内容**:
- ✅ Docker镜像更新
- ⚠️ 配置文件更新（按需）
- ⚠️ 数据库迁移（按需）
- ❌ 不需要完整的models/等大文件

### 增量更新流程

#### 方案 A: 仅镜像更新（最常用）

**适用**: 代码更新，配置不变

```bash
# ========== 开发机器操作 ==========

# 1. 构建新版本镜像
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 2. 导出镜像
docker save pepgmp-backend:$VERSION_TAG | gzip > /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

# 3. 传输镜像
scp /tmp/pepgmp-backend-$VERSION_TAG.tar.gz ubuntu@<生产IP>:/tmp/

# ========== 生产服务器操作 ==========

# 4. SSH到生产
ssh ubuntu@<生产IP>

# 5. 导入新镜像
docker load < /tmp/pepgmp-backend-$VERSION_TAG.tar.gz
rm -f /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

# 6. 更新版本号
cd /home/ubuntu/projects/PEPGMP
bash scripts/update_image_version.sh $VERSION_TAG

# 7. 滚动更新（零停机）
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api

# 或使用标准重启（有短暂停机）
docker compose -f docker-compose.prod.yml --env-file .env.production restart api

# 8. 验证
docker compose logs api --tail 50
curl http://localhost/api/v1/monitoring/health
```

**优点**: 快速、简单、风险低
**耗时**: 5-10分钟（取决于网络速度）

#### 方案 B: 镜像 + 配置更新

**适用**: 代码更新 + 配置文件变更

```bash
# ========== 开发机器操作 ==========

# 1. 构建新镜像
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 2. 导出镜像
docker save pepgmp-backend:$VERSION_TAG | gzip > /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

# 3. 传输镜像和配置
scp /tmp/pepgmp-backend-$VERSION_TAG.tar.gz ubuntu@<生产IP>:/tmp/
scp -r config/* ubuntu@<生产IP>:/home/ubuntu/projects/PEPGMP/config/
scp docker-compose.prod.yml ubuntu@<生产IP>:/home/ubuntu/projects/PEPGMP/

# ========== 生产服务器操作 ==========

# 4. SSH到生产
ssh ubuntu@<生产IP>

# 5. 导入镜像
docker load < /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

# 6. 更新版本号
cd /home/ubuntu/projects/PEPGMP
bash scripts/update_image_version.sh $VERSION_TAG

# 7. 重启服务（应用新配置）
docker compose -f docker-compose.prod.yml --env-file .env.production down
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 8. 验证
docker compose logs -f
```

**优点**: 可以更新配置文件
**耗时**: 10-15分钟

#### 方案 C: 完整同步更新（最保险）

**适用**: 重大更新、多文件变更

```bash
# ========== 开发机器操作 ==========

# 使用 prepare_minimal_deploy.sh 增量模式
bash scripts/prepare_minimal_deploy.sh /home/ubuntu/projects/PEPGMP no

# 该脚本会:
# - 检测文件变化（md5/shasum）
# - 只复制变更的文件
# - 跳过未变化的大文件（models/）
```

**优点**: 最保险，确保一致性
**耗时**: 15-30分钟（取决于变更文件数量）

---

## 🔧 数据库迁移处理

### 如果有数据库变更

```bash
# 1. 备份数据库（重要！）
docker compose exec -T postgres pg_dump -U pepgmp_prod pepgmp_production | gzip > backup-$(date +%Y%m%d).sql.gz

# 2. 应用迁移
docker compose exec api alembic upgrade head

# 或执行SQL脚本
docker compose exec -T postgres psql -U pepgmp_prod pepgmp_production < scripts/migrations/xxx.sql

# 3. 验证迁移
docker compose exec postgres psql -U pepgmp_prod pepgmp_production -c "\dt"
```

---

## 📊 部署方案对比

| 场景 | 传输内容 | 停机时间 | 适用 | 耗时 |
|------|---------|---------|------|------|
| **首次全新部署** | 完整项目 + 镜像 | 新环境，无停机 | 新服务器 | 30-60分钟 |
| **仅镜像更新** | 镜像文件 | 0-10秒 | 代码更新 | 5-10分钟 |
| **镜像 + 配置** | 镜像 + 配置文件 | 10-30秒 | 代码 + 配置更新 | 10-15分钟 |
| **完整同步** | 增量文件 + 镜像 | 10-30秒 | 重大更新 | 15-30分钟 |

---

## 🎯 推荐的自动化脚本

### 创建快速更新脚本

**文件**: `scripts/quick_update_production.sh`

```bash
#!/bin/bash
# 快速更新生产环境（仅镜像）
# 使用方式: bash scripts/quick_update_production.sh <生产IP> [版本号]

set -e

PRODUCTION_IP="${1}"
PRODUCTION_USER="${2:-ubuntu}"
VERSION_TAG="${3:-$(date +%Y%m%d)}"

if [ -z "$PRODUCTION_IP" ]; then
    echo "错误: 请提供生产服务器IP"
    echo "使用方式: bash $0 <生产IP> [SSH用户] [版本号]"
    exit 1
fi

echo "========================================================================="
echo "快速更新生产环境"
echo "========================================================================="
echo "目标服务器: $PRODUCTION_USER@$PRODUCTION_IP"
echo "版本标签: $VERSION_TAG"
echo ""

# 步骤1: 构建镜像
echo "[1/5] 构建Docker镜像..."
bash scripts/build_prod_only.sh $VERSION_TAG

# 步骤2: 导出镜像
echo "[2/5] 导出镜像..."
docker save pepgmp-backend:$VERSION_TAG | gzip > /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

# 步骤3: 传输镜像
echo "[3/5] 传输镜像到生产服务器..."
scp /tmp/pepgmp-backend-$VERSION_TAG.tar.gz $PRODUCTION_USER@$PRODUCTION_IP:/tmp/

# 步骤4: 远程更新
echo "[4/5] 在生产服务器上更新..."
ssh $PRODUCTION_USER@$PRODUCTION_IP << EOF
    set -e
    cd /home/ubuntu/projects/PEPGMP

    echo "导入镜像..."
    docker load < /tmp/pepgmp-backend-$VERSION_TAG.tar.gz
    rm -f /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

    echo "更新版本号..."
    bash scripts/update_image_version.sh $VERSION_TAG

    echo "滚动更新服务..."
    docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps api

    echo "等待服务启动..."
    sleep 10

    echo "验证服务..."
    docker compose logs api --tail 20
EOF

# 步骤5: 健康检查
echo "[5/5] 健康检查..."
sleep 5
if ssh $PRODUCTION_USER@$PRODUCTION_IP "curl -sf http://localhost/api/v1/monitoring/health > /dev/null"; then
    echo "✓ 更新成功！"
else
    echo "⚠️  健康检查失败，请检查日志"
    ssh $PRODUCTION_USER@$PRODUCTION_IP "docker compose -f /home/ubuntu/projects/PEPGMP/docker-compose.prod.yml logs api --tail 50"
fi

# 清理本地临时文件
rm -f /tmp/pepgmp-backend-$VERSION_TAG.tar.gz

echo ""
echo "========================================================================="
echo "更新完成"
echo "========================================================================="
echo "版本: $VERSION_TAG"
echo "访问: http://$PRODUCTION_IP/"
echo ""
```

### 使用快速更新脚本

```bash
# 自动使用今天的日期作为版本号
bash scripts/quick_update_production.sh 192.168.1.100

# 指定版本号
bash scripts/quick_update_production.sh 192.168.1.100 ubuntu 20251215
```

---

## 🔄 版本回滚

如果新版本有问题，快速回滚到之前的版本：

```bash
# 在生产服务器上
cd /home/ubuntu/projects/PEPGMP

# 查看可用的镜像版本
docker images | grep pepgmp-backend

# 回滚到指定版本
OLD_VERSION="20251210"
bash scripts/update_image_version.sh $OLD_VERSION

# 重启服务
docker compose -f docker-compose.prod.yml --env-file .env.production restart api

# 验证
curl http://localhost/api/v1/monitoring/health
```

---

## 📝 部署检查清单

### 首次部署检查清单

- [ ] 服务器环境准备（Docker、权限等）
- [ ] 部署目录创建（/home/ubuntu/projects/PEPGMP）
- [ ] 镜像已构建并传输
- [ ] 配置文件已生成（.env.production）
- [ ] 模型文件已传输（如需要）
- [ ] 数据库已初始化
- [ ] 服务启动成功
- [ ] 健康检查通过
- [ ] 前端可访问
- [ ] API可访问

### 增量更新检查清单

- [ ] 新版本镜像已构建
- [ ] 镜像已传输到生产
- [ ] 版本号已更新（.env.production）
- [ ] 数据库迁移（如有）
- [ ] 服务已重启
- [ ] 健康检查通过
- [ ] 旧镜像已保留（用于回滚）
- [ ] 日志无错误

---

## 🚨 故障处理

### 问题1: 服务启动失败

```bash
# 查看详细日志
docker compose logs api --tail 100

# 检查容器状态
docker compose ps

# 检查配置
docker compose config
```

### 问题2: 健康检查失败

```bash
# 检查端口
netstat -tlnp | grep 8000

# 检查进程
docker compose exec api ps aux

# 重启服务
docker compose restart api
```

### 问题3: 数据库连接失败

```bash
# 检查数据库容器
docker compose logs postgres --tail 50

# 测试数据库连接
docker compose exec postgres psql -U pepgmp_prod -d pepgmp_production -c "SELECT 1;"
```

---

## 📚 相关文档

- [脚本分析报告](./SCRIPTS_ANALYSIS_AND_FIX.md)
- [rsync传输方案](./RSYNC传输方案.md)
- [系统架构文档](./SYSTEM_ARCHITECTURE.md)

---

**文档版本**: 1.0
**更新日期**: 2025-12-15
