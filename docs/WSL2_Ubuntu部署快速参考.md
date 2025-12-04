# WSL2/Ubuntu 部署快速参考

## 🚀 快速部署（3种方式）

### 方式 1: 自动化脚本（推荐）

**前提**：macOS 和 WSL2 可以通过 SSH 连接

```bash
# 在 macOS 上
cd /Users/zhou/Code/Pyt

# 自动构建、导出、传输、部署
bash scripts/deploy_to_wsl2.sh user@wsl2-host 20251204

# 或使用默认版本号（当前日期）
bash scripts/deploy_to_wsl2.sh user@wsl2-host
```

### 方式 2: 半自动（手动传输）

**步骤 1: 在 macOS 上准备**

```bash
cd /Users/zhou/Code/Pyt

# 1. 构建镜像
VERSION_TAG=$(date +%Y%m%d)
bash scripts/build_prod_only.sh $VERSION_TAG

# 2. 导出镜像
mkdir -p docker-images
docker save pepgmp-backend:$VERSION_TAG -o docker-images/pepgmp-backend-$VERSION_TAG.tar
docker save pepgmp-frontend:$VERSION_TAG -o docker-images/pepgmp-frontend-$VERSION_TAG.tar

# 3. 准备部署包
bash scripts/prepare_minimal_deploy.sh ~/deploy-packages/Pyt
```

**步骤 2: 传输到 WSL2**

```bash
# 方式 A: 通过 SCP
scp docker-images/*.tar user@wsl2-host:/tmp/
scp -r ~/deploy-packages/Pyt user@wsl2-host:~/projects/

# 方式 B: 通过 Windows 文件系统
# 将文件放到 Windows 可访问的位置，然后在 WSL2 中复制
```

**步骤 3: 在 WSL2 中部署**

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 1. 导入镜像
docker load -i /tmp/pepgmp-backend-20251204.tar
docker load -i /tmp/pepgmp-frontend-20251204.tar

# 2. 生成配置
bash scripts/generate_production_config.sh
# 输入镜像版本: 20251204

# 3. 启动服务
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 4. 检查状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

### 方式 3: Docker Desktop WSL2 集成（最简单）

**如果使用 Docker Desktop 并启用了 WSL2 集成**，镜像会自动共享：

```bash
# 在 macOS 上构建镜像
cd /Users/zhou/Code/Pyt
bash scripts/build_prod_only.sh 20251204

# 在 WSL2 中直接使用（无需导入）
cd ~/projects/Pyt
bash scripts/generate_production_config.sh
# 输入镜像版本: 20251204

docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 📋 关键步骤检查清单

### macOS 端
- [ ] 构建镜像：`bash scripts/build_prod_only.sh 20251204`
- [ ] 验证镜像：`docker images | grep pepgmp`
- [ ] 导出镜像（如需要）：`docker save ...`
- [ ] 准备部署包：`bash scripts/prepare_minimal_deploy.sh ...`

### WSL2 端
- [ ] 导入镜像（如需要）：`docker load -i ...`
- [ ] 验证镜像：`docker images | grep pepgmp`
- [ ] 准备部署目录：`mkdir -p ~/projects/Pyt`
- [ ] 复制部署包到部署目录
- [ ] 生成配置：`bash scripts/generate_production_config.sh`
- [ ] 检查配置：`cat .env.production | grep IMAGE_TAG`
- [ ] 启动服务：`docker compose up -d`
- [ ] 检查状态：`docker compose ps`
- [ ] 测试访问：`curl http://localhost/`

---

## 🔧 常用命令

### 查看服务状态
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

### 查看日志
```bash
# 所有服务
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 特定服务
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f api
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f nginx
```

### 重启服务
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production restart nginx
```

### 停止服务
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production down
```

### 更新部署
```bash
# 1. 停止服务
docker compose -f docker-compose.prod.yml --env-file .env.production down

# 2. 导入新镜像
docker load -i /path/to/new-image.tar

# 3. 更新 .env.production 中的 IMAGE_TAG

# 4. 重新启动
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 🐛 常见问题

### 镜像不存在
```bash
# 检查镜像
docker images | grep pepgmp

# 如果不存在，导入
docker load -i /path/to/image.tar
```

### 端口被占用
```bash
# 检查端口
sudo netstat -tulpn | grep -E "80|8000"

# 修改 .env.production 中的端口
```

### 前端白屏
```bash
# 重新提取静态文件
rm -rf frontend/dist/*
docker compose -f docker-compose.prod.yml --env-file .env.production up frontend-init
docker compose -f docker-compose.prod.yml --env-file .env.production restart nginx
```

### 数据库连接失败
```bash
# 检查数据库容器
docker compose -f docker-compose.prod.yml --env-file .env.production logs database

# 检查密码配置
cat .env.production | grep DATABASE_PASSWORD
```

---

## 📚 详细文档

- [WSL2/Ubuntu 部署完整指南](./WSL2_Ubuntu部署完整指南.md) - 完整详细步骤
- [WSL2 生产部署详细步骤](./WSL2生产部署详细步骤.md) - 原始详细指南
- [macOS 生产部署指南](./macOS生产部署指南.md) - macOS 部署参考

---

**最后更新**: 2025-12-04
