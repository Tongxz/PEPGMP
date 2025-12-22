# Docker容器名 "pyt-" 前缀完整清单

**生成时间**: 2025-01-03
**目的**: 列出所有包含 "pyt-" 前缀的 Docker 容器名称，供判断是否需要修改

---

## 📋 容器名清单（按文件分类）

### 1. Docker Compose 配置文件

#### 1.1 `docker-compose.test.yml` - 测试环境

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 18 | `pyt-postgres-test` | PostgreSQL | 测试数据库 |
| 39 | `pyt-redis-test` | Redis | 测试缓存 |
| 61 | `pyt-api-test` | API服务 | 测试API服务 |

**当前镜像**: 使用 `pepgmp-backend:latest`，但容器名为 `pyt-*`
**建议**: ⚠️ 考虑统一为 `pepgmp-*` 前缀

---

#### 1.2 `docker-compose.prod.yml` - 生产环境（可选监控服务）

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 271 | `pyt-prometheus` | Prometheus | 监控服务（可选） |
| 296 | `pyt-grafana` | Grafana | 可视化服务（可选） |

**说明**: 这些是可选的监控服务，通过 profile 控制启用
**建议**: ⚠️ 考虑统一为 `pepgmp-*` 前缀

---

#### 1.3 `docker-compose.prod.full.yml` - 完整生产环境

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 196 | `pyt-prometheus-prod` | Prometheus | 生产监控服务 |
| 223 | `pyt-grafana-prod` | Grafana | 生产可视化服务 |
| 250 | `pyt-mlflow-prod` | MLflow | MLOps实验跟踪 |
| 285 | `pyt-dvc-prod` | DVC | 数据版本控制 |

**说明**: 完整生产环境配置，包含监控和MLOps服务
**建议**: ⚠️ 考虑统一为 `pepgmp-*` 前缀

---

#### 1.4 `docker-compose.prod.mlops.yml` - MLOps专用配置

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 19 | `pyt-mlflow-prod` | MLflow | MLOps实验跟踪 |
| 45 | `pyt-dvc-prod` | DVC | 数据版本控制 |
| 6 | `pyt-prod-network` | 网络 | Docker网络名称 |

**说明**: MLOps专用配置，使用外部网络 `pyt-prod-network`
**建议**: ⚠️ 考虑统一为 `pepgmp-*` 前缀

---

#### 1.5 `docker-compose.prod.windows.yml` - Windows生产环境

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 200 | `pyt-prometheus` | Prometheus | 监控服务 |
| 224 | `pyt-grafana` | Grafana | 可视化服务 |

**说明**: Windows环境生产配置
**建议**: ⚠️ 考虑统一为 `pepgmp-*` 前缀

---

#### 1.6 `docker-compose.dev-db.yml` - 开发数据库配置

| 行号 | 容器名 | 服务类型 | 说明 |
|------|--------|---------|------|
| 68 | `pyt-adminer` | Adminer | 数据库管理工具（已注释） |

**说明**: 开发环境数据库配置，Adminer服务已被注释
**建议**: ✅ 无需修改（已注释）

---

### 2. 源代码文件

#### 2.1 `src/infrastructure/deployment/docker_service.py`

| 行号 | 代码位置 | 说明 |
|------|---------|------|
| 151 | 默认过滤器 | `filters = {"name": ["pyt-"]}` - 列出所有 pyt- 开头的容器 |
| 206 | 容器名生成 | `container_name = f"pyt-{detection_task.replace('_', '-')}"` - 动态生成容器名 |
| 227 | 默认返回值 | `return "pyt-api"` - 默认容器名 |

**说明**: 这是部署服务的代码实现，会动态生成容器名
**建议**: ⚠️ 如果修改容器名规范，这里也需要更新

---

#### 2.2 `src/database/init_db.py`

| 行号 | 代码位置 | 说明 |
|------|---------|------|
| 93, 120 | Docker配置 | `"image": "pyt-api:latest"` - 示例配置中的镜像名 |

**说明**: 数据库初始化脚本中的示例配置
**建议**: ⚠️ 示例配置，建议更新为 `pepgmp-backend:latest`

---

### 3. 脚本文件

#### 3.1 `scripts/backup_dev_data.sh`

| 行号 | 变量名 | 说明 |
|------|--------|------|
| 19 | `DB_CONTAINER_OLD` | 旧数据库容器名：`pyt-postgres-dev` |
| 26 | `REDIS_CONTAINER_OLD` | 旧Redis容器名：`pyt-redis-dev` |

**说明**: 备份脚本中定义的旧容器名（用于迁移）
**建议**: ✅ 无需修改（这是历史兼容性变量）

---

#### 3.2 `scripts/rebuild_dev_environment.sh`

| 行号 | 变量名 | 说明 |
|------|--------|------|
| 31 | `OLD_CONTAINERS` | 旧容器列表：`["pyt-postgres-dev", "pyt-redis-dev", "pyt-api-dev", "pyt-frontend-dev"]` |
| 45 | `OLD_NETWORKS` | 旧网络列表：`["pyt-dev-network"]` |

**说明**: 重建开发环境脚本中的旧容器/网络名（用于清理）
**建议**: ✅ 无需修改（这是历史兼容性变量）

---

#### 3.3 `scripts/deploy_prod.sh`（历史脚本，已移除）

| 行号 | 代码 | 说明 |
|------|------|------|
| 192 | `kubectl rollout status deployment/pyt-api` | Kubernetes部署名 |
| 197 | `kubectl get pods -l app=pyt-api` | Kubernetes应用标签 |

