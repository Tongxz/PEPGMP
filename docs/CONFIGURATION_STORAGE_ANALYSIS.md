# 配置文件与数据库存储分析

## 📊 概述

本文档详细分析了项目中所有配置文件的存储方式，以及哪些配置存储在文件中，哪些存储在数据库中。

---

## 1. 配置文件清单

### 1.1 主要配置文件

| 文件路径 | 文件类型 | 用途 | 存储状态 |
|---------|---------|------|---------|
| `config/cameras.yaml` | YAML | 相机配置 | 🟡 双重存储（数据库为主，YAML为回退） |
| `config/regions.json` | JSON | 区域配置 | 🟡 双重存储（数据库为主，JSON为回退） |
| `config/unified_params.yaml` | YAML | 统一检测参数 | 🟡 双重存储（YAML为主，数据库为可选） |
| `config/enhanced_detection_config.yaml` | YAML | 增强检测配置 | 🟢 仅文件存储 |

---

## 2. 详细分析

### 2.1 相机配置（`config/cameras.yaml`）

#### 📁 文件内容示例

```yaml
cameras:
- id: cam0
  name: 灰度测试更新
  source: '0'
  regions_file: config/regions.json
  profile: accurate
  device: auto
  imgsz: auto
  auto_tune: true
  active: true
  auto_start: false
- id: vid1
  name: 测试视频
  source: tests/fixtures/videos/20250724072708.mp4
  # ... 更多配置
```

#### 💾 数据库存储

**表名**: `cameras`

