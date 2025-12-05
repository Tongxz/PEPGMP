# Windows下Git远程仓库同步指南

**更新时间**: 2025-12-04  
**适用场景**: 项目名称和远程仓库名称已更改，需要在Windows环境下同步

---

## 📋 前提条件

- ✅ 本地项目目录已重命名（从 `Pyt` 改为 `PEPGMP`）
- ✅ 远程仓库已在Git平台（GitHub/GitLab）上重命名
- ✅ 本地Git仓库仍然存在（`.git` 目录未丢失）

---

## 🔧 同步步骤

### 方法1: 使用PowerShell（推荐）

#### 步骤1: 打开PowerShell

在Windows中：
1. 按 `Win + X`，选择 "Windows PowerShell" 或 "终端"
2. 或按 `Win + R`，输入 `powershell`，回车

#### 步骤2: 进入项目目录

```powershell
# 进入项目目录（根据您的实际路径调整）
cd C:\Users\YourName\Code\PEPGMP
# 或
cd F:\code\PythonCode\PEPGMP
```

#### 步骤3: 查看当前远程仓库配置

```powershell
git remote -v
```

**预期输出**（旧配置）:
```
origin      https://github.com/Tongxz/Pyt.git (fetch)
origin      https://github.com/Tongxz/Pyt.git (push)
internal    git@192.168.30.83:Pyt.git (fetch)
internal    git@192.168.30.83:Pyt.git (push)
```

#### 步骤4: 更新远程仓库URL

```powershell
# 更新 origin (GitHub)
git remote set-url origin https://github.com/Tongxz/PEPGMP.git

# 更新 internal (内部Git服务器，如果有)
git remote set-url internal git@192.168.30.83:PEPGMP.git
```

#### 步骤5: 验证更新

```powershell
git remote -v
```

**预期输出**（新配置）:
```
origin      https://github.com/Tongxz/PEPGMP.git (fetch)
origin      https://github.com/Tongxz/PEPGMP.git (push)
internal    git@192.168.30.83:PEPGMP.git (fetch)
internal    git@192.168.30.83:PEPGMP.git (push)
```

#### 步骤6: 测试连接

```powershell
# 测试 origin 连接
git fetch origin

# 测试 internal 连接（如果有）
git fetch internal
```

#### 步骤7: 同步远程分支

```powershell
# 拉取远程分支信息
git fetch --all

# 查看所有分支
git branch -a

# 如果主分支已重命名，更新本地分支跟踪
git branch --set-upstream-to=origin/develop develop
```

---

### 方法2: 使用Git Bash

如果您安装了Git for Windows，可以使用Git Bash：

#### 步骤1: 打开Git Bash

在项目目录右键，选择 "Git Bash Here"

#### 步骤2: 执行同步命令

```bash
# 查看当前配置
git remote -v

# 更新远程URL
git remote set-url origin https://github.com/Tongxz/PEPGMP.git
git remote set-url internal git@192.168.30.83:PEPGMP.git

# 验证
git remote -v

# 测试连接
git fetch origin
```

---

### 方法3: 使用自动化脚本

#### 创建PowerShell脚本

创建文件 `scripts/update_git_remote_windows.ps1`:

