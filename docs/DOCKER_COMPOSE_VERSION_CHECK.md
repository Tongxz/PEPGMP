# Docker Compose 版本检查

## 问题

错误：`unknown shorthand flag: 'f' in -f`

这通常表示使用的是独立的 `docker-compose` 工具（带连字符），而不是 Docker CLI 插件版本（空格分隔）。

## 解决方案

### 使用 docker-compose（带连字符）

如果你的系统使用的是 `docker-compose`（带连字符），请使用以下命令：

```bash
# 验证配置
docker-compose -f docker-compose.prod.yml config

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

### 方法2: 升级到 Docker Compose V2（推荐）

```bash
# 检查当前版本
docker-compose --version
docker compose version

# 如果只有 V1，需要升级
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 或使用 Docker Desktop（已包含 V2）
```

### 方法3: 创建别名（临时解决）

```bash
# 在 ~/.bashrc 中添加
alias docker-compose='docker compose'

# 重新加载
source ~/.bashrc
```

## 验证

```bash
# 检查版本
docker compose version
# 应该显示：Docker Compose version v2.x.x

# 或
docker-compose --version
# 应该显示：docker-compose version 1.x.x 或 2.x.x
```

