# 数据库连接泄漏修复

## 问题描述

前端在查询历史记录时出现超时错误（30秒超时），即使数据库查询本身很快（< 0.001秒）。

## 根本原因

**数据库连接泄漏**：`PostgreSQLDetectionRepository` 的 `find_by_time_range` 和 `find_by_camera_id` 方法在获取数据库连接后，**没有在 finally 块中释放连接**，导致：

1. 连接池中的连接被耗尽
2. 后续请求无法获取连接，一直等待
3. 最终导致前端请求超时

## 修复方案

### 修复文件

`src/infrastructure/repositories/postgresql_detection_repository.py`

### 修复内容

#### 1. `find_by_time_range` 方法

**修复前**：
```python
conn = await self._get_connection()

try:
    # 执行查询
    rows = await conn.fetch(...)
except Exception:
    # 兼容模式查询
    rows = await conn.fetch(...)

return [self._row_to_record(row) for row in rows]
# ❌ 连接没有被释放！
```

**修复后**：
```python
conn = await self._get_connection()
rows = None

try:
    # 执行查询
    rows = await conn.fetch(...)
except Exception:
    # 兼容模式查询
    try:
        rows = await conn.fetch(...)
    except Exception as e:
        logger.error(f"兼容模式查询也失败: {e}")
        rows = []
finally:
    # ✅ 确保连接被释放，避免连接泄漏
    await self._release_connection(conn)

if rows is None:
    rows = []
records = [self._row_to_record(row) for row in rows]
return records
```

#### 2. `find_by_camera_id` 方法

**修复前**：
```python
conn = await self._get_connection()

try:
    rows = await conn.fetch(...)
except Exception:
    rows = await conn.fetch(...)

return [self._row_to_record(row) for row in rows]
# ❌ 连接没有被释放！
```

**修复后**：
```python
conn = await self._get_connection()
rows = None

try:
    rows = await conn.fetch(...)
except Exception:
    try:
        rows = await conn.fetch(...)
    except Exception as e:
        logger.error(f"兼容模式查询也失败: {e}")
        rows = []
finally:
    # ✅ 确保连接被释放
    await self._release_connection(conn)

if rows is None:
    rows = []
return [self._row_to_record(row) for row in rows]
```

## 修复效果

### 修复前
- 每次查询后连接不释放
- 连接池逐渐耗尽（默认最大10个连接）
- 第11个请求开始等待，直到超时（30秒）
- **结果**: 前端请求超时 ❌

### 修复后
- 每次查询后连接立即释放
- 连接池可以正常复用
- 所有请求都能正常获取连接
- **结果**: 查询正常完成 ✅

## 连接池配置

当前连接池配置：
- 最小连接数：2
- 最大连接数：10
- 命令超时：30秒

修复后，即使有10个并发请求，连接也能正常释放和复用。

## 其他可能存在连接泄漏的方法

检查并确保以下方法也正确释放连接：
- ✅ `find_by_time_range` - 已修复
- ✅ `find_by_camera_id` - 已修复
- ✅ `save` - 已有 `finally` 块
- ✅ `find_by_id` - 已有 `finally` 块
- ⚠️ `find_by_confidence_range` - 需要检查
- ⚠️ `count_by_camera_id` - 需要检查
- ⚠️ `get_statistics` - 需要检查

## 测试验证

### 测试场景

1. **单次查询**：
   - ✅ 查询后连接应该被释放
   - ✅ 查询应该正常完成

2. **多次查询**：
   - ✅ 连续查询10次，应该都能正常完成
   - ✅ 连接池不应该耗尽

3. **并发查询**：
   - ✅ 同时发起10个请求，应该都能正常完成
   - ✅ 连接应该正常释放和复用

## 预防措施

### 代码审查检查清单

在编写使用数据库连接的代码时，确保：

- [ ] 使用 `try-finally` 确保连接释放
- [ ] 在 `finally` 块中调用 `_release_connection`
- [ ] 不要在 `try` 或 `except` 中直接 `return`，除非在 `finally` 之后
- [ ] 使用连接上下文管理器（如果可用）

### 推荐的模式

```python
async def some_method(self):
    conn = await self._get_connection()
    rows = None

    try:
        # 执行查询
        rows = await conn.fetch(...)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        rows = []
    finally:
        # 确保连接被释放
        await self._release_connection(conn)

    # 处理结果
    if rows is None:
        rows = []
    return process_rows(rows)
```

## 相关文档

- `docs/TIMEOUT_FIX_LATEST.md` - 超时问题修复
- `docs/PERFORMANCE_OPTIMIZATION_TIMEOUT_FIX.md` - 性能优化

---

**修复日期**: 2024-11-05
**修复文件**: `src/infrastructure/repositories/postgresql_detection_repository.py`
**严重程度**: P0（导致系统无法使用）
