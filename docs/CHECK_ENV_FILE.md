# 检查环境变量文件

## 问题

配置验证显示环境变量为 `CHANGE_ME`，说明 `.env.production` 文件可能：
1. 包含占位符而不是实际密码
2. 文件格式不正确
3. 文件路径不对

## 检查步骤

在 WSL Ubuntu 中运行：

```bash
cd ~/projects/Pyt

# 1. 检查文件是否存在
ls -la .env.production

# 2. 查看文件内容（前30行）
head -30 .env.production

# 3. 检查关键变量
grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD|IMAGE_TAG' .env.production

# 4. 检查是否有 CHANGE_ME 占位符
grep CHANGE_ME .env.production

# 5. 检查文件格式（应该是 KEY=value 格式，没有引号）
grep '^DATABASE_PASSWORD=' .env.production
```

## 如果文件包含 CHANGE_ME

说明配置文件没有正确生成，需要重新生成：

```bash
cd ~/projects/Pyt

# 删除旧文件
rm .env.production

# 重新生成
bash scripts/generate_production_config.sh

# 按提示输入：
# - API Port [8000]: 回车
# - Admin Username [admin]: 回车
# - CORS Origins [*]: 回车
# - Image Tag [latest]: 20251201  ← 重要！
```

## 验证生成的文件

```bash
# 检查密码是否已生成（不应该是 CHANGE_ME）
grep DATABASE_PASSWORD .env.production
# 应该看到类似：DATABASE_PASSWORD=实际的强随机密码

# 检查镜像标签
grep IMAGE_TAG .env.production
# 应该看到：IMAGE_TAG=20251201
```

