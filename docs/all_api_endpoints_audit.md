# 全部API端点审计报告

## 日期
2025-10-31

## 概述

本文档统计项目中所有API端点，并分析哪些已接入领域服务，哪些尚未接入。

## 📊 端点统计

### 总体统计

| 路由文件 | 端点数量 | 已接入 | 未接入 | 状态 |
|---------|---------|--------|--------|------|
| **records.py** | 7 | 6 | 1 | ✅ 高覆盖率 |
| **statistics.py** | 5 | 5 | 0 | ✅ 已完成 |
| **cameras.py** | 18 | 3 | 15 | ⚠️ 部分接入 |
| **alerts.py** | 4 | 2 | 2 | ⚠️ 部分接入 |
| **system.py** | 3 | 1 | 2 | ⚠️ 部分接入 |
| **events.py** | 1 | 1 | 0 | ✅ 已完成 |
| **monitoring.py** | 2 | 0 | 2 | ⚠️ 未接入 |
| **mlops.py** | 16 | 0 | 16 | ❌ 未接入 |
| **security.py** | 17 | 0 | 17 | ❌ 未接入 |
| **region_management.py** | 7 | 0 | 7 | ❌ 未接入 |
| **error_monitoring.py** | 14 | 0 | 14 | ❌ 未接入 |
| **video_stream.py** | 3 | 0 | 3 | ❌ 未接入 |
| **download.py** | 3 | 0 | 3 | ❌ 未接入 |
| **comprehensive.py** | 3 | 0 | 3 | ❌ 未接入 |
| **metrics.py** | 1 | 0 | 1 | ❌ 未接入 |
| **总计** | **105** | **18** | **87** | ⚠️ 17%完成 |

## ✅ 已接入领域服务的端点（18个）

### Records路由 (`/api/v1/records`)

1. ✅ `GET /api/v1/records/violations` - 违规记录列表
2. ✅ `GET /api/v1/records/violations/{violation_id}` - 违规详情
3. ✅ `PUT /api/v1/records/violations/{violation_id}/status` - 更新违规状态
4. ✅ `GET /api/v1/records/statistics/summary` - 统计摘要
5. ✅ `GET /api/v1/records/statistics/{camera_id}` - 摄像头统计
6. ✅ `GET /api/v1/records/detection-records/{camera_id}` - 检测记录

**未接入**: 1个
- ⏳ `GET /api/v1/records/health` - 健康检查（基础端点，可保持现状）

### Statistics路由 (`/api/v1/statistics`)

1. ✅ `GET /api/v1/statistics/realtime` - 实时统计
2. ✅ `GET /api/v1/statistics/summary` - 事件统计汇总
3. ✅ `GET /api/v1/statistics/daily` - 按天统计事件趋势
4. ✅ `GET /api/v1/statistics/events` - 事件列表查询
5. ✅ `GET /api/v1/statistics/history` - 近期事件历史

**全部完成** ✅

### Cameras路由 (`/api/v1/cameras`)

1. ✅ `GET /api/v1/cameras` - 摄像头列表
2. ✅ `GET /api/v1/cameras/{camera_id}/stats` - 摄像头统计
3. ✅ `POST /api/v1/cameras` - 创建摄像头
4. ✅ `PUT /api/v1/cameras/{camera_id}` - 更新摄像头
5. ✅ `DELETE /api/v1/cameras/{camera_id}` - 删除摄像头

**未接入**: 13个摄像头相关操作端点
- ⏳ `GET /api/v1/cameras/{camera_id}/preview` - 预览
- ⏳ `POST /api/v1/cameras/{camera_id}/start` - 启动
- ⏳ `POST /api/v1/cameras/{camera_id}/stop` - 停止
- ⏳ `POST /api/v1/cameras/{camera_id}/restart` - 重启
- ⏳ `GET /api/v1/cameras/{camera_id}/status` - 状态
- ⏳ `POST /api/v1/cameras/batch-status` - 批量状态
- ⏳ `POST /api/v1/cameras/{camera_id}/activate` - 激活
- ⏳ `POST /api/v1/cameras/{camera_id}/deactivate` - 停用
- ⏳ `PUT /api/v1/cameras/{camera_id}/auto-start` - 自动启动
- ⏳ `GET /api/v1/cameras/{camera_id}/logs` - 日志
- ⏳ `POST /api/v1/cameras/refresh` - 刷新

