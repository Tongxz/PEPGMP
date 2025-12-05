# WSL 下 Git 代码同步指南

**更新时间**: 2025-12-04  
**适用场景**: 在 Windows WSL 环境中同步 Git 代码

---

## 📋 概述

WSL（Windows Subsystem for Linux）环境中的代码同步主要有两种场景：

1. **Git 远程仓库同步** - 从远程 Git 仓库拉取/推送代码（与 Linux/macOS 类似）
2. **Windows 文件系统同步** - 将代码从 Windows 文件系统（`/mnt/c/...`）复制到 WSL 文件系统（`~/projects/...`）

**推荐方式**：
- ✅ 优先使用 **Git 远程仓库同步**（代码在 Git 仓库中）
- ✅ 如需从 Windows 同步，使用 **rsync 或同步脚本**（性能更好）

---

## 🔧 场景 1: Git 远程仓库同步

### 前提条件

- ✅ 远程仓库已在 Git 平台（GitHub/GitLab）上重命名（从 `Pyt` 改为 `PEPGMP`）
- ✅ WSL 中已安装 Git
- ✅ SSH 密钥已配置（或使用 HTTPS 认证）

### 方式 1: 使用自动化脚本（推荐）

#### 步骤 1: 打开 WSL 终端

```bash
# 在 Windows 中打开 WSL
wsl

# 或从 Windows Terminal 选择 WSL 标签页
```

#### 步骤 2: 进入项目目录

```bash
# 如果代码在 WSL 文件系统中
cd ~/projects/PEPGMP

# 或如果代码在 Windows 文件系统中（不推荐，性能较差）
cd /mnt/c/Users/YourName/Code/PEPGMP
```

#### 步骤 3: 运行更新脚本

```bash
# 运行 Git 远程仓库更新脚本
bash scripts/update_git_remote.sh
```

脚本会自动：
- 检测当前远程仓库配置
- 更新 `origin` 和 `internal` 远程 URL
- 可选择测试连接

#### 步骤 4: 验证更新

```bash
# 查看远程仓库配置
git remote -v

# 应该看到：
# origin      https://github.com/Tongxz/PEPGMP.git (fetch)
# origin      https://github.com/Tongxz/PEPGMP.git (push)
# internal    git@192.168.30.83:PEPGMP.git (fetch)
# internal    git@192.168.30.83:PEPGMP.git (push)
```

#### 步骤 5: 同步代码

```bash
# 拉取最新代码
git fetch origin
git pull origin develop

# 或拉取所有远程分支
git fetch --all
```

---

### 方式 2: 手动更新（适用于自定义配置）

#### 步骤 1: 查看当前配置

```bash
cd ~/projects/PEPGMP
git remote -v
```

#### 步骤 2: 更新远程 URL

```bash
# 更新 origin (GitHub)
git remote set-url origin https://github.com/Tongxz/PEPGMP.git

# 或使用 SSH（推荐，更安全）
git remote set-url origin git@github.com:Tongxz/PEPGMP.git

# 更新 internal（如果有）
git remote set-url internal git@192.168.30.83:PEPGMP.git
```

#### 步骤 3: 验证并同步

```bash
# 验证更新
git remote -v

# 测试连接
git fetch origin

# 拉取代码
git pull origin develop
```

---

## 📁 场景 2: Windows 文件系统同步到 WSL

### 为什么需要同步？

**性能差异**：
- Windows 文件系统（`/mnt/c/...`）I/O 性能较差，Docker 构建会很慢
- WSL 文件系统（`~/projects/...`）性能更好，构建速度快 2-3 倍

**性能对比**：
- Windows 文件系统构建：约 30-40 分钟（首次）
- WSL 文件系统构建：约 15-25 分钟（首次）

### 方式 1: 使用同步脚本（推荐）

项目已提供同步脚本 `scripts/sync_code_to_wsl.sh`：

```bash
# 在 WSL 中执行
cd ~/projects

# 运行同步脚本（自动检测 Windows 项目路径）
bash PEPGMP/scripts/sync_code_to_wsl.sh

# 或指定源路径和目标路径
bash PEPGMP/scripts/sync_code_to_wsl.sh \
  /mnt/c/Users/YourName/Code/PEPGMP \
  ~/projects/PEPGMP
```

