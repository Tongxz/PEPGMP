# 修复脚本文件行尾符问题

## 问题描述

在 Windows 中编辑的脚本文件使用 CRLF（`\r\n`）行尾符，但在 Linux/WSL 中需要 LF（`\n`）行尾符。

**错误症状**：
```
./scripts/generate_production_config.sh: line 2: $'\r': command not found
./scripts/generate_production_config.sh: line 8: $'\r': command not found
```

## 解决方案

### 方法1: 使用 PowerShell 脚本（推荐）

在 **Windows PowerShell** 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fix_line_endings.ps1
```

### 方法2: 在 WSL 中使用 sed 命令

在 **WSL2 Ubuntu** 中运行：

```bash
# 修复单个文件
sed -i 's/\r$//' scripts/generate_production_config.sh
sed -i 's/\r$//' scripts/prepare_minimal_deploy.sh

# 或批量修复所有 .sh 文件
find scripts/ -name "*.sh" -exec sed -i 's/\r$//' {} \;
```

### 方法3: 使用 dos2unix（如果已安装）

在 **WSL2 Ubuntu** 中运行：

```bash
# 安装 dos2unix（如果未安装）
sudo apt-get update && sudo apt-get install -y dos2unix

# 修复文件
dos2unix scripts/generate_production_config.sh
dos2unix scripts/prepare_minimal_deploy.sh

# 或批量修复
dos2unix scripts/*.sh
```

### 方法4: 使用 Git 配置自动转换

在 **WSL2 Ubuntu** 中配置 Git：

```bash
# 配置 Git 自动转换行尾符
git config --global core.autocrlf input

# 重新检出文件
git checkout -- scripts/generate_production_config.sh
git checkout -- scripts/prepare_minimal_deploy.sh
```

## 验证修复

修复后，在 **WSL2 Ubuntu** 中验证：

```bash
# 检查文件类型
file scripts/generate_production_config.sh

# 应该显示：ASCII text（而不是 "with CRLF line terminators"）

# 测试运行
bash scripts/generate_production_config.sh
```

## 预防措施

### 1. 配置 Git 自动转换

在项目根目录创建 `.gitattributes`：

```
*.sh text eol=lf
*.bash text eol=lf
```

### 2. 配置编辑器

**VS Code**：
- 设置：`"files.eol": "\n"`
- 或在状态栏点击行尾符，选择 "LF"

**其他编辑器**：
- 确保保存为 Unix 格式（LF）

## 常见问题

### Q: 为什么会出现这个问题？

A: Windows 使用 CRLF（`\r\n`），Linux 使用 LF（`\n`）。在 Windows 中编辑的脚本在 Linux 中运行时会出错。

### Q: 如何避免这个问题？

A: 
1. 使用 `.gitattributes` 配置 Git
2. 配置编辑器使用 LF 行尾符
3. 在 WSL 中编辑脚本文件

### Q: 修复后还需要做什么？

A: 修复后可以正常在 WSL 中运行脚本。建议提交修复后的文件到 Git。

---

**最后更新**: 2025-12-01