### Alerts路由 (`/api/v1/alerts`)

1. ✅ `GET /api/v1/alerts/history-db` - 查询告警历史
2. ✅ `GET /api/v1/alerts/rules` - 列出告警规则

**未接入**: 2个
- ⏳ `POST /api/v1/alerts/rules` - 创建告警规则
- ⏳ `PUT /api/v1/alerts/rules/{rule_id}` - 更新告警规则

### System路由 (`/api/v1/system`)

1. ✅ `GET /api/v1/system/info` - 系统信息

**未接入**: 2个
- ⏳ `GET /api/v1/system/config` - 系统配置信息
- ⏳ `GET /api/v1/system/health` - 系统健康状态

### Events路由 (`/api/v1/events`)

1. ✅ `GET /api/v1/events/recent` - 最近事件

**全部完成** ✅

## ❌ 未接入领域服务的端点（87个）

### Monitoring路由 (`/api/v1/monitoring`) - 2个端点

1. ⏳ `GET /api/v1/monitoring/health` - 健康检查
2. ⏳ `GET /api/v1/monitoring/metrics` - 监控指标

**说明**: 这些是基础设施端点，可以考虑保持现状或简单封装。

### MLOps路由 (`/api/v1/mlops`) - 16个端点

1. ⏳ `GET /api/v1/mlops/datasets` - 数据集列表
2. ⏳ `POST /api/v1/mlops/datasets/upload` - 上传数据集
3. ⏳ `GET /api/v1/mlops/datasets/{dataset_id}` - 数据集详情
4. ⏳ `DELETE /api/v1/mlops/datasets/{dataset_id}` - 删除数据集
5. ⏳ `GET /api/v1/mlops/datasets/{dataset_id}/download` - 下载数据集
6. ⏳ `GET /api/v1/mlops/datasets/{dataset_id}/files/{file_path}` - 数据集文件
7. ⏳ `GET /api/v1/mlops/deployments` - 部署列表
8. ⏳ `POST /api/v1/mlops/deployments` - 创建部署
9. ⏳ `PUT /api/v1/mlops/deployments/{deployment_id}/scale` - 扩缩容
10. ⏳ `PUT /api/v1/mlops/deployments/{deployment_id}` - 更新部署
11. ⏳ `DELETE /api/v1/mlops/deployments/{deployment_id}` - 删除部署
12. ⏳ `GET /api/v1/mlops/workflows` - 工作流列表
13. ⏳ `POST /api/v1/mlops/workflows` - 创建工作流
14. ⏳ `PUT /api/v1/mlops/workflows/{workflow_id}` - 更新工作流
15. ⏳ `POST /api/v1/mlops/workflows/{workflow_id}/run` - 运行工作流
16. ⏳ `DELETE /api/v1/mlops/workflows/{workflow_id}` - 删除工作流

**说明**: MLOps相关端点，属于独立功能模块，建议保持现状或单独重构。

### Security路由 (`/api/v1/security`) - 17个端点