**脚本功能**：
- ✅ 自动检测源路径（Windows 文件系统）
- ✅ 排除不需要的文件（`.git`, `node_modules`, `venv` 等）
- ✅ 使用 rsync 增量同步（快速）
- ✅ 自动备份已存在的目标目录
- ✅ 验证同步结果

**排除的文件**：
- `.git` - Git 仓库（建议在 WSL 中重新 clone）
- `node_modules` - Node.js 依赖（会在构建时重新安装）
- `venv` - Python 虚拟环境（会在构建时重新创建）
- `__pycache__`, `*.pyc` - Python 缓存
- `dist`, `build` - 构建产物
- `logs`, `output` - 日志和输出文件
- `data`, `models` - 大数据文件（可选，根据需要）

---

### 方式 2: 使用 rsync（高效，支持增量）

```bash
# 在 WSL 中执行
cd ~/projects

# 首次同步（完整复制）
rsync -avz --progress \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='*.egg-info' \
  --exclude='logs' \
  --exclude='output' \
  /mnt/c/Users/YourName/Code/PEPGMP/ \
  ~/projects/PEPGMP/

# 后续更新（只同步变更的文件）
rsync -avz --progress \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='venv' \
  /mnt/c/Users/YourName/Code/PEPGMP/ \
  ~/projects/PEPGMP/
```

**rsync 参数说明**：
- `-a` - 归档模式（保留权限、时间戳等）
- `-v` - 显示详细信息
- `-z` - 压缩传输
- `--progress` - 显示进度
- `--exclude` - 排除文件/目录

---

### 方式 3: 使用 cp（简单但较慢）

```bash
# 在 WSL 中执行
cd ~/projects

# 复制整个目录（首次）
cp -r /mnt/c/Users/YourName/Code/PEPGMP ~/projects/PEPGMP

# 注意：cp 不支持增量更新，每次都是完整复制
```

---

### 方式 4: 直接使用 Windows 文件系统（不推荐）

如果不想复制，也可以直接在 Windows 文件系统中工作：

```bash
# 在 WSL 中
cd /mnt/c/Users/YourName/Code/PEPGMP

# 直接构建（性能较慢）
bash scripts/build_prod_only.sh 20251204
```

**缺点**：
- ❌ I/O 性能差，构建很慢
- ❌ 可能存在文件权限问题
- ❌ 某些脚本可能无法正常工作

---

## 🔄 完整工作流程

### 首次设置（代码在 Windows 中）

```bash
# 1. 打开 WSL 终端
wsl

# 2. 同步代码到 WSL 文件系统
cd ~/projects
bash /mnt/c/Users/YourName/Code/PEPGMP/scripts/sync_code_to_wsl.sh \
  /mnt/c/Users/YourName/Code/PEPGMP \
  ~/projects/PEPGMP

# 3. 进入项目目录
cd ~/projects/PEPGMP

# 4. 初始化 Git 仓库（如果还没有）
git remote -v
# 如果远程 URL 还是旧的，运行：
bash scripts/update_git_remote.sh

# 5. 拉取最新代码
git fetch origin
git pull origin develop

# 6. 设置工作环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 日常开发工作流（代码已同步到 WSL）

```bash
# 1. 在 WSL 中打开项目
cd ~/projects/PEPGMP

# 2. 拉取最新代码
git fetch origin
git pull origin develop

# 3. 进行开发...

# 4. 提交更改
git add .
git commit -m "feat: 添加新功能"
git push origin develop

# 5. 如果需要同步回 Windows（通常不需要）
# 代码已经在 Git 仓库中，Windows 中直接 pull 即可
```

---

### 定期同步工作流（代码在 Windows 中开发）

如果主要在 Windows 中开发，需要定期同步到 WSL：

```bash
# 在 WSL 中执行同步脚本
cd ~/projects
bash PEPGMP/scripts/sync_code_to_wsl.sh \
  /mnt/c/Users/YourName/Code/PEPGMP \
  ~/projects/PEPGMP

