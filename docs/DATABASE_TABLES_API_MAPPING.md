# 数据库表与API接口映射关系

## 📅 文档日期: 2025-11-04

本文档详细说明了数据库中所有表与对应API接口的映射关系。

---

## 📊 核心业务表

### 1. `detection_records` - 检测记录表

**表描述**: 存储所有检测记录，包括检测到的对象、统计信息等

**主要字段**:
- `id` (bigint) - 主键
- `camera_id` (varchar) - 摄像头ID
- `timestamp` (timestamp) - 检测时间
- `objects` (jsonb) - 检测到的对象列表
- `person_count` (integer) - 人数统计
- `handwash_events` (integer) - 洗手事件数
- `sanitize_events` (integer) - 消毒事件数
- `hairnet_violations` (integer) - 发网违规数
- `confidence` (float) - 置信度
- `processing_time` (float) - 处理时间

**仓储实现**: `PostgreSQLDetectionRepository`
- 文件: `src/infrastructure/repositories/postgresql_detection_repository.py`

**领域服务**: `DetectionServiceDomain`
- 文件: `src/services/detection_service_domain.py`

**API路由**: `/api/v1/records`

**接口列表**:
- `GET /api/v1/records/violations` - 获取违规记录列表
  - 参数: `camera_id`, `status`, `violation_type`, `limit`, `offset`
- `GET /api/v1/records/detection-records/{camera_id}` - 获取指定摄像头的检测记录
  - 参数: `limit`, `offset`
- `GET /api/v1/records/summary` - 获取统计摘要
  - 参数: `period` (1d, 7d, 30d)
- `GET /api/v1/records/health` - 健康检查

**API文件**: `src/api/routers/records.py`

---

### 2. `cameras` - 摄像头配置表

**表描述**: 存储摄像头配置信息，包括位置、类型、状态等

**主要字段**:
- `id` (varchar) - 摄像头ID（主键）
- `name` (varchar) - 摄像头名称
- `location` (varchar) - 位置
- `status` (varchar) - 状态 (active/inactive)
- `camera_type` (varchar) - 类型 (fixed/ptz)
- `resolution` (jsonb) - 分辨率
- `fps` (integer) - 帧率
- `region_id` (varchar) - 关联区域ID
- `metadata` (jsonb) - 元数据

**仓储实现**: `PostgreSQLCameraRepository`
- 文件: `src/infrastructure/repositories/postgresql_camera_repository.py`

**领域服务**: `CameraService`, `CameraControlService`
- 文件: `src/domain/services/camera_service.py`, `src/domain/services/camera_control_service.py`

**API路由**: `/api/cameras`

**接口列表**:
- `GET /api/cameras` - 获取所有摄像头列表
- `GET /api/cameras/{camera_id}` - 获取单个摄像头详情
- `POST /api/cameras` - 创建新摄像头
- `PUT /api/cameras/{camera_id}` - 更新摄像头配置
- `DELETE /api/cameras/{camera_id}` - 删除摄像头
- `POST /api/cameras/{camera_id}/start` - 启动摄像头检测
- `POST /api/cameras/{camera_id}/stop` - 停止摄像头检测
- `GET /api/cameras/{camera_id}/status` - 获取摄像头运行状态
- `GET /api/cameras/{camera_id}/logs` - 获取摄像头日志

**API文件**: `src/api/routers/cameras.py`

---

### 3. `regions` - 检测区域配置表

**表描述**: 存储检测区域配置，包括多边形坐标、规则等

**主要字段**:
- `region_id` (varchar) - 区域ID（主键）
- `region_type` (varchar) - 区域类型
- `name` (varchar) - 区域名称
- `polygon` (jsonb) - 多边形坐标
- `is_active` (boolean) - 是否激活
- `rules` (jsonb) - 规则配置
- `camera_id` (varchar) - 关联摄像头ID
- `metadata` (jsonb) - 元数据

**仓储实现**: `PostgreSQLRegionRepository`
- 文件: `src/infrastructure/repositories/postgresql_region_repository.py`