1. ⏳ `POST /api/v1/security/auth/login` - 用户登录
2. ⏳ `POST /api/v1/security/auth/logout` - 用户登出
3. ⏳ `GET /api/v1/security/auth/me` - 当前用户信息
4. ⏳ `GET /api/v1/security/events` - 安全事件
5. ⏳ `GET /api/v1/security/report` - 安全报告
6. ⏳ `GET /api/v1/security/rules` - 访问控制规则
7. ⏳ `POST /api/v1/security/rules` - 创建访问控制规则
8. ⏳ `DELETE /api/v1/security/rules/{rule_id}` - 删除访问控制规则
9. ⏳ `GET /api/v1/security/sessions` - 活跃会话
10. ⏳ `POST /api/v1/security/block-ip/{ip_address}` - 阻止IP
11. ⏳ `DELETE /api/v1/security/block-ip/{ip_address}` - 解除IP阻止
12. ⏳ `GET /api/v1/security/blocked-ips` - 被阻止的IP列表
13. ⏳ `POST /api/v1/security/threat-detection/test` - 测试威胁检测
14. ⏳ `GET /api/v1/security/threat-types` - 威胁类型列表
15. ⏳ `GET /api/v1/security/security-levels` - 安全级别列表
16. ⏳ `GET /api/v1/security/stats` - 安全统计

**说明**: 安全相关端点，属于独立功能模块，建议保持现状或单独重构。

### Region Management路由 (`/api/v1/management/regions`) - 7个端点

1. ⏳ `GET /api/v1/management/regions` - 获取所有区域信息
2. ⏳ `POST /api/v1/management/regions` - 创建新区域
3. ⏳ `POST /api/v1/management/regions/meta` - 更新区域元信息
4. ⏳ `PUT /api/v1/management/regions/{region_id}` - 更新区域信息
5. ⏳ `DELETE /api/v1/management/regions/{region_id}` - 删除区域
6. ⏳ `GET /api/regions` - [兼容] 获取区域（旧版前端）
7. ⏳ `POST /api/regions` - [兼容] 保存区域（旧版前端）

**说明**: 区域管理相关端点，属于独立功能模块，建议保持现状或单独重构。

### Error Monitoring路由 (`/api/v1/monitoring`) - 14个端点

1. ⏳ `GET /api/v1/monitoring/errors/stats` - 错误统计
2. ⏳ `GET /api/v1/monitoring/errors/by-category/{category}` - 根据分类获取错误
3. ⏳ `GET /api/v1/monitoring/errors/by-severity/{severity}` - 根据严重程度获取错误
4. ⏳ `GET /api/v1/monitoring/health` - 系统健康状态
5. ⏳ `GET /api/v1/monitoring/health/detailed` - 详细健康检查
6. ⏳ `GET /api/v1/monitoring/alerts/active` - 获取活跃告警
7. ⏳ `GET /api/v1/monitoring/alerts/history` - 获取告警历史
8. ⏳ `POST /api/v1/monitoring/alerts/{alert_id}/resolve` - 解决告警
9. ⏳ `GET /api/v1/monitoring/performance` - 性能统计
10. ⏳ `POST /api/v1/monitoring/monitoring/start` - 启动错误监控
11. ⏳ `POST /api/v1/monitoring/monitoring/stop` - 停止错误监控
12. ⏳ `GET /api/v1/monitoring/monitoring/status` - 获取监控状态
13. ⏳ `GET /api/v1/monitoring/errors/categories` - 错误分类列表
14. ⏳ `GET /api/v1/monitoring/errors/severities` - 错误严重程度列表

**说明**: 错误监控相关端点，属于独立功能模块，建议保持现状或单独重构。

### Video Stream路由 (`/api/v1/video-stream`) - 3个端点

1. ⏳ `GET /api/v1/video-stream/stats` - 视频流统计
2. ⏳ `GET /api/v1/video-stream/status/{camera_id}` - 摄像头视频流状态
3. ⏳ `POST /api/v1/video-stream/frame/{camera_id}` - 接收视频帧(HTTP推送)

**说明**: 视频流相关端点，属于实时流处理，建议保持现状。

### Download路由 (`/api/v1/download`) - 3个端点

1. ⏳ `GET /api/v1/download/video/{filename}` - 下载处理后的视频
2. ⏳ `GET /api/v1/download/image/{filename}` - 下载处理后的图片
3. ⏳ `GET /api/v1/download/overlay` - 下载最近的区域叠加图

**说明**: 文件下载端点，属于基础设施层，建议保持现状。