**表结构**:
```sql
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),              -- 摄像头位置（可选）
    status VARCHAR(20) DEFAULT 'inactive',  -- 配置状态
    camera_type VARCHAR(50) DEFAULT 'fixed', -- 摄像头类型
    resolution JSONB,                   -- [width, height]
    fps INTEGER,
    region_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,  -- source, regions_file, profile, device, imgsz, log_interval 等
    stream_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

**存储在数据库的字段**:
- ✅ `id` - 相机ID（UUID，自动生成）
- ✅ `name` - 相机名称
- ✅ `location` - 位置
- ✅ `status` - 配置状态（active/inactive/maintenance/error）
- ✅ `camera_type` - 类型（fixed/ptz/mobile/thermal）
- ✅ `resolution` - 分辨率（JSONB数组）
- ✅ `fps` - 帧率
- ✅ `region_id` - 区域ID
- ✅ `metadata` - 元数据（JSONB），包含：
  - `source` - 视频源（摄像头索引或文件路径）
  - `regions_file` - 区域配置文件路径
  - `profile` - 检测配置文件（accurate/fast）
  - `device` - 设备（auto/cpu/cuda）
  - `imgsz` - 图像尺寸（auto或具体值）
  - `log_interval` - 检测频率
  - `auto_tune` - 自动调优
  - `auto_start` - 自动启动
  - `env` - 环境变量（字典）

**存储在文件的字段**:
- ⚠️ 所有字段（作为回退）

#### 🔄 读取策略

**API层** (`src/api/routers/cameras.py`):
1. **优先从数据库读取**（通过 `CameraService`）
2. 如果数据库不可用，回退到YAML文件（`_read_yaml()`）

**检测进程** (`src/services/executors/local.py`):
1. **优先从数据库读取**（通过 `PostgreSQLCameraRepository`）
2. 如果数据库不可用，回退到YAML文件（`_read_yaml()`）

**写入策略**:
- ✅ **创建/更新**: 写入数据库（通过 `CameraService`）
- ⚠️ **YAML写入**: 已移除（不再写入YAML，数据库是单一数据源）
- 📝 **导出工具**: `scripts/export_cameras_to_yaml.py`（用于备份）

#### ⚠️ 当前问题

1. **双重存储不一致**:
   - YAML文件可能包含过时的配置
   - 数据库是权威数据源，但YAML仍在使用

2. **建议**:
   - ✅ 数据库是主要数据源（已完成）
   - ⚠️ YAML文件仅作为回退（建议逐步移除）

---

### 2.2 区域配置（`config/regions.json`）

#### 📁 文件内容示例

```json
{
  "regions": [
    {
      "region_id": "region_1756783110752",
      "region_type": "entrance",
      "polygon": [[449.0, 14.0], [444.0, 108.0], ...],
      "name": "入口线",
      "is_active": true,
      "rules": {
        "required_behaviors": [],
        "forbidden_behaviors": [],
        "max_occupancy": -1,
        "min_duration": 0,
        "max_duration": -1,
        "alert_on_violation": true
      },
      "stats": {
        "total_entries": 0,
        "current_occupancy": 0,
        "violations": 0,
        "last_entry_time": null,
        "last_exit_time": null
      }
    }
  ]
}
```

#### 💾 数据库存储

**表名**: `regions`

**表结构**:
```sql
CREATE TABLE regions (
    region_id VARCHAR(100) PRIMARY KEY,
    region_type VARCHAR(50),  -- entrance, sink, stand, dryer, work
    polygon JSONB NOT NULL,   -- 多边形坐标点 [[x1,y1], [x2,y2], ...]
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    rules JSONB DEFAULT '{}'::jsonb,  -- 规则配置
    camera_id VARCHAR(100),           -- 可选，关联的摄像头ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

**注意**: `stats` 统计信息**不存储在数据库中**，应该从 `detection_records` 和 `violation_events` 表实时计算。

**存储在数据库的字段**:
- ✅ `region_id` - 区域ID
- ✅ `region_type` - 区域类型
- ✅ `polygon` - 多边形坐标（JSONB）
- ✅ `name` - 区域名称
- ✅ `is_active` - 是否激活
- ✅ `rules` - 规则配置（JSONB）

**存储在文件的字段**:
- ⚠️ 所有字段（作为回退）
- ⚠️ `stats` - 统计信息（应该实时计算，不应存储在文件中）

#### 🔄 读取策略

**API层** (`src/api/routers/region_management.py`):
1. **优先从数据库读取**（通过 `RegionService`）
2. 如果数据库不可用，回退到JSON文件

**检测进程** (`src/core/region.py`):
1. **优先从数据库读取**
2. 如果数据库不可用，回退到JSON文件

**写入策略**:
- ✅ **创建/更新**: 写入数据库（通过 `RegionDomainService`）
- ✅ **导入功能**: 从JSON文件导入到数据库（`POST /api/v1/management/regions/import`）
- ✅ **导出功能**: 从数据库导出到JSON文件（`GET /api/v1/management/regions/export`）
- ⚠️ **自动导入**: 应用启动时，如果数据库为空且有 `config/regions.json` 文件，自动导入到数据库
- ❌ **JSON写入**: 不再直接写入JSON文件（仅用于导出备份）

#### ✅ 当前状态

1. **统计信息处理**:
   - ✅ `stats` 字段**不存储在数据库中**（符合设计）
   - ✅ 统计信息应该从 `violation_events` 和 `detection_records` 表实时计算
   - ⚠️ JSON文件中可能仍有 `stats` 字段（仅用于兼容，不应使用）

2. **配置迁移状态**:
   - ✅ 区域定义和规则 → 存储在数据库（已完成）
   - ✅ 自动导入机制 → 应用启动时自动导入（已完成）
   - ✅ 导入/导出API → 支持手动导入/导出（已完成）

---

### 2.3 统一检测参数（`config/unified_params.yaml`）

#### 📁 文件内容示例

```yaml
behavior_recognition:
  confidence_threshold: 0.65
  hairnet_min_duration: 1.0
  # ... 更多参数

hairnet_detection:
  confidence_threshold: 0.2
  model_path: models/multi_behavior/multi_behavior_20251118_070707.pt
  # ... 更多参数

human_detection:
  confidence_threshold: 0.5
  model_path: models/yolo/yolov8s.pt
  # ... 更多参数

pose_detection:
  confidence_threshold: 0.5
  model_path: models/yolo/yolov8n-pose.pt
  # ... 更多参数
```

#### 💾 数据库存储

**表名**: `detection_configs`

**表结构**:
```sql
CREATE TABLE detection_configs (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(50) NOT NULL,  -- human_detection, hairnet_detection, pose_detection, behavior_recognition
    config_key VARCHAR(100) NOT NULL,  -- confidence_threshold, model_path, etc.
    config_value JSONB,                 -- 配置值（可以是字符串、数字、对象等）
    camera_id VARCHAR(100),            -- 可选，按相机覆盖
    is_global BOOLEAN DEFAULT true,    -- 是否为全局配置
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(config_type, config_key, camera_id)
)
```

**存储在数据库的字段**:
- ✅ 所有检测参数（可选，通过前端API配置）
- ✅ 支持全局配置和按相机覆盖

**存储在文件的字段**:
- ✅ 所有检测参数（默认值，版本控制）

#### 🔄 读取策略

**API层** (`src/api/routers/detection_config.py`):
1. **优先从数据库读取**（通过 `DetectionConfigService`）
2. 如果数据库不可用，回退到YAML文件（`get_unified_params()`）

**检测进程**:
1. **优先从数据库读取**（通过 `load_unified_params_from_db()`）
2. 如果数据库不可用，回退到YAML文件

**写入策略**:
- ✅ **前端API修改**: 写入数据库（通过 `DetectionConfigService`）
- ✅ **YAML文件**: 作为默认值，通过Git版本控制

#### ✅ 当前状态

- ✅ 数据库和YAML双重存储，但职责清晰：
  - **YAML**: 默认值，版本控制
  - **数据库**: 用户自定义配置，按相机覆盖

---

### 2.4 增强检测配置（`config/enhanced_detection_config.yaml`）

#### 📁 文件内容示例

```yaml
system:
  version: "2.0.0"
  debug_mode: false
  log_level: "INFO"

enhanced_hand_detection:
  mediapipe:
    static_image_mode: false
    max_num_hands: 2
    min_detection_confidence: 0.5
  quality_assessment:
    enabled: true
    overall_threshold: 0.3
    # ... 更多参数
```

#### 💾 数据库存储

**存储状态**: ❌ **仅文件存储**

**原因**:
- 算法增强配置，不常修改
- 适合版本控制（Git）
- 不需要用户动态配置
- 不需要按相机覆盖

#### 🔄 读取策略

**检测进程**:
- 直接从YAML文件读取（`config/enhanced_detection_config.yaml`）

**写入策略**:
- ✅ 仅通过Git版本控制修改
- ❌ 不通过API修改

#### ✅ 当前状态

- ✅ 仅文件存储，符合设计

---

## 3. 配置存储策略总结

### 3.1 存储位置分类

| 配置类型 | 主要存储 | 回退存储 | 是否可动态更新 |
|---------|---------|---------|--------------|
| **相机配置** | 数据库 | YAML文件 | ✅ 是（通过API） |
| **区域配置** | 数据库 | JSON文件 | ✅ 是（通过API） |
| **检测参数** | YAML文件（默认）<br>数据库（用户自定义） | YAML文件 | ✅ 是（通过API） |
| **增强检测配置** | YAML文件 | - | ❌ 否（仅Git） |
| **运行时配置** | Redis | - | ✅ 是（每100帧更新） |
| **环境变量** | `.env`文件 | 系统环境变量 | ❌ 否（需重启） |

### 3.2 配置读取优先级

#### 相机配置读取优先级

1. **数据库**（`cameras`表）← **主要数据源**
2. YAML文件（`config/cameras.yaml`）← **回退**

#### 区域配置读取优先级

1. **数据库**（`regions`表）← **主要数据源**
2. JSON文件（`config/regions.json`）← **回退**

#### 检测参数读取优先级

1. **数据库**（`detection_configs`表，按相机覆盖）← **用户自定义**
2. **数据库**（`detection_configs`表，全局配置）← **用户自定义**
3. YAML文件（`config/unified_params.yaml`）← **默认值**

#### 运行时配置读取优先级

1. **Redis**（`video_stream:config:{camera_id}`）← **运行时动态更新**
2. 命令行参数（启动时）
3. 环境变量
4. 代码默认值

---

## 4. 数据库表结构汇总

### 4.1 配置相关表

| 表名 | 用途 | 主要字段 |
|------|------|---------|
| `cameras` | 相机配置 | `id`, `name`, `location`, `status`, `camera_type`, `resolution`, `fps`, `metadata` |
| `regions` | 区域配置 | `region_id`, `region_type`, `polygon`, `name`, `is_active`, `rules` |
| `detection_configs` | 检测参数配置 | `config_type`, `config_key`, `config_value`, `camera_id`, `is_global` |

### 4.2 数据记录表

| 表名 | 用途 | 主要字段 |
|------|------|---------|
| `detection_records` | 检测记录 | `id`, `camera_id`, `frame_id`, `timestamp`, `objects`, `violations` |
| `violation_events` | 违规记录 | `id`, `camera_id`, `violation_type`, `timestamp`, `region_id` |

### 4.3 MLOps相关表

| 表名 | 用途 | 主要字段 |
|------|------|---------|
| `datasets` | 数据集 | `id`, `name`, `version`, `status`, `file_path` |
| `deployments` | 模型部署 | `id`, `name`, `model_version`, `status`, `deployment_config` |
| `workflows` | 工作流 | `id`, `name`, `status`, `workflow_config` |
| `workflow_runs` | 工作流运行 | `id`, `workflow_id`, `status`, `run_config`, `step_outputs` |

---

## 5. 配置迁移状态

### 5.1 已完成迁移

- ✅ **相机配置** → 数据库（`cameras`表）
  - 状态: 已完成
  - YAML文件: 仅作为回退
  - 写入: 仅写入数据库

- ✅ **区域配置** → 数据库（`regions`表）
  - 状态: 已完成
  - JSON文件: 仅作为回退

- ✅ **检测参数配置** → 数据库（`detection_configs`表）
  - 状态: 已完成（可选）
  - YAML文件: 作为默认值

### 5.2 保留在文件

- ✅ **增强检测配置** → 仅文件存储
  - 原因: 算法配置，不需要动态修改

- ✅ **环境变量** → `.env`文件
  - 原因: 系统基础设施配置

### 5.3 运行时配置

- ✅ **运行时配置** → Redis
  - 原因: 需要高频更新，不适合数据库

---

## 6. 配置读取流程详解

### 6.1 相机配置读取流程

#### API层读取流程

```
客户端请求 → FastAPI路由 → CameraService → PostgreSQLCameraRepository → 数据库
                                                      ↓ (失败)
                                                  YAML文件（回退）
```

**代码位置**:
- `src/api/routers/cameras.py` - API路由层
- `src/domain/services/camera_service.py` - 领域服务层
- `src/infrastructure/repositories/postgresql_camera_repository.py` - 仓储实现层

#### 检测进程读取流程

```
检测进程启动 → LocalProcessExecutor.start() → PostgreSQLCameraRepository → 数据库
                                                      ↓ (失败)
                                                  YAML文件（回退）
```

**代码位置**:
- `src/services/executors/local.py` - 进程执行器
- `LocalProcessExecutor._init_camera_repository()` - 初始化数据库连接
- `LocalProcessExecutor.list_cameras()` - 读取相机列表

**关键代码**:
```python
# src/services/executors/local.py
def list_cameras(self) -> List[Dict[str, Any]]:
    """优先从数据库读取，失败时回退到YAML"""
    if self._init_camera_repository() and self._camera_repository is not None:
        # 从数据库读取
        cameras = await self._camera_repository.find_all()
        return cameras
    else:
        # 回退到YAML文件
        return _read_yaml(self.cameras_path)
```

### 6.2 区域配置读取流程

#### API层读取流程

```
客户端请求 → FastAPI路由 → RegionDomainService → PostgreSQLRegionRepository → 数据库
                                                      ↓ (失败)
                                                  HTTPException 500（不回退到JSON）
```

**代码位置**:
- `src/api/routers/region_management.py` - API路由层
- `src/domain/services/region_service.py` - 领域服务层
- `src/infrastructure/repositories/postgresql_region_repository.py` - 仓储实现层

**关键特点**:
- ✅ **无回退逻辑**: 如果数据库不可用，直接返回HTTP 500错误
- ✅ **统一数据源**: 数据库是唯一数据源

#### 检测进程读取流程

```
检测进程启动 → RegionManager.load_regions_config() → JSON文件（仅用于初始化）
                                                      ↓
                                                 数据库（通过API）
```

**代码位置**:
- `src/core/region.py` - 区域管理器
- `RegionManager.load_regions_config()` - 从文件加载（仅用于初始化）

**关键特点**:
- ⚠️ **检测进程**: 仍从JSON文件读取（用于初始化）
- ✅ **API层**: 统一从数据库读取

### 6.3 检测参数读取流程

#### API层读取流程

```
客户端请求 → FastAPI路由 → DetectionConfigService → PostgreSQLDetectionConfigRepository → 数据库
                                                      ↓ (失败)
                                                  UnifiedParams.load_from_yaml() → YAML文件
```

**代码位置**:
- `src/api/routers/detection_config.py` - API路由层
- `src/domain/services/detection_config_service.py` - 领域服务层
- `src/config/unified_params_loader.py` - 配置加载器

**关键特点**:
- ✅ **双重存储**: 数据库（用户自定义）+ YAML（默认值）
- ✅ **优先级**: 数据库配置 > YAML默认值

### 6.4 应用启动时的自动导入

#### 区域配置自动导入

```
应用启动 → lifespan() → RegionDomainService → 检查数据库是否为空
                                              ↓ (为空)
                                          检查 config/regions.json 是否存在
                                              ↓ (存在)
                                          自动导入到数据库
```

**代码位置**:
- `src/api/app.py` - 应用生命周期管理
- `lifespan()` 函数中的区域服务初始化

**关键代码**:
```python
# src/api/app.py
if os.path.exists(regions_file):
    # 检查数据库是否为空
    existing_regions = await region_domain_service.get_all_regions()
    if not existing_regions:
        # 自动导入
        result = await region_domain_service.import_from_file(regions_file)
        logger.info(f"自动导入区域配置: {result}")
```

---

## 7. 建议和最佳实践

### 6.1 配置存储原则

1. **用户可配置的配置** → 数据库
   - 相机配置
   - 区域配置
   - 检测参数（用户自定义）

2. **算法默认配置** → YAML文件
   - 检测参数默认值
   - 增强检测配置
   - 适合版本控制

3. **运行时动态配置** → Redis
   - `log_interval`
   - `stream_interval`
   - 需要高频更新

4. **系统基础设施配置** → 环境变量
   - 数据库连接
   - Redis连接
   - 日志配置

### 6.2 配置读取最佳实践

1. **API层**:
   - 优先从数据库读取
   - 失败时回退到文件（仅用于兼容）

2. **检测进程**:
   - 优先从数据库读取
   - 失败时回退到文件（仅用于兼容）

3. **配置更新**:
   - 通过API更新数据库
   - 不直接修改文件（除非是算法默认值）

### 6.3 配置一致性保证

1. **单一数据源**:
   - 数据库是权威数据源
   - 文件仅作为回退

2. **数据同步**:
   - 不再写入YAML/JSON文件
   - 使用导出工具进行备份

3. **版本控制**:
   - YAML默认值通过Git版本控制
   - 数据库配置通过迁移脚本管理

---

## 7. 相关文档

- `docs/CONFIGURATION_MIGRATION_PLAN.md` - 配置迁移计划
- `docs/CONFIGURATION_ANALYSIS.md` - 配置分析文档
- `docs/camera_config_storage_strategy.md` - 相机配置存储策略
- `docs/config_files_audit.md` - 配置文件审计报告
- `docs/CAMERA_STATUS_ANALYSIS.md` - 相机状态字段分析

---

**更新日期**: 2025-11-18  
**状态**: 当前配置存储策略分析

