# 生产镜像构建与部署脚本

本目录包含生产环境 Docker 镜像的构建、推送和导出脚本，支持在线和离线两种部署方式。

## 📋 脚本列表

| 脚本 | 用途 | 使用场景 |
|------|------|----------|
| `prepare_base_images.sh` | 拉取并推送基础镜像到私有Registry | 初次部署或基础镜像更新 |
| `build_prod_images.sh` | 构建、推送生产镜像并导出tar | 每次发布新版本 |
| `load_offline_images.sh` | 从tar加载基础镜像（离线） | 无外网环境 |

## 🚀 使用流程

### 方案一：在线部署（推荐）

适用于能访问 Docker Hub 的环境。

#### 1. 配置 Docker insecure-registries（如私有Registry为HTTP）

编辑 `/etc/docker/daemon.json`（macOS为 Docker Desktop 的 Settings → Docker Engine）：

```json
{
  "insecure-registries": ["192.168.30.83:5433"]
}
```

重启 Docker：
```bash
# Linux
sudo systemctl restart docker

# macOS
# 在 Docker Desktop 中重启
```

#### 2. 预热基础镜像

首次部署时执行一次：

```bash
bash scripts/prepare_base_images.sh
```

此脚本会：
- 从 Docker Hub 拉取 CUDA、Node、Nginx 基础镜像
- 推送到你的私有 Registry（192.168.30.83:5433）
- 可选：导出离线 tar 备份

#### 3. 构建并推送生产镜像

每次发版时执行：

```bash
bash scripts/build_prod_images.sh
```

此脚本会：
- 构建后端生产镜像（基于 CUDA）
- 构建前端生产镜像（基于 Node + Nginx）
- 推送到私有 Registry
- 导出 tar 包到 `./docker_exports/`
- 可选：压缩 tar 包以节省空间

### 方案二：离线部署

适用于无法访问 Docker Hub 的生产环境。

#### 1. 在可联网机器上准备

```bash
# 拉取并导出基础镜像
bash scripts/prepare_base_images.sh
# 选择 "是" 导出离线备份

# 将 docker_exports/base_images/ 目录传输到目标机器
```

#### 2. 在离线机器上加载

```bash
# 加载基础镜像并推送到本地私有Registry
bash scripts/load_offline_images.sh ./docker_exports/base_images

# 构建生产镜像
bash scripts/build_prod_images.sh
```

## 📦 输出产物

### Registry 镜像

推送到 `192.168.30.83:5433` 的镜像：

```
192.168.30.83:5433/pyt-api:prod              # 后端最新版
192.168.30.83:5433/pyt-api:YYYYMMDD         # 后端日期版本
192.168.30.83:5433/pyt-frontend:prod        # 前端最新版
192.168.30.83:5433/pyt-frontend:YYYYMMDD    # 前端日期版本
```

### 本地 tar 文件

导出到 `./docker_exports/` 的文件：

```
docker_exports/
├── pyt-api_prod_YYYYMMDD.tar         # 后端镜像
├── pyt-frontend_prod_YYYYMMDD.tar    # 前端镜像
└── base_images/                       # 基础镜像（可选）
    ├── base_cuda.tar
    ├── base_node.tar
    └── base_nginx.tar
```

## 🔍 验证

### 验证 Registry

```bash
# 查看所有仓库
curl http://192.168.30.83:5433/v2/_catalog

# 查看特定镜像的标签
curl http://192.168.30.83:5433/v2/pyt-api/tags/list
curl http://192.168.30.83:5433/v2/pyt-frontend/tags/list
```

### 验证本地镜像

```bash
# 查看本地镜像
docker images | grep pyt

# 从 tar 加载验证
docker load -i docker_exports/pyt-api_prod_YYYYMMDD.tar
docker load -i docker_exports/pyt-frontend_prod_YYYYMMDD.tar
```

## 🚢 部署

### 使用 docker-compose（推荐）

```bash
# 生产环境部署
docker-compose -f docker-compose.prod.yml pull  # 从私有Registry拉取
docker-compose -f docker-compose.prod.yml up -d

# 健康检查
curl http://localhost:8000/health  # 后端
curl http://localhost:8080/        # 前端
curl http://localhost:8080/api/v1/health  # 前端通过Nginx代理访问后端
```

### 手动部署

```bash
# 后端
docker run -d \
  --name pyt-api \
  --gpus all \
  -p 8000:8000 \
  -v ./config:/app/config:ro \
  -v ./logs:/app/logs \
  -e ENVIRONMENT=production \
  192.168.30.83:5433/pyt-api:prod

# 前端
docker run -d \
  --name pyt-frontend \
  -p 8080:80 \
  --link pyt-api:api \
  192.168.30.83:5433/pyt-frontend:prod
```

## ⚙️ 自定义配置

如需修改 Registry 地址或其他配置，编辑各脚本顶部的配置区域：

```bash
# =============================================================================
# 配置区域
# =============================================================================
REGISTRY="192.168.30.83:5433"  # 修改为你的Registry地址
PROJECT_NAME="pyt"
```

## 🛠️ 故障排查

### 问题1：无法推送到 Registry

**错误**: `http: server gave HTTP response to HTTPS client`

**解决**: 配置 insecure-registries（见上文第1步）

---

### 问题2：基础镜像拉取失败

**错误**: `failed to fetch anonymous token`

**解决**:
- 检查网络连接到 Docker Hub
- 使用离线部署方案（方案二）
- 配置 Docker Hub 镜像加速器

---

### 问题3：GPU 相关错误

**错误**: `could not select device driver`

**解决**:
- 确保安装 NVIDIA Docker Runtime
- 检查 `docker info | grep -i runtime`
- 参考: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

---

### 问题4：tar 文件过大

**解决**:
- 构建后选择压缩（gzip -9）
- 可减小 60-70% 体积
- 或使用 Registry 直接分发，无需 tar

## 📚 相关文档

- [项目 README](../README.md)
- [Docker 部署文档](../docs/README.md)
- [生产环境 docker-compose.prod.yml](../docker-compose.prod.yml)

## 🔐 安全建议

1. **生产环境使用 HTTPS Registry**
   - 配置 TLS 证书
   - 启用认证（basic auth 或 token）

2. **镜像签名与验证**
   ```bash
   # 使用 Docker Content Trust
   export DOCKER_CONTENT_TRUST=1
   ```

3. **定期更新基础镜像**
   - 修复已知安全漏洞
   - 每月执行一次 `prepare_base_images.sh`

4. **镜像扫描**
   ```bash
   # 使用 Trivy 扫描漏洞
   trivy image 192.168.30.83:5433/pyt-api:prod
   ```

## 📞 支持

如遇问题，请查看：
- 脚本执行日志（彩色输出）
- Docker 日志: `docker logs <container_name>`
- Registry 日志: `docker logs registry`
