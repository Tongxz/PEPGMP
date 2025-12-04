# WSL 一键部署和快速更新指南

## 📋 概述

本指南提供 WSL/Ubuntu 环境下的**一键部署**和**快速更新**方案，与 macOS 部署脚本功能对等。

---

## 🚀 一键部署（首次部署）

### 使用一键部署脚本

```bash
# 在 WSL 中
cd ~/projects/Pyt

# 一键部署（自动构建镜像、准备配置、启动服务）
bash scripts/deploy_prod_wsl.sh

# 或指定部署目录和版本号
bash scripts/deploy_prod_wsl.sh ~/projects/PEPGMP-deploy 20251204
```

**脚本自动完成**：
1. ✅ 检查 Docker 环境
2. ✅ 检查端口可用性
3. ✅ 检查 GPU 支持（如需要）
4. ✅ 构建生产镜像（如需要）
5. ✅ 准备部署目录
6. ✅ 生成配置文件
7. ✅ 清理旧容器
8. ✅ 启动服务
9. ✅ 验证部署

### 跳过构建（使用已有镜像）

```bash
# 如果镜像已构建，可以跳过构建步骤
bash scripts/deploy_prod_wsl.sh ~/projects/PEPGMP-deploy 20251204 true
```

---

## 🔄 快速更新部署

### 更新所有服务（前后端）

```bash
# 在 WSL 中
cd ~/projects/Pyt

# 快速更新（自动构建、停止旧服务、启动新服务）
bash scripts/update_deployment_wsl.sh

# 或指定参数
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy 20251204 all
```

### 仅更新后端

```bash
# 只更新后端，前端保持不变
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy 20251204 backend
```

### 仅更新前端

```bash
# 只更新前端，后端保持不变
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy 20251204 frontend
```

**更新脚本自动完成**：
1. ✅ 同步代码（如需要）
2. ✅ 构建新镜像（根据更新类型）
3. ✅ 更新配置文件
4. ✅ 停止旧服务
5. ✅ 清理前端静态文件（如更新前端）
6. ✅ 启动新服务
7. ✅ 验证更新

---

## 📊 macOS vs WSL 部署对比

| 功能 | macOS | WSL |
|------|-------|-----|
| **一键部署** | ✅ `deploy_prod_macos.sh` | ✅ `deploy_prod_wsl.sh` |
| **快速更新** | ❌ 需要手动 | ✅ `update_deployment_wsl.sh` |
| **自动构建** | ✅ | ✅ |
| **自动配置** | ✅ | ✅ |
| **自动清理** | ✅ | ✅ |
| **自动验证** | ✅ | ✅ |

**现在 WSL 也有一键部署了！** 🎉

---

## 🎯 使用场景

### 场景 1: 首次部署

```bash
cd ~/projects/Pyt
bash scripts/deploy_prod_wsl.sh
```

### 场景 2: 代码更新后重新部署

```bash
cd ~/projects/Pyt

# 1. 同步代码（如果代码在 Windows 文件系统中）
# 可选：bash scripts/sync_code_to_wsl.sh

# 2. 快速更新部署
bash scripts/update_deployment_wsl.sh
```

### 场景 3: 仅更新后端代码

```bash
cd ~/projects/Pyt

# 1. 更新后端代码
# git pull 或手动更新

# 2. 仅更新后端
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy $(date +%Y%m%d) backend
```

### 场景 4: 仅更新前端代码

```bash
cd ~/projects/Pyt

# 1. 更新前端代码
# git pull 或手动更新

# 2. 仅更新前端
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy $(date +%Y%m%d) frontend
```

---

## 🔧 脚本参数说明

### deploy_prod_wsl.sh

```bash
bash scripts/deploy_prod_wsl.sh [DEPLOY_DIR] [VERSION_TAG] [SKIP_BUILD]
```

**参数**：
- `DEPLOY_DIR`: 部署目录（默认: `~/projects/PEPGMP-deploy`）
- `VERSION_TAG`: 镜像版本标签（默认: 当前日期，如 `20251204`）
- `SKIP_BUILD`: 是否跳过构建（默认: `false`，设置为 `true` 跳过构建）

