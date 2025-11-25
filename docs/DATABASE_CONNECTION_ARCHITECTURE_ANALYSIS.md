# 数据库连接架构分析：MLOps vs 其他模块

## 📋 问题概述

**现象**: MLOps API端点连接不到数据库（`Connection refused`），但系统的其他模块（告警、摄像头、检测记录等）能正常连接数据库。

**问题**: 为什么同样的数据库，不同的模块会有不同的连接结果？

---

## 🔍 一、数据库连接方式的差异

### 1.1 MLOps模块的连接方式

**使用技术栈**:
- **SQLAlchemy异步引擎** (`create_async_engine`)
- **SQLAlchemy异步会话** (`AsyncSessionLocal`)
- **SQLAlchemy ORM** (`DatasetDAO`, `DeploymentDAO`, `WorkflowDAO`)

**连接配置**:
```python
# src/database/connection.py
ASYNC_DATABASE_URL = "postgresql+asyncpg://user:pass@host:port/db"
async_engine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=async_engine)
```

**使用方式**:
```python
# src/api/routers/mlops.py
@router.get("/datasets")
async def get_datasets(session: AsyncSession = Depends(get_async_session)):
    datasets = await DatasetDAO.get_all(session, ...)
```

**关键特点**:
- ✅ 需要 `postgresql+asyncpg://` 协议（SQLAlchemy异步驱动）
- ✅ 使用SQLAlchemy ORM进行数据库操作
- ✅ 通过 `AsyncSessionLocal` 创建会话
- ❌ **依赖 `ASYNC_DATABASE_URL` 环境变量**（修复前未设置）

---

### 1.2 其他模块的连接方式

**使用技术栈**:
- **asyncpg直接连接** (`asyncpg.create_pool`)
- **原生SQL查询** (不使用ORM)
- **仓储模式** (`PostgreSQLAlertRepository`, `PostgreSQLCameraRepository`)

**连接配置**:
```python
# src/services/database_service.py
database_url = os.getenv("DATABASE_URL", "postgresql://...")
self.pool = await asyncpg.create_pool(database_url, ...)
```

**使用方式**:
```python
# src/api/routers/alerts.py
async def get_alert_service():
    db = await get_db_service()  # 返回DatabaseService
    alert_repo = PostgreSQLAlertRepository(db.pool)  # 直接使用asyncpg Pool
    return AlertService(alert_repo)
```

**关键特点**:
- ✅ 只需要 `postgresql://` 协议（asyncpg原生协议）
- ✅ 直接使用 `asyncpg.Pool` 连接池
- ✅ 使用原生SQL查询，不依赖ORM
- ✅ **只依赖 `DATABASE_URL` 环境变量**（已正确设置）

---

## 📊 二、连接方式的详细对比

### 2.1 连接字符串格式

| 模块类型 | 协议格式 | 示例 | 驱动 |
|---------|---------|------|------|
| **MLOps** | `postgresql+asyncpg://` | `postgresql+asyncpg://user:pass@database:5432/db` | SQLAlchemy + asyncpg |
| **其他模块** | `postgresql://` | `postgresql://user:pass@database:5432/db` | asyncpg 直接 |

### 2.2 连接池创建方式

#### MLOps模块（SQLAlchemy）
```python
# 使用SQLAlchemy异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,  # 需要 postgresql+asyncpg://
    pool_pre_ping=True,
    pool_recycle=300,
)
AsyncSessionLocal = async_sessionmaker(bind=async_engine)
```

#### 其他模块（asyncpg直接）
```python
# 直接使用asyncpg创建连接池
pool = await asyncpg.create_pool(
    DATABASE_URL,  # 只需要 postgresql://
    min_size=5,
    max_size=20,
)
```

### 2.3 数据库操作方式

#### MLOps模块（ORM方式）
```python
# 使用SQLAlchemy ORM
async with AsyncSessionLocal() as session:
    datasets = await DatasetDAO.get_all(session, ...)
    # DatasetDAO内部使用SQLAlchemy ORM查询
```

