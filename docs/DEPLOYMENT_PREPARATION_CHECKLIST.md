# 部署前准备工作清单

## 📋 概述

本文档列出了在生产环境部署前必须完成的所有工作、需要测试的内容、需要优化调整的地方，以及详细的部署流程。

**更新日期**: 2025-11-24  
**目标环境**: Ubuntu 22.04 LTS 内网环境  
**部署方式**: Docker 容器化部署 / Docker Compose / 内网私有Registry

---

## 🔴 一、部署前必须完成的工作（P0 - 阻塞部署）

### 1.1 配置管理 ✅

#### 必需配置文件

- [ ] **`.env.production`** - 生产环境配置
  - 检查命令: `bash scripts/check_deployment_readiness.sh`
  - 生成命令: `bash scripts/generate_production_config.sh`
  - 验证密码强度:
    - `ADMIN_PASSWORD` ≥ 16字符
    - `DATABASE_PASSWORD` ≥ 16字符
    - `REDIS_PASSWORD` ≥ 16字符
    - `SECRET_KEY` ≥ 32字符
    - `JWT_SECRET_KEY` ≥ 32字符
  - 文件权限: `chmod 600 .env.production`
  - 确保所有 `CHANGE_ME` 占位符已替换

- [ ] **`config/` 目录** - 配置文件目录
  - 检查关键配置文件存在:
    - `config/cameras.yaml` 或 `config/default.yaml`
    - `config/unified_params.yaml` (可选)
  - 验证配置格式正确

- [ ] **`models/` 目录** - AI模型文件
  - 确认必需的模型文件存在
  - 检查模型文件大小（预计传输时间）
  - 建议模型文件预上传到生产服务器

#### 配置文件检查清单

```bash
# 1. 检查配置文件
bash scripts/check_deployment_readiness.sh

# 2. 验证配置
python scripts/validate_config.py

# 3. 检查密码强度
grep -E "PASSWORD|SECRET" .env.production | grep -v "^#"
```

### 1.2 Docker 环境准备 ✅

#### Docker配置

- [ ] **Docker Desktop 已安装并运行** (开发环境)
  - 验证: `docker info`
  - 检查镜像: `docker images pyt-backend:latest`

- [ ] **内网Docker Registry 配置** (内网私有Registry: 192.168.30.83:5433)
  - **注意**: 这是内网Registry，需要确保内网连通性
  - 开发环境配置（macOS）:
    ```json
    {
      "insecure-registries": ["192.168.30.83:5433"]
    }
    ```
  - **Ubuntu 22.04 生产环境配置**:
    ```bash
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json <<EOF
    {
      "insecure-registries": ["192.168.30.83:5433"],
      "log-driver": "json-file",
      "log-opts": {
        "max-size": "50m",
        "max-file": "3"
      }
    }
    EOF
    sudo systemctl restart docker
    ```
  - 验证内网Registry连接: `curl http://192.168.30.83:5433/v2/_catalog`
  - 如无法连接，检查内网网络配置和防火墙规则

- [ ] **Ubuntu 22.04 生产服务器Docker环境**
  - **Docker Engine 安装** (Ubuntu 22.04):
    ```bash
    # 更新软件包索引
    sudo apt-get update
    
    # 安装Docker依赖
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    
    # 添加Docker官方GPG密钥
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # 添加Docker仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 验证安装
    sudo docker --version
    sudo docker compose version
    ```
  - **Docker Compose V2** (Ubuntu 22.04 默认包含):
    - 使用 `docker compose`（V2命令，无连字符）
    - 或安装兼容的 `docker-compose`（V1命令）
  - **Docker服务配置**:
    - Docker服务运行: `sudo systemctl status docker`
    - 设置Docker开机自启: `sudo systemctl enable docker`
    - 将当前用户添加到docker组（避免每次sudo）:
      ```bash
      sudo usermod -aG docker $USER
      # 需要重新登录生效，或使用 newgrp docker
      ```

#### 镜像构建和推送

- [ ] **构建生产镜像**
  ```bash
  docker build -f Dockerfile.prod -t pyt-backend:latest .
  ```

- [ ] **验证镜像大小**
  - 目标: < 1GB
  - 检查: `docker images pyt-backend:latest`

- [ ] **推送到Registry**
  ```bash
  bash scripts/push_to_registry.sh latest v1.0.0
  ```

### 1.3 生产服务器环境准备 ✅

#### 服务器要求

