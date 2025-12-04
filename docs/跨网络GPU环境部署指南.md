# 跨网络 GPU 环境部署指南

## 📋 适用场景

- ✅ macOS 和 WSL/Ubuntu 不在同一网络
- ✅ 需要在 WSL Ubuntu 中部署测试（有 GPU）
- ✅ 最终部署到 Ubuntu Server（有 GPU）

## 🎯 部署策略

**推荐方式**：在 WSL/Ubuntu 中直接构建（最简单）

**如果代码已同步到 WSL**：
- ✅ 直接在 WSL 中构建镜像（推荐）
- ✅ 无需从 macOS 打包传输
- ✅ 更简单、更快速

**如果代码未同步**：
- 方式 A: 在 WSL 中直接构建（推荐）
- 方式 B: macOS 打包后传输（适合代码未同步的情况）

**流程选择**：
1. **代码已同步** → 在 WSL 中直接构建和部署（最简单）
2. **代码未同步** → macOS 打包传输，或在 WSL 中 git clone

---

## 🚀 方式 A: 在 WSL 中直接构建（推荐，代码已同步）

### 步骤 A.1：同步代码到 WSL

```bash
# 在 WSL Ubuntu 中
cd ~/projects

# 方式 1: Git clone（推荐）
git clone <your-repo-url> Pyt
cd Pyt

# 方式 2: 从 macOS 通过共享文件夹复制
# cp -r /mnt/c/Users/YourName/Code/PEPGMP ~/projects/Pyt
# cd ~/projects/Pyt
```

### 步骤 A.2：在 WSL 中构建镜像

```bash
cd ~/projects/Pyt

# 使用日期作为版本号
VERSION_TAG=$(date +%Y%m%d)
# 例如：20251204

# 构建镜像（会自动跳过类型检查）
bash scripts/build_prod_only.sh $VERSION_TAG

# 验证构建
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251204
# pepgmp-frontend:20251204
```

### 步骤 A.3：准备部署目录

```bash
# 如果当前目录就是部署目录，直接使用
# 或创建单独的部署目录
mkdir -p ~/projects/PEPGMP-deploy
cd ~/projects/PEPGMP-deploy

# 使用准备脚本创建最小化部署包
bash ../Pyt/scripts/prepare_minimal_deploy.sh ~/projects/PEPGMP-deploy

# 或手动复制必要文件
# cp ../Pyt/docker-compose.prod.yml .
# cp -r ../Pyt/config .
# cp -r ../Pyt/scripts .
# cp -r ../Pyt/nginx .
```

### 步骤 A.4：生成配置并启动

```bash
cd ~/projects/PEPGMP-deploy

# 生成配置
bash scripts/generate_production_config.sh
# 输入镜像版本: 20251204

# 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 验证部署
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

**优势**：
- ✅ 无需传输大文件（镜像文件 2-3GB）
- ✅ 构建速度快（本地构建）
- ✅ 版本自动匹配
- ✅ 适合 GPU 环境（直接在目标环境构建）

---

## 📦 方式 B: macOS 打包传输（代码未同步时使用）

### 步骤 1.1：构建生产镜像

```bash
cd /Users/zhou/Code/Pyt

# 使用日期作为版本号
VERSION_TAG=$(date +%Y%m%d)
# 例如：20251204

# 构建镜像
bash scripts/build_prod_only.sh $VERSION_TAG

# 验证构建
docker images | grep pepgmp
```

### 步骤 1.2：导出镜像

```bash
# 创建导出目录
mkdir -p docker-images

# 导出后端镜像
docker save pepgmp-backend:$VERSION_TAG -o docker-images/pepgmp-backend-$VERSION_TAG.tar

# 导出前端镜像
docker save pepgmp-frontend:$VERSION_TAG -o docker-images/pepgmp-frontend-$VERSION_TAG.tar

# 验证导出文件
ls -lh docker-images/

# 预期输出：
# pepgmp-backend-20251204.tar    (约 2-3 GB)
# pepgmp-frontend-20251204.tar   (约 100-200 MB)
```

### 步骤 1.3：准备部署包

```bash
# 创建部署包（包含配置文件、脚本等）
bash scripts/prepare_minimal_deploy.sh ~/deploy-packages/Pyt-$VERSION_TAG

