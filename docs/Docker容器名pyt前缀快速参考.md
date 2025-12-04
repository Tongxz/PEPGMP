# Docker容器名 "pyt-" 前缀快速参考

## 📋 需要判断的容器名列表

### 🔴 实际在用的容器（需要判断是否修改）

#### 测试环境容器
```
docker-compose.test.yml:
  - pyt-postgres-test   (PostgreSQL数据库)
  - pyt-redis-test      (Redis缓存)
  - pyt-api-test        (API服务)
```

#### 生产监控服务容器
```
docker-compose.prod.yml:
  - pyt-prometheus      (Prometheus监控)
  - pyt-grafana         (Grafana可视化)

docker-compose.prod.full.yml:
  - pyt-prometheus-prod (Prometheus监控)
  - pyt-grafana-prod    (Grafana可视化)

docker-compose.prod.windows.yml:
  - pyt-prometheus      (Prometheus监控)
  - pyt-grafana         (Grafana可视化)
```

#### MLOps服务容器
```
docker-compose.prod.full.yml:
  - pyt-mlflow-prod     (MLflow实验跟踪)
  - pyt-dvc-prod        (DVC数据版本控制)

docker-compose.prod.mlops.yml:
  - pyt-mlflow-prod     (MLflow服务)
  - pyt-dvc-prod        (DVC服务)
  - pyt-prod-network    (Docker网络名称)
```

### 🟡 代码中动态生成的容器名（需要判断）

```
src/infrastructure/deployment/docker_service.py:
  - 行151: 默认过滤器 ["pyt-"]
  - 行206: 动态生成 f"pyt-{detection_task}"
  - 行227: 默认返回 "pyt-api"
```

### 🟢 历史兼容性/已注释（通常无需修改）

```
docker-compose.dev-db.yml:
  - pyt-adminer         (已注释，无需修改)

scripts/backup_dev_data.sh:
  - pyt-postgres-dev    (历史兼容变量)
  - pyt-redis-dev       (历史兼容变量)

scripts/rebuild_dev_environment.sh:
  - pyt-*-dev           (旧容器列表，用于清理)
  - pyt-dev-network     (旧网络列表)
```

### 🔵 工具脚本中的硬编码（建议修改）

```
scripts/tools/check_video_stream_status.sh:
  - pyt-redis-dev       (硬编码容器名)

scripts/tests/test_deployment_service.py:
  - pyt-postgres-dev    (测试用例)
```

---

## 💡 判断建议

### 对比：当前主要容器命名

**已使用 `pepgmp-*` 前缀的容器**:
- ✅ `pepgmp-api-prod` - API服务
- ✅ `pepgmp-postgres-prod` - PostgreSQL数据库
- ✅ `pepgmp-redis-prod` - Redis缓存
- ✅ `pepgmp-frontend-prod` - 前端服务

**仍使用 `pyt-*` 前缀的容器**:
- ⚠️ 测试环境容器 (`pyt-*-test`)
- ⚠️ 监控服务 (`pyt-prometheus`, `pyt-grafana`)
- ⚠️ MLOps服务 (`pyt-mlflow-prod`, `pyt-dvc-prod`)

### 决策建议

#### 选项1: 保持现状（分离命名）
- 主要生产服务：`pepgmp-*`
- 测试/监控/MLOps：`pyt-*`
- **优点**: 可以通过前缀区分服务类型
- **缺点**: 命名不一致

#### 选项2: 统一为 `pepgmp-*`（推荐）
- 所有容器统一使用 `pepgmp-*` 前缀
- **优点**: 命名一致，易于管理
- **缺点**: 需要修改多个配置文件

---

## 📝 详细清单文档

完整清单请查看：[Docker容器名pyt前缀清单.md](Docker容器名pyt前缀清单.md)