- [ ] **操作系统**: Ubuntu 22.04 LTS（内网环境）
- [ ] **硬件要求**:
  - 至少 4GB RAM
  - 至少 20GB 磁盘空间
  - 至少 2 CPU 核心
- [ ] **内网环境要求**:
  - ✅ 服务器位于内网环境（无公网访问）
  - ✅ 内网DNS配置正确（如需要）
  - ✅ 内网Registry可访问 (192.168.30.83:5433)
  - ✅ 开放端口 8000 (API)
  - ✅ 开放端口 80, 443 (Nginx, 可选)
  - ✅ 内网服务间可相互访问

#### Ubuntu 22.04 内网服务器初始化

- [ ] **创建部署目录**
  ```bash
  sudo mkdir -p /opt/pyt
  sudo chown $USER:$USER /opt/pyt
  cd /opt/pyt
  ```

- [ ] **配置内网防火墙**（Ubuntu 22.04 使用 ufw）
  ```bash
  # 检查防火墙状态
  sudo ufw status
  
  # 允许SSH（确保不会断开连接）
  sudo ufw allow 22/tcp
  
  # 允许API端口
  sudo ufw allow 8000/tcp
  
  # 允许Nginx端口（如使用）
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  
  # 如内网Registry在同一内网，确保端口可访问
  # sudo ufw allow from 192.168.0.0/16 to any port 5433
  
  # 启用防火墙
  sudo ufw enable
  
  # 验证防火墙规则
  sudo ufw status numbered
  ```

- [ ] **配置内网DNS（如需要）**
  ```bash
  # 如内网有DNS服务器，配置 /etc/resolv.conf 或使用 netplan
  # Ubuntu 22.04 使用 netplan
  sudo nano /etc/netplan/00-installer-config.yaml
  
  # 添加DNS配置示例:
  # network:
  #   version: 2
  #   ethernets:
  #     eth0:
  #       nameservers:
  #         addresses:
  #           - 192.168.1.1  # 内网DNS服务器
  #       dhcp4: true
  # 
  # sudo netplan apply
  ```

- [ ] **验证内网连通性**
  ```bash
  # 测试内网Registry连通性
  ping 192.168.30.83
  curl http://192.168.30.83:5433/v2/_catalog
  
  # 测试其他内网服务连通性（如需要）
  # ping <其他内网服务IP>
  ```

### 1.4 数据库和Redis准备 ✅

#### 数据库初始化

- [ ] **数据库迁移脚本**
  - 检查迁移脚本存在: `scripts/migrations/`
  - 准备迁移命令:
    ```bash
    # 在Docker Compose中自动执行
    # 或手动执行:
    docker exec pyt-postgres-prod psql -U pyt_prod -d pyt_production -f /path/to/migration.sql
    ```

- [ ] **数据库备份策略**
  - 设置备份脚本: `scripts/backup_db.sh`
  - 配置定时任务: `crontab -e`
    ```bash
    0 2 * * * /opt/pyt/scripts/backup_db.sh
    ```

#### Redis配置

- [ ] **Redis持久化配置**
  - 已包含在 `docker-compose.prod.yml` 中
  - 验证配置: `appendonly yes`

### 1.5 代码质量检查 ✅

#### Git状态

- [ ] **所有更改已提交**
  ```bash
  git status
  # 确保工作目录干净
  ```

- [ ] **当前分支正确**
  - 建议在 `develop` 或 `main` 分支部署
  - 验证: `git branch --show-current`

#### 代码审查

- [ ] **无硬编码密码或敏感信息**
  ```bash
  grep -r "password\|secret" src/ --exclude-dir=__pycache__ | grep -v "#"
  ```

- [ ] **无调试代码**
  ```bash
  grep -r "TODO\|FIXME\|XXX\|HACK" src/
  ```

---

## 🟡 二、部署前需要测试的内容（P1 - 重要）

### 2.1 单元测试 ✅

#### 运行单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定模块测试
pytest tests/unit/test_domain_models.py -v
pytest tests/unit/test_interfaces.py -v
```

**测试覆盖目标**:
- [ ] 单元测试通过率 ≥ 80%
- [ ] 关键业务逻辑测试覆盖
- [ ] 领域模型测试通过

### 2.2 集成测试 ✅

#### API集成测试

```bash
# 启动开发服务器
bash scripts/start_dev.sh

# 运行集成测试
python tests/integration/test_api_integration.py

