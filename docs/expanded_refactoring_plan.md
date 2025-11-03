# API端点扩展重构计划

## 概述

当前已完成重构的API端点（3个）：
1. ✅ `GET /api/v1/statistics/summary` - 事件统计汇总
2. ✅ `GET /api/v1/records/violations` - 违规记录列表
3. ✅ `GET /api/v1/records/statistics/{camera_id}` - 摄像头统计

本文档列出可以进一步重构的其他API端点，按优先级分类。

## 已重构端点状态

- **数量**: 3个
- **类型**: 全部为读操作（GET）
- **状态**: 已全量灰度（ROLLOUT_PERCENT=100%）
- **验证**: 已通过功能、性能、回退验证

## 待重构端点分类

### 🔴 高优先级 - 读操作端点（优先重构）

这些端点都是读操作，风险低，适合优先重构：

#### Records 路由 (`/api/v1/records`)

1. **`GET /api/v1/records/detection-records/{camera_id}`**
   - **当前实现**: 直接查询数据库
   - **重构方案**: 使用 `DetectionServiceDomain.get_detection_records()`
   - **难度**: ⭐ 低
   - **依赖**: `IDetectionRepository.find_by_camera_id()`

2. **`GET /api/v1/records/violations/{violation_id}`**
   - **当前实现**: 查询所有违规记录后过滤
   - **重构方案**: 使用 `DetectionServiceDomain.get_violation_details()` 或新增 `get_violation_by_id()`
   - **难度**: ⭐ 低
   - **依赖**: 需要在领域服务中增加 `get_violation_by_id()` 方法

#### Statistics 路由 (`/api/v1/statistics`)

3. **`GET /api/v1/statistics/daily`** - 按天统计事件趋势
   - **当前实现**: 从日志文件读取
   - **重构方案**: 使用 `DetectionServiceDomain.get_daily_statistics()`
   - **难度**: ⭐⭐ 中
   - **依赖**: 需要在领域服务中增加按天统计方法

4. **`GET /api/v1/statistics/events`** - 事件列表查询
   - **当前实现**: 从日志文件读取
   - **重构方案**: 使用 `DetectionServiceDomain.get_detection_records()` 或新增 `get_events()`
   - **难度**: ⭐ 低
   - **依赖**: `IDetectionRepository.find_by_time_range()`

5. **`GET /api/v1/statistics/history`** - 近期事件历史
   - **当前实现**: 从日志文件读取
   - **重构方案**: 使用 `DetectionServiceDomain.get_detection_records()`
   - **难度**: ⭐ 低
   - **依赖**: `IDetectionRepository.find_by_time_range()`

#### Cameras 路由 (`/api/v1/cameras`)

6. **`GET /api/v1/cameras`** - 摄像头列表
   - **当前实现**: 查询数据库
   - **重构方案**: 使用 `CameraRepository` 或 `DetectionServiceDomain.get_cameras()`
   - **难度**: ⭐⭐ 中
   - **依赖**: `ICameraRepository` 接口和方法

7. **`GET /api/v1/cameras/{camera_id}/stats`** - 摄像头详细统计
   - **当前实现**: 从Redis缓存读取
   - **重构方案**: 使用 `DetectionServiceDomain.get_camera_analytics()`（已部分实现）
   - **难度**: ⭐⭐ 中
   - **依赖**: 需要整合Redis缓存的实时数据

### 🟡 中优先级 - 读操作端点（后续重构）

这些端点也是读操作，但涉及其他领域（非检测记录）：

8. **`GET /api/v1/alerts/history-db`** - 查询告警历史
   - **当前实现**: 查询告警表
   - **重构方案**: 需要创建 `AlertService` 和 `IAlertRepository`
   - **难度**: ⭐⭐⭐ 高
   - **依赖**: 需要创建新的领域模型

9. **`GET /api/v1/alerts/rules`** - 列出告警规则
   - **当前实现**: 查询告警规则表
   - **重构方案**: 需要创建 `AlertRuleService`
   - **难度**: ⭐⭐⭐ 高
   - **依赖**: 需要创建新的领域模型

