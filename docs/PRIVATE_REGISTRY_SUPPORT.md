# 私有容器仓库支持文档

## 概述

本项目已支持私有容器仓库（Private Docker Registry），可以在不修改代码的情况下，通过环境变量切换镜像来源。

## 支持的部署模式

### 模式 1：本地镜像（默认，当前使用）

**适用场景**：
- 测试环境
- 无私有仓库时
- 离线部署

**镜像来源**：
- Windows 构建 → 导出 `.tar` → WSL2/Ubuntu 导入

**配置**：
```bash
# .env.production
IMAGE_REGISTRY=  # 留空或不设置
IMAGE_TAG=20251203
```

**镜像格式**：
```
pepgmp-backend:20251203
pepgmp-frontend:20251203
```

---

### 模式 2：私有仓库（未来使用）

**适用场景**：
- 生产环境
- 多服务器部署
- CI/CD 自动化

**镜像来源**：
- 构建后推送到私有仓库 → 各服务器直接拉取

**配置**：
```bash
# .env.production
IMAGE_REGISTRY=registry.example.com/  # 注意末尾的斜杠
IMAGE_TAG=20251203
```

**镜像格式**：
```
registry.example.com/pepgmp-backend:20251203
registry.example.com/pepgmp-frontend:20251203
```

---

## 实现原理

### Docker Compose 配置

**docker-compose.prod.yml**：
```yaml
services:
  api:
    # ${IMAGE_REGISTRY:-} 表示：使用 IMAGE_REGISTRY 环境变量，如果未设置则为空
    image: ${IMAGE_REGISTRY:-}pepgmp-backend:${IMAGE_TAG:-latest}

  frontend-init:
    image: ${IMAGE_REGISTRY:-}pepgmp-frontend:${IMAGE_TAG:-latest}
```

**变量展开示例**：

| IMAGE_REGISTRY | IMAGE_TAG | 最终镜像名 |
|----------------|-----------|-----------|
| *(未设置)* | 20251203 | `pepgmp-backend:20251203` |
| `registry.example.com/` | 20251203 | `registry.example.com/pepgmp-backend:20251203` |
| `harbor.company.com/project/` | v1.0.0 | `harbor.company.com/project/pepgmp-backend:v1.0.0` |

---

## 部署流程对比

### 当前流程（本地镜像）

```bash
# ========== Windows ==========
# 1. 构建镜像
.\scripts\build_prod_only.ps1 20251203

# 2. 导出镜像
.\scripts\export_images_to_wsl.ps1 20251203

# ========== WSL2/Ubuntu ==========
# 3. 导入镜像
docker load -i /path/to/pepgmp-backend-20251203.tar
docker load -i /path/to/pepgmp-frontend-20251203.tar

# 4. 配置环境变量
cat > .env.production << EOF
IMAGE_REGISTRY=
IMAGE_TAG=20251203
EOF

# 5. 部署
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

### 未来流程（私有仓库）

```bash
# ========== Windows/CI 服务器 ==========
# 1. 构建镜像
.\scripts\build_prod_only.ps1 20251203

# 2. 推送到私有仓库
docker tag pepgmp-backend:20251203 registry.example.com/pepgmp-backend:20251203
docker tag pepgmp-frontend:20251203 registry.example.com/pepgmp-frontend:20251203
docker push registry.example.com/pepgmp-backend:20251203
docker push registry.example.com/pepgmp-frontend:20251203

# ========== 生产服务器 ==========
# 3. 配置环境变量
cat > .env.production << EOF
IMAGE_REGISTRY=registry.example.com/
IMAGE_TAG=20251203
EOF

# 4. 部署（自动拉取镜像）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**优势**：
- ✅ 无需手动传输 `.tar` 文件
- ✅ 支持多服务器同时部署
- ✅ 版本管理更清晰
- ✅ 支持 CI/CD 自动化

---

## 搭建私有仓库

### 方案 1：Docker Registry（最简单）

```bash
# 启动 Registry
docker run -d -p 5000:5000 --name registry \
  -v /opt/registry:/var/lib/registry \
  registry:2

# 配置 Docker 信任该仓库（如果是 HTTP）
# /etc/docker/daemon.json
{
  "insecure-registries": ["registry.example.com:5000"]
}

# 重启 Docker
sudo systemctl restart docker
```

### 方案 2：Harbor（推荐生产环境）

**特性**：
- ✅ Web UI 管理界面
- ✅ 用户权限管理
- ✅ 镜像扫描（安全漏洞检测）
- ✅ 镜像签名
- ✅ 镜像复制（多地域同步）

