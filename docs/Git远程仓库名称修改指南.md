# Git远程仓库名称修改指南

**更新时间**: 2025-01-03
**适用场景**: 修改 Git 远程仓库的 URL 或名称

---

## 📋 当前远程仓库配置

```bash
$ git remote -v

origin      https://github.com/Tongxz/Pyt.git (fetch)
origin      https://github.com/Tongxz/Pyt.git (push)
internal    git@192.168.30.83:Pyt.git (fetch)
internal    git@192.168.30.83:Pyt.git (push)
```

---

## 🎯 修改场景

### 场景1: 仓库在 Git 平台上已重命名

如果仓库在 GitHub/GitLab 上已经重命名（例如：`Pyt` → `PEPGMP`），需要更新本地远程 URL。

### 场景2: 修改远程仓库别名

如果想修改远程仓库的别名（例如：`origin` → `github`）。

### 场景3: 修改远程仓库 URL

如果想改变远程仓库的 URL（例如：从 HTTPS 改为 SSH，或更改服务器地址）。

---

## 🔧 修改方法

### 方法1: 修改现有远程仓库 URL

#### 1.1 修改 `origin` 远程仓库 URL

```bash
# 查看当前远程仓库
git remote -v

# 修改 origin 的 URL（假设仓库已重命名为 PEPGMP）
git remote set-url origin https://github.com/Tongxz/PEPGMP.git

# 验证修改
git remote -v
```

#### 1.2 修改 `internal` 远程仓库 URL

```bash
# 修改 internal 的 URL
git remote set-url internal git@192.168.30.83:PEPGMP.git

# 验证修改
git remote -v
```

---

### 方法2: 重命名远程仓库别名

```bash
# 将 origin 重命名为 github
git remote rename origin github

# 将 internal 重命名为 gitlab
git remote rename internal gitlab

# 验证修改
git remote -v
```

---

### 方法3: 删除并重新添加远程仓库

```bash
# 删除现有的远程仓库
git remote remove origin

# 添加新的远程仓库
git remote add origin https://github.com/Tongxz/PEPGMP.git

# 或添加多个远程仓库
git remote add github https://github.com/Tongxz/PEPGMP.git
git remote add internal git@192.168.30.83:PEPGMP.git

# 验证修改
git remote -v
```

---

## 📝 完整修改步骤示例

### 示例1: 将仓库重命名为 PEPGMP

假设 GitHub 仓库已从 `Pyt` 重命名为 `PEPGMP`：

```bash
# 步骤1: 查看当前配置
git remote -v

# 步骤2: 修改 origin 远程 URL
git remote set-url origin https://github.com/Tongxz/PEPGMP.git

# 步骤3: 修改 internal 远程 URL（如果有）
git remote set-url internal git@192.168.30.83:PEPGMP.git

# 步骤4: 验证修改
git remote -v

# 步骤5: 测试连接（可选）
git fetch origin
```

### 示例2: 从 HTTPS 改为 SSH（或相反）

```bash
# 从 HTTPS 改为 SSH
git remote set-url origin git@github.com:Tongxz/PEPGMP.git

# 从 SSH 改为 HTTPS
git remote set-url origin https://github.com/Tongxz/PEPGMP.git

# 验证修改
git remote -v
```

### 示例3: 添加多个远程仓库

```bash
# 添加 GitHub 远程仓库
git remote add github https://github.com/Tongxz/PEPGMP.git

# 添加内部 GitLab 远程仓库
git remote add internal git@192.168.30.83:PEPGMP.git

# 添加备用远程仓库（可选）
git remote add backup https://gitee.com/Tongxz/PEPGMP.git

# 查看所有远程仓库
git remote -v

# 推送到特定远程仓库
git push github main
git push internal main
```

---

## 🔍 常用命令

### 查看远程仓库信息

```bash
# 查看所有远程仓库
git remote -v

# 查看远程仓库详细信息
git remote show origin

# 查看远程仓库 URL
git remote get-url origin
```

### 修改远程仓库

```bash
# 修改远程仓库 URL
git remote set-url <远程名称> <新的URL>

# 重命名远程仓库
git remote rename <旧名称> <新名称>

# 删除远程仓库
git remote remove <远程名称>

# 添加远程仓库
git remote add <名称> <URL>
```

---

## ⚠️ 注意事项

### 1. 仓库名称变更流程

如果仓库在 GitHub/GitLab 上需要重命名：

**GitHub**:
1. 登录 GitHub
2. 进入仓库页面
3. 点击 "Settings" → "General"
4. 在 "Repository name" 部分输入新名称
5. 点击 "Rename"
6. 更新本地远程 URL（见上面的步骤）

**GitLab**:
1. 登录 GitLab
2. 进入仓库页面
3. 点击 "Settings" → "General" → "Advanced"
4. 展开 "Rename repository"
5. 输入新路径
6. 点击 "Rename project"
7. 更新本地远程 URL

### 2. 团队协作注意事项

- ✅ **通知团队成员**: 仓库重命名后，所有团队成员都需要更新本地远程 URL
- ✅ **更新 CI/CD**: 如果有 CI/CD 配置，需要更新仓库 URL
- ✅ **更新文档**: 更新所有文档中的仓库 URL 引用
- ✅ **更新 Webhook**: 如果有第三方服务集成，需要更新 Webhook URL

### 3. 推送和拉取

