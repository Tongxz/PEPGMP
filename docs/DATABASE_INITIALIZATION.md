# 数据库初始化机制说明

## 📋 概述

项目使用 **混合初始化机制**，不同类型的表采用不同的初始化方式：

1. **MLOps表**：通过 SQLAlchemy ORM 自动创建
2. **业务表**：通过 SQL 脚本或仓储方法动态创建
3. **Docker 容器**：首次启动时自动执行初始化脚本

---

## 🗂️ 数据库表分类

### 1. MLOps 核心表（ORM 自动创建）

这些表定义在 `src/database/models.py` 中，通过 SQLAlchemy ORM 自动创建：

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `workflows` | `Workflow` | 工作流定义 |
| `workflow_runs` | `WorkflowRun` | 工作流运行记录 |
| `datasets` | `Dataset` | 数据集管理 |
| `deployments` | `Deployment` | 模型部署 |
| `model_registry` | `ModelRegistry` | 模型注册表 |

**初始化方式**：
- 应用启动时，`src/api/app.py` 的 `lifespan` 函数调用 `src/database/connection.py` 的 `init_database()`
- 使用 `Base.metadata.create_all()` 自动创建所有 ORM 定义的表

### 2. 业务领域表（SQL 脚本或动态创建）

这些表通过 SQL 脚本或仓储方法创建：

| 表名 | 初始化方式 | 脚本位置 |
|------|-----------|---------|
| `detection_records` | 仓储方法 | `src/infrastructure/repositories/postgresql_detection_repository.py` |
| `violation_events` | SQL 脚本 | `scripts/migrations/001_create_core_tables.sql` |
| `statistics_hourly` | SQL 脚本 | `scripts/migrations/001_create_core_tables.sql` |
| `alert_rules` | SQL 脚本 | `scripts/migrations/001_create_core_tables.sql` |
| `alert_history` | SQL 脚本 | `scripts/migrations/001_create_core_tables.sql` |
| `cameras` | 仓储方法 | `src/infrastructure/repositories/postgresql_camera_repository.py` |
| `regions` | 仓储方法 | `src/infrastructure/repositories/postgresql_region_repository.py` |

**初始化方式**：
- **SQL 脚本**：`scripts/migrations/001_create_core_tables.sql` 定义了核心业务表
- **仓储方法**：仓储实现中的 `_ensure_table_exists()` 方法在首次使用时动态创建表

---

## 🚀 首次部署初始化流程

### 方式 1：Docker 容器自动初始化（推荐）

**适用场景**：使用 Docker Compose 部署

**流程**：
1. **PostgreSQL 容器首次启动**：
   - Docker Compose 配置了 `./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro`
   - PostgreSQL 容器首次启动时会自动执行 `scripts/init_db.sql`
   - 创建扩展、基础表结构（如果脚本存在）

2. **应用容器启动**：
   - `src/api/app.py` 的 `lifespan` 函数执行
   - 调用 `init_database()` 创建所有 ORM 定义的表
   - 仓储方法在首次使用时动态创建业务表

**命令**：
```bash
# 启动所有服务（包括数据库和应用）
docker-compose up -d

# 查看数据库初始化日志
docker logs pyt-postgres-dev
```

### 方式 2：手动执行 SQL 脚本

**适用场景**：需要精确控制初始化过程，或修复表结构

**步骤**：
1. **执行核心表创建脚本**：
```bash
docker exec -i pyt-postgres-dev psql -U pyt_dev -d pyt_development < scripts/migrations/001_create_core_tables.sql
```

2. **执行应用初始化**（创建 ORM 表）：
```bash
# 方式 A：通过 Python 脚本
docker exec pyt-api-dev python scripts/init_database.py

# 方式 B：应用启动时自动创建（推荐）
# 只需启动应用，lifespan 函数会自动调用 init_database()
```

### 方式 3：Python 初始化脚本

**适用场景**：需要创建初始数据（示例工作流、数据集等）

**命令**：
```bash
# 在容器内执行
docker exec pyt-api-dev python scripts/init_database.py

# 或在本地执行（需要配置数据库连接）
python scripts/init_database.py
```

**功能**：
- 创建所有 ORM 定义的表（通过 `init_database()`）
- 插入示例数据（工作流、数据集、部署配置等）

---

## 📝 初始化脚本说明

### 1. `scripts/init_db.sql`

**位置**：`scripts/init_db.sql`

**作用**：
- PostgreSQL 容器首次启动时自动执行
- 创建数据库扩展（`uuid-ossp`, `pg_trgm`）
- 创建基础表结构（如果脚本包含表定义）

**注意**：此脚本可能是旧版本，当前表结构主要通过其他方式创建。

### 2. `scripts/migrations/001_create_core_tables.sql`

**位置**：`scripts/migrations/001_create_core_tables.sql`

**作用**：
- 创建核心业务表：`detection_records`, `violation_events`, `statistics_hourly`, `alert_rules`, `alert_history`
- 创建索引和视图
- 创建触发器和函数

**执行方式**：
```bash
docker exec -i pyt-postgres-dev psql -U pyt_dev -d pyt_development < scripts/migrations/001_create_core_tables.sql
```

### 3. `scripts/init_database.py`

**位置**：`scripts/init_database.py`

**作用**：
- 调用 `src/database/init_db.py` 的 `main()` 函数
- 创建所有 ORM 定义的表
- 插入示例数据

