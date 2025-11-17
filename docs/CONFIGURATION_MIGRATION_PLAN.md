# 配置存储方式调整方案

## 1. 当前配置存储问题分析

### 1.1 存在的问题

#### 问题1：相机配置双重存储
- **现状**：相机配置同时存储在数据库和 `config/cameras.yaml`
- **影响**：
  - `LocalProcessExecutor` 从 YAML 读取相机配置启动检测进程
  - API 从数据库读取相机配置
  - 数据不一致风险

#### 问题2：检测参数存储位置不清
- **现状**：检测参数存储在 `config/unified_params.yaml`，可通过前端 API 修改
- **问题**：前端修改后只更新 YAML，检测进程需要重启才能生效
- **影响**：配置修改不及时生效

#### 问题3：运行时配置优先级混乱
- **现状**：`log_interval` 从命令行参数、Redis、YAML 等多个来源读取
- **问题**：优先级不清晰，Redis 可能覆盖命令行参数
- **影响**：用户设置的配置可能不生效

---

## 2. 目标配置存储方案

### 2.1 配置存储原则

1. **数据库（PostgreSQL）**：
   - 相机配置（单一数据源）
   - 检测参数默认值（全局/按相机）
   - 区域配置
   - 违规规则配置

2. **文件（YAML/JSON）**：
   - 基础设施配置（`unified_params.yaml` 作为默认值）
   - 模型文件路径（静态路径）
   - 区域配置文件（`regions.json`）- 作为导入源

3. **Redis**：
   - 运行时动态配置（`log_interval`, `stream_interval`）
   - 仅在运行时使用，不覆盖启动时配置

4. **环境变量**：
   - 数据库连接（`DATABASE_URL`）
   - Redis连接（`REDIS_URL`）
   - 系统级配置（`LOG_LEVEL`, `ENVIRONMENT`）

---

## 3. 配置调整影响分析

### 3.1 需要修改的代码模块

#### 3.1.1 相机配置读取（高优先级）

**当前问题**：
- `LocalProcessExecutor.list_cameras()` 从 `config/cameras.yaml` 读取
- 需要改为从数据库读取

**影响范围**：
- `src/services/executors/local.py` - `list_cameras()` 方法
- `src/services/executors/local.py` - `_build_command()` 方法（读取相机配置）

**修改方案**：
```python
# 当前（从YAML读取）
def list_cameras(self) -> List[Dict[str, Any]]:
    data = _read_yaml(self.cameras_path)
    return list(data.get("cameras", []))

# 修改后（从数据库读取）
async def list_cameras(self) -> List[Dict[str, Any]]:
    # 需要注入 CameraRepository
    cameras = await self.camera_repository.find_all()
    return [c.to_dict() for c in cameras]
```

**影响**：
- `LocalProcessExecutor` 需要支持异步（或使用同步数据库访问）
- 需要注入 `CameraRepository` 依赖
- 需要处理数据库连接失败的情况

#### 3.1.2 检测参数存储（中优先级）

**当前问题**：
- 检测参数存储在 `unified_params.yaml`
- 前端 API 修改后只更新 YAML，检测进程需要重启

**影响范围**：
- `src/api/routers/detection_config.py` - 当前只读写 YAML
- `src/config/unified_params.py` - 从 YAML 加载
- 所有使用 `get_unified_params()` 的地方

**修改方案**：
1. 创建 `detection_configs` 表存储检测参数
2. 修改 `get_unified_params()` 优先从数据库读取
3. 前端 API 修改后同时更新数据库和 Redis（通知检测进程）

**数据库表设计**：
```sql
CREATE TABLE detection_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NULL,  -- NULL表示全局默认值
    config_type VARCHAR(50) NOT NULL,  -- human_detection, hairnet_detection, etc.
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, config_type, config_key)
);
```

**影响**：
- 需要创建数据库表
- 需要迁移现有 YAML 配置到数据库
- `get_unified_params()` 需要支持从数据库读取
- 需要保持向后兼容（YAML 作为默认值）

#### 3.1.3 运行时配置读取（中优先级）

**当前问题**：
- Redis 配置可能覆盖命令行参数
- 优先级不清晰

**影响范围**：
- `src/application/detection_loop_service.py` - `update_from_redis()` 方法
- `src/application/detection_loop_service.py` - `run()` 方法中的配置读取逻辑

**修改方案**：
- 启动时：命令行参数 > 数据库配置 > YAML 默认值
- 运行时：Redis 配置（用于动态更新，不覆盖启动配置）

**影响**：
- 已修复（在前面的修复中已调整优先级）

---

## 4. 详细迁移计划

### 阶段1：相机配置统一到数据库（高优先级）

#### 步骤1.1：修改 LocalProcessExecutor
- [ ] 将 `list_cameras()` 改为从数据库读取
- [ ] 注入 `CameraRepository` 依赖
- [ ] 处理数据库连接失败的情况（回退到 YAML）

#### 步骤1.2：移除 YAML 依赖
- [ ] 移除 `LocalProcessExecutor` 对 `cameras.yaml` 的依赖
- [ ] 保留 `cameras.yaml` 作为导出/备份用途
- [ ] 更新文档说明 YAML 不再用于运行时配置

**预计影响**：
- ✅ 数据一致性：相机配置单一数据源
- ✅ 实时性：前端修改立即生效（无需重启）
- ⚠️ 需要处理数据库连接失败的情况

### 阶段2：检测参数迁移到数据库（中优先级）