**安装**：
```bash
# 下载 Harbor
wget https://github.com/goharbor/harbor/releases/download/v2.10.0/harbor-offline-installer-v2.10.0.tgz
tar xzvf harbor-offline-installer-v2.10.0.tgz
cd harbor

# 配置
cp harbor.yml.tmpl harbor.yml
# 编辑 harbor.yml，设置域名、密码等

# 安装
sudo ./install.sh
```

### 方案 3：云服务商

- **阿里云 ACR**：https://cr.console.aliyun.com/
- **腾讯云 TCR**：https://console.cloud.tencent.com/tcr
- **AWS ECR**：https://aws.amazon.com/ecr/
- **Azure ACR**：https://azure.microsoft.com/services/container-registry/

---

## 迁移到私有仓库

### 步骤 1：搭建私有仓库

选择上述方案之一，搭建私有仓库。

### 步骤 2：推送现有镜像

```bash
# 假设私有仓库地址为 registry.example.com

# 1. 标记镜像
docker tag pepgmp-backend:20251203 registry.example.com/pepgmp-backend:20251203
docker tag pepgmp-frontend:20251203 registry.example.com/pepgmp-frontend:20251203

# 2. 登录私有仓库（如果需要认证）
docker login registry.example.com

# 3. 推送镜像
docker push registry.example.com/pepgmp-backend:20251203
docker push registry.example.com/pepgmp-frontend:20251203
```

### 步骤 3：更新环境变量

```bash
# 编辑 .env.production
sed -i 's/IMAGE_REGISTRY=.*/IMAGE_REGISTRY=registry.example.com\//' .env.production
```

### 步骤 4：重新部署

```bash
# 停止现有服务
docker-compose -f docker-compose.prod.yml down

# 重新部署（自动从私有仓库拉取）
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 自动化脚本（未来可创建）

### 推送到私有仓库脚本

**scripts/push_to_registry.ps1**（Windows）：
```powershell
param(
    [string]$Version,
    [string]$Registry = "registry.example.com"
)

# 标记镜像
docker tag pepgmp-backend:$Version ${Registry}/pepgmp-backend:$Version
docker tag pepgmp-frontend:$Version ${Registry}/pepgmp-frontend:$Version

# 推送镜像
docker push ${Registry}/pepgmp-backend:$Version
docker push ${Registry}/pepgmp-frontend:$Version

Write-Host "Images pushed to $Registry"
```

### 从私有仓库部署脚本

**scripts/deploy_from_registry.sh**（Linux）：
```bash
#!/bin/bash
VERSION=$1
REGISTRY=${2:-"registry.example.com"}

# 更新环境变量
sed -i "s/IMAGE_REGISTRY=.*/IMAGE_REGISTRY=${REGISTRY}\//" .env.production
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=${VERSION}/" .env.production

# 部署
docker-compose -f docker-compose.prod.yml --env-file .env.production pull
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

echo "Deployed version $VERSION from $REGISTRY"
```

---

## 常见问题

### Q1: 如何验证私有仓库配置是否正确？

```bash
# 测试拉取镜像
docker pull ${IMAGE_REGISTRY}pepgmp-backend:${IMAGE_TAG}

# 查看 docker-compose 配置
docker-compose -f docker-compose.prod.yml config | grep image:
```

### Q2: 私有仓库需要认证怎么办？

```bash
# 方法 1: 手动登录
docker login registry.example.com

# 方法 2: 使用 docker-compose secrets（推荐）
# 在 docker-compose.prod.yml 中添加：
services:
  api:
    image: ${IMAGE_REGISTRY:-}pepgmp-backend:${IMAGE_TAG:-latest}
    # 如果需要认证，Docker 会自动使用 ~/.docker/config.json 中的凭据
```

### Q3: 如何回退到本地镜像模式？

```bash
# 编辑 .env.production
sed -i 's/IMAGE_REGISTRY=.*/IMAGE_REGISTRY=/' .env.production

# 重新部署
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Q4: 私有仓库和本地镜像可以混用吗？

**可以**，但不推荐。示例：
```bash
# .env.production
IMAGE_REGISTRY=registry.example.com/
IMAGE_TAG=20251203

# docker-compose.prod.yml
services:
  api:
    image: ${IMAGE_REGISTRY:-}pepgmp-backend:${IMAGE_TAG:-latest}  # 从私有仓库拉取

  frontend-init:
    image: pepgmp-frontend:latest  # 使用本地镜像（硬编码）
```

---

## 总结

- ✅ **当前**：使用本地镜像（导出/导入 `.tar`）
- ✅ **未来**：支持私有仓库（只需配置 `IMAGE_REGISTRY` 环境变量）
- ✅ **无缝切换**：修改 `.env.production` 即可切换模式
- ✅ **向后兼容**：不设置 `IMAGE_REGISTRY` 时，行为与之前完全相同

**建议**：
- 测试环境：继续使用本地镜像（简单快速）
- 生产环境：搭建私有仓库（标准化、自动化）
