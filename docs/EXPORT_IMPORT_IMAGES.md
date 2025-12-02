# 导出和导入 Docker 镜像（Windows → WSL2）

## 问题说明

你在 Windows 上构建了 Docker 镜像，但 1Panel 运行在 WSL2 Ubuntu 中。需要将镜像从 Windows 导出，然后导入到 WSL2 中。

## 完整流程

### 步骤 1: 在 Windows 上导出镜像

在 Windows PowerShell 中运行：

```powershell
# 进入项目目录
cd F:\Code\PythonCode\Pyt

# 导出镜像（使用你构建时的标签，例如 20251201）
.\scripts\export_images_to_wsl.ps1 20251201
```

**脚本会**：
- 检查镜像是否存在
- 导出后端镜像到 `docker-images/pepgmp-backend-20251201.tar`
- 如果存在，导出前端镜像到 `docker-images/pepgmp-frontend-20251201.tar`
- 显示文件大小和下一步操作说明

**输出示例**：
```
=========================================================================
Export Docker Images to WSL2
=========================================================================

Version Tag: 20251201

[OK] Backend image found: pepgmp-backend:20251201
[OK] Frontend image found: pepgmp-frontend:20251201

Export directory: F:\Code\PythonCode\Pyt\docker-images

Exporting backend image...
  Image: pepgmp-backend:20251201
  Output: F:\Code\PythonCode\Pyt\docker-images\pepgmp-backend-20251201.tar
[OK] Backend image exported successfully
  Size: 1234.56 MB

...

Next steps (in WSL2 Ubuntu):
  1. Import backend image:
     cd /mnt/f/code/PythonCode/Pyt/docker-images
     docker load -i pepgmp-backend-20251201.tar
```

### 步骤 2: 在 WSL2 Ubuntu 中导入镜像

在 WSL2 Ubuntu 中运行：

```bash
# 方法1: 使用导入脚本（推荐）
cd /mnt/f/code/PythonCode/Pyt
bash scripts/import_images_from_windows.sh 20251201

# 方法2: 手动导入
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-backend-20251201.tar

# 如果构建了前端镜像
docker load -i pepgmp-frontend-20251201.tar
```

**导入脚本会自动**：
- 检查镜像文件是否存在
- 导入后端镜像
- 如果存在，导入前端镜像
- 验证镜像是否正确导入
- 检查 `.env.production` 中的 `IMAGE_TAG` 是否匹配

### 步骤 3: 验证镜像已导入

```bash
# 在 WSL2 Ubuntu 中
docker images | grep pepgmp

# 应该看到：
# pepgmp-backend    20251201    ...    ...    ...
# pepgmp-backend    latest      ...    ...    ...
# pepgmp-frontend   20251201    ...    ...    ...（如果构建了）
```

### 步骤 4: 确保配置文件中的镜像标签正确

```bash
cd ~/projects/Pyt

# 检查镜像标签
grep IMAGE_TAG .env.production

# 应该显示：IMAGE_TAG=20251201

# 如果不匹配，更新配置文件
sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=20251201/' .env.production
```

### 步骤 5: 在 1Panel 中部署

现在镜像已经在 WSL2 中，可以在 1Panel 中部署了：

1. **登录 1Panel**
2. **创建 Compose 项目**：
   - 项目名称：`pepgmp-production`
   - 工作目录：`/home/pep/projects/Pyt`
   - Compose 文件：`docker-compose.prod.yml`
3. **启动服务**

1Panel 会自动：
- 加载 `.env.production` 文件
- 使用 `IMAGE_TAG=20251201` 找到对应的镜像
- 启动所有服务

## 快速命令参考

### Windows 端（导出）

```powershell
# 导出镜像
.\scripts\export_images_to_wsl.ps1 20251201

# 检查导出的文件
ls docker-images\*.tar
```

### WSL2 端（导入）

```bash
# 导入镜像（自动）
bash scripts/import_images_from_windows.sh 20251201

# 或手动导入
cd /mnt/f/code/PythonCode/Pyt/docker-images
docker load -i pepgmp-backend-20251201.tar

# 验证
docker images | grep pepgmp

# 检查配置
cd ~/projects/Pyt
grep IMAGE_TAG .env.production
```

## 常见问题

### Q1: 导出文件很大，需要多长时间？

**A**: 镜像文件通常 1-3GB，导出时间取决于磁盘速度，通常需要 1-5 分钟。

### Q2: 可以只导出后端镜像吗？

**A**: 可以。脚本会自动检测，如果前端镜像不存在，只会导出后端镜像。

### Q3: 导入后镜像标签不对怎么办？

**A**: 检查 `.env.production` 中的 `IMAGE_TAG`，确保与导入的镜像标签一致。

### Q4: 如果 Docker Desktop 启用了 WSL2 集成，还需要导出吗？

**A**: 如果 Docker Desktop 已启用 WSL2 集成，镜像会自动共享，可以直接使用：

```bash
# 在 WSL2 中检查
wsl docker images | grep pepgmp
```

如果能看到镜像，就不需要导出/导入了。

### Q5: 如何更新镜像？

**A**: 重新构建 → 重新导出 → 重新导入：

```powershell
# Windows: 重新构建
.\scripts\build_prod_only.ps1 20251201

# Windows: 重新导出
.\scripts\export_images_to_wsl.ps1 20251201

# WSL2: 重新导入（会覆盖旧镜像）
bash scripts/import_images_from_windows.sh 20251201
```

## 文件位置

- **导出目录（Windows）**: `F:\Code\PythonCode\Pyt\docker-images\`
- **WSL2 路径**: `/mnt/f/code/PythonCode/Pyt/docker-images/`
- **部署目录（WSL2）**: `~/projects/Pyt/`

## 注意事项

1. **镜像标签必须一致**：构建、导出、导入、配置文件中的标签必须相同
2. **文件大小**：镜像文件通常很大（1-3GB），确保有足够的磁盘空间
3. **网络路径**：WSL2 访问 Windows 文件系统（`/mnt/f/...`）可能较慢，但导入操作通常很快
4. **权限**：确保有读写权限

