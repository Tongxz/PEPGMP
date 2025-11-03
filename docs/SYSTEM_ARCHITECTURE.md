# 系统架构文档

## 概述

本文档描述了人体行为检测系统的完整架构设计，基于领域驱动设计（DDD）原则和现代软件工程最佳实践。

**更新日期**: 2025-11-03
**架构状态**: ✅ **重构完成**

---

## 🏗️ 架构概览

### 架构模式

本项目采用**分层架构（Layered Architecture）**结合**领域驱动设计（DDD）**，遵循以下原则：

- ✅ **SOLID原则**：单一职责、开闭原则、里氏替换、接口隔离、依赖倒置
- ✅ **领域驱动设计（DDD）**：实体、值对象、领域服务、仓储模式
- ✅ **设计模式**：策略模式、工厂模式、仓储模式、依赖注入

### 架构层次

```
┌─────────────────────────────────────────────────────────┐
│                    API层 (Interfaces)                    │
│  • REST API (FastAPI)                                    │
│  • WebSocket                                            │
│  • 路由处理、请求验证、响应格式化                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 应用层 (Application)                     │
│  • 用例编排                                              │
│  • DTO转换                                              │
│  • 事务协调                                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  领域层 (Domain)                         │
│  • 实体 (Entities)                                      │
│    - Alert, AlertRule, Camera, DetectionRecord, ...     │
│  • 值对象 (Value Objects)                                │
│    - BoundingBox, Confidence, Timestamp                 │
│  • 领域服务 (Domain Services)                            │
│    - AlertService, CameraService, DetectionService, ...  │
│  • 仓储接口 (Repository Interfaces)                      │
│    - IAlertRepository, ICameraRepository, ...            │
│  • 领域事件 (Domain Events)                              │
│    - DetectionCreatedEvent, ViolationDetectedEvent       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              基础设施层 (Infrastructure)                  │
│  • 仓储实现 (Repository Implementations)                 │
│    - PostgreSQLAlertRepository                          │
│    - PostgreSQLCameraRepository                         │
│    - PostgreSQLDetectionRepository                      │
│    - PostgreSQLRegionRepository                        │
│    - RedisDetectionRepository                           │
│    - HybridDetectionRepository                          │
│  • 外部服务集成                                          │
│    - AI模型 (YOLOv8, MediaPipe)                         │
│    - 数据库连接 (PostgreSQL, Redis)                      │
│  • 监控和日志                                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构

### 领域层 (`src/domain/`)

```
src/domain/
├── entities/              # 实体
│   ├── alert.py          # 告警实体
│   ├── alert_rule.py     # 告警规则实体
│   ├── camera.py         # 摄像头实体
│   ├── detection_record.py  # 检测记录实体
│   └── detected_object.py   # 检测对象实体
├── value_objects/        # 值对象
│   ├── bounding_box.py   # 边界框值对象
│   ├── confidence.py     # 置信度值对象
│   └── timestamp.py      # 时间戳值对象
├── services/             # 领域服务
│   ├── alert_service.py  # 告警领域服务
│   ├── alert_rule_service.py  # 告警规则领域服务
│   ├── camera_service.py  # 摄像头领域服务
│   ├── camera_control_service.py  # 摄像头控制服务
│   ├── detection_service.py  # 检测领域服务
│   ├── region_service.py    # 区域领域服务
│   ├── system_service.py    # 系统信息服务
│   └── violation_service.py  # 违规检测服务
├── repositories/         # 仓储接口
│   ├── alert_repository.py  # 告警仓储接口
│   ├── alert_rule_repository.py  # 告警规则仓储接口
│   ├── camera_repository.py  # 摄像头仓储接口
│   └── detection_repository.py  # 检测记录仓储接口
└── events/              # 领域事件
    └── detection_events.py  # 检测相关事件
```

### 基础设施层 (`src/infrastructure/`)

```
src/infrastructure/
└── repositories/        # 仓储实现
    ├── postgresql_alert_repository.py  # PostgreSQL告警仓储
    ├── postgresql_alert_rule_repository.py  # PostgreSQL告警规则仓储
    ├── postgresql_camera_repository.py  # PostgreSQL摄像头仓储
    ├── postgresql_detection_repository.py  # PostgreSQL检测记录仓储
    ├── postgresql_region_repository.py  # PostgreSQL区域仓储
    ├── redis_detection_repository.py  # Redis检测记录仓储
    ├── hybrid_detection_repository.py  # 混合仓储
    └── repository_factory.py  # 仓储工厂