#### 其他模块（原生SQL）
```python
# 使用原生SQL查询
conn = await pool.acquire()
try:
    rows = await conn.fetch("SELECT * FROM alerts WHERE ...")
finally:
    await pool.release(conn)
```

---

## 🔍 三、问题根本原因分析

### 3.1 环境变量配置差异

**docker-compose.yml配置**:
```yaml
environment:
  - DATABASE_URL=postgresql://pepgmp_dev:...@database:5432/pepgmp_development
  # ❌ ASYNC_DATABASE_URL 未设置
```

**问题**:
1. ✅ `DATABASE_URL` 已正确设置 → 其他模块正常工作
2. ❌ `ASYNC_DATABASE_URL` 未设置 → MLOps模块使用默认值

### 3.2 默认值的问题

**MLOps模块的默认值**:
```python
# src/database/connection.py (修复前)
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    "postgresql+asyncpg://...@localhost:5432/..."  # ❌ 使用localhost
)
```

**其他模块的默认值**:
```python
# src/services/database_service.py
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://...@localhost:5432/..."  # 也有默认值，但环境变量已设置
)
```

**关键差异**:
- **其他模块**: `DATABASE_URL` 环境变量已设置 → 使用正确的 `database:5432`
- **MLOps模块**: `ASYNC_DATABASE_URL` 环境变量未设置 → 使用默认值 `localhost:5432` → **连接失败**

---

## 📈 四、连接架构对比图

```
┌─────────────────────────────────────────────────────────────┐
│                    MLOps模块连接架构                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Endpoint                                           │
│       ↓                                                      │
│  get_async_session()                                        │
│       ↓                                                      │
│  AsyncSessionLocal (SQLAlchemy)                             │
│       ↓                                                      │
│  create_async_engine(ASYNC_DATABASE_URL)                    │
│       ↓                                                      │
│  postgresql+asyncpg://user@database:5432/db                │
│       ↓                                                      │
│  asyncpg驱动 (通过SQLAlchemy)                               │
│       ↓                                                      │
│  PostgreSQL数据库                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  其他模块连接架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FastAPI Endpoint                                           │
│       ↓                                                      │
│  get_db_service()                                           │
│       ↓                                                      │
│  DatabaseService                                            │
│       ↓                                                      │
│  asyncpg.create_pool(DATABASE_URL)                          │
│       ↓                                                      │
│  postgresql://user@database:5432/db                        │
│       ↓                                                      │
│  asyncpg驱动 (直接)                                         │
│       ↓                                                      │
│  PostgreSQL数据库                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 五、关键差异总结

### 5.1 技术栈差异

| 特性 | MLOps模块 | 其他模块 |
|------|-----------|---------|
| **ORM框架** | ✅ SQLAlchemy ORM | ❌ 无ORM，直接SQL |
| **连接驱动** | SQLAlchemy + asyncpg | asyncpg 直接 |
| **会话管理** | SQLAlchemy AsyncSession | asyncpg Pool |
| **查询方式** | ORM查询 (`DatasetDAO.get_all()`) | 原生SQL (`conn.fetch()`) |
| **连接字符串** | `postgresql+asyncpg://` | `postgresql://` |

### 5.2 环境变量依赖

| 模块类型 | 依赖的环境变量 | 默认值问题 |
|---------|--------------|-----------|
| **MLOps** | `ASYNC_DATABASE_URL` | ❌ 未设置，使用默认值 `localhost` |
| **其他模块** | `DATABASE_URL` | ✅ 已设置，使用正确的 `database` |

### 5.3 连接池管理

| 特性 | MLOps模块 | 其他模块 |
|------|-----------|---------|
| **连接池类型** | SQLAlchemy连接池 | asyncpg连接池 |
| **创建时机** | 模块导入时创建引擎 | 服务初始化时创建池 |
| **生命周期** | 应用生命周期 | 服务生命周期 |

---

## 💡 六、为什么会有两种连接方式？

### 6.1 历史演进

**MLOps模块**:
- 使用SQLAlchemy ORM是为了：
  - ✅ 类型安全（Pydantic模型）
  - ✅ 自动迁移支持
  - ✅ 更高级的查询API
  - ✅ 与FastAPI更好的集成

