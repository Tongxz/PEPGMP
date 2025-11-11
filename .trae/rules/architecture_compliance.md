# 架构合规规则

## 📋 核心原则

**所有代码实现、功能改造、错误修复都必须符合当前最新的DDD架构要求。**

---

## 🏗️ 架构要求

### 架构层次（必须严格遵守）

```
API层 (Interfaces) → 应用层 (Application) → 领域层 (Domain) → 基础设施层 (Infrastructure)
```

#### 1. API层 (`src/api/`)
- **职责**: HTTP请求处理、参数验证、响应格式化
- **禁止**:
  - ❌ 直接访问数据库连接池
  - ❌ 直接调用仓储实现类
  - ❌ 包含业务逻辑
  - ❌ 回退逻辑（fallback）
  - ❌ 灰度控制参数（`force_domain`、`should_use_domain`）
- **必须**:
  - ✅ 通过领域服务或应用服务访问数据
  - ✅ 统一的错误处理（HTTP异常）
  - ✅ 如果服务不可用，返回明确的HTTP 503错误

#### 2. 应用层 (`src/application/`)
- **职责**: 用例编排、DTO转换、事务协调
- **禁止**:
  - ❌ 直接访问数据库
  - ❌ 包含领域业务逻辑
- **必须**:
  - ✅ 协调领域服务和基础设施
  - ✅ 处理跨领域事务

#### 3. 领域层 (`src/domain/`)
- **职责**: 业务逻辑、领域规则、领域模型
- **包含**:
  - ✅ 实体 (Entities) - `src/domain/entities/`
  - ✅ 值对象 (Value Objects) - `src/domain/value_objects/`
  - ✅ 领域服务 (Domain Services) - `src/domain/services/`
  - ✅ 仓储接口 (Repository Interfaces) - `src/domain/repositories/`
  - ✅ 领域事件 (Domain Events) - `src/domain/events/`
- **禁止**:
  - ❌ 依赖基础设施层
  - ❌ 直接访问数据库
  - ❌ 包含框架特定代码

#### 4. 基础设施层 (`src/infrastructure/`)
- **职责**: 仓储实现、外部服务集成、技术实现
- **包含**:
  - ✅ 仓储实现 - `src/infrastructure/repositories/`
  - ✅ 数据库连接
  - ✅ 外部API集成
- **必须**:
  - ✅ 实现领域层定义的仓储接口
  - ✅ 只负责技术实现，不包含业务逻辑

---

## 🚫 禁止事项

### 1. 禁止回退逻辑（Fallback）

**原因**: 回退逻辑会导致结果不可预期，违反架构原则。

**禁止的模式**:
```python
# ❌ 禁止：回退到旧实现
try:
    result = await domain_service.get_data()
    return result
except Exception:
    # 回退到旧实现
    return old_implementation()

# ❌ 禁止：回退到直接数据库查询
try:
    result = await domain_service.get_data()
except Exception:
    async with db.pool.acquire() as conn:
        # 直接查询数据库
        return await conn.fetch(...)

# ❌ 禁止：回退到日志文件
try:
    result = await domain_service.get_data()
except Exception:
    # 读取日志文件
    return _read_from_log_file()
```

**正确的做法**:
```python
# ✅ 正确：统一使用领域服务，失败时返回明确的HTTP错误
def _ensure_domain_service():
    if get_domain_service is None:
        raise HTTPException(
            status_code=503,
            detail="领域服务不可用，请联系系统管理员"
        )
    return get_domain_service()

@router.get("/endpoint")
async def get_data():
    try:
        domain_service = _ensure_domain_service()
        result = await domain_service.get_data()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取数据失败: {str(e)}"
        )
```

### 2. 禁止灰度控制

**原因**: 灰度控制会在代码中留下多条执行路径，增加维护成本。

**禁止的模式**:
```python
# ❌ 禁止：灰度控制参数
async def endpoint(
    force_domain: Optional[bool] = Query(None),
):
    if should_use_domain(force_domain):
        # 新实现
        return await new_service.get_data()
    # 旧实现
    return await old_service.get_data()
```

**正确的做法**:
```python
# ✅ 正确：统一使用新架构
async def endpoint():
    domain_service = _ensure_domain_service()
    return await domain_service.get_data()
```