```

### API层 (`src/api/`)

```
src/api/
├── routers/            # API路由
│   ├── alerts.py       # 告警相关端点
│   ├── cameras.py     # 摄像头相关端点
│   ├── records.py     # 检测记录相关端点
│   ├── statistics.py  # 统计相关端点
│   ├── region_management.py  # 区域管理端点
│   └── ...
└── middleware/         # 中间件
    ├── error_middleware.py  # 错误处理中间件
    ├── metrics_middleware.py  # 指标收集中间件
    └── security_middleware.py  # 安全中间件
```

---

## 🔄 数据流

### 读操作流程

```
客户端请求
    ↓
API路由 (routers/*.py)
    ↓
领域服务 (domain/services/*.py)
    ↓
仓储接口 (domain/repositories/*.py)
    ↓
仓储实现 (infrastructure/repositories/*.py)
    ↓
数据库 (PostgreSQL/Redis)
    ↓
返回结果
```

### 写操作流程

```
客户端请求
    ↓
API路由 (验证请求)
    ↓
领域服务 (业务逻辑处理)
    ↓
仓储接口 (事务管理)
    ↓
仓储实现 (持久化)
    ↓
数据库 (事务提交)
    ↓
领域事件发布 (可选)
    ↓
返回结果
```

---

## 💾 数据存储

### 数据库设计

#### PostgreSQL（主数据源）

**cameras表** - 相机配置
```sql
CREATE TABLE cameras (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    status VARCHAR(20) DEFAULT 'inactive',
    camera_type VARCHAR(50) DEFAULT 'fixed',
    resolution JSONB,
    fps INTEGER,
    region_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

**regions表** - 区域配置
```sql
CREATE TABLE regions (
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
)
```

**detection_records表** - 检测记录
```sql
CREATE TABLE detection_records (
    id VARCHAR(255) PRIMARY KEY,
    camera_id VARCHAR(255) NOT NULL,
    objects JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    confidence FLOAT NOT NULL,
    processing_time FLOAT NOT NULL,
    frame_id INTEGER,
    region_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
```

**alerts表** - 告警记录
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id UUID REFERENCES cameras(id),
    zone_id UUID REFERENCES detection_zones(id),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
```

#### Redis（缓存和消息队列）

- **缓存**: 检测结果缓存
- **消息队列**: 异步任务队列

### 配置文件

**已迁移到数据库**:
- ✅ `cameras.yaml` → PostgreSQL `cameras`表
- ✅ `regions.json` → PostgreSQL `regions`表 + `system_configs`表

**保留在文件**（用于版本控制）:
- `unified_params.yaml` - 算法参数配置
- `enhanced_detection_config.yaml` - 算法增强配置

---

## 🔌 API端点

### 已完成重构的端点（38个）

#### 核心业务读操作（16个）
- `GET /api/v1/records/violations` - 违规记录列表
- `GET /api/v1/records/violations/{violation_id}` - 违规详情
- `GET /api/v1/records/detection-records/{camera_id}` - 检测记录列表
- `GET /api/v1/records/statistics/summary` - 统计摘要
- `GET /api/v1/records/statistics/{camera_id}` - 摄像头统计
- `GET /api/v1/statistics/summary` - 事件统计汇总
- `GET /api/v1/statistics/realtime` - 实时统计接口
- `GET /api/v1/statistics/daily` - 按天统计事件趋势
- `GET /api/v1/statistics/events` - 事件列表查询
- `GET /api/v1/statistics/history` - 近期事件历史
- `GET /api/v1/events/recent` - 最近事件列表
- `GET /api/v1/cameras` - 摄像头列表
- `GET /api/v1/cameras/{camera_id}/stats` - 摄像头详细统计
- `GET /api/v1/system/info` - 系统信息
- `GET /api/v1/alerts/history-db` - 告警历史
- `GET /api/v1/alerts/rules` - 告警规则列表

#### 核心业务写操作（4个）
- `PUT /api/v1/records/violations/{violation_id}/status` - 更新违规状态
- `POST /api/v1/cameras` - 创建摄像头
- `PUT /api/v1/cameras/{camera_id}` - 更新摄像头
- `DELETE /api/v1/cameras/{camera_id}` - 删除摄像头

#### 告警规则写操作（2个）
- `POST /api/v1/alerts/rules` - 创建告警规则
- `PUT /api/v1/alerts/rules/{rule_id}` - 更新告警规则

#### 摄像头操作端点（11个）
- `POST /api/v1/cameras/{camera_id}/start` - 启动摄像头
- `POST /api/v1/cameras/{camera_id}/stop` - 停止摄像头
- `POST /api/v1/cameras/{camera_id}/restart` - 重启摄像头
- `GET /api/v1/cameras/{camera_id}/status` - 获取状态
- `POST /api/v1/cameras/batch-status` - 批量状态查询
- `POST /api/v1/cameras/{camera_id}/activate` - 激活摄像头
- `POST /api/v1/cameras/{camera_id}/deactivate` - 停用摄像头
- `PUT /api/v1/cameras/{camera_id}/auto-start` - 设置自动启动
- `POST /api/v1/cameras/refresh` - 刷新摄像头列表
- `GET /api/v1/cameras/{camera_id}/preview` - 获取预览
- `GET /api/v1/cameras/{camera_id}/logs` - 获取日志

#### 区域管理端点（5个）
- `GET /api/v1/management/regions` - 获取所有区域
- `POST /api/v1/management/regions` - 创建区域
- `PUT /api/v1/management/regions/{region_id}` - 更新区域
- `DELETE /api/v1/management/regions/{region_id}` - 删除区域
- `POST /api/v1/management/regions/meta` - 更新区域meta

详见 [API文档](./API_文档.md)

---

## 🔄 灰度发布机制

所有重构的API端点都支持灰度发布，确保平滑过渡和快速回滚。

### 灰度控制方式

1. **环境变量控制**:
   - `USE_DOMAIN_SERVICE=true/false` - 全局开关
   - `ROLLOUT_PERCENT=0-100` - 灰度百分比

2. **查询参数控制**:
   - `force_domain=true` - 强制使用领域服务
   - `force_domain=false` - 强制使用旧实现

3. **自动回退**:
   - 领域服务失败时自动回退到旧实现
   - 保证API可用性，不中断服务

---

## 🧪 测试策略

### 单元测试

- ✅ **覆盖率**: ≥90%
- ✅ **测试用例**: 119个单元测试
- ✅ **仓储测试**: 37个仓储测试

### 集成测试

- ✅ **测试用例**: 24个端点测试用例
- ✅ **通过率**: 100%

### 测试覆盖

- 领域服务测试
- 仓储实现测试
- API端点测试
- 业务逻辑测试

---

## 📊 监控和运维

### 健康检查

- `GET /api/v1/monitoring/health` - 健康检查端点
  - 数据库连接检查
  - Redis连接检查
  - 服务状态检查

### 监控指标

- `GET /api/v1/monitoring/metrics` - 监控指标端点
  - 请求总数
  - 响应时间
  - 错误率
  - 领域服务使用率

### 日志

- 结构化日志
- 错误追踪
- 性能监控

---

## 🚀 部署架构

### Docker部署

- **生产镜像**: `Dockerfile.prod`
- **开发镜像**: `Dockerfile.dev`
- **Docker Compose**:
  - `docker-compose.prod.yml` - 生产环境
  - `docker-compose.prod.full.yml` - 完整生产环境（包含监控）

### 跨平台部署

- **开发环境**: macOS
- **生产环境**: Ubuntu
- **私有Registry**: 支持私有Docker Registry部署

详见 [生产部署指南](./production_deployment_guide.md)

---

## 📚 相关文档

- [重构完成检查清单](./REFACTORING_COMPLETE_CHECKLIST.md)
- [API文档](./API_文档.md)
- [配置迁移报告](./all_configs_migration_complete.md)
- [生产部署指南](./production_deployment_guide.md)

---

**更新日期**: 2025-11-03
**状态**: ✅ **架构重构完成**