**领域服务**: `RegionDomainService`
- 文件: `src/domain/services/region_service.py`

**API路由**: `/api/regions`

**接口列表**:
- `GET /api/regions` - 获取所有区域列表
  - 参数: `active_only`, `camera_id`
- `GET /api/regions/{region_id}` - 获取单个区域详情
- `POST /api/regions` - 创建新区域
- `PUT /api/regions/{region_id}` - 更新区域配置
- `DELETE /api/regions/{region_id}` - 删除区域
- `POST /api/regions/import` - 从JSON文件导入区域配置
- `GET /api/regions/export` - 导出区域配置到JSON文件

**API文件**: `src/api/routers/region_management.py`

---

## 🔔 告警相关表

### 4. `alert_history` - 告警历史记录表

**表描述**: 存储所有告警历史记录

**主要字段**:
- `id` (bigint) - 主键
- `rule_id` (integer) - 关联规则ID
- `camera_id` (varchar) - 摄像头ID
- `timestamp` (timestamp) - 告警时间
- `alert_type` (varchar) - 告警类型
- `message` (text) - 告警消息
- `details` (jsonb) - 详细信息
- `notification_sent` (boolean) - 是否已发送通知

**仓储实现**: `PostgreSQLAlertRepository`
- 文件: `src/infrastructure/repositories/postgresql_alert_repository.py`

**领域服务**: `AlertService`
- 文件: `src/domain/services/alert_service.py`

**API路由**: `/api/alerts`

**接口列表**:
- `GET /api/alerts/history-db` - 获取告警历史记录
  - 参数: `limit`, `camera_id`, `alert_type`

**API文件**: `src/api/routers/alerts.py`

---

### 5. `alert_rules` - 告警规则配置表

**表描述**: 存储告警规则配置

**主要字段**:
- `id` (integer) - 主键
- `name` (varchar) - 规则名称
- `camera_id` (varchar) - 摄像头ID
- `rule_type` (varchar) - 规则类型
- `conditions` (jsonb) - 触发条件
- `notification_channels` (jsonb) - 通知渠道
- `recipients` (jsonb) - 接收人列表
- `enabled` (boolean) - 是否启用
- `priority` (varchar) - 优先级

**仓储实现**: `PostgreSQLAlertRuleRepository`
- 文件: `src/infrastructure/repositories/postgresql_alert_rule_repository.py`

**领域服务**: `AlertRuleService`
- 文件: `src/domain/services/alert_rule_service.py`

**API路由**: `/api/alerts`

**接口列表**:
- `GET /api/alerts/rules` - 获取告警规则列表
  - 参数: `camera_id`, `enabled`
- `POST /api/alerts/rules` - 创建告警规则
- `PUT /api/alerts/rules/{rule_id}` - 更新告警规则
- `DELETE /api/alerts/rules/{rule_id}` - 删除告警规则

**API文件**: `src/api/routers/alerts.py`

---

## 📈 统计相关表

### 6. `statistics_hourly` - 每小时统计数据表

**表描述**: 存储每小时统计数据（聚合表）

**主要字段**:
- `id` (bigint) - 主键
- `camera_id` (varchar) - 摄像头ID
- `hour_start` (timestamp) - 小时起始时间
- `total_frames` (integer) - 总帧数
- `total_persons` (integer) - 总人数
- `total_hairnet_violations` (integer) - 总发网违规数
- `total_handwash_events` (integer) - 总洗手事件数
- `total_sanitize_events` (integer) - 总消毒事件数
- `avg_fps` (float) - 平均帧率
- `avg_processing_time` (float) - 平均处理时间

**仓储实现**: 通过 `DetectionServiceDomain` 间接访问

**领域服务**: `DetectionServiceDomain`

**API路由**: `/api/statistics`

**接口列表**:
- `GET /api/statistics/realtime` - 获取实时统计
- `GET /api/statistics/summary` - 获取统计摘要
- `GET /api/statistics/daily` - 获取每日统计

