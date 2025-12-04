# WSL 直接构建部署指南（推荐）

## 📋 适用场景

- ✅ 代码已同步到 WSL 环境
- ✅ 需要在 WSL 中部署测试（有 GPU）
- ✅ 最终部署到 Ubuntu Server（有 GPU）
- ✅ **无需从 macOS 打包传输**

## 🎯 优势

1. **无需传输大文件**：镜像文件 2-3GB，直接构建更快
2. **版本自动匹配**：构建和部署在同一环境，避免版本不一致
3. **GPU 支持**：直接在 GPU 环境中构建，确保兼容性
4. **更简单**：减少传输步骤，降低出错概率

---

## 🚀 完整部署流程

### 步骤 1: 同步代码到 WSL

#### 方式 1: Git Clone（推荐，代码在远程仓库）

```bash
# 在 WSL Ubuntu 中
cd ~/projects
git clone <your-repo-url> Pyt
cd Pyt
```

#### 方式 2: 从 Windows 文件系统复制（代码已在 Windows 中）

**重要**：如果代码在 Windows 文件系统中（`/mnt/c/...`），**强烈建议复制到 WSL 文件系统**以获得更好的构建性能。

```bash
# 在 WSL Ubuntu 中

# 1. 检查代码位置
ls -la /mnt/c/Users/YourName/Code/PEPGMP

# 2. 复制到 WSL 文件系统（推荐）
mkdir -p ~/projects
cp -r /mnt/c/Users/YourName/Code/PEPGMP ~/projects/Pyt
cd ~/projects/Pyt

# 3. 验证复制
ls -la ~/projects/Pyt
ls -la ~/projects/PEPGMPscripts/

# 注意：
# - Windows 文件系统（/mnt/c/...）I/O 性能较差
# - WSL 文件系统（~/projects/...）性能更好
# - 构建镜像时会有明显性能差异
```

**性能对比**：
- Windows 文件系统构建：约 30-40 分钟（首次）
- WSL 文件系统构建：约 15-25 分钟（首次）

#### 方式 3: 使用 rsync（更高效，适合大项目）

```bash
# 在 WSL Ubuntu 中
# 使用 rsync 可以更高效地同步，并支持增量更新

mkdir -p ~/projects
rsync -avz --progress /mnt/c/Users/YourName/Code/PEPGMP/ ~/projects/PEPGMP

# 后续更新时，rsync 只会同步变更的文件
rsync -avz --progress /mnt/c/Users/YourName/Code/PEPGMP/ ~/projects/PEPGMP
```

#### 方式 4: 直接使用 Windows 文件系统（不推荐，但可行）

如果不想复制，也可以直接在 Windows 文件系统中构建，但性能会较差：

```bash
# 在 WSL Ubuntu 中
cd /mnt/c/Users/YourName/Code/PEPGMP

# 直接构建（性能较慢）
bash scripts/build_prod_only.sh 20251204
```

### 步骤 2: 验证环境

```bash
# 检查 Docker
docker --version
docker compose version
docker ps

# 检查 GPU 支持（如果需要）
nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

### 步骤 3: 构建镜像

```bash
cd ~/projects/Pyt

# 使用日期作为版本号（推荐）
VERSION_TAG=$(date +%Y%m%d)
# 例如：20251204

# 构建镜像
bash scripts/build_prod_only.sh $VERSION_TAG

# 构建过程：
# 1. 构建后端镜像（pepgmp-backend:$VERSION_TAG）
# 2. 构建前端镜像（pepgmp-frontend:$VERSION_TAG）
# 3. 自动跳过 TypeScript 类型检查（SKIP_TYPE_CHECK=true）

# 验证构建
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251204
# pepgmp-backend:latest
# pepgmp-frontend:20251204
# pepgmp-frontend:latest
```

**构建时间**：
- 后端镜像：约 10-20 分钟（首次构建）
- 前端镜像：约 2-5 分钟
- 后续构建：利用缓存，更快

### 步骤 4: 准备部署目录

#### 方式 1: 使用准备脚本（推荐）

```bash
# 创建单独的部署目录（推荐，保持代码和部署分离）
mkdir -p ~/projects/PEPGMP-deploy
cd ~/projects/PEPGMP-deploy

# 使用准备脚本
bash ../Pyt/scripts/prepare_minimal_deploy.sh ~/projects/PEPGMP-deploy

# 脚本会复制：
# - docker-compose.prod.yml
# - config/ 目录
# - scripts/ 目录
# - nginx/ 目录
# - models/ 目录（可选）
```

#### 方式 2: 直接使用项目目录

```bash
# 如果项目目录就是部署目录
cd ~/projects/Pyt

# 确保有必要的文件
ls -la docker-compose.prod.yml
ls -la config/
ls -la scripts/generate_production_config.sh
```

### 步骤 5: 生成配置文件

```bash
cd ~/projects/PEPGMP-deploy
# 或 cd ~/projects/PEPGMP��如果直接使用项目目录）

