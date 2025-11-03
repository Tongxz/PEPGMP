# Docker 快速命令参考

## 🚀 一键启动命令

```bash
# ✨ 推荐：使用整合版（最简单）
docker-compose -f docker-compose.prod.full.yml up -d

# 基础环境 + MLOps
docker-compose -f docker-compose.prod.full.yml --profile mlops up -d

# 完整环境（所有服务）
docker-compose -f docker-compose.prod.full.yml \
  --profile mlops \
  --profile monitoring \
  up -d
```

## 📋 服务配置对比

| 配置文件 | 服务 | 推荐场景 |
|---------|------|----------|
| `docker-compose.prod.full.yml` ✨ | API+DB+Redis+可选MLOps | **生产环境（推荐）** |
| `docker-compose.prod.yml` | API+DB+Redis | 基础环境 |
| `docker-compose.prod.mlops.yml` | MLflow+DVC | MLOps扩展 |
| `docker-compose.dev-db.yml` | DB+Redis | 开发环境 |

## 🎯 常用命令

### 启动服务
```bash
# 后台启动
docker-compose -f docker-compose.prod.full.yml up -d

# 前台启动（查看日志）
docker-compose -f docker-compose.prod.full.yml up

# 构建并启动
docker-compose -f docker-compose.prod.full.yml up -d --build
```

### 查看状态
```bash
# 查看所有容器
docker-compose -f docker-compose.prod.full.yml ps

# 查看日志
docker-compose -f docker-compose.prod.full.yml logs -f api

# 查看资源使用
docker stats
```

### 停止服务
```bash
# 停止（保留数据）
docker-compose -f docker-compose.prod.full.yml stop

# 停止并删除容器（保留数据卷）
docker-compose -f docker-compose.prod.full.yml down

# 停止并删除所有（包括数据）⚠️ 危险
docker-compose -f docker-compose.prod.full.yml down -v
```

### 重启服务
```bash
# 重启所有
docker-compose -f docker-compose.prod.full.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.full.yml restart api
```

## 🔍 健康检查

```bash
# API健康检查
curl http://localhost:8000/api/v1/monitoring/health

# 查看监控指标
curl http://localhost:8000/api/v1/monitoring/metrics

# 数据库连接测试
docker-compose -f docker-compose.prod.full.yml exec database \
  pg_isready -U pyt_prod
```

## 💡 为什么用 Dockerfile + docker-compose？

### Dockerfile（构建镜像）
```bash
# 单独构建
docker build -f Dockerfile.prod -t pyt-backend:latest .
```
- 定义**如何构建**应用镜像
- 安装依赖、复制代码
- 类似"做蛋糕的配方"

### docker-compose（运行环境）
```bash
# 启动完整环境
docker-compose -f docker-compose.prod.full.yml up -d
```
- 定义**如何运行**多个容器
- 配置网络、数据卷、环境变量
- 类似"摆餐桌的规则"

### 组合使用
```bash
# 1. Dockerfile构建镜像（或docker-compose自动构建）
docker build -f Dockerfile.prod -t pyt-backend:latest .

# 2. docker-compose启动所有服务
docker-compose -f docker-compose.prod.full.yml up -d
```

## 📚 相关文档

- 详细指南: `docs/docker_compose_usage_guide.md`
- Docker构建报告: `docs/docker_build_success_report.md`
- 生产部署指南: `docs/production_deployment_guide.md`

---

**快速帮助**: `docker-compose -f docker-compose.prod.full.yml --help`