# 或使用pytest
pytest tests/integration/ -v
```

**测试内容**:
- [ ] **读操作API** (17个端点)
  - [ ] 摄像头管理 API
  - [ ] 检测记录 API
  - [ ] 统计信息 API
  - [ ] 告警管理 API
  - [ ] 系统监控 API

- [ ] **写操作API** (4个端点)
  - [ ] 创建摄像头
  - [ ] 更新摄像头
  - [ ] 创建告警规则
  - [ ] 数据集上传

- [ ] **领域服务验证** (3个端点)
  - [ ] 违规记录列表（领域服务）
  - [ ] 统计摘要（领域服务）
  - [ ] 摄像头列表（领域服务）

**测试脚本**:
- [ ] `tests/integration/test_api_integration.py` - Python集成测试
- [ ] `scripts/test_frontend_improvements.py` - 前端改进测试
- [ ] `tools/integration_test.sh` - Shell快速测试

### 2.3 前端功能测试 ✅

#### 前端自动化测试

```bash
# 启动前端开发服务器
cd frontend && npm run dev

# 运行前端测试
cd frontend && npm test

# 检查构建
cd frontend && npm run build
```

**测试内容**:
- [ ] 所有页面可访问
- [ ] API调用正常
- [ ] 无控制台错误
- [ ] 响应式布局正常
- [ ] 关键功能流程:
  - [ ] 首页显示实时统计
  - [ ] 实时监控视频流正常
  - [ ] 检测记录分页和筛选
  - [ ] 告警历史分页和排序
  - [ ] 统计数据图表显示

### 2.4 性能测试 ✅

#### API性能测试

```bash
# 使用ab或wrk进行压力测试
ab -n 1000 -c 10 http://localhost:8000/api/v1/monitoring/health

# 或使用Python脚本
python scripts/performance/performance_profiler.py
```

**性能指标目标**:
- [ ] **响应时间**:
  - 健康检查: < 50ms
  - 简单查询: < 200ms
  - 复杂查询: < 1s

- [ ] **吞吐量**:
  - QPS ≥ 100 (健康检查)
  - QPS ≥ 50 (业务API)

- [ ] **资源使用**:
  - CPU使用率 < 80%
  - 内存使用 < 4GB
  - 磁盘IO < 80%

### 2.5 数据库测试 ✅

#### 数据库连接和查询测试

```bash
# 测试数据库连接
python scripts/test_database.py

# 测试数据库结构
python scripts/check_db_structure.py
```

**测试内容**:
- [ ] 数据库连接正常
- [ ] 表结构正确
- [ ] 索引已创建
- [ ] 查询性能可接受
- [ ] 迁移脚本执行成功

### 2.6 部署环境测试 ✅

#### Docker Compose测试

```bash
# 使用生产配置测试本地Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 验证服务健康
docker-compose -f docker-compose.prod.yml ps

# 测试API
curl http://localhost:8000/api/v1/monitoring/health