# 运行配置生成脚本
bash scripts/generate_production_config.sh

# 按提示输入：
# - API端口 [8000]: 直接回车（或输入自定义端口）
# - 管理员用户名 [admin]: 直接回车（或输入自定义用户名）
# - CORS来源 [*]: 直接回车（或输入特定域名）
# - 镜像标签 [latest]: 20251204  ← 重要！输入你的镜像版本号
# - 数据库密码: 输入强密码（或使用自动生成的）
# - Redis 密码: 输入强密码（或使用自动生成的）

# 检查配置
cat .env.production | grep IMAGE_TAG
# 应该显示: IMAGE_TAG=20251204
```

### 步骤 6: 清理旧容器（如需要）

如果遇到容器名称冲突错误，需要先清理旧容器：

```bash
# 方式 1: 使用清理脚本（推荐）
bash scripts/cleanup_old_containers.sh

# 方式 2: 手动清理
docker stop $(docker ps -aq --filter "name=pepgmp") 2>/dev/null || true
docker rm $(docker ps -aq --filter "name=pepgmp") 2>/dev/null || true

# 方式 3: 如果知道之前的部署目录
cd ~/projects/PEPGMP # 或其他部署目录
docker compose -f docker-compose.prod.yml down
```

### 步骤 7: 启动服务

```bash
# 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看启动日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 等待约 60-90 秒让所有服务启动
```

### 步骤 8: 验证部署

```bash
# 检查服务状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 应该看到所有服务都是 "Up" 状态：
# ✅ pepgmp-postgres-prod    Up (healthy)
# ✅ pepgmp-redis-prod       Up (healthy)
# ✅ pepgmp-api-prod         Up (healthy)
# ✅ pepgmp-frontend-init    Exited (0)  ← 正常，任务完成后退出
# ✅ pepgmp-nginx-prod       Up

# 测试 API
curl http://localhost:8000/api/v1/monitoring/health

# 测试前端
curl -I http://localhost/

# 获取 WSL IP（用于 Windows 浏览器访问）
hostname -I
```

---

## 🔧 GPU 环境配置（如需要）

### 检查 GPU 支持

```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

### 配置 Docker Compose 使用 GPU

如果需要 API 服务使用 GPU，修改 `docker-compose.prod.yml`：

```yaml
api:
  # ... 其他配置
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

或使用环境变量方式：

```yaml
api:
  # ... 其他配置
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
  runtime: nvidia  # 需要安装 nvidia-container-runtime
```

---

## 📋 快速检查清单

### 代码同步
- [ ] 代码已同步到 WSL（`~/projects/PEPGMP）
- [ ] 代码完整（包含所有必要文件）

### 环境检查
- [ ] Docker 已安装并运行
- [ ] Docker Compose 已安装
- [ ] GPU 支持正常（如需要）：`nvidia-smi` 和 `docker run --gpus all ...`

### 构建镜像
- [ ] 构建脚本可执行：`chmod +x scripts/build_prod_only.sh`
- [ ] 构建成功：`docker images | grep pepgmp`
- [ ] 镜像版本号记录（如 `20251204`）

### 部署配置
- [ ] 部署目录已准备
- [ ] 配置文件已生成：`.env.production`
- [ ] `IMAGE_TAG` 与构建的镜像版本一致

### 服务启动
- [ ] 所有服务启动成功：`docker compose ps`
- [ ] API 健康检查通过：`curl http://localhost:8000/api/v1/monitoring/health`
- [ ] 前端访问正常：`curl -I http://localhost/`

---

## 🔄 更新部署

### 代码更新后重新部署

```bash
cd ~/projects/Pyt

# 1. 拉取最新代码
git pull

# 2. 构建新镜像
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 3. 更新部署配置
cd ~/projects/PEPGMP-deploy
# 更新 .env.production 中的 IMAGE_TAG
sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/" .env.production

# 4. 重启服务
docker compose -f docker-compose.prod.yml --env-file .env.production down
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 🎯 与 macOS 打包方式的对比

| 特性 | WSL 直接构建 | macOS 打包传输 |
|------|------------|---------------|
| **代码同步** | 需要 | 不需要 |
| **传输文件大小** | 0（无需传输） | 2-3GB（镜像文件） |
| **构建速度** | 快（本地构建） | 快（但需要传输） |
| **版本匹配** | 自动匹配 | 需要手动匹配 |
| **GPU 测试** | 可直接测试 | 需要导入后测试 |
| **适用场景** | 代码已同步 | 代码未同步 |

---

## 📚 相关文档

- [跨网络 GPU 环境部署指南](./跨网络GPU环境部署指南.md) - 包含 macOS 打包方式
- [WSL2/Ubuntu 部署完整指南](./WSL2_Ubuntu部署完整指南.md)
- [WSL2/Ubuntu 部署快速参考](./WSL2_Ubuntu部署快速参考.md)

---

**最后更新**: 2025-12-04
