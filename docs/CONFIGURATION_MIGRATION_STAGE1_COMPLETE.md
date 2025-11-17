# 配置迁移阶段1完成报告

## 📊 执行摘要

**状态**: ✅ **完成**

阶段1（相机配置统一到数据库）已完成。现在相机配置以数据库（PostgreSQL）为单一数据源，API层从数据库读取配置并传递给executor，避免了executor在运行时依赖YAML文件。

---

## ✅ 完成的工作

### 1. 修改LocalProcessExecutor支持传入相机配置

**文件**: `src/services/executors/local.py`

- ✅ `start()` 方法新增 `camera_config` 参数
- ✅ 优先使用传入的配置，避免调用 `list_cameras()`
- ✅ 保留 `list_cameras()` 作为回退机制（用于命令行启动）

**关键变更**:
```python
def start(self, camera_id: str, camera_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # 如果提供了相机配置，直接使用；否则从列表查找
    if camera_config is not None:
        cam = camera_config
    else:
        # 回退到list_cameras()
        ...
```

### 2. 修改DetectionScheduler传递相机配置

**文件**: `src/services/scheduler.py`

- ✅ `start_detection()` 方法新增 `camera_config` 参数
- ✅ 将配置传递给executor

**关键变更**:
```python
def start_detection(self, camera_id: str, camera_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return self.executor.start(camera_id, camera_config)
```

### 3. 修改CameraControlService从数据库获取配置

**文件**: `src/domain/services/camera_control_service.py`

- ✅ `start_camera()` 方法改为 `async`
- ✅ 从数据库获取相机配置
- ✅ 转换为executor期望的格式
- ✅ 传递给scheduler

**关键变更**:
```python
async def start_camera(self, camera_id: str) -> Dict[str, Any]:
    # 3. 从数据库获取摄像头配置
    camera = await self.camera_service.camera_repository.find_by_id(camera_id)
    if not camera:
        raise ValueError(f"摄像头 {camera_id} 不存在")
    
    # 转换为字典格式（兼容executor期望的格式）
    camera_config = camera.to_dict()
    # ... 提取metadata字段 ...
    
    # 4. 启动进程（传递配置给执行器）
    res = self.scheduler.start_detection(camera_id, camera_config)
    ...
```

### 4. 修改API路由支持传递配置

**文件**: `src/api/routers/cameras.py`

- ✅ `start_camera()` 路由从数据库获取配置
- ✅ 传递给scheduler（如果使用领域服务，则自动处理）
- ✅ 保留回退机制（最终回退到executor自动查找）

**关键变更**:
```python
@router.post("/cameras/{camera_id}/start")
async def start_camera(...):
    # 优先使用领域服务（自动从数据库获取配置）
    if should_use_domain(force_domain) and get_camera_control_service is not None:
        control_service = await get_camera_control_service()
        if control_service:
            result = await control_service.start_camera(camera_id)
            return result
    
    # 回退：从数据库获取配置后传递给executor
    if get_camera_service is not None:
        camera_service = await get_camera_service()
        if camera_service:
            camera = await camera_service.camera_repository.find_by_id(camera_id)
            if camera:
                camera_config = camera.to_dict()
                # ... 转换格式 ...
                res = scheduler.start_detection(camera_id, camera_config)
                return res
    
    # 最终回退：让executor自己查找配置
    res = scheduler.start_detection(camera_id)
    ...
```

### 5. 保留YAML回退机制

**文件**: `src/services/executors/local.py`

- ✅ `list_cameras()` 方法保留YAML回退
- ✅ 添加警告日志，提醒YAML不再是主要配置源
- ✅ 仅在数据库不可用或命令行启动时使用

**关键变更**:
```python
def list_cameras(self) -> List[Dict[str, Any]] | Dict[str, Any]:
    """列出所有相机配置（优先从数据库读取，失败时回退到YAML）
    
    注意：
    - 在FastAPI环境中，应该通过API层传递相机配置给executor，而不是调用此方法
    - 此方法主要用于命令行启动检测进程时的回退机制
    - YAML文件仅作为最后的回退选项，不应作为主要配置源
    """
    # 尝试从数据库读取（仅在同步上下文中）
    ...
    # YAML回退（仅用于命令行启动或数据库不可用时）
    logger.warning(
        f"使用YAML回退模式读取相机配置: {self.cameras_path}。"
        "注意：YAML文件已不再是主要配置源，建议使用数据库配置。"
    )
    ...
```

