# 生产部署快速参考

## 🚀 一键部署（最简单）

```bash
# 步骤1: 生成配置
bash scripts/generate_production_config.sh

# 步骤2: 一键部署
bash scripts/quick_deploy.sh <服务器IP> <SSH用户>

# 示例
bash scripts/quick_deploy.sh 192.168.1.100 ubuntu
```

**完成！** 就这么简单！🎉

---

## 📋 部署脚本速查表

| 命令 | 用途 | 示例 |
|------|------|------|
| `generate_production_config.sh` | 生成配置文件 | `bash scripts/generate_production_config.sh` |
| `quick_deploy.sh` | **一键部署** ✨ | `bash scripts/quick_deploy.sh 192.168.1.100` |
| `push_to_registry.sh` | 推送镜像 | `bash scripts/push_to_registry.sh` |
| `deploy_from_registry.sh` | 从Registry部署 | `bash scripts/deploy_from_registry.sh 192.168.1.100` |

---

## 🔄 常用操作

### 更新应用

```bash
# 方式1: 一键更新
bash scripts/quick_deploy.sh 192.168.1.100

# 方式2: 分步更新
docker build -f Dockerfile.prod -t pepgmp-backend:latest .
bash scripts/push_to_registry.sh
ssh ubuntu@192.168.1.100 'cd /opt/pyt && docker-compose pull && docker-compose up -d'
```

### 查看日志

```bash
ssh ubuntu@192.168.1.100
cd /opt/pyt
docker-compose logs -f api
```

### 重启服务

```bash
ssh ubuntu@192.168.1.100
cd /opt/pyt
docker-compose restart api
```

### 检查状态

```bash
# 本地检查
curl http://192.168.1.100:8000/api/v1/monitoring/health

# 远程检查
ssh ubuntu@192.168.1.100 'docker ps'
```

---

## 🔐 配置说明

### Registry地址
```
http://192.168.30.83:5433
```

### 部署目录
```
/opt/pyt
```

### 重要文件
- `/opt/pyt/.env` - 环境配置
- `/opt/pyt/docker-compose.yml` - 服务编排
- `/opt/pyt/config/` - 应用配置
- `/opt/pyt/models/` - 模型文件

---

## 🆘 快速故障排查

### 服务无法启动

```bash
ssh ubuntu@192.168.1.100
cd /opt/pyt
docker-compose logs api --tail=100
```

### Registry连接失败

```bash
# 检查配置
curl http://192.168.30.83:5433/v2/_catalog

# macOS配置
Docker Desktop -> Preferences -> Docker Engine
添加: "insecure-registries": ["192.168.30.83:5433"]
```

### 权限错误

```bash
# 确保文件权限
chmod 600 .env.production
chmod +x scripts/*.sh
```

---

## 📞 获取帮助

```bash
# 查看详细文档
cat docs/production_deployment_guide.md

# 查看Docker Compose指南
cat docs/docker_compose_usage_guide.md

# 查看部署历史
cat deployment_history.log
```

---

**快速链接**: [完整部署指南](./production_deployment_guide.md)