```powershell
# Windows下更新Git远程仓库URL
# Update Git Remote Repository URL on Windows

param(
    [string]$OldRepoName = "Pyt",
    [string]$NewRepoName = "PEPGMP",
    [string]$GitHubUser = "Tongxz",
    [string]$InternalServer = "192.168.30.83"
)

Write-Host "🔄 更新Git远程仓库URL..." -ForegroundColor Cyan
Write-Host ""

# 检查是否在Git仓库中
if (-not (Test-Path ".git")) {
    Write-Host "❌ 错误: 当前目录不是Git仓库" -ForegroundColor Red
    exit 1
}

# 显示当前配置
Write-Host "📋 当前远程仓库配置:" -ForegroundColor Yellow
git remote -v
Write-Host ""

# 更新 origin (GitHub)
$originUrl = git remote get-url origin 2>$null
if ($originUrl) {
    if ($originUrl -match "github.com") {
        $newOriginUrl = "https://github.com/${GitHubUser}/${NewRepoName}.git"
        Write-Host "🔄 更新 origin:" -ForegroundColor Cyan
        Write-Host "  旧: $originUrl"
        Write-Host "  新: $newOriginUrl"
        git remote set-url origin $newOriginUrl
        Write-Host "  ✅ origin 已更新" -ForegroundColor Green
    }
}

Write-Host ""

# 更新 internal
$internalUrl = git remote get-url internal 2>$null
if ($internalUrl) {
    if ($internalUrl -match $InternalServer) {
        $newInternalUrl = "git@${InternalServer}:${NewRepoName}.git"
        Write-Host "🔄 更新 internal:" -ForegroundColor Cyan
        Write-Host "  旧: $internalUrl"
        Write-Host "  新: $newInternalUrl"
        git remote set-url internal $newInternalUrl
        Write-Host "  ✅ internal 已更新" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ 更新后的远程仓库配置:" -ForegroundColor Yellow
git remote -v
Write-Host ""

# 测试连接
Write-Host "🔍 是否测试远程连接？(Y/N): " -NoNewline -ForegroundColor Cyan
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    Write-Host "测试 origin 连接..."
    git fetch origin --dry-run 2>&1 | Select-Object -First 5
    Write-Host ""
    
    if ($internalUrl) {
        Write-Host "测试 internal 连接..."
        git fetch internal --dry-run 2>&1 | Select-Object -First 5
    }
}

Write-Host ""
Write-Host "🎉 更新完成！" -ForegroundColor Green
Write-Host ""
Write-Host "💡 提示:" -ForegroundColor Yellow
Write-Host "  - 如果仓库在GitHub/GitLab上尚未重命名，请先在平台上重命名"
Write-Host "  - 如果连接测试失败，请检查仓库名称和认证信息"
```

**使用方法**:

```powershell
# 在项目根目录执行
.\scripts\update_git_remote_windows.ps1

# 或指定参数
.\scripts\update_git_remote_windows.ps1 -OldRepoName "Pyt" -NewRepoName "PEPGMP"
```

---

## ⚠️ 常见问题

### 问题1: 权限错误

**错误信息**:
```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

**解决方案**:
```powershell
# 使用SSH方式（推荐）
git remote set-url origin git@github.com:Tongxz/PEPGMP.git

# 或配置Git凭据管理器
git config --global credential.helper manager-core
```

### 问题2: SSH密钥未配置

**错误信息**:
```
Permission denied (publickey)
```

**解决方案**:
1. 检查SSH密钥是否存在：
   ```powershell
   # 查看SSH密钥
   ls ~/.ssh
   ```

2. 如果没有密钥，生成新的SSH密钥：
   ```powershell
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

3. 将公钥添加到GitHub/GitLab：
   ```powershell
   # 显示公钥内容
   cat ~/.ssh/id_ed25519.pub
   ```
   然后复制内容到GitHub/GitLab的SSH密钥设置中

### 问题3: 分支跟踪问题

**错误信息**:
```
fatal: The current branch develop has no upstream branch
```

**解决方案**:
```powershell
# 设置上游分支
git branch --set-upstream-to=origin/develop develop

# 或推送时设置
git push -u origin develop
```

---

## 📝 完整同步流程示例

### 场景：从旧仓库迁移到新仓库

```powershell
# 1. 进入项目目录
cd C:\Users\YourName\Code\PEPGMP

# 2. 查看当前状态
git status
git remote -v

# 3. 更新远程URL
git remote set-url origin https://github.com/Tongxz/PEPGMP.git
git remote set-url internal git@192.168.30.83:PEPGMP.git

# 4. 验证更新
git remote -v

# 5. 测试连接
git fetch origin

# 6. 拉取最新代码
git pull origin develop

# 7. 推送本地更改（如果有）
git push origin develop
```

---

## 🔍 验证清单

同步完成后，请验证：

- [ ] `git remote -v` 显示新的仓库URL
- [ ] `git fetch origin` 成功执行
- [ ] `git branch -a` 显示远程分支
- [ ] `git pull` 可以正常拉取代码
- [ ] `git push` 可以正常推送代码

---

## 📚 相关文档

- [Git远程仓库名称修改指南](Git远程仓库名称修改指南.md)
- [项目重命名指南](项目重命名指南.md)

---

## 💡 快速参考

### 常用命令

```powershell
# 查看远程仓库
git remote -v

# 更新远程URL
git remote set-url <远程名> <新URL>

# 删除远程仓库
git remote remove <远程名>

# 添加远程仓库
git remote add <远程名> <URL>

# 测试连接
git fetch <远程名>

# 拉取代码
git pull <远程名> <分支名>

# 推送代码
git push <远程名> <分支名>
```

---

**提示**: 如果遇到问题，请检查：
1. 远程仓库是否已在平台上重命名
2. 网络连接是否正常
3. 认证信息是否正确（SSH密钥或HTTPS凭据）