# 清理
docker-compose -f docker-compose.prod.yml down
```

**测试内容**:
- [ ] 所有容器正常启动
- [ ] 健康检查通过
- [ ] 服务间通信正常
- [ ] 日志输出正常
- [ ] 资源限制生效

---

## 🟢 三、需要优化调整的地方（P2 - 建议）

### 3.1 安全优化 ✅

#### SSL/TLS配置

- [ ] **配置HTTPS** (可选但强烈推荐)
  - 准备SSL证书 (Let's Encrypt 或自签名)
  - 配置Nginx HTTPS
  - 更新API配置支持HTTPS

#### 安全头配置

- [ ] **Nginx安全头**
  ```nginx
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-XSS-Protection "1; mode=block" always;
  ```

#### 访问控制

- [ ] **API认证增强**
  - JWT Token过期时间配置
  - 刷新Token机制
  - 访问频率限制

- [ ] **防火墙规则**
  - 只开放必需端口
  - 配置IP白名单 (如需要)

### 3.2 性能优化 ✅

#### 应用层优化

- [ ] **Gunicorn Workers配置**
  - 当前: 4 workers
  - 建议: `(2 × CPU核心数) + 1`
  - 调整 `Dockerfile.prod` 或环境变量

- [ ] **数据库连接池**
  - 检查连接池大小
  - 优化查询语句
  - 添加索引（如需要）

- [ ] **Redis缓存策略**
  - 配置缓存过期时间
  - 优化缓存键名
  - 监控缓存命中率

#### 前端优化

- [ ] **前端构建优化**
  ```bash
  cd frontend
  npm run build
  # 检查构建产物大小
  ```

- [ ] **CDN配置** (可选)
  - 静态资源CDN
  - 图片CDN

### 3.3 监控和日志 ✅

#### 监控配置

- [ ] **Prometheus配置** (可选)
  - 配置文件: `monitoring/prometheus.yml`
  - 启动Prometheus: `docker-compose -f docker-compose.prod.full.yml --profile monitoring up -d`
  - 验证指标收集

- [ ] **Grafana配置** (可选)
  - 数据源配置
  - 仪表板导入
  - 告警规则配置

#### 日志管理

- [ ] **日志轮转配置**
  - 已在 `docker-compose.prod.yml` 中配置
  - 验证日志文件大小限制
  - 配置日志清理策略

- [ ] **日志聚合** (可选)
  - ELK Stack
  - Loki + Grafana

### 3.4 备份和恢复 ✅

#### 备份策略

- [ ] **数据库备份**
  - 自动备份脚本: `scripts/backup_db.sh`
  - 定时任务配置
  - 备份存储位置

- [ ] **配置文件备份**
  ```bash
  tar czf config_backup_$(date +%Y%m%d).tar.gz config/ .env.production
  ```

- [ ] **恢复测试**
  - 测试备份恢复流程
  - 验证恢复后功能正常

### 3.5 文档完善 ✅

#### 部署文档

- [ ] **部署流程文档**
  - 更新 `docs/production_deployment_guide.md`
  - 添加故障排查指南
  - 添加回滚流程

#### 运维文档

- [ ] **运维手册**
  - 日常维护操作
  - 常见问题解决
  - 紧急响应流程

---

## 🚀 四、部署流程

### 4.1 部署前最终检查

```bash
# 1. 运行部署就绪检查
bash scripts/check_deployment_readiness.sh

# 2. 验证配置
python scripts/validate_config.py

# 3. 检查Git状态
git status

# 4. 确认生产服务器信息
echo "生产服务器IP: <SERVER_IP>"
echo "SSH用户名: ubuntu"
```

### 4.2 快速部署（推荐）✨

```bash
# 一键部署（构建 -> 推送 -> 部署）
bash scripts/quick_deploy.sh <SERVER_IP> ubuntu
```

**执行流程**:
1. ✅ 构建Docker镜像
2. ✅ 推送到Registry
3. ✅ 部署到生产服务器
4. ✅ 健康检查
5. ✅ 记录部署历史

### 4.3 分步部署

#### 步骤1: 构建和推送镜像

```bash
# 构建镜像
docker build -f Dockerfile.prod -t pyt-backend:latest .

# 推送镜像
bash scripts/push_to_registry.sh latest v1.0.0
```

#### 步骤2: 准备生产服务器

```bash
# SSH到生产服务器
ssh ubuntu@<SERVER_IP>

# 创建部署目录
sudo mkdir -p /opt/pyt
sudo chown $USER:$USER /opt/pyt
cd /opt/pyt
```

#### 步骤3: 部署配置文件

```bash
# 在开发机器上打包配置（不包含.env.production）
tar czf deploy_config.tar.gz \
    docker-compose.prod.yml \
    Dockerfile.prod \
    config/ \
    scripts/

# 传输到生产服务器
scp deploy_config.tar.gz ubuntu@<SERVER_IP>:/opt/pyt/
scp .env.production ubuntu@<SERVER_IP>:/opt/pyt/

# 在生产服务器上解压
cd /opt/pyt
tar xzf deploy_config.tar.gz
chmod 600 .env.production
```

#### 步骤4: 部署服务

```bash
# 在生产服务器上
cd /opt/pyt

# 从Registry拉取镜像
docker pull 192.168.30.83:5433/pyt-backend:latest
docker tag 192.168.30.83:5433/pyt-backend:latest pyt-backend:latest

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 验证部署
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/api/v1/monitoring/health
```

### 4.4 部署后验证

#### 基础验证

```bash
# 1. 检查容器状态
docker ps

# 2. 检查健康状态
curl http://localhost:8000/api/v1/monitoring/health

# 3. 检查系统信息
curl http://localhost:8000/api/v1/system/info

# 4. 查看日志
docker-compose -f docker-compose.prod.yml logs -f api
```

#### 功能验证

```bash
# 1. 测试摄像头列表
curl http://localhost:8000/api/v1/cameras

