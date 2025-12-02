# 在 WSL 中修复行尾符问题

## 快速修复命令

在 **WSL2 Ubuntu** 中运行以下命令：

```bash
cd /mnt/f/code/PythonCode/Pyt

# 方法1: 使用 sed 修复所有 .sh 文件（推荐）
find scripts/ -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;

# 方法2: 修复特定文件
sed -i 's/\r$//' scripts/generate_production_config.sh
sed -i 's/\r$//' scripts/prepare_minimal_deploy.sh
sed -i 's/\r$//' scripts/start_prod_wsl.sh

# 验证修复
file scripts/generate_production_config.sh
# 应该显示：ASCII text（而不是 "with CRLF line terminators"）

# 测试运行
bash scripts/generate_production_config.sh
```

## 如果 sed 命令不可用

```bash
# 使用 tr 命令
tr -d '\r' < scripts/generate_production_config.sh > scripts/generate_production_config.sh.tmp
mv scripts/generate_production_config.sh.tmp scripts/generate_production_config.sh
chmod +x scripts/generate_production_config.sh
```

## 安装 dos2unix（推荐）

```bash
# 安装 dos2unix
sudo apt-get update
sudo apt-get install -y dos2unix

# 修复所有脚本文件
dos2unix scripts/*.sh

# 验证
file scripts/generate_production_config.sh
```