# 进入项目目录
cd ~/projects/PEPGMP

# 更新 Git 远程 URL（如果需要）
bash scripts/update_git_remote.sh

# 拉取最新代码
git fetch origin
git pull origin develop
```

---

## ⚠️ 常见问题

### 问题 1: Git 远程 URL 仍然是旧名称

**错误信息**:
```bash
fatal: repository 'https://github.com/Tongxz/Pyt.git' not found
```

**解决方案**:
```bash
# 运行更新脚本
bash scripts/update_git_remote.sh

# 或手动更新
git remote set-url origin https://github.com/Tongxz/PEPGMP.git
git remote -v  # 验证
```

---

### 问题 2: SSH 密钥未配置

**错误信息**:
```
Permission denied (publickey)
```

**解决方案**:

1. 检查 SSH 密钥是否存在：
```bash
ls -la ~/.ssh
```

2. 如果没有密钥，生成新的 SSH 密钥：
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

3. 将公钥添加到 GitHub/GitLab：
```bash
# 显示公钥内容
cat ~/.ssh/id_ed25519.pub
```
然后复制内容到 GitHub/GitLab 的 SSH 密钥设置中

4. 测试连接：
```bash
ssh -T git@github.com
```

---

### 问题 3: 文件权限问题

**问题**: 从 Windows 同步的文件权限可能不正确

**解决方案**:
```bash
# 在 WSL 项目目录中
cd ~/projects/PEPGMP

# 设置脚本可执行权限
chmod +x scripts/*.sh

# 设置目录权限
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;

# 设置脚本文件权限
find scripts -type f -name "*.sh" -exec chmod +x {} \;
```

---

### 问题 4: 同步脚本找不到源路径

**错误信息**:
```
源路径不存在: /mnt/c/Users/$USER/Code/PEPGMP
```

**解决方案**:

1. 检查 Windows 项目路径：
```bash
# 在 WSL 中列出 Windows 用户目录
ls -la /mnt/c/Users/

# 检查项目是否存在
ls -la /mnt/c/Users/YourWindowsUsername/Code/PEPGMP
```

2. 使用完整路径运行脚本：
```bash
bash scripts/sync_code_to_wsl.sh \
  /mnt/c/Users/YourWindowsUsername/Code/PEPGMP \
  ~/projects/PEPGMP
```

---

### 问题 5: rsync 未安装

**错误信息**:
```
rsync: command not found
```

**解决方案**:
```bash
# 在 Ubuntu/Debian 中
sudo apt update
sudo apt install rsync

# 在 Fedora/CentOS 中
sudo dnf install rsync
```

---

## 📋 快速参考

### Git 命令

```bash
# 查看远程仓库
git remote -v

# 更新远程 URL
git remote set-url origin <新URL>

# 拉取代码
git fetch origin
git pull origin develop

# 推送代码
git push origin develop

# 查看分支
git branch -a
```

### 同步命令

```bash
# 使用同步脚本
bash scripts/sync_code_to_wsl.sh [源路径] [目标路径]

# 使用 rsync
rsync -avz --progress --exclude='.git' <源路径>/ <目标路径>/

# 使用 cp
cp -r <源路径> <目标路径>
```

---

## 📚 相关文档

- [Windows 下 Git 远程仓库同步指南](./Windows下Git远程仓库同步指南.md) - Windows PowerShell 环境
- [WSL 直接构建部署指南](./WSL直接构建部署指南.md) - WSL 部署相关
- [项目重命名指南](./项目重命名指南.md) - 项目重命名相关

---

## 💡 最佳实践

1. **优先使用 Git 同步**：代码应保存在 Git 仓库中，通过 Git 拉取/推送同步
2. **WSL 文件系统性能更好**：从 Windows 文件系统同步到 WSL 文件系统后，在 WSL 中构建和部署
3. **定期同步**：如果同时在 Windows 和 WSL 中工作，定期同步代码
4. **使用自动化脚本**：利用项目提供的脚本简化操作
5. **排除不需要的文件**：同步时排除 `node_modules`、`venv` 等，在 WSL 中重新安装

---

**最后更新**: 2025-12-04

