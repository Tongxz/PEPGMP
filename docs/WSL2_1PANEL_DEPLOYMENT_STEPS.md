# WSL2 + 1Panel 完整部署流程

## 📋 概述

本指南提供从 Windows 构建镜像到 WSL2 Ubuntu + 1Panel 部署的完整步骤。

**前提条件**：
- ✅ 已在 Windows 上成功构建镜像（`pepgmp-backend:20251201`）
- ✅ 镜像已导出并导入到 WSL2 Ubuntu 中
- ✅ 1Panel 已安装并运行
- ✅ WSL2 Ubuntu 已配置 Docker

---

## 🚀 完整部署流程

### 第一步：验证镜像已导入

在 **WSL2 Ubuntu** 终端中执行：

```bash
# 检查镜像是否存在
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend:20251201
# pepgmp-backend:latest
# pepgmp-frontend:20251201 (如果构建了前端)
```

**如果镜像不存在**，需要先导入：

```bash
# 从 Windows 文件系统导入
docker load -i /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-backend-20251201.tar
docker load -i /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-frontend-20251201.tar
```

---

### 第二步：准备最小化部署包

#### 方式1: 使用准备脚本（推荐）

在 **WSL2 Ubuntu** 终端中执行：

```bash
# 从 Windows 项目目录运行准备脚本
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh

# 脚本会：
# 1. 创建 ~/projects/Pyt 目录
# 2. 复制 docker-compose.prod.1panel.yml
# 3. 复制 config/ 和 models/ 目录
# 4. 复制 generate_production_config.sh 脚本
# 5. 提示运行配置生成脚本
```

**如果之前已经运行过脚本**，可以：

```bash
# 选项1: 重新运行（会覆盖现有文件）
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh

# 选项2: 只更新特定文件
cd ~/projects/Pyt
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/docker-compose.prod.1panel.yml docker-compose.prod.yml
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/generate_production_config.sh scripts/
chmod +x scripts/generate_production_config.sh
```

#### 方式2: 手动准备

```bash
# 创建目录
mkdir -p ~/projects/Pyt/{config,models,data,logs,scripts}
cd ~/projects/Pyt

# 复制必需文件
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/docker-compose.prod.1panel.yml docker-compose.prod.yml
cp -r /mnt/c/Users/YourName/Code/PythonCode/Pyt/config/* config/
cp -r /mnt/c/Users/YourName/Code/PythonCode/Pyt/models/* models/ 2>/dev/null || true
cp /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/generate_production_config.sh scripts/
chmod +x scripts/generate_production_config.sh
```

---

### 第三步：生成生产环境配置文件

在 **WSL2 Ubuntu** 中执行：

```bash
cd ~/projects/Pyt

# 运行配置生成脚本
bash scripts/generate_production_config.sh
```

**脚本会询问以下信息**（直接回车使用默认值）：

```
API端口 [8000]: 
管理员用户名 [admin]: 
允许的CORS来源 [*]: 
镜像标签 [latest]: 20251201  ← 输入你的镜像标签
```

**脚本会自动生成**：
- ✅ `.env.production` - 完整的生产环境配置文件
- ✅ `.env.production.credentials` - 凭证信息文件（包含所有密码）

**重要**：
- 脚本会生成强随机密码，请妥善保存 `.env.production.credentials` 文件
- 确认保存凭证后，可以删除 `.env.production.credentials` 文件

---

### 第四步：验证配置文件

```bash
cd ~/projects/Pyt

# 检查配置文件是否存在
ls -la .env.production

# 验证 Docker Compose 配置语法
docker compose -f docker-compose.prod.yml config

# 检查镜像标签配置
grep IMAGE_TAG .env.production
# 应该显示: IMAGE_TAG=20251201
```

---

### 第五步：在 1Panel 中部署

#### 5.1 登录 1Panel

1. 打开浏览器访问 1Panel（通常是 `http://localhost:端口` 或 `http://你的IP:端口`）
2. 使用安装时设置的用户名和密码登录

#### 5.2 创建 Compose 项目

1. **进入容器管理**
   - 点击左侧菜单 **"容器"** 或 **"Docker"**
   - 选择 **"Compose"** 或 **"编排"** 标签页

2. **创建新项目**
   - 点击 **"创建"** 或 **"新建"** 按钮
   - 项目名称：`pepgmp-production`
   - 工作目录：`/home/你的用户名/projects/Pyt`（或 `~/projects/Pyt`）

3. **配置 Compose 文件**
   - 方式1：上传 `docker-compose.prod.yml` 文件
   - 方式2：在编辑器中粘贴文件内容
   - 方式3：选择 **"从文件创建"**，指向 `~/projects/Pyt/docker-compose.prod.yml`