### Comprehensive路由 (`/api/v1/detect`) - 3个端点

1. ⏳ `POST /api/v1/detect/comprehensive` - 综合检测接口
2. ⏳ `POST /api/v1/detect/image` - 图像检测接口
3. ⏳ `POST /api/v1/detect/hairnet` - 发网检测接口

**说明**: 核心检测流程端点，属于业务核心，建议保持现状或谨慎重构。

### Metrics路由 - 1个端点

1. ⏳ `GET /metrics` - Prometheus格式指标

**说明**: Prometheus指标端点，属于基础设施层，建议保持现状。

## 📋 分类总结

### ✅ 已完成重构（核心业务端点）- 18个

这些端点是核心业务逻辑相关的，已经成功接入领域服务：

1. **Records统计和查询** (6个) ✅
2. **Statistics统计** (5个) ✅
3. **Cameras基础CRUD** (5个) ✅
4. **Alerts查询** (2个) ✅
5. **System信息** (1个) ✅
6. **Events查询** (1个) ✅

### ⚠️ 部分接入（建议优先完成）- 15个

这些端点属于已重构模块，但还有部分未接入：

1. **Cameras操作端点** (13个) - 摄像头启动/停止/状态等操作
2. **Alerts写操作** (2个) - 创建和更新告警规则

### ❌ 未接入（建议保持现状或单独规划）- 72个

这些端点属于独立功能模块或基础设施层：

1. **MLOps** (16个) - 独立功能模块
2. **Security** (17个) - 独立功能模块
3. **Error Monitoring** (14个) - 独立功能模块
4. **Region Management** (7个) - 独立功能模块
5. **Video Stream** (3个) - 实时流处理
6. **Download** (3个) - 基础设施层
7. **Comprehensive** (3个) - 核心检测流程
8. **Monitoring** (2个) - 基础设施层
9. **Metrics** (1个) - 基础设施层

## 🎯 建议

### 立即接入（高优先级）- 15个端点

1. **Cameras操作端点** (13个)
   - 这些端点是摄像头管理的一部分，应该与CRUD端点保持一致
   - 建议创建 `CameraControlService` 封装这些操作

2. **Alerts写操作** (2个)
   - 创建和更新告警规则，应该与查询操作保持一致
   - 已有 `AlertRuleService`，只需要接入写操作

### 保持现状（中低优先级）- 72个端点

这些端点属于独立功能模块，建议：

1. **独立规划**: 如果需要重构，应该作为独立的项目进行
2. **保持现状**: 当前实现已经足够，不需要急于重构
3. **渐进式改进**: 如果业务需要，可以逐步重构

### 核心业务覆盖率

**核心业务端点** (检测、统计、记录相关):
- 总数: ~30个
- 已接入: 18个
- 完成率: **60%** ✅

**操作端点** (摄像头控制、告警规则):
- 总数: ~15个
- 已接入: 0个
- 完成率: **0%** ⚠️

**基础设施端点** (下载、监控、安全等):
- 总数: ~60个
- 已接入: 0个
- 完成率: **0%** (建议保持现状)

## 📊 总结

### 当前状态

- ✅ **核心业务端点**: 60%完成 (18/30)
- ⚠️ **操作端点**: 0%完成 (0/15)
- ❌ **基础设施端点**: 保持现状 (0/60)

### 下一步建议

1. **优先完成摄像头操作端点** (13个)
   - 创建 `CameraControlService`
   - 接入所有摄像头操作端点
   - 预计工作量: 1-2周

2. **完成告警规则写操作** (2个)
   - 扩展 `AlertRuleService`
   - 接入创建和更新端点
   - 预计工作量: 3-5天

3. **评估独立模块重构需求**
   - MLOps、Security、Error Monitoring等
   - 根据业务需求决定是否重构

---

**状态**: ⚠️ **部分完成**
**核心业务完成率**: 60%
**总完成率**: 17% (18/105)
**建议**: 优先完成摄像头操作端点和告警规则写操作