**其他模块**:
- 使用asyncpg直接连接是为了：
  - ✅ 更高的性能（无ORM开销）
  - ✅ 更灵活的原生SQL查询
  - ✅ 更早的实现（历史原因）

### 6.2 架构设计考虑

**MLOps模块** (ORM方式):
- 适合复杂的数据模型关系
- 适合需要类型检查和验证的场景
- 适合需要数据库迁移的场景

**其他模块** (原生SQL):
- 适合高性能要求的场景
- 适合需要复杂SQL查询的场景
- 适合需要精细控制查询的场景

---

## 🎯 七、问题根源总结

### 7.1 核心问题

**问题**: 为什么MLOps连接失败，其他模块正常？

**答案**: 
1. **环境变量配置不一致**
   - `DATABASE_URL` 已设置 → 其他模块正常
   - `ASYNC_DATABASE_URL` 未设置 → MLOps使用默认值 `localhost` → 失败

2. **连接方式不同**
   - MLOps需要 `postgresql+asyncpg://` 协议
   - 其他模块只需要 `postgresql://` 协议

3. **默认值问题**
   - MLOps的默认值使用 `localhost`（容器内不可用）
   - 其他模块虽然也有默认值，但环境变量已正确设置

### 7.2 为什么修复后能工作？

**修复方案**: 从 `DATABASE_URL` 自动生成 `ASYNC_DATABASE_URL`

```python
# 修复后的逻辑
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
```

**结果**:
- ✅ `DATABASE_URL`: `postgresql://...@database:5432/...`
- ✅ `ASYNC_DATABASE_URL`: `postgresql+asyncpg://...@database:5432/...` (自动生成)
- ✅ 两者都使用正确的服务名 `database`

---

## 📝 八、架构建议

### 8.1 统一连接方式（可选）

**方案1**: 统一使用SQLAlchemy ORM
- ✅ 类型安全
- ✅ 统一的查询API
- ❌ 需要重构现有代码
- ❌ 可能有性能开销

**方案2**: 统一使用asyncpg直接连接
- ✅ 性能更好
- ✅ 更灵活
- ❌ 需要重构MLOps模块
- ❌ 失去ORM的优势

**方案3**: 保持现状，但统一配置管理
- ✅ 最小改动
- ✅ 保持各自优势
- ✅ 通过配置管理统一环境变量

### 8.2 配置管理建议

**当前状态**: 
- `DATABASE_URL` 已设置
- `ASYNC_DATABASE_URL` 自动生成（修复后）

**建议**:
- ✅ 保持自动生成机制（已实现）
- ✅ 可选：在docker-compose.yml中显式设置两个环境变量（更明确）
- ✅ 文档说明两种连接方式的差异

---

## ✅ 九、总结

### 9.1 问题原因

1. **环境变量配置不一致**
   - `DATABASE_URL` 已设置，`ASYNC_DATABASE_URL` 未设置

2. **连接方式不同**
   - MLOps使用SQLAlchemy ORM（需要 `postgresql+asyncpg://`）
   - 其他模块使用asyncpg直接连接（只需要 `postgresql://`）

3. **默认值问题**
   - MLOps的默认值使用 `localhost`，在Docker容器中不可用

### 9.2 解决方案

- ✅ 从 `DATABASE_URL` 自动生成 `ASYNC_DATABASE_URL`
- ✅ 确保两者都使用正确的服务名（`database`）
- ✅ 保持向后兼容

### 9.3 架构差异

| 特性 | MLOps模块 | 其他模块 |
|------|-----------|---------|
| **连接方式** | SQLAlchemy ORM | asyncpg直接 |
| **协议** | `postgresql+asyncpg://` | `postgresql://` |
| **查询方式** | ORM查询 | 原生SQL |
| **优势** | 类型安全、ORM特性 | 性能、灵活性 |

---

**分析完成日期**: 2025-11-25  
**状态**: ✅ **问题已分析清楚，架构差异已明确**