10. **`GET /api/v1/system/info`** - 系统信息
    - **当前实现**: 收集系统信息
    - **重构方案**: 可以创建 `SystemService`
    - **难度**: ⭐⭐ 中
    - **依赖**: 系统信息收集逻辑

### 🟢 低优先级 - 写操作端点（谨慎重构）

这些端点涉及写操作（POST/PUT/DELETE），需要更谨慎：

11. **`PUT /api/v1/records/violations/{violation_id}/status`** - 更新违规状态
    - **当前实现**: 更新数据库
    - **重构方案**: 使用 `ViolationService.update_violation_status()`
    - **难度**: ⭐⭐⭐ 高
    - **依赖**: 需要确保事务性和一致性
    - **风险**: ⚠️ 写操作，需要事务支持

12. **`POST /api/v1/cameras`** - 创建摄像头
    - **当前实现**: 插入数据库
    - **重构方案**: 使用 `CameraService.create_camera()`
    - **难度**: ⭐⭐⭐ 高
    - **依赖**: 需要创建 `CameraService` 和完整验证逻辑
    - **风险**: ⚠️ 写操作，需要完整验证

13. **`PUT /api/v1/cameras/{camera_id}`** - 更新摄像头
    - **当前实现**: 更新数据库
    - **重构方案**: 使用 `CameraService.update_camera()`
    - **难度**: ⭐⭐⭐ 高
    - **依赖**: 需要完整验证逻辑
    - **风险**: ⚠️ 写操作，需要完整验证

14. **`DELETE /api/v1/cameras/{camera_id}`** - 删除摄像头
    - **当前实现**: 删除数据库记录
    - **重构方案**: 使用 `CameraService.delete_camera()`
    - **难度**: ⭐⭐⭐ 高
    - **依赖**: 需要处理级联删除
    - **风险**: ⚠️ 写操作，需要级联处理

### ⚫ 暂不重构 - 特殊功能端点

这些端点涉及特殊功能，建议保持现状：

- **`POST /api/v1/detect/comprehensive`** - 综合检测接口（核心检测流程）
- **`POST /api/v1/detect/image`** - 图像检测接口（核心检测流程）
- **`POST /api/v1/detect/hairnet`** - 发网检测接口（核心检测流程）
- **WebSocket 端点** - 实时推送（保持现状）
- **视频流端点** - 视频流处理（保持现状）
- **下载端点** - 文件下载（基础设施层）

## 重构计划

### 阶段一：高优先级读操作端点（1-2周）

**目标**: 重构所有高优先级的读操作端点

**端点列表**:
1. `GET /api/v1/records/detection-records/{camera_id}`
2. `GET /api/v1/records/violations/{violation_id}`
3. `GET /api/v1/statistics/daily`
4. `GET /api/v1/statistics/events`
5. `GET /api/v1/statistics/history`
6. `GET /api/v1/cameras`
7. `GET /api/v1/cameras/{camera_id}/stats`（完善）

**实施步骤**:
1. 补充领域服务方法（如 `get_violation_by_id()`, `get_daily_statistics()`）
2. 为每个端点创建灰度开关（使用 `should_use_domain()`）
3. 实现新旧实现的兼容响应结构
4. 添加单元测试
5. 集成测试验证
6. 性能对比测试
7. 逐步灰度发布（10% → 25% → 50% → 100%）

### 阶段二：中优先级读操作端点（2-3周）

**目标**: 重构中优先级的读操作端点

**端点列表**:
8. `GET /api/v1/alerts/history-db`
9. `GET /api/v1/alerts/rules`
10. `GET /api/v1/system/info`

**实施步骤**:
- 创建新的领域模型（Alert, AlertRule）
- 创建新的领域服务（AlertService, AlertRuleService）
- 创建新的仓储接口和实现
- 遵循阶段一的实施步骤

### 阶段三：低优先级写操作端点（3-4周，谨慎）

**目标**: 重构写操作端点