### 3. 禁止跨层调用

**禁止的模式**:
```python
# ❌ 禁止：API层直接访问数据库
@router.get("/endpoint")
async def get_data():
    async with db.pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM ...")

# ❌ 禁止：领域层依赖基础设施
from src.infrastructure.repositories.postgresql_repository import PostgreSQLRepository

# ❌ 禁止：基础设施层包含业务逻辑
class PostgreSQLRepository:
    def save(self, record):
        # 业务逻辑验证
        if record.count > 100:
            raise ValueError("超过限制")
        # 保存
```

**正确的做法**:
```python
# ✅ 正确：API层通过领域服务
@router.get("/endpoint")
async def get_data():
    domain_service = _ensure_domain_service()
    return await domain_service.get_data()

# ✅ 正确：领域层定义接口
from src.domain.repositories.repository_interface import IRepository

# ✅ 正确：基础设施层只负责技术实现
class PostgreSQLRepository(IRepository):
    def save(self, record):
        # 只负责持久化，业务逻辑在领域层
        await self.conn.execute("INSERT INTO ...")
```

---

## ✅ 必须遵守的原则

### 1. SOLID原则

- **单一职责原则 (SRP)**: 每个类只有一个改变的理由
- **开闭原则 (OCP)**: 对扩展开放，对修改关闭
- **里氏替换原则 (LSP)**: 子类可以替换父类
- **接口隔离原则 (ISP)**: 客户端不应依赖不需要的接口
- **依赖倒置原则 (DIP)**: 依赖抽象而不是具体实现

### 2. 依赖方向

**正确的依赖方向**:
```
API层 → 应用层 → 领域层 ← 基础设施层
```

**禁止的依赖方向**:
```
❌ 领域层 → 基础设施层
❌ API层 → 基础设施层（绕过领域层）
❌ 基础设施层 → 应用层
```

### 3. 数据访问模式

**所有数据访问必须通过仓储接口**:

```python
# ✅ 正确：通过仓储接口
domain_service.detection_repository.find_by_id(id)

# ❌ 禁止：直接访问数据库
async with db.pool.acquire() as conn:
    await conn.fetch("SELECT * FROM ...")
```

### 4. 错误处理

**统一的错误处理规范**:

```python
# 服务不可用（HTTP 503）
if service is None:
    raise HTTPException(
        status_code=503,
        detail="服务不可用，请联系系统管理员"
    )

# 业务错误（HTTP 400/404）
if not found:
    raise HTTPException(
        status_code=404,
        detail="资源不存在"
    )

# 系统错误（HTTP 500）
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"操作失败: {str(e)}"
    )
```

---

## 📝 代码审查检查清单

在提交代码前，请确保：

- [ ] **无回退逻辑**: 代码中没有 `try-except` 回退到旧实现
- [ ] **无灰度控制**: 代码中没有 `should_use_domain` 或 `force_domain` 参数
- [ ] **无跨层调用**: API层不直接访问数据库，领域层不依赖基础设施
- [ ] **统一错误处理**: 使用HTTP异常，不返回默认值
- [ ] **通过仓储接口**: 所有数据访问通过仓储接口
- [ ] **职责清晰**: 每层只负责自己的职责
- [ ] **符合SOLID**: 代码符合SOLID原则
- [ ] **依赖方向正确**: 依赖方向符合架构要求

---

## 📚 参考文档

- [系统架构文档](../docs/SYSTEM_ARCHITECTURE.md)
- [架构符合性检查](../docs/ARCHITECTURE_COMPLIANCE_CHECK.md)
- [架构符合性改进](../docs/ARCHITECTURE_COMPLIANCE_IMPROVEMENTS.md)
- [架构合规 - 移除回退逻辑](../docs/ARCHITECTURE_COMPLIANCE_NO_FALLBACK.md)

---

## 🔄 更新历史

- **2025-11-04**: 初始版本 - 明确禁止回退逻辑和灰度控制
- **2025-11-04**: 添加架构层次要求和依赖方向规范

---

**重要提醒**: 任何不符合本规则的代码修改都将被拒绝。如有疑问，请参考架构文档或咨询架构负责人。
