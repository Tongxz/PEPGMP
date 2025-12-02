# 修复环境变量加载问题

## 问题

运行 `docker-compose -f docker-compose.prod.yml config` 时出现警告：
- `WARN[0000] The "DATABASE_PASSWORD" variable is not set. Defaulting to a blank string.`
- `WARN[0000] The "REDIS_PASSWORD" variable is not set. Defaulting to a blank string.`

## 原因

`.env.production` 文件可能没有被正确加载，或者文件路径不对。

## 解决方案

### 方法1: 检查 .env.production 文件位置

```bash
cd ~/projects/Pyt

# 确认文件存在
ls -la .env.production

# 检查文件内容（前几行）
head -20 .env.production

# 检查关键变量
grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD|IMAGE_TAG' .env.production
```

### 方法2: 使用 --env-file 参数

```bash
# 明确指定环境变量文件
docker-compose -f docker-compose.prod.yml --env-file .env.production config
```

### 方法3: 检查 docker-compose.prod.yml 中的 env_file 配置

确保 Compose 文件中正确配置了 `env_file`：

```yaml
services:
  api:
    env_file:
      - .env.production
```

### 方法4: 在 1Panel 中配置

在 1Panel 的 Compose 项目设置中：
1. 确保工作目录正确：`/home/pep/projects/Pyt`
2. 确保 `.env.production` 文件在该目录中
3. 1Panel 会自动加载 `.env.production` 文件

## 验证

```bash
cd ~/projects/Pyt

# 方法1: 使用 --env-file
docker-compose -f docker-compose.prod.yml --env-file .env.production config | grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD|IMAGE_TAG'

# 方法2: 导出环境变量后验证
export $(cat .env.production | grep -v '^#' | xargs)
docker-compose -f docker-compose.prod.yml config | grep -E 'DATABASE_PASSWORD|REDIS_PASSWORD|IMAGE_TAG'
```