**端点列表**:
11. `PUT /api/v1/records/violations/{violation_id}/status`
12. `POST /api/v1/cameras`
13. `PUT /api/v1/cameras/{camera_id}`
14. `DELETE /api/v1/cameras/{camera_id}`

**实施步骤**:
- 确保事务支持
- 完整的业务规则验证
- 完整的单元测试和集成测试
- 更长的灰度观察期（1-2周）
- 准备详细的回滚方案

## 技术实施细节

### 领域服务扩展

需要在 `DetectionServiceDomain` 中增加以下方法：

```python
# 检测记录相关
async def get_detection_records_by_camera(
    self, camera_id: str, limit: int = 100, offset: int = 0
) -> Dict[str, Any]

async def get_detection_records_by_time_range(
    self, start_time: datetime, end_time: datetime,
    camera_id: Optional[str] = None, limit: int = 100
) -> Dict[str, Any]

# 违规相关
async def get_violation_by_id(self, violation_id: int) -> Optional[Dict[str, Any]]

# 统计相关
async def get_daily_statistics(
    self, days: int = 7, camera_id: Optional[str] = None
) -> List[Dict[str, Any]]

async def get_event_history(
    self, start_time: datetime, end_time: datetime,
    camera_id: Optional[str] = None, limit: int = 100
) -> Dict[str, Any]

# 摄像头相关
async def get_cameras(
    self, active_only: bool = False
) -> List[Dict[str, Any]]
```

### 仓储接口扩展

需要在 `IDetectionRepository` 中增加（如果还没有）：

- ✅ `find_by_camera_id()` - 已有
- ✅ `find_by_time_range()` - 已有
- ⚠️ `find_by_id()` - 已有（用于单个违规记录）
- ⚠️ `get_statistics()` - 已有（用于统计）

### 灰度开关扩展

所有新重构的端点都应使用相同的灰度机制：

```python
from src.api.utils.rollout import should_use_domain

@router.get("/endpoint")
async def endpoint_handler(
    force_domain: Optional[bool] = Query(None),
    ...
):
    if should_use_domain(force_domain) and get_detection_service_domain is not None:
        # 使用领域服务
        try:
            domain_service = get_detection_service_domain()
            result = await domain_service.get_xxx(...)
            return result
        except Exception as e:
            logger.warning(f"领域服务失败，回退: {e}")

    # 旧实现（回退）
    ...
```

## 风险评估

### 阶段一（高优先级读操作）
- **风险**: ⭐ 低
- **理由**: 都是读操作，不影响数据一致性
- **回滚**: 一键回退到旧实现

### 阶段二（中优先级读操作）
- **风险**: ⭐⭐ 中
- **理由**: 涉及新领域模型，需要更多测试
- **回滚**: 一键回退到旧实现

### 阶段三（低优先级写操作）
- **风险**: ⭐⭐⭐ 高
- **理由**: 写操作涉及数据一致性，需要事务支持
- **回滚**: 需要数据库事务回滚机制

## 成功标准

### 功能标准
- ✅ 所有新重构端点功能正常
- ✅ 响应结构与前端期望对齐
- ✅ 新旧实现响应结构一致

### 性能标准
- ✅ 性能与旧实现同量级（±15%）
- ✅ 单次请求响应时间可接受（<50ms）
- ✅ QPS满足需求

### 稳定性标准
- ✅ 回退机制正常
- ✅ 无异常堆栈或错误
- ✅ 前端页面正常访问

## 时间估算

- **阶段一**: 1-2周（7个端点）
- **阶段二**: 2-3周（3个端点，包含新领域模型）
- **阶段三**: 3-4周（4个端点，包含事务支持）
- **总计**: 6-9周

## 后续建议

1. **优先完成阶段一**: 快速获得收益，风险低
2. **阶段二需评估**: 根据业务需要决定是否创建新的领域模型
3. **阶段三需谨慎**: 写操作需要更长的测试和观察期
4. **保持灰度机制**: 所有重构都应支持灰度发布和回退

---

**创建日期**: 2025-10-31
**更新日期**: 2025-10-31
**状态**: 待执行
