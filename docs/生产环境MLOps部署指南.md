# 生产环境MLOps部署指南

## 📋 概述

本指南介绍如何在生产环境中部署包含MLOps功能的智能检测系统，包括MLflow实验跟踪、DVC模型版本管理和WebSocket实时通信。

## 🏗️ 架构变更

### 新增服务
- **MLflow服务器**: 实验跟踪和模型管理
- **DVC服务**: 数据版本控制
- **WebSocket支持**: 实时状态更新
- **Redis Pub/Sub**: 实时数据总线

### 存储需求
- **MLflow数据**: 实验元数据和指标
- **DVC缓存**: 模型和数据版本
- **实验数据**: `mlruns` 目录持久化

## 🚀 部署步骤

### 1. 环境准备

```bash
# 检查Docker环境
docker --version
docker-compose --version

# 检查GPU支持
nvidia-smi
```

### 2. 配置文件

创建 `.env.prod` 文件：

```bash
# 数据库配置
POSTGRES_DB=pyt_production
POSTGRES_USER=pyt_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432

# Redis配置
REDIS_PASSWORD=your_redis_password
REDIS_PORT=6379

# 服务端口
API_PORT=8000
FRONTEND_PORT=8080
MLFLOW_PORT=5000

# 安全配置
SECRET_KEY=your_secret_key
JWT_SECRET=your_jwt_secret
LOG_LEVEL=INFO

# MLOps配置
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=production_detection
DVC_REMOTE_URL=/dvc/remote
```

### 3. 启动服务

#### 基础服务启动
```bash
# 启动核心服务
docker-compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### MLOps服务启动
```bash
# 启动MLOps服务
docker-compose -f docker-compose.prod.mlops.yml up -d

# 检查MLOps服务状态
docker-compose -f docker-compose.prod.mlops.yml ps
```

#### 一键启动
```bash
# 使用脚本一键启动
./scripts/deployment/start_production_with_mlops.sh
```

## 📊 服务访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:8080 | 用户界面 |
| API接口 | http://localhost:8000 | REST API |
| API文档 | http://localhost:8000/docs | Swagger文档 |
| MLflow UI | http://localhost:5000 | 实验跟踪界面 |
| WebSocket | ws://localhost:8000/ws/status | 实时状态更新 |

## 🔧 配置说明

### MLflow配置
- **后端存储**: PostgreSQL数据库
- **文件存储**: 本地文件系统
- **实验名称**: `production_detection`
- **端口**: 5000

### DVC配置
- **缓存目录**: `/dvc/cache`
- **远程存储**: 可配置
- **数据目录**: 只读挂载

### WebSocket配置
- **端点**: `/ws/status`
- **心跳**: 自动ping/pong
- **重连**: 自动重连机制

## 📁 数据管理

### 目录结构
```
生产环境/
├── config/           # 配置文件
├── logs/            # 日志文件
├── output/          # 输出文件
├── data/            # 数据文件
├── models/          # 模型文件
├── mlruns/          # MLflow实验数据
└── dvc_cache/       # DVC缓存
```

### 数据备份
```bash
# 备份MLflow数据
tar -czf mlruns_backup_$(date +%Y%m%d).tar.gz mlruns/

# 备份模型数据
tar -czf models_backup_$(date +%Y%m%d).tar.gz models/

# 备份配置数据
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
```

## 🔍 监控和维护

### 健康检查
```bash
# 检查所有服务状态
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.mlops.yml ps

# 检查服务日志
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.mlops.yml logs -f mlflow
```

### 性能监控
- **API性能**: 通过 `/health` 端点
- **MLflow性能**: 通过MLflow UI
- **Redis性能**: 通过Redis CLI
- **数据库性能**: 通过PostgreSQL监控

### 日志管理
```bash
# 查看API日志
docker-compose -f docker-compose.prod.yml logs -f api

# 查看MLflow日志
docker-compose -f docker-compose.prod.mlops.yml logs -f mlflow

# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 🚨 故障排除

### 常见问题

#### 1. MLflow连接失败
```bash
# 检查MLflow服务状态
docker-compose -f docker-compose.prod.mlops.yml ps mlflow

# 检查数据库连接
docker-compose -f docker-compose.prod.yml exec database psql -U pyt_user -d pyt_production -c "SELECT 1;"
```

#### 2. WebSocket连接失败
```bash
# 检查API服务状态
docker-compose -f docker-compose.prod.yml ps api

# 检查Redis连接
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

#### 3. 模型加载失败
```bash
# 检查模型文件权限
ls -la models/

# 检查模型文件完整性
docker-compose -f docker-compose.prod.yml exec api python -c "import torch; print('PyTorch version:', torch.__version__)"
```

## 📈 性能优化

### 资源分配
- **API服务**: 2-4 CPU核心，4-8GB内存
- **MLflow服务**: 1-2 CPU核心，2-4GB内存
- **Redis服务**: 1 CPU核心，1-2GB内存
- **数据库**: 2-4 CPU核心，4-8GB内存

### 存储优化
- **SSD存储**: 用于数据库和缓存
- **网络存储**: 用于模型和实验数据
- **定期清理**: 清理旧的实验数据

## 🔒 安全考虑

### 网络安全
- **防火墙**: 限制外部访问
- **SSL/TLS**: 生产环境使用HTTPS
- **VPN**: 限制管理访问

### 数据安全
- **密码策略**: 强密码要求
- **数据加密**: 敏感数据加密
- **访问控制**: 基于角色的访问控制

## 📋 检查清单

### 部署前检查
- [ ] Docker和Docker Compose已安装
- [ ] GPU驱动已安装（如需要）
- [ ] 环境变量已配置
- [ ] 必要目录已创建
- [ ] 模型文件已准备

### 部署后检查
- [ ] 所有服务正常运行
- [ ] 健康检查通过
- [ ] 端口访问正常
- [ ] 日志无错误
- [ ] 功能测试通过

### 定期维护
- [ ] 日志轮转
- [ ] 数据备份
- [ ] 性能监控
- [ ] 安全更新
- [ ] 容量规划
