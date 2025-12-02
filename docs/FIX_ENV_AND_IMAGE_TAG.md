# 修复环境变量和镜像标签问题

## 问题1: 环境变量显示为 CHANGE_ME

### 检查 .env.production 文件

```bash
cd ~/projects/Pyt

# 检查文件内容
cat .env.production | grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD'

# 如果显示 CHANGE_ME，说明文件没有正确生成
```

### 解决方案

如果文件包含 `CHANGE_ME`，需要重新生成：

```bash
cd ~/projects/Pyt

# 备份旧文件（可选）
cp .env.production .env.production.backup

# 删除旧文件
rm .env.production

# 重新生成
bash scripts/generate_production_config.sh

# 输入镜像标签：20251201
```

## 问题2: 镜像标签显示 latest

### 原因

Docker Compose 在解析 `image:` 行时，环境变量可能还没有被加载。需要使用 `--env-file` 参数明确指定。

### 解决方案

```bash
cd ~/projects/Pyt

# 方法1: 使用 --env-file 参数
docker-compose -f docker-compose.prod.yml --env-file .env.production config

# 方法2: 导出环境变量
export $(cat .env.production | grep -v '^#' | xargs)
docker-compose -f docker-compose.prod.yml config

# 方法3: 在 1Panel 中部署时，确保工作目录正确
# 1Panel 会自动加载 .env.production 文件
```

## 验证修复

```bash
cd ~/projects/Pyt

# 验证配置（使用 --env-file）
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'image:|IMAGE_TAG|DATABASE_PASSWORD|REDIS_PASSWORD'

# 应该看到：
# - image: pepgmp-backend:20251201（不再是 latest）
# - DATABASE_PASSWORD: 实际的强随机密码（不再是 CHANGE_ME）
# - REDIS_PASSWORD: 实际的强随机密码（不再是 CHANGE_ME）
```

## 在 1Panel 中部署

1Panel 会自动加载工作目录中的 `.env.production` 文件，所以：
- 确保工作目录正确：`/home/pep/projects/Pyt`
- 确保 `.env.production` 文件在该目录中
- 确保文件包含实际的密码（不是 CHANGE_ME）