**示例**：
```bash
# 使用默认值
bash scripts/deploy_prod_wsl.sh

# 指定部署目录和版本
bash scripts/deploy_prod_wsl.sh ~/projects/PEPGMPprod 20251204

# 跳过构建（使用已有镜像）
bash scripts/deploy_prod_wsl.sh ~/projects/PEPGMP-deploy 20251204 true
```

### update_deployment_wsl.sh

```bash
bash scripts/update_deployment_wsl.sh [DEPLOY_DIR] [VERSION_TAG] [UPDATE_TYPE]
```

**参数**：
- `DEPLOY_DIR`: 部署目录（默认: `~/projects/PEPGMP-deploy`）
- `VERSION_TAG`: 新镜像版本标签（默认: 当前日期）
- `UPDATE_TYPE`: 更新类型（默认: `all`）
  - `all`: 更新前后端
  - `backend`: 仅更新后端
  - `frontend`: 仅更新前端

**示例**：
```bash
# 更新所有服务
bash scripts/update_deployment_wsl.sh

# 仅更新后端
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy 20251204 backend

# 仅更新前端
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy 20251204 frontend
```

---

## 📝 完整工作流示例

### 首次部署

```bash
# 1. 进入项目目录
cd ~/projects/Pyt

# 2. 一键部署
bash scripts/deploy_prod_wsl.sh

# 完成！服务已启动
```

### 日常更新

```bash
# 1. 进入项目目录
cd ~/projects/Pyt

# 2. 更新代码（如果使用 Git）
git pull

# 或从 Windows 文件系统同步
bash scripts/sync_code_to_wsl.sh

# 3. 快速更新部署
bash scripts/update_deployment_wsl.sh

# 完成！服务已更新
```

### 仅更新后端

```bash
cd ~/projects/Pyt

# 更新后端代码
# ... 修改后端代码 ...

# 仅更新后端
VERSION_TAG=$(date +%Y%m%d)
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy $VERSION_TAG backend
```

### 仅更新前端

```bash
cd ~/projects/Pyt

# 更新前端代码
# ... 修改前端代码 ...

# 仅更新前端
VERSION_TAG=$(date +%Y%m%d)
bash scripts/update_deployment_wsl.sh ~/projects/PEPGMP-deploy $VERSION_TAG frontend
```

---

## 🎯 为什么之前需要多个命令？

### 原因分析

1. **macOS 脚本已存在**：`deploy_prod_macos.sh` 是一个完整的自动化脚本
2. **WSL 脚本缺失**：之前没有为 WSL 创建对应的自动化脚本
3. **文档导向**：之前的文档是分步骤的，适合学习和理解流程

### 现在的解决方案

✅ **已创建 WSL 一键部署脚本**：`deploy_prod_wsl.sh`
- 功能与 macOS 脚本对等
- 自动完成所有部署步骤

✅ **已创建快速更新脚本**：`update_deployment_wsl.sh`
- macOS 没有的功能
- 支持选择性更新（全部/后端/前端）

---

## 🔄 快速更新工作流

### 推荐工作流

```bash
# 1. 更新代码
cd ~/projects/Pyt
git pull  # 或同步代码

# 2. 快速更新部署
bash scripts/update_deployment_wsl.sh

# 完成！
```

### 更新类型选择

- **全部更新**（`all`）：前后端都更新，适合重大版本更新
- **仅后端**（`backend`）：只更新后端，前端保持不变，适合 API 更新
- **仅前端**（`frontend`）：只更新前端，后端保持不变，适合 UI 更新

---

## 📚 相关文档

- [WSL 直接构建部署指南](./WSL直接构建部署指南.md) - 详细的分步骤指南
- [跨网络 GPU 环境部署指南](./跨网络GPU环境部署指南.md) - 跨网络部署方案
- [容器名称冲突问题解决](./容器名称冲突问题解决.md) - 常见问题解决

---

**最后更新**: 2025-12-04
