# 修复 Ubuntu 终端中文乱码问题

## 问题描述

在 WSL Ubuntu 中运行脚本时，中文显示为乱码。

## 解决方案

### 方法1: 设置 UTF-8 Locale（推荐）

在 WSL Ubuntu 终端中运行：

```bash
# 检查当前 locale
locale

# 设置 UTF-8 locale
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

# 或者使用英文 locale（避免乱码）
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# 永久设置（添加到 ~/.bashrc）
echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
source ~/.bashrc
```

### 方法2: 安装中文语言包

```bash
# 安装中文语言包
sudo apt-get update
sudo apt-get install -y language-pack-zh-hans

# 设置 locale
sudo locale-gen zh_CN.UTF-8
export LANG=zh_CN.UTF-8
```

### 方法3: 使用英文提示（最简单）

如果不想处理编码问题，可以修改脚本使用英文提示。

## 临时解决（当前会话）

```bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
bash scripts/generate_production_config.sh
```

