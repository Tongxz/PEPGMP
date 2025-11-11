# 统一数据库存储架构

## 📅 更新日期: 2025-11-04

**目标**: 统一所有数据存储到数据库，移除JSON文件回退逻辑，以数据库为主要数据源。

---

## 🎯 架构原则

### 1. 数据存储策略

- ✅ **数据库为主要数据源**: 所有业务数据存储在PostgreSQL数据库中
- ✅ **配置文件作为导入源**: JSON配置文件可以作为数据导入源，但导入后写入数据库
- ✅ **无回退逻辑**: 移除所有JSON文件的回退逻辑，统一使用数据库
- ✅ **自动导入**: 应用启动时，如果数据库为空且有配置文件，自动导入到数据库

### 2. 数据流程

```
配置文件 (JSON) → 导入 → 数据库 (PostgreSQL) → 读取 → API → 前端
```

---

## ✅ 已完成的修改

### 1. 区域管理（Regions）

**修改文件**:
- `src/api/routers/region_management.py`
- `src/domain/services/region_service.py`
- `src/api/app.py`

**修改内容**:

#### 1.1 统一使用数据库读取

**修改前**:
```python
# 有JSON文件回退逻辑
if should_use_domain(force_domain):
    # 使用领域服务（数据库）
else:
    # 回退到JSON文件
```

**修改后**:
```python
# 统一使用数据库（领域服务）
if get_region_domain_service is not None:
    region_domain_service = await get_region_domain_service()
    regions = await region_domain_service.get_all_regions(active_only=active_only)
    return regions
else:
    raise HTTPException(status_code=500, detail="区域服务不可用")
```

#### 1.2 添加导入/导出功能

**新增API**:
- `POST /api/v1/management/regions/import` - 从配置文件导入区域到数据库
- `GET /api/v1/management/regions/export` - 从数据库导出区域配置到文件

**新增方法**:
```python
# src/domain/services/region_service.py
async def import_from_file(self, file_path: str, camera_id: Optional[str] = None) -> Dict[str, Any]:
    """从配置文件导入区域到数据库."""
    # 读取JSON文件
    # 检查是否已存在
    # 导入到数据库
```

#### 1.3 应用启动时自动导入

**修改**:
```python
# src/api/app.py
# 检查是否有配置文件需要导入
if os.path.exists(regions_file):
    # 检查数据库中是否已有区域
    existing_regions = await region_domain_service.get_all_regions(active_only=False)
    if not existing_regions:
        # 如果数据库为空，导入配置文件
        result = await region_domain_service.import_from_file(regions_file)
```

---

### 2. 统计分析（Statistics）

**修改文件**:
- `src/api/routers/statistics.py`

**修改内容**:

#### 2.1 移除日志文件回退逻辑

**修改前**:
```python
# 优先使用领域服务（数据库）
if should_use_domain(force_domain):
    # 从数据库查询
# 如果失败，回退到日志文件
rows = _read_recent_events(...)
```

**修改后**:
```python
# 优先使用领域服务（数据库）
if should_use_domain(force_domain):
    # 从数据库查询
# 如果失败，返回空结果（不再回退到日志文件）
return {
    "window_minutes": minutes,
    "total_events": 0,
    "counts_by_type": {},
    "samples": [],
}
```

#### 2.2 添加数据库查询回退逻辑

**新增**:
- 如果领域服务不可用，直接从数据库查询
- 正确处理时区转换（aware datetime → naive datetime）

---

## 📊 API变更

### 区域管理API

| 方法 | 路径 | 变更 |
|------|------|------|
| GET | `/api/v1/management/regions` | ✅ 统一从数据库读取 |
| POST | `/api/v1/management/regions` | ✅ 统一存储到数据库 |
| PUT | `/api/v1/management/regions/{region_id}` | ✅ 统一更新到数据库 |
| DELETE | `/api/v1/management/regions/{region_id}` | ✅ 统一从数据库删除 |
| POST | `/api/v1/management/regions/import` | 🆕 从配置文件导入到数据库 |
| GET | `/api/v1/management/regions/export` | 🆕 从数据库导出到文件 |