**API文件**: `src/api/routers/statistics.py`

---

### 7. `violation_events` - 违规事件记录表

**表描述**: 存储违规事件详细记录

**主要字段**:
- `id` (bigint) - 主键
- `detection_id` (bigint) - 关联检测记录ID
- `camera_id` (varchar) - 摄像头ID
- `timestamp` (timestamp) - 违规时间
- `violation_type` (varchar) - 违规类型
- `track_id` (integer) - 跟踪ID
- `confidence` (float) - 置信度
- `snapshot_path` (varchar) - 快照路径
- `bbox` (jsonb) - 边界框
- `status` (varchar) - 状态

**仓储实现**: 通过 `DetectionServiceDomain` 间接访问

**领域服务**: `DetectionServiceDomain`

**API路由**: `/api/v1/records`

**接口列表**:
- `GET /api/v1/records/violations` - 获取违规记录列表

**API文件**: `src/api/routers/records.py`

---

## 🔄 MLOps相关表

### 8. `datasets` - 数据集管理表

**表描述**: 存储数据集信息

**主要字段**:
- `id` (varchar) - 数据集ID（主键）
- `name` (varchar) - 数据集名称
- `version` (varchar) - 版本
- `status` (varchar) - 状态
- `size` (bigint) - 大小
- `sample_count` (integer) - 样本数
- `label_count` (integer) - 标签数
- `quality_score` (float) - 质量评分

**仓储实现**: `DatasetDAO`
- 文件: `src/database/dao.py`

**API路由**: `/api/v1/mlops/datasets`

**接口列表**:
- `GET /api/v1/mlops/datasets` - 获取数据集列表
- `POST /api/v1/mlops/datasets/upload` - 上传数据集
- `GET /api/v1/mlops/datasets/{dataset_id}` - 获取数据集详情
- `DELETE /api/v1/mlops/datasets/{dataset_id}` - 删除数据集

**API文件**: `src/api/routers/mlops.py`

---

### 9. `deployments` - 模型部署记录表

**表描述**: 存储模型部署信息

**主要字段**:
- `id` (varchar) - 部署ID（主键）
- `name` (varchar) - 部署名称
- `model_version` (varchar) - 模型版本
- `environment` (varchar) - 环境
- `status` (varchar) - 状态
- `replicas` (integer) - 副本数
- `cpu_limit` (varchar) - CPU限制
- `memory_limit` (varchar) - 内存限制
- `gpu_count` (integer) - GPU数量

**仓储实现**: `DeploymentDAO`
- 文件: `src/database/dao.py`

**API路由**: `/api/v1/mlops/deployments`

**接口列表**:
- `GET /api/v1/mlops/deployments` - 获取部署列表
- `POST /api/v1/mlops/deployments` - 创建部署
- `GET /api/v1/mlops/deployments/{deployment_id}` - 获取部署详情
- `PUT /api/v1/mlops/deployments/{deployment_id}` - 更新部署
- `DELETE /api/v1/mlops/deployments/{deployment_id}` - 删除部署

**API文件**: `src/api/routers/mlops.py`

---

### 10. `workflows` - 工作流配置表

**表描述**: 存储工作流配置

**主要字段**:
- `id` (varchar) - 工作流ID（主键）
- `name` (varchar) - 工作流名称
- `type` (varchar) - 类型
- `status` (varchar) - 状态
- `trigger` (varchar) - 触发方式
- `schedule` (varchar) - 调度配置
- `steps` (json) - 步骤配置
- `run_count` (integer) - 运行次数
- `success_rate` (float) - 成功率

**仓储实现**: `WorkflowDAO`
- 文件: `src/database/dao.py`

**API路由**: `/api/v1/mlops/workflows`

**接口列表**:
- `GET /api/v1/mlops/workflows` - 获取工作流列表
- `POST /api/v1/mlops/workflows` - 创建工作流
- `GET /api/v1/mlops/workflows/{workflow_id}` - 获取工作流详情
- `PUT /api/v1/mlops/workflows/{workflow_id}` - 更新工作流
- `DELETE /api/v1/mlops/workflows/{workflow_id}` - 删除工作流

