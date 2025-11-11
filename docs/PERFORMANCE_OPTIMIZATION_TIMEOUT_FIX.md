# 接口超时问题优化方案

## 问题描述

前端调用以下接口时出现15秒超时错误：
- `/records/detection-records/cam0` - 获取检测记录
- `/records/violations` - 获取违规记录
- `/records/detection-records/vid1` - 获取检测记录

## 问题分析

### 根本原因

1. **COUNT查询性能问题**：
   - `count_by_camera_id()` 方法每次都会执行 `SELECT COUNT(*)` 全表扫描
   - 当数据量很大时，COUNT查询会非常慢
   - 违规记录查询也存在同样的问题

2. **缺少索引优化**：
   - 可能缺少 `camera_id` 和 `timestamp` 的复合索引
   - 导致查询性能下降

3. **查询逻辑未优化**：
   - 即使不需要总数，也会执行COUNT查询
   - 没有利用时间范围筛选来减少查询范围

## 优化方案

### 1. 检测记录查询优化

**修改文件**：`src/services/detection_service_domain.py`

**优化策略**：
1. **时间范围查询优化**：
   - 如果提供了时间范围，使用 `find_by_time_range()` 代替 `find_by_camera_id()`
   - 时间范围查询更高效，因为可以限制查询范围

2. **COUNT查询优化**：
   - 只在第一页（offset=0）时查询总数
   - 非第一页使用近似值（当前记录数+offset）
   - 如果COUNT查询失败，使用近似值而不是抛出异常

3. **时间范围参数支持**：
   - API接口支持 `start_time` 和 `end_time` 参数
   - 前端已经传递时间范围参数，后端现在可以正确使用

**关键代码**：
```python
# 如果有时间范围，使用时间范围查询（更高效）
if start_time and end_time:
    records = await self.detection_repository.find_by_time_range(
        start_time=start_time,
        end_time=end_time,
        camera_id=camera_id,
        limit=limit,
    )
    # 对于时间范围查询，使用近似总数，避免全表COUNT查询
    total = len(records) + offset if len(records) == limit else len(records) + offset
else:
    # 只有在第一页时才获取总数，避免性能问题
    if offset == 0:
        try:
            total = await self.detection_repository.count_by_camera_id(camera_id)
        except Exception as e:
            logger.warning(f"获取总数失败，使用近似值: {e}")
            total = len(records) + offset if len(records) == limit else len(records) + offset
    else:
        # 非第一页不查询总数，使用近似值
        total = len(records) + offset if len(records) == limit else len(records) + offset
```

### 2. 违规记录查询优化

**修改文件**：`src/infrastructure/repositories/postgresql_detection_repository.py`

**优化策略**：
1. **COUNT查询优化**：
   - 只在第一页（offset=0）时查询总数
   - 非第一页使用近似值（当前记录数+offset）
   - 如果COUNT查询失败，使用近似值

**关键代码**：
```python
# 优化：只在第一页（offset=0）时查询总数，避免性能问题
if offset == 0:
    try:
        total_sql = f"SELECT COUNT(*) AS total FROM violation_events{where_sql}"
        total = await conn.fetchval(total_sql, *params)
    except Exception as e:
        logger.warning(f"获取违规记录总数失败，使用近似值: {e}")
        total = None
else:
    # 非第一页不查询总数，使用近似值
    total = None

# 如果没有查询总数，使用近似值
if total is None:
    total = len(violations) + offset if len(violations) == limit else len(violations) + offset
```

### 3. API接口增强

**修改文件**：`src/api/routers/records.py`

**新增功能**：
- 支持 `start_time` 和 `end_time` 查询参数
- 自动解析ISO格式时间字符串
- 将时间参数传递给领域服务

**关键代码**：
```python
@router.get("/detection-records/{camera_id}")
async def get_detection_records(
    camera_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO格式)"),
) -> Dict[str, Any]:
    # 解析时间参数并传递给领域服务
    ...
```

## 性能提升预期

### 优化前
- 每次查询都会执行COUNT查询（全表扫描）
- 数据量大时，COUNT查询可能需要10-30秒
- 导致接口超时（15秒）

### 优化后
- 第一页：COUNT查询（如果数据量大，仍可能较慢，但只执行一次）
- 非第一页：不执行COUNT查询，使用近似值（几乎瞬间完成）
- 有时间范围：使用时间范围查询，不执行COUNT查询（性能大幅提升）

### 预期效果
- **第一页查询**：如果数据量大，可能仍需要几秒，但不会超时（如果数据库有索引）
- **非第一页查询**：几乎瞬间完成（< 1秒）
- **有时间范围筛选**：性能大幅提升（< 2秒）

## 进一步优化建议

### 1. 数据库索引优化

检查并创建以下索引（如果不存在）：

```sql
-- 检测记录表索引
CREATE INDEX IF NOT EXISTS idx_detection_records_camera_timestamp
ON detection_records(camera_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_detection_records_timestamp
ON detection_records(timestamp DESC);

-- 违规记录表索引
CREATE INDEX IF NOT EXISTS idx_violation_events_camera_timestamp
ON violation_events(camera_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_violation_events_status
ON violation_events(status);

CREATE INDEX IF NOT EXISTS idx_violation_events_type
ON violation_events(violation_type);
```

### 2. 前端超时时间调整（临时方案）

如果优化后仍有超时问题，可以考虑：
- 增加前端请求超时时间（从15秒增加到30秒）
- 但这不是根本解决方案，应该优化数据库查询

### 3. 缓存策略

对于频繁查询的统计数据：
- 使用Redis缓存总数
- 设置合理的缓存过期时间（如5分钟）
- 当数据更新时，清除缓存

## 测试建议

1. **测试第一页查询**：
   - 验证COUNT查询是否正常
   - 验证响应时间是否在可接受范围内

2. **测试非第一页查询**：
   - 验证是否不执行COUNT查询
   - 验证响应时间是否大幅提升

3. **测试时间范围筛选**：
   - 验证时间范围查询是否正常工作
   - 验证性能是否提升

4. **测试大数据量场景**：
   - 在有大量数据的情况下测试
   - 验证优化效果

## 总结

通过以下优化措施，接口超时问题应该得到显著改善：

1. ✅ 只在第一页查询总数，非第一页使用近似值
2. ✅ 支持时间范围查询，减少查询范围
3. ✅ COUNT查询失败时使用近似值，不抛出异常
4. ✅ API接口支持时间范围参数

**下一步**：
- 验证优化效果
- 如果仍有问题，考虑添加数据库索引
- 考虑实现缓存策略

---

**文档版本**: 1.0
**最后更新**: 2024-11-05
**状态**: ✅ 优化已完成