### 统计分析API

| 方法 | 路径 | 变更 |
|------|------|------|
| GET | `/api/v1/statistics/summary` | ✅ 统一从数据库读取（移除日志文件回退） |
| GET | `/api/v1/statistics/events` | ✅ 统一从数据库读取（移除日志文件回退） |

---

## 🔄 数据迁移

### 自动导入流程

1. **应用启动时检查**:
   - 检查数据库是否已有区域数据
   - 如果数据库为空，检查是否有配置文件

2. **自动导入**:
   - 如果配置文件存在且数据库为空，自动导入
   - 记录导入结果（导入数量、跳过数量、错误数量）

3. **日志记录**:
   ```
   INFO: 数据库中没有区域数据，从配置文件导入: config/regions.json
   INFO: 区域导入完成: 导入=5, 跳过=0, 错误=0
   ```

### 手动导入

**API调用**:
```bash
curl -X POST "http://localhost:8000/api/v1/management/regions/import?file_path=config/regions.json"
```

**响应**:
```json
{
  "status": "success",
  "imported": 5,
  "skipped": 0,
  "errors": 0,
  "total": 5
}
```

---

## 📝 数据库表结构

### regions表

```sql
CREATE TABLE IF NOT EXISTS regions (
    region_id VARCHAR(100) PRIMARY KEY,
    region_type VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    polygon JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    rules JSONB DEFAULT '{}'::jsonb,
    camera_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## ⚠️ 注意事项

### 1. 配置文件导入

- **导入时机**: 仅在数据库为空时自动导入
- **重复导入**: 如果区域ID已存在，会跳过（不覆盖）
- **错误处理**: 导入失败不影响应用启动

### 2. 数据一致性

- **单一数据源**: 数据库是唯一的数据源
- **配置文件**: 仅作为导入源，不参与运行时读取
- **导出功能**: 用于备份和迁移，不用于运行时读取

### 3. 性能考虑

- **数据库查询**: 所有读取操作都从数据库查询
- **索引优化**: 已创建必要的索引（camera_id, region_type, is_active）
- **连接池**: 使用PostgreSQL连接池管理数据库连接

---

## 🧪 测试验证

### 1. 区域导入测试

```bash
# 测试自动导入（应用启动时）
# 检查日志：应看到"区域导入完成"消息

# 测试手动导入
curl -X POST "http://localhost:8000/api/v1/management/regions/import"

# 验证导入结果
curl "http://localhost:8000/api/v1/management/regions"
```

### 2. 区域读取测试

```bash
# 测试从数据库读取
curl "http://localhost:8000/api/v1/management/regions"

# 测试按摄像头过滤
curl "http://localhost:8000/api/v1/management/regions?camera_id=cam0"

# 测试只返回活跃区域
curl "http://localhost:8000/api/v1/management/regions?active_only=true"
```

### 3. 统计查询测试

```bash
# 测试统计摘要（从数据库）
curl "http://localhost:8000/api/v1/statistics/summary?minutes=1440&camera_id=test_xgboost_fix"

# 测试事件列表（从数据库）
curl "http://localhost:8000/api/v1/statistics/events?start_time=2025-11-04T00:00:00Z&end_time=2025-11-04T23:59:59Z"
```

---

## 📚 相关文档

- [前端数据缺失问题修复总结](./FRONTEND_DATA_FIX_SUMMARY.md) - 之前的修复记录
- [数据库时区问题修复](./DATABASE_TIMEZONE_COMPLETE_CHECK.md) - 时区处理相关

---

**更新完成日期**: 2025-11-04
**状态**: ✅ 已完成
**下一步**: 测试验证

---

*统一数据库存储架构已实现，所有数据统一从数据库读取，配置文件仅作为导入源。*