#### 5.3 启动服务

1. 在 1Panel 中点击 **"启动"** 或 **"部署"** 按钮
2. 等待服务启动（首次启动需要60-70秒）
3. 查看服务状态

---

### 第六步：验证部署

#### 在 1Panel 中验证

1. **查看容器状态**
   - 在容器列表中查看所有容器
   - 确保所有容器状态为 **"运行中"**

2. **查看日志**
   - 点击容器名称
   - 选择 **"日志"** 标签
   - 检查是否有错误信息

#### 使用命令行验证

在 **WSL2 Ubuntu** 终端中执行：

```bash
cd ~/projects/Pyt

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 查看 API 日志
docker compose -f docker-compose.prod.yml logs -f api

# 检查数据库连接
docker exec pepgmp-postgres-prod psql -U pepgmp_prod -d pepgmp_production -c "SELECT version();"

# 检查 Redis 连接
docker exec pepgmp-redis-prod redis-cli -a $(grep REDIS_PASSWORD .env.production | cut -d'=' -f2) ping
```

---

## 📋 快速检查清单

部署前检查：

- [ ] 镜像已导入到 WSL2（`docker images | grep pepgmp`）
- [ ] 部署目录已创建（`~/projects/Pyt`）
- [ ] Docker Compose 文件已复制（`docker-compose.prod.yml`）
- [ ] 配置文件目录已复制（`config/`）
- [ ] 模型文件目录已复制（`models/`，如果需要）
- [ ] 配置文件已生成（`.env.production`）
- [ ] 镜像标签已设置（`IMAGE_TAG=20251201`）
- [ ] 凭证信息已保存（`.env.production.credentials`）

部署后检查：

- [ ] 所有容器状态为"运行中"
- [ ] API 健康检查通过（`curl http://localhost:8000/api/v1/monitoring/health`）
- [ ] 数据库连接正常
- [ ] Redis 连接正常
- [ ] 日志无错误信息

---

## 🔄 更新部署

### 更新镜像

```bash
# 1. 在 Windows 中构建新镜像
# 2. 导出镜像
docker save pepgmp-backend:新标签 -o pepgmp-backend-新标签.tar

# 3. 在 WSL2 中导入新镜像
docker load -i /mnt/c/Users/YourName/Code/PythonCode/Pyt/pepgmp-backend-新标签.tar

# 4. 更新配置文件中的 IMAGE_TAG
cd ~/projects/Pyt
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=新标签/' .env.production

# 5. 在 1Panel 中重启服务
# 或在命令行中：
docker compose -f docker-compose.prod.yml up -d --force-recreate api
```

### 更新配置

```bash
# 1. 修改配置文件
cd ~/projects/Pyt
nano .env.production

# 2. 在 1Panel 中重启服务
# 或在命令行中：
docker compose -f docker-compose.prod.yml restart api
```

---

## 🐛 故障排查

### 问题1: 容器无法启动

**检查步骤**：
1. 在 1Panel 中查看容器日志
2. 检查环境变量配置是否正确
3. 检查镜像是否存在：`docker images | grep pepgmp`
4. 检查镜像标签是否匹配：`grep IMAGE_TAG .env.production`

### 问题2: 配置文件不完整

**解决方案**：
```bash
cd ~/projects/Pyt

# 重新生成配置文件
bash scripts/generate_production_config.sh
```

### 问题3: 镜像标签不匹配

**解决方案**：
```bash
cd ~/projects/Pyt

# 检查已导入的镜像标签
docker images | grep pepgmp

# 更新配置文件中的镜像标签
nano .env.production
# 修改 IMAGE_TAG=你的镜像标签

# 重启服务
docker compose -f docker-compose.prod.yml up -d --force-recreate api
```

---

## 📚 相关文档

- [1Panel 部署指南](1PANEL_DEPLOYMENT_GUIDE.md)
- [WSL2 最小化部署指南](WSL2_MINIMAL_DEPLOYMENT.md)
- [WSL2 快速部署指南](WSL2_DEPLOYMENT_QUICK_START.md)

---

## 🎯 快速参考命令

```bash
# 准备部署包
bash /mnt/c/Users/YourName/Code/PythonCode/Pyt/scripts/prepare_minimal_deploy.sh

# 生成配置文件
cd ~/projects/Pyt && bash scripts/generate_production_config.sh

# 验证配置
docker compose -f docker-compose.prod.yml config

# 启动服务（命令行方式）
docker compose -f docker-compose.prod.yml up -d

# 查看状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f api

# 健康检查
curl http://localhost:8000/api/v1/monitoring/health
```

---

**最后更新**: 2025-12-01  
**适用版本**: WSL2 Ubuntu + 1Panel