# 部署包包含：
# - docker-compose.prod.yml
# - config/ 目录
# - models/ 目录（可选）
# - scripts/ 目录（包含 generate_production_config.sh）
# - nginx/ 目录
```

### 步骤 1.4：打包传输文件

```bash
# 创建传输包
cd ~
tar -czf pyt-deployment-$VERSION_TAG.tar.gz \
  docker-images/pepgmp-backend-$VERSION_TAG.tar \
  docker-images/pepgmp-frontend-$VERSION_TAG.tar \
  deploy-packages/Pyt-$VERSION_TAG

# 验证打包
ls -lh pyt-deployment-$VERSION_TAG.tar.gz

# 现在可以传输这个文件到 WSL/Ubuntu
```

---

## 🚀 第二阶段：WSL Ubuntu 部署

### 步骤 2.1：传输文件到 WSL

#### 方式 A: 通过 Windows 文件系统（推荐）

```bash
# 在 macOS 上，将文件放到 Windows 可访问的位置
# 例如：通过共享文件夹、U盘、或网络传输

# 在 WSL Ubuntu 中，从 Windows 文件系统复制
# 假设文件在 Windows 的 Downloads 目录
cp /mnt/c/Users/YourName/Downloads/pyt-deployment-20251204.tar.gz ~/
cd ~
tar -xzf pyt-deployment-20251204.tar.gz
```

#### 方式 B: 通过 U盘/移动硬盘

```bash
# 在 macOS 上复制到 U盘
# 在 WSL Ubuntu 中，U盘通常挂载在 /mnt/ 下
# 找到 U盘挂载点并复制
ls /mnt/
cp /mnt/<usb-drive>/pyt-deployment-20251204.tar.gz ~/
cd ~
tar -xzf pyt-deployment-20251204.tar.gz
```

#### 方式 C: 通过网络传输（如果可能）

```bash
# 在 macOS 上启动临时 HTTP 服务器
cd ~
python3 -m http.server 8000

# 在 WSL Ubuntu 中下载
wget http://<macos-ip>:8000/pyt-deployment-20251204.tar.gz
tar -xzf pyt-deployment-20251204.tar.gz
```

### 步骤 2.2：验证 Docker 和 GPU 支持

```bash
# 检查 Docker
docker --version
docker compose version

# 检查 GPU 支持（如果使用 NVIDIA GPU）
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi

# 如果 nvidia-smi 正常显示，说明 GPU 支持正常
```

### 步骤 2.3：导入镜像

```bash
# 进入解压后的目录
cd ~/docker-images

# 导入后端镜像
docker load -i pepgmp-backend-20251204.tar

# 导入前端镜像
docker load -i pepgmp-frontend-20251204.tar

# 验证导入
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251204
# pepgmp-frontend:20251204
```

### 步骤 2.4：准备部署目录

```bash
# 创建部署目录（推荐在 WSL 文件系统中）
mkdir -p ~/projects/Pyt
cd ~/projects/Pyt