#### 步骤2.1：创建数据库表
```sql
CREATE TABLE detection_configs (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100) NULL,
    config_type VARCHAR(50) NOT NULL,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(camera_id, config_type, config_key)
);

CREATE INDEX idx_detection_configs_camera ON detection_configs(camera_id);
CREATE INDEX idx_detection_configs_type ON detection_configs(config_type);
```

#### 步骤2.2：创建仓储和服务
- [ ] 创建 `IDetectionConfigRepository` 接口
- [ ] 实现 `PostgreSQLDetectionConfigRepository`
- [ ] 创建 `DetectionConfigService` 领域服务

#### 步骤2.3：迁移现有配置
- [ ] 编写迁移脚本：从 `unified_params.yaml` 导入到数据库
- [ ] 设置全局默认值（`camera_id = NULL`）

#### 步骤2.4：修改配置加载逻辑
- [ ] 修改 `get_unified_params()` 优先从数据库读取
- [ ] YAML 作为默认值回退
- [ ] 支持按相机覆盖配置

#### 步骤2.5：更新前端 API
- [ ] 修改检测配置 API 同时更新数据库和 YAML（兼容）
- [ ] 添加配置生效通知机制（Redis Pub/Sub）

**预计影响**：
- ✅ 支持按相机配置不同的检测参数
- ✅ 前端修改立即生效（通过 Redis 通知）
- ⚠️ 需要数据迁移
- ⚠️ 需要保持向后兼容

### 阶段3：运行时配置优化（低优先级）

#### 步骤3.1：明确配置优先级
- [x] 启动时：命令行参数 > 数据库配置 > YAML 默认值
- [x] 运行时：Redis 配置（用于动态更新）

#### 步骤3.2：优化 Redis 配置同步
- [ ] 相机配置修改时同步到 Redis
- [ ] 检测进程启动时从数据库读取配置并同步到 Redis

---

## 5. 影响评估

### 5.1 代码修改范围

| 模块 | 文件数 | 修改复杂度 | 影响范围 |
|------|--------|-----------|---------|
| 相机配置读取 | 1 | 中 | `LocalProcessExecutor` |
| 检测参数存储 | 3-5 | 高 | `config/`, `api/routers/`, `domain/services/` |
| 运行时配置 | 1 | 低 | `detection_loop_service.py` (已修复) |

### 5.2 数据库变更

- **新增表**：
  - `detection_configs` - 检测参数配置
  - `violation_rules` - 违规规则配置（可选）

- **现有表**：
  - `cameras` - 已存在，无需修改

### 5.3 向后兼容性

#### 需要保持兼容的部分：
1. **YAML 配置文件**：
   - `unified_params.yaml` 作为默认值回退
   - `cameras.yaml` 作为导出/备份用途

2. **环境变量**：
   - 保持不变

3. **命令行参数**：
   - 保持最高优先级

#### 不兼容的部分：
1. **LocalProcessExecutor**：
   - `list_cameras()` 从同步改为异步（或使用同步数据库访问）
   - 需要注入数据库依赖

---

## 6. 风险评估

### 6.1 高风险项

1. **LocalProcessExecutor 改为从数据库读取**
   - 风险：如果数据库连接失败，无法启动检测进程
   - 缓解：保留 YAML 作为回退

2. **检测参数迁移到数据库**
   - 风险：如果数据库中没有配置，检测进程无法启动
   - 缓解：YAML 作为默认值回退

### 6.2 中风险项

1. **配置读取性能**
   - 风险：从数据库读取可能比文件慢
   - 缓解：使用连接池，添加缓存

2. **配置一致性**
   - 风险：多个来源可能导致配置不一致
   - 缓解：明确优先级，单一数据源

### 6.3 低风险项

1. **运行时配置更新**
   - 风险：Redis 配置更新可能不及时
   - 缓解：使用 Pub/Sub 机制，定期同步

---

## 7. 实施建议

### 7.1 分阶段实施（推荐）

**阶段1（1-2天）**：相机配置统一到数据库
- 影响范围小
- 风险可控
- 立即收益

**阶段2（3-5天）**：检测参数迁移到数据库
- 影响范围大
- 需要充分测试
- 长期收益

**阶段3（1天）**：运行时配置优化
- 已完成大部分工作
- 仅需完善

### 7.2 实施步骤

1. **准备阶段**：
   - [ ] 创建数据库表结构
   - [ ] 编写迁移脚本
   - [ ] 编写单元测试

2. **实施阶段**：
   - [ ] 按阶段逐步修改代码
   - [ ] 运行测试确保兼容性
   - [ ] 迁移现有配置数据

3. **验证阶段**：
   - [ ] 功能测试
   - [ ] 性能测试
   - [ ] 向后兼容性测试

4. **上线阶段**：
   - [ ] 灰度发布
   - [ ] 监控运行状态
   - [ ] 逐步全量

---

## 8. 预期收益

### 8.1 短期收益
- ✅ 配置数据一致性
- ✅ 前端修改立即生效
- ✅ 配置管理集中化

### 8.2 长期收益
- ✅ 支持按相机配置不同的检测参数
- ✅ 配置变更历史追踪（数据库时间戳）
- ✅ 更好的可扩展性（添加新配置类型）

---

## 9. 后续优化方向

1. **配置版本管理**：
   - 记录配置变更历史
   - 支持配置回滚

2. **配置验证**：
   - 配置值有效性检查
   - 配置依赖关系检查

3. **配置模板**：
   - 预设配置模板（如"高精度模式"、"性能模式"）
   - 快速应用模板到多个相机