# 2. 测试检测记录
curl http://localhost:8000/api/v1/records/violations?limit=10

# 3. 测试统计信息
curl http://localhost:8000/api/v1/statistics/summary

# 4. 测试前端访问
curl http://localhost:8000/
```

#### 性能验证

```bash
# 1. 响应时间测试
time curl http://localhost:8000/api/v1/monitoring/health

# 2. 资源使用监控
docker stats

# 3. 数据库连接测试
docker exec pyt-postgres-prod pg_isready -U pyt_prod
```

### 4.5 回滚流程

#### 回滚到之前版本

```bash
# 在生产服务器上
cd /opt/pyt

# 1. 查看可用版本
curl http://192.168.30.83:5433/v2/pyt-backend/tags/list

# 2. 拉取之前版本
docker pull 192.168.30.83:5433/pyt-backend:v1.0.0
docker tag 192.168.30.83:5433/pyt-backend:v1.0.0 pyt-backend:latest

# 3. 重启服务
docker-compose -f docker-compose.prod.yml up -d --force-recreate api

# 4. 验证
curl http://localhost:8000/api/v1/monitoring/health
```

---

## 📊 五、检查清单总结

### 部署前检查清单（快速版）

```
□ .env.production 已创建并配置
□ 所有密码已设置为强密码
□ config/ 目录存在且包含必需配置
□ models/ 目录存在（如需要）
□ Docker环境已准备
□ Registry连接正常
□ 生产服务器环境已准备
□ 数据库迁移脚本已准备
□ 代码已提交到Git
□ 单元测试通过
□ 集成测试通过
□ 前端功能测试通过
□ Docker Compose测试通过
□ 部署脚本可执行
□ 备份策略已配置
```

### 部署检查清单（执行版）

```
□ 运行 check_deployment_readiness.sh 通过
□ 镜像已构建并推送到Registry
□ 生产服务器可访问
□ 配置文件已传输
□ 服务已启动
□ 健康检查通过
□ 功能验证通过
□ 日志正常
□ 性能指标正常
```

---

## 🔧 六、故障排查

### 常见问题

#### 问题1: Registry连接失败

**症状**: `Error: Cannot connect to registry`

**解决方案**:
```bash
# 检查Registry可访问性
curl http://192.168.30.83:5433/v2/_catalog

# 检查Docker配置
cat /etc/docker/daemon.json

# 重启Docker
sudo systemctl restart docker
```

#### 问题2: 容器启动失败

**症状**: `Container exited with code 1`

**解决方案**:
```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs api

# 检查环境变量
docker-compose -f docker-compose.prod.yml config

# 检查文件权限
ls -la .env.production
```

#### 问题3: 数据库连接失败

**症状**: `Connection to database failed`

**解决方案**:
```bash
# 检查数据库容器
docker ps | grep postgres

# 检查数据库日志
docker-compose -f docker-compose.prod.yml logs database

# 测试连接
docker exec pyt-postgres-prod pg_isready -U pyt_prod
```

---

## 📝 七、部署记录模板

### 部署记录

```yaml
部署日期: 2025-11-24
部署版本: v1.0.0
部署人员: <姓名>
部署方式: Docker Compose
服务器IP: <IP>
Git Commit: <commit-hash>

部署前检查:
  - [ ] 配置检查通过
  - [ ] 测试通过
  - [ ] 代码审查通过

部署步骤:
  1. 构建镜像: ✅
  2. 推送镜像: ✅
  3. 部署服务: ✅
  4. 验证功能: ✅

部署后验证:
  - [ ] 健康检查通过
  - [ ] 功能验证通过
  - [ ] 性能指标正常

问题记录:
  - 无

备注:
  - 无
```

---

## 📚 相关文档

- [生产环境部署指南](./production_deployment_guide.md)
- [生产环境部署实施报告](./production_deployment_implementation.md)
- [Docker Compose使用指南](./docker_compose_usage_guide.md)
- [配置管理最佳实践](./configuration_management_best_practices.md)
- [集成测试文档](./integration_test_complete.md)
- [前端功能改进文档](./FRONTEND_IMPROVEMENT_COMPLETION_REPORT.md)

---

**状态**: ✅ **部署准备清单已完成**  
**下一步**: 根据清单逐项检查和执行  
**优先级**: P0项必须完成，P1项强烈推荐，P2项建议完成