---

## 🎯 架构改进成果

### 之前（双重存储）

```
┌──────────────┐
│  API Layer   │
└──────┬───────┘
       │
       ├─→ Database  ← 数据源1
       └─→ YAML     ← 数据源2（executor依赖）
```

**问题**:
- ❌ executor运行时依赖YAML文件
- ❌ 数据不一致风险
- ❌ 前端修改配置后，executor可能读取到旧配置

### 现在（单一数据源）

```
┌──────────────┐
│  API Layer   │
└──────┬───────┘
       │
       ├─→ Database  ← 单一数据源 ✅
       │
       └─→ Executor（接收配置，不依赖YAML）✅
```

**优势**:
- ✅ 数据库作为单一数据源
- ✅ API层从数据库获取配置并传递给executor
- ✅ executor不依赖YAML文件（保留回退机制）
- ✅ 前端修改配置后，executor立即使用新配置
- ✅ 数据一致性保证

---

## 📊 配置读取流程

### FastAPI环境（推荐）

```
1. 前端调用 API: POST /cameras/{camera_id}/start
2. API层: 从数据库获取相机配置
3. API层: 转换为executor期望的格式
4. API层: 调用 scheduler.start_detection(camera_id, camera_config)
5. Scheduler: 调用 executor.start(camera_id, camera_config)
6. Executor: 直接使用传入的配置，启动检测进程
```

**优势**:
- ✅ 不需要YAML文件
- ✅ 配置实时从数据库读取
- ✅ 避免了事件循环冲突

### 命令行环境（回退）

```
1. 命令行: 直接调用 executor.start(camera_id)
2. Executor: 调用 list_cameras()
3. list_cameras(): 尝试从数据库读取（同步上下文）
4. 如果失败: 回退到YAML文件
```

**优势**:
- ✅ 支持命令行启动
- ✅ 保留了回退机制
- ✅ 兼容旧的工作流程

---

## 🔧 配置存储状态

### ✅ 已存入数据库

- **相机配置**（`cameras` 表）
  - 主要配置：`id`, `name`, `location`, `status`, `camera_type`
  - 元数据（`metadata` JSONB）：
    - `source`: 视频源
    - `log_interval`: 检测频率
    - `regions_file`: 区域文件
    - `profile`: 检测配置
    - `device`: 计算设备
    - `imgsz`: 图像大小
    - `auto_start`: 自动启动
    - `env`: 环境变量

### ✅ 保留在文件（仅用于回退）

- **`config/cameras.yaml`**
  - 仅用于命令行启动或数据库不可用时
  - 不应作为主要配置源
  - 可以用于导出/备份

---

## 🚀 后续工作

### 阶段2：检测参数迁移到数据库（待实施）

- [ ] 创建 `detection_configs` 数据库表
- [ ] 创建 `IDetectionConfigRepository` 接口和PostgreSQL实现
- [ ] 创建 `DetectionConfigService` 领域服务
- [ ] 编写从 `unified_params.yaml` 迁移到数据库的脚本
- [ ] 修改 `get_unified_params()` 优先从数据库读取
- [ ] 更新检测配置API同时更新数据库和YAML
- [ ] 添加配置变更通知机制（Redis Pub/Sub）

### 阶段3：运行时配置优化（待实施）

- [ ] 优化Redis配置同步逻辑（相机配置修改时同步到Redis）
- [ ] 添加配置变更通知机制

---

## 📝 注意事项

1. **YAML文件不再用于运行时配置**：
   - `config/cameras.yaml` 仅用于回退或导出/备份
   - 不应手动编辑YAML文件来修改配置
   - 应通过前端API或数据库直接修改

2. **API层必须传递配置**：
   - 在FastAPI环境中，API层应该从数据库获取配置并传递给executor
   - 不要依赖executor自动查找配置（可能在FastAPI环境中失败）

3. **命令行启动支持**：
   - 命令行启动时，executor会自动尝试从数据库读取
   - 如果数据库不可用，会回退到YAML文件
   - 这是为了兼容旧的工作流程

---

## 📚 相关文档

- `docs/CONFIGURATION_ANALYSIS.md` - 配置分析文档
- `docs/CONFIGURATION_MIGRATION_PLAN.md` - 配置迁移计划
- `docs/camera_migration_complete.md` - 相机配置迁移完成报告

---

**更新日期**: 2025-11-13
**状态**: 阶段1完成，待验证