**执行方式**：
```bash
python scripts/init_database.py
```

### 4. 仓储方法 `_ensure_table_exists()`

**位置**：各仓储实现类中

**作用**：
- 在首次使用仓储时动态检查并创建表
- 适用于：`detection_records`, `cameras`, `regions`

**示例**：
- `PostgreSQLDetectionRepository._ensure_table_exists()`：创建 `detection_records` 表
- `PostgreSQLCameraRepository._ensure_table_exists()`：创建 `cameras` 表
- `PostgreSQLRegionRepository._ensure_table_exists()`：创建 `regions` 表

---

## ✅ 推荐的首次部署流程

### 完整初始化步骤

1. **启动 Docker 容器**：
```bash
# 启动数据库和 Redis
docker-compose up -d database redis

# 等待数据库就绪
docker-compose ps
```

2. **执行 SQL 迁移脚本**（如果需要）：
```bash
# 创建核心业务表
docker exec -i pyt-postgres-dev psql -U pyt_dev -d pyt_development < scripts/migrations/001_create_core_tables.sql
```

3. **启动应用**（自动创建 ORM 表）：
```bash
# 启动 API 服务
docker-compose up -d api

# 查看初始化日志
docker logs pyt-api-dev | grep -i "数据库初始化"
```

4. **验证表创建**（可选）：
```bash
# 查看所有表
docker exec pyt-postgres-dev psql -U pyt_dev -d pyt_development -c "\dt"

# 查看表结构
docker exec pyt-postgres-dev psql -U pyt_dev -d pyt_development -c "\d workflows"
docker exec pyt-postgres-dev psql -U pyt_dev -d pyt_development -c "\d detection_records"
```

5. **插入初始数据**（可选）：
```bash
# 如果需要示例数据
docker exec pyt-api-dev python scripts/init_database.py
```

---

## 🔍 表创建时机总结

| 表类型 | 创建时机 | 创建方式 |
|--------|---------|---------|
| **MLOps 表** | 应用启动时 | SQLAlchemy ORM (`init_database()`) |
| **业务表（SQL）** | 手动执行 SQL 脚本 | `scripts/migrations/001_create_core_tables.sql` |
| **业务表（仓储）** | 首次使用仓储时 | 仓储方法 `_ensure_table_exists()` |

---

## ⚠️ 注意事项

1. **表结构一致性**：
   - ORM 模型定义的表结构应与数据库实际结构一致
   - 如果修改了 ORM 模型，需要执行数据库迁移（Alembic）或手动更新表结构

2. **初始化顺序**：
   - 建议先创建业务表（SQL 脚本），再启动应用（创建 ORM 表）
   - 如果表已存在，`CREATE TABLE IF NOT EXISTS` 不会报错

3. **数据持久化**：
   - Docker volume `postgres_dev_data` 持久化数据库数据
   - 删除 volume 会清空所有数据：`docker volume rm pyt_postgres_dev_data`

4. **迁移脚本**：
   - 当前项目未使用 Alembic 进行版本化迁移
   - 表结构变更需要手动执行 SQL 或更新仓储方法

---

## 📚 相关文件

- **ORM 模型**：`src/database/models.py`
- **数据库连接**：`src/database/connection.py`
- **初始化脚本**：`src/database/init_db.py`
- **SQL 迁移脚本**：`scripts/migrations/001_create_core_tables.sql`
- **Python 初始化脚本**：`scripts/init_database.py`
- **Docker 配置**：`docker-compose.yml`

---

## 🔧 故障排查

### 问题 1：表不存在

**症状**：应用启动时报错 "relation does not exist"

**解决方案**：
```bash
# 检查表是否存在
docker exec pyt-postgres-dev psql -U pyt_dev -d pyt_development -c "\dt"

# 手动执行 SQL 脚本创建表
docker exec -i pyt-postgres-dev psql -U pyt_dev -d pyt_development < scripts/migrations/001_create_core_tables.sql

# 或重启应用（自动创建 ORM 表）
docker-compose restart api
```

### 问题 2：表结构不匹配

**症状**：ORM 模型与数据库表结构不一致

**解决方案**：
1. 检查 ORM 模型定义：`src/database/models.py`
2. 检查数据库实际结构：`docker exec pyt-postgres-dev psql -U pyt_dev -d pyt_development -c "\d table_name"`
3. 手动执行 ALTER TABLE 或更新迁移脚本

### 问题 3：初始化脚本未执行

**症状**：Docker 容器启动后表未创建

**解决方案**：
```bash
# 检查容器日志
docker logs pyt-postgres-dev | grep -i "init"

# 手动执行初始化
docker exec pyt-api-dev python scripts/init_database.py
```

---

## 📝 总结

项目的数据库初始化采用**混合机制**：

1. **MLOps 表**：通过 SQLAlchemy ORM 自动创建（应用启动时）
2. **业务表**：通过 SQL 脚本或仓储方法创建
3. **Docker 容器**：首次启动时自动执行初始化脚本

**推荐流程**：
1. 启动 Docker 容器
2. 执行 SQL 迁移脚本（如需要）
3. 启动应用（自动创建 ORM 表）
4. 验证表创建
5. 插入初始数据（可选）

这样可以确保所有表都能正确创建，并且数据持久化到 Docker volume 中。