**API文件**: `src/api/routers/mlops.py`

---

### 11. `workflow_runs` - 工作流运行记录表

**表描述**: 存储工作流运行历史

**主要字段**:
- `id` (varchar) - 运行ID（主键）
- `workflow_id` (varchar) - 关联工作流ID
- `status` (varchar) - 运行状态
- `started_at` (timestamp) - 开始时间
- `ended_at` (timestamp) - 结束时间
- `duration` (integer) - 持续时间（秒）
- `error_message` (text) - 错误消息
- `run_log` (text) - 运行日志

**仓储实现**: `WorkflowRunDAO`
- 文件: `src/database/dao.py`

**API路由**: `/api/v1/mlops/workflows`

**接口列表**:
- `GET /api/v1/mlops/workflows/{workflow_id}/runs` - 获取工作流运行记录

**API文件**: `src/api/routers/mlops.py`

---

## 📊 视图（Views）

### 12. `v_daily_statistics` - 每日统计视图

**视图描述**: 每日统计数据视图（从 `detection_records` 聚合）

**主要字段**:
- `camera_id` (varchar) - 摄像头ID
- `date` (date) - 日期
- `total_frames` (bigint) - 总帧数
- `total_persons` (bigint) - 总人数
- `total_hairnet_violations` (bigint) - 总发网违规数
- `total_handwash_events` (bigint) - 总洗手事件数
- `total_sanitize_events` (bigint) - 总消毒事件数
- `avg_fps` (float) - 平均帧率
- `avg_processing_time` (float) - 平均处理时间

**仓储实现**: 通过 `DetectionServiceDomain` 间接访问

**领域服务**: `DetectionServiceDomain`

**API路由**: `/api/statistics`

**接口列表**:
- `GET /api/statistics/daily` - 获取每日统计

**API文件**: `src/api/routers/statistics.py`

---

### 13. `v_recent_violations` - 最近违规记录视图

**视图描述**: 最近违规记录视图（从 `violation_events` 聚合）

**主要字段**:
- `id` (bigint) - 记录ID
- `camera_id` (varchar) - 摄像头ID
- `timestamp` (timestamp) - 违规时间
- `violation_type` (varchar) - 违规类型
- `track_id` (integer) - 跟踪ID
- `confidence` (float) - 置信度
- `status` (varchar) - 状态
- `snapshot_path` (varchar) - 快照路径

**仓储实现**: 通过 `DetectionServiceDomain` 间接访问

**领域服务**: `DetectionServiceDomain`

**API路由**: `/api/v1/records`

**接口列表**:
- `GET /api/v1/records/violations` - 获取违规记录列表

**API文件**: `src/api/routers/records.py`

---

## 📋 总结

### 表统计

- **核心业务表**: 3个 (`detection_records`, `cameras`, `regions`)
- **告警相关表**: 2个 (`alert_history`, `alert_rules`)
- **统计相关表**: 2个 (`statistics_hourly`, `violation_events`)
- **MLOps相关表**: 4个 (`datasets`, `deployments`, `workflows`, `workflow_runs`)
- **视图**: 2个 (`v_daily_statistics`, `v_recent_violations`)

**总计**: 13个表/视图

### 架构层次

```
API层 (src/api/routers/)
    ↓
应用层/领域层 (src/domain/services/, src/services/)
    ↓
仓储层 (src/infrastructure/repositories/)
    ↓
数据库 (PostgreSQL)
```

### 访问方式

1. **直接仓储访问**: `cameras`, `regions`, `alert_history`, `alert_rules`
2. **领域服务访问**: `detection_records`, `violation_events`, `statistics_hourly`
3. **DAO访问**: `datasets`, `deployments`, `workflows`, `workflow_runs`
4. **视图访问**: `v_daily_statistics`, `v_recent_violations`

---

**文档更新时间**: 2025-11-04
**数据库版本**: PostgreSQL
**API版本**: v1