# 复制部署包内容
cp -r ~/deploy-packages/Pyt-20251204/* .

# 或直接解压到部署目录
# tar -xzf ~/pyt-deployment-20251204.tar.gz -C ~/projects/Pyt
```

### 步骤 2.5：生成配置文件

```bash
cd ~/projects/Pyt

# 运行配置生成脚本
bash scripts/generate_production_config.sh

# 按提示输入：
# - API端口 [8000]: 直接回车
# - 管理员用户名 [admin]: 直接回车
# - CORS来源 [*]: 直接回车
# - 镜像标签 [latest]: 20251204  ← 重要！输入你的镜像版本号
# - 数据库密码: 输入强密码（或使用自动生成的）
# - Redis 密码: 输入强密码（或使用自动生成的）

# 检查配置
cat .env.production | grep IMAGE_TAG
# 应该显示: IMAGE_TAG=20251204
```

### 步骤 2.6：检查 GPU 配置（如果需要）

如果应用需要使用 GPU，需要检查 `docker-compose.prod.yml` 中的 GPU 配置：

```bash
# 检查 docker-compose.prod.yml 中是否有 GPU 配置
grep -i gpu docker-compose.prod.yml

# 如果没有，可能需要添加（根据实际需求）
# 例如，在 api 服务中添加：
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: 1
#           capabilities: [gpu]
```

### 步骤 2.7：启动服务

```bash
cd ~/projects/Pyt

# 启动所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看启动日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 等待约 60-90 秒让所有服务启动
```

### 步骤 2.8：验证部署

```bash
# 检查服务状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 应该看到所有服务都是 "Up" 状态

# 测试 API
curl http://localhost:8000/api/v1/monitoring/health

# 测试前端
curl -I http://localhost/

# 获取 WSL IP（用于 Windows 浏览器访问）
hostname -I
```

---

## 🖥️ 第三阶段：Ubuntu Server 部署

部署到 Ubuntu Server 的流程与 WSL 基本相同，只需注意：

### 差异点

1. **文件传输方式**：
   - 可以通过 SCP：`scp pyt-deployment-20251204.tar.gz user@server:/tmp/`
   - 或通过 U盘/移动硬盘
   - 或通过内网文件服务器

2. **网络访问**：
   - Ubuntu Server 通常有固定 IP
   - 需要配置防火墙规则（如需要）

3. **GPU 配置**：
   - 确保 NVIDIA 驱动已安装：`nvidia-smi`
   - 确保 Docker GPU 支持：`docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi`

### 部署步骤

```bash
# 1. 传输文件到服务器
scp pyt-deployment-20251204.tar.gz user@server:/tmp/

# 2. SSH 连接到服务器
ssh user@server

# 3. 解压文件
cd /opt  # 或你选择的部署目录
tar -xzf /tmp/pyt-deployment-20251204.tar.gz

# 4. 导入镜像
cd docker-images
docker load -i pepgmp-backend-20251204.tar
docker load -i pepgmp-frontend-20251204.tar

# 5. 准备部署目录
mkdir -p /opt/pepgmp
cd /opt/pepgmp
cp -r ~/deploy-packages/Pyt-20251204/* .

# 6. 生成配置
bash scripts/generate_production_config.sh

# 7. 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 8. 配置防火墙（如需要）
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
```

---

## 🔧 GPU 环境特殊配置

### 检查 GPU 可用性

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

或使用环境变量：

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

### macOS 端
- [ ] 构建镜像：`bash scripts/build_prod_only.sh 20251204`
- [ ] 导出镜像：`docker save ...`
- [ ] 准备部署包：`bash scripts/prepare_minimal_deploy.sh ...`
- [ ] 打包传输文件：`tar -czf pyt-deployment-20251204.tar.gz ...`

### WSL/Ubuntu 端
- [ ] 传输文件到 WSL
- [ ] 解压文件
- [ ] 导入镜像：`docker load -i ...`
- [ ] 验证镜像：`docker images | grep pepgmp`
- [ ] 准备部署目录
- [ ] 生成配置：`bash scripts/generate_production_config.sh`
- [ ] 检查 GPU 支持（如需要）
- [ ] 启动服务：`docker compose up -d`
- [ ] 验证部署：`curl http://localhost/`

### Ubuntu Server 端
- [ ] 传输文件到服务器
- [ ] 解压文件
- [ ] 导入镜像
- [ ] 准备部署目录
- [ ] 生成配置
- [ ] 配置防火墙（如需要）
- [ ] 启动服务
- [ ] 验证部署

---

## 🎯 推荐工作流

### 第一次部署

1. **macOS 准备**（一次性）：
   ```bash
   VERSION_TAG=$(date +%Y%m%d)
   bash scripts/build_prod_only.sh $VERSION_TAG
   # 导出镜像和准备部署包
   ```

2. **传输到 WSL**：
   - 通过 Windows 文件系统或 U盘

3. **WSL 部署测试**：
   ```bash
   # 导入镜像、生成配置、启动服务
   ```

4. **测试通过后，部署到 Ubuntu Server**：
   - 使用相同的镜像和部署包
   - 流程完全相同

### 后续更新

1. **macOS 构建新版本**：
   ```bash
   VERSION_TAG=$(date +%Y%m%d)
   bash scripts/build_prod_only.sh $VERSION_TAG
   ```

2. **传输新镜像**：
   - 只传输新的镜像文件（不需要重新传输部署包）

3. **更新部署**：
   ```bash
   # 在 WSL/Server 中
   docker load -i new-image.tar
   # 更新 .env.production 中的 IMAGE_TAG
   docker compose down
   docker compose up -d
   ```

---

## 📚 相关文档

- [WSL2/Ubuntu 部署完整指南](./WSL2_Ubuntu部署完整指南.md)
- [WSL2/Ubuntu 部署快速参考](./WSL2_Ubuntu部署快速参考.md)
- [macOS 生产部署指南](./macOS生产部署指南.md)

---

**最后更新**: 2025-12-04