修改远程 URL 后：

```bash
# 首次推送前，验证远程连接
git fetch origin

# 如果出现认证问题，可能需要更新凭证
git config --global credential.helper store

# 推送代码
git push origin main

# 或者指定远程和分支
git push -u origin develop
```

---

## 📚 推荐配置

### 推荐配置：多个远程仓库

```bash
# 主要远程仓库（GitHub）
git remote add origin https://github.com/Tongxz/PEPGMP.git

# 内部镜像仓库（可选）
git remote add internal git@192.168.30.83:PEPGMP.git

# 查看配置
git remote -v

# 应该看到：
# origin      https://github.com/Tongxz/PEPGMP.git (fetch)
# origin      https://github.com/Tongxz/PEPGMP.git (push)
# internal    git@192.168.30.83:PEPGMP.git (fetch)
# internal    git@192.168.30.83:PEPGMP.git (push)
```

### 同时推送到多个远程仓库

```bash
# 方法1: 逐个推送
git push origin main
git push internal main

# 方法2: 配置多个 push URL（不推荐，容易混乱）
git remote set-url --add --push origin https://github.com/Tongxz/PEPGMP.git
git remote set-url --add --push origin git@192.168.30.83:PEPGMP.git
```

---

## 🚀 快速修改脚本

### 脚本：批量更新远程仓库 URL

创建脚本 `scripts/update_git_remote.sh`:

```bash
#!/bin/bash
# 更新 Git 远程仓库 URL

set -e

OLD_REPO_NAME="Pyt"
NEW_REPO_NAME="PEPGMP"
GITHUB_USER="Tongxz"
INTERNAL_SERVER="192.168.30.83"

echo "🔄 更新 Git 远程仓库 URL..."

# 更新 origin (GitHub)
if git remote get-url origin &>/dev/null; then
    OLD_URL=$(git remote get-url origin)
    NEW_URL=$(echo "$OLD_URL" | sed "s|/$OLD_REPO_NAME\.git|/$NEW_REPO_NAME.git|g" | sed "s|/$OLD_REPO_NAME$|/$NEW_REPO_NAME.git|g")

    if [ "$OLD_URL" != "$NEW_URL" ]; then
        echo "  修改 origin: $OLD_URL → $NEW_URL"
        git remote set-url origin "$NEW_URL"
    else
        echo "  origin 已是最新配置"
    fi
fi

# 更新 internal
if git remote get-url internal &>/dev/null; then
    OLD_URL=$(git remote get-url internal)
    NEW_URL=$(echo "$OLD_URL" | sed "s|:$OLD_REPO_NAME\.git|:$NEW_REPO_NAME.git|g" | sed "s|:$OLD_REPO_NAME$|:$NEW_REPO_NAME.git|g")

    if [ "$OLD_URL" != "$NEW_URL" ]; then
        echo "  修改 internal: $OLD_URL → $NEW_URL"
        git remote set-url internal "$NEW_URL"
    else
        echo "  internal 已是最新配置"
    fi
fi

# 显示更新后的配置
echo ""
echo "✅ 当前远程仓库配置:"
git remote -v

# 测试连接
echo ""
echo "🔍 测试远程连接..."
if git fetch origin --dry-run &>/dev/null; then
    echo "  ✅ origin 连接正常"
else
    echo "  ⚠️  origin 连接失败，请检查 URL 和认证"
fi

if git remote get-url internal &>/dev/null; then
    if git fetch internal --dry-run &>/dev/null; then
        echo "  ✅ internal 连接正常"
    else
        echo "  ⚠️  internal 连接失败，请检查 URL 和认证"
    fi
fi

echo ""
echo "🎉 更新完成！"
```

**使用方法**:

```bash
# 给脚本添加执行权限
chmod +x scripts/update_git_remote.sh

# 运行脚本
./scripts/update_git_remote.sh
```

---

## 📋 检查清单

修改远程仓库前，请确认：

- [ ] 仓库在 Git 平台上已重命名（如果需要）
- [ ] 已通知团队成员更新远程 URL
- [ ] 已备份当前远程配置：`git remote -v > remote_backup.txt`
- [ ] 已更新 CI/CD 配置（如果有）
- [ ] 已更新文档中的仓库 URL
- [ ] 已测试远程连接：`git fetch origin`

---

## 🔗 相关文档

- [项目重命名指南](项目重命名指南.md)
- [Git 官方文档 - 远程仓库](https://git-scm.com/book/zh/v2/Git-基础-远程仓库的使用)

---

## 💡 常见问题

### Q1: 修改远程 URL 后，本地分支会受影响吗？

**A**: 不会。修改远程 URL 只影响推送和拉取的目标地址，不会影响本地分支和提交历史。

### Q2: 如何恢复原来的远程 URL？

**A**: 如果之前备份过，可以直接恢复。或者查看 Git 配置历史：

```bash
# 查看 Git 配置历史（如果启用了 reflog）
git reflog

# 或手动恢复
git remote set-url origin <原来的URL>
```

### Q3: 多个团队成员如何同步更新？

**A**: 创建并推送一个说明文档或脚本，团队成员依次执行：

```bash
# 团队成员执行
git remote set-url origin https://github.com/Tongxz/PEPGMP.git
git fetch origin
```

---

**提示**: 建议在修改远程仓库 URL 前，先在测试仓库中验证操作流程。
