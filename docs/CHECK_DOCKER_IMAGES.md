# 检查 Docker 镜像

## 检查 Windows 上的镜像

在 Windows PowerShell 中运行：

```powershell
# 查看所有 pepgmp 相关镜像
docker images | Select-String "pepgmp"

# 或者查看所有镜像并按大小排序
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | Select-String "pepgmp"
```

## 检查 WSL2 Ubuntu 上的镜像

在 WSL2 Ubuntu 中运行：

```bash
# 查看所有 pepgmp 相关镜像
docker images | grep pepgmp

# 查看详细信息
docker images pepgmp-backend
docker images pepgmp-frontend

# 查看镜像大小
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep pepgmp
```

## 预期结果

应该看到以下镜像：

### 后端镜像
- `pepgmp-backend:20251201`（或你构建时使用的标签）
- `pepgmp-backend:latest`

### 前端镜像（如果构建了）
- `pepgmp-frontend:20251201`
- `pepgmp-frontend:latest`

## 如果镜像在 Windows 上，需要导出到 WSL2

### 方法 1: 使用 Docker Desktop WSL2 集成（推荐）

如果 Docker Desktop 已启用 WSL2 集成，镜像会自动共享。

检查 WSL2 集成：
```powershell
# 在 PowerShell 中
wsl docker images | grep pepgmp
```

### 方法 2: 手动导出和导入

#### 步骤 1: 在 Windows 上导出镜像

```powershell
# 在 PowerShell 中
cd F:\Code\PythonCode\Pyt

# 导出后端镜像
docker save pepgmp-backend:20251201 -o pepgmp-backend-20251201.tar

# 导出前端镜像（如果构建了）
docker save pepgmp-frontend:20251201 -o pepgmp-frontend-20251201.tar
```

#### 步骤 2: 复制到 WSL2

```bash
# 在 WSL2 Ubuntu 中
# 从 Windows 路径复制到 WSL2
cp /mnt/f/code/PythonCode/Pyt/pepgmp-backend-20251201.tar ~/pepgmp-backend-20251201.tar

# 如果构建了前端
cp /mnt/f/code/PythonCode/Pyt/pepgmp-frontend-20251201.tar ~/pepgmp-frontend-20251201.tar
```

#### 步骤 3: 在 WSL2 中导入镜像

```bash
# 在 WSL2 Ubuntu 中
cd ~

# 导入后端镜像
docker load -i pepgmp-backend-20251201.tar

# 导入前端镜像（如果构建了）
docker load -i pepgmp-frontend-20251201.tar

# 验证导入
docker images | grep pepgmp
```

## 验证镜像标签

确保镜像标签与 `.env.production` 中的 `IMAGE_TAG` 一致：

```bash
# 在 WSL2 Ubuntu 中
cd ~/projects/Pyt

# 检查配置文件中的镜像标签
grep IMAGE_TAG .env.production

# 检查 Docker 镜像标签
docker images | grep pepgmp-backend
```

如果标签不一致，需要：
1. 重新构建镜像并指定正确的标签
2. 或者更新 `.env.production` 中的 `IMAGE_TAG`

## 快速检查脚本

创建检查脚本：

```bash
#!/bin/bash
echo "========================================================================="
echo "Checking Docker Images"
echo "========================================================================="
echo ""
echo "Backend images:"
docker images | grep pepgmp-backend || echo "No backend images found"
echo ""
echo "Frontend images:"
docker images | grep pepgmp-frontend || echo "No frontend images found"
echo ""
echo "========================================================================="
echo "Checking .env.production IMAGE_TAG:"
grep IMAGE_TAG ~/projects/Pyt/.env.production 2>/dev/null || echo "No .env.production found"
echo "========================================================================="
```