**说明**: Kubernetes部署脚本中的部署名和应用标签
**建议**: ⚠️ 如果使用Kubernetes，建议统一命名

---

### 4. 文档文件

#### 4.1 文档中的示例命令

多个文档中包含使用 `pyt-*` 容器名的示例命令：

- `docs/DATABASE_INITIALIZATION.md` - 数据库初始化文档
- `docs/configuration_management_best_practices.md` - 配置管理最佳实践
- `docs/数据库配置历史分析.md` - 数据库配置历史
- `docs/完整部署方案说明.md` - 完整部署方案

**说明**: 文档中的示例命令
**建议**: 🟢 低优先级，文档更新时逐步修正

---

## 📊 统计汇总

### 按容器类型分类

| 容器类型 | 数量 | 文件位置 |
|---------|------|---------|
| 测试环境容器 | 3 | `docker-compose.test.yml` |
| 生产监控容器 | 4 | `docker-compose.prod.yml`, `docker-compose.prod.full.yml`, `docker-compose.prod.windows.yml` |
| MLOps容器 | 2 | `docker-compose.prod.full.yml`, `docker-compose.prod.mlops.yml` |
| 代码中的动态生成 | 3 | `src/infrastructure/deployment/docker_service.py` |
| 脚本中的引用 | 10+ | 各种脚本文件 |
| 文档示例 | 20+ | 各种文档文件 |

**总计**: 约 40+ 处引用

---

## 🔍 分析建议

### 是否需要修改？

根据 `docs/项目重命名指南.md` 的说明：

> **`pepgmp`** - Docker/容器命名（**不需要修改**）
> - Docker 容器名称：`pepgmp-postgres-prod`, `pepgmp-api-prod` 等
> - **这些名称保持不变，与根目录名称无关**

但实际发现的情况是：
- 主要生产容器已使用 `pepgmp-*` 前缀（如 `pepgmp-api-prod`, `pepgmp-postgres-prod`）
- 但测试环境、监控服务、MLOps服务仍使用 `pyt-*` 前缀
- 代码中也有动态生成 `pyt-*` 容器名的逻辑

### 建议分类

#### ✅ 无需修改（历史兼容）

- `scripts/backup_dev_data.sh` - 备份脚本中的旧容器名变量
- `scripts/rebuild_dev_environment.sh` - 重建脚本中的旧容器列表
- 文档中的示例命令（低优先级）

#### ⚠️ 建议统一修改（保持一致性）

1. **Docker Compose 配置**
   - `docker-compose.test.yml` - 测试环境容器名
   - `docker-compose.prod.yml` - 监控服务容器名
   - `docker-compose.prod.full.yml` - 完整环境容器名
   - `docker-compose.prod.mlops.yml` - MLOps容器名和网络名
   - `docker-compose.prod.windows.yml` - Windows环境容器名

2. **源代码**
   - `src/infrastructure/deployment/docker_service.py` - 容器名生成逻辑
   - `src/database/init_db.py` - 示例配置

3. **脚本**
   - 工具/测试脚本目录已随仓库收敛移除，不再包含对应硬编码示例

#### 🟢 低优先级（文档示例）

- 所有文档文件中的示例命令

---

## 💡 修改建议

### 统一命名规范

建议将所有容器名统一为 `pepgmp-*` 前缀，以保持一致性：

**测试环境**:
- `pyt-postgres-test` → `pepgmp-postgres-test`
- `pyt-redis-test` → `pepgmp-redis-test`
- `pyt-api-test` → `pepgmp-api-test`

**监控服务**:
- `pyt-prometheus` → `pepgmp-prometheus`
- `pyt-grafana` → `pepgmp-grafana`
- `pyt-prometheus-prod` → `pepgmp-prometheus-prod`
- `pyt-grafana-prod` → `pepgmp-grafana-prod`

**MLOps服务**:
- `pyt-mlflow-prod` → `pepgmp-mlflow-prod`
- `pyt-dvc-prod` → `pepgmp-dvc-prod`

**网络**:
- `pyt-prod-network` → `pepgmp-prod-network`

**代码中的动态生成**:
- `f"pyt-{detection_task}"` → `f"pepgmp-{detection_task}"`
- `"pyt-api"` → `"pepgmp-api"`

---

## ⚠️ 注意事项

### 如果决定修改容器名

1. **影响范围**:
   - 需要更新所有 Docker Compose 配置文件
   - 需要更新代码中的容器名生成逻辑
   - 需要更新脚本中的硬编码容器名
   - 可能需要重新创建容器（容器名变更）

2. **数据迁移**:
   - 如果容器已有数据，需要确保数据卷正确迁移
   - 检查是否有脚本依赖特定的容器名

3. **向后兼容**:
   - 考虑是否需要保留旧容器名的兼容性
   - 备份脚本中的 `OLD_CONTAINERS` 变量应该保留（用于历史数据迁移）

---

## 📝 决策参考

### 当前状态

- ✅ 主要生产容器：已使用 `pepgmp-*` 前缀
- ⚠️ 测试/监控/MLOps容器：仍使用 `pyt-*` 前缀
- ⚠️ 代码逻辑：动态生成 `pyt-*` 容器名

### 建议

根据项目重命名指南的说明，容器命名与根目录名称无关。但从**一致性**角度考虑：

- **选项1**: 保持现状（`pyt-*` 用于测试/监控/MLOps，`pepgmp-*` 用于主要服务）
- **选项2**: 统一为 `pepgmp-*`（推荐，提高一致性）

---

## 📚 相关文档

- [项目重命名指南](项目重命名指南.md)
- [目录重命名验证报告](目录重命名验证报告.md)
