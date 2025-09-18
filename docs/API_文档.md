# API 接口文档 (v2.1)

## 1. 概述

人体行为检测系统提供了一套完整的 RESTful API 接口和 WebSocket 服务，支持图像/视频的综合检测、区域管理、实时统计等功能。本文档详细介绍了所有可用的 API 端点。

- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **统一路径前缀**: `/api/v1`

## 2. API 路径规范

所有API接口都遵循统一的路径规范：

### 2.1 路径结构
```
/api/v1/{模块}/{资源}[/{资源ID}][/{操作}]
```

### 2.2 模块分类
- **system**: 系统相关接口 (`/api/v1/system/*`)
- **cameras**: 摄像头管理接口 (`/api/v1/cameras/*`)
- **management**: 资源管理接口 (`/api/v1/management/*`)
- **statistics**: 统计分析接口 (`/api/v1/statistics/*`)
- **detect**: 检测服务接口 (`/api/v1/detect/*`)

## 3. 系统接口

### 3.1 系统健康检查

**端点**: `GET /api/v1/system/health`

**描述**: 检查系统运行状态和健康信息

**响应示例**:
```json
{
  "timestamp": "2025-01-17T17:03:45.323188",
  "status": "healthy",
  "issues": [],
  "directories": {
    "config": {"exists": true, "is_directory": true, "readable": true, "writable": true},
    "src": {"exists": true, "is_directory": true, "readable": true, "writable": true}
  },
  "resources": {
    "memory_usage": 73.9,
    "disk_usage": 6.5,
    "cpu_usage": 8.9
  }
}
```

### 3.2 系统信息

**端点**: `GET /api/v1/system/info`

**描述**: 获取系统基本信息

### 3.3 系统配置

**端点**: `GET /api/v1/system/config`

**描述**: 获取系统配置信息

## 4. 摄像头管理接口

### 4.1 获取摄像头列表

**端点**: `GET /api/v1/cameras`

**描述**: 获取所有配置的摄像头信息

**响应示例**:
```json
{
  "cameras": [
    {
      "id": "cam0",
      "name": "USB0",
      "source": "0",
      "regions_file": "config/regions.json",
      "profile": "accurate",
      "device": "auto",
      "imgsz": "auto",
      "auto_tune": true
    }
  ]
}
```

### 4.2 创建摄像头

**端点**: `POST /api/v1/cameras`

**描述**: 创建新的摄像头配置

### 4.3 更新摄像头

**端点**: `PUT /api/v1/cameras/{camera_id}`

**描述**: 更新指定摄像头的配置

### 4.4 删除摄像头

**端点**: `DELETE /api/v1/cameras/{camera_id}`

**描述**: 删除指定的摄像头配置

### 4.5 摄像头预览

**端点**: `GET /api/v1/cameras/{camera_id}/preview`

**描述**: 获取摄像头预览图像

### 4.6 摄像头控制

- **启动**: `POST /api/v1/cameras/{camera_id}/start`
- **停止**: `POST /api/v1/cameras/{camera_id}/stop`
- **重启**: `POST /api/v1/cameras/{camera_id}/restart`
- **状态**: `GET /api/v1/cameras/{camera_id}/status`

## 5. 区域管理接口

### 5.1 获取区域列表

**端点**: `GET /api/v1/management/regions`

**描述**: 获取所有配置的检测区域

**响应示例**:
```json
{
  "regions": [
    {
      "region_id": "region_123",
      "region_type": "handwash",
      "polygon": [[100, 100], [200, 100], [200, 200], [100, 200]],
      "name": "洗手区域",
      "is_active": true,
      "rules": {
        "required_behaviors": [],
        "forbidden_behaviors": [],
        "max_occupancy": -1,
        "alert_on_violation": true
      }
    }
  ]
}
```

### 5.2 创建区域

**端点**: `POST /api/v1/management/regions`

**描述**: 创建新的检测区域

### 5.3 更新区域

**端点**: `PUT /api/v1/management/regions/{region_id}`

**描述**: 更新指定区域的配置

### 5.4 删除区域

**端点**: `DELETE /api/v1/management/regions/{region_id}`

**描述**: 删除指定的检测区域

## 6. 统计分析接口

### 6.1 统计摘要

**端点**: `GET /api/v1/statistics/summary`

**描述**: 获取统计摘要信息

**查询参数**:
- `camera_id` (可选): 摄像头ID筛选

**响应示例**:
```json
{
  "window_minutes": 60,
  "total_events": 125,
  "counts_by_type": {
    "handwashing": 45,
    "mask_detection": 38,
    "region_violation": 22,
    "occupancy_alert": 20
  },
  "samples": []
}
```

### 6.2 每日统计

**端点**: `GET /api/v1/statistics/daily`

**描述**: 获取每日统计数据

**查询参数**:
- `days` (可选, 默认7): 查询天数
- `camera_id` (可选): 摄像头ID筛选

**响应示例**:
```json
[
  {
    "date": "2025-01-17",
    "total_events": 50,
    "counts_by_type": {
      "handwashing": 20,
      "mask_detection": 15,
      "region_violation": 10,
      "occupancy_alert": 5
    }
  }
]
```

### 6.3 事件列表

**端点**: `GET /api/v1/statistics/events`

**描述**: 获取统计事件列表

**查询参数**:
- `start_date` (可选): 开始日期
- `end_date` (可选): 结束日期
- `event_type` (可选): 事件类型筛选
- `camera_id` (可选): 摄像头ID筛选

**响应示例**:
```json
[
  {
    "id": "event_1",
    "timestamp": "2025-01-17T10:30:00",
    "type": "handwashing",
    "camera_id": "camera_1",
    "confidence": 0.95,
    "details": {
      "duration": 15,
      "location": "区域_1"
    }
  }
]
```

### 6.4 其他统计接口

- **基础统计**: `GET /api/v1/statistics`
- **违规记录**: `GET /api/v1/violations`
- **实时统计**: `GET /api/v1/statistics/realtime`

## 7. 综合检测接口

### 7.1 综合检测

这是系统的核心检测入口，支持对图像和视频文件进行全面的行为分析，包括人体、发网、洗手、消毒等。

**端点**: `POST /api/v1/detect/comprehensive`

**请求参数 (`multipart/form-data`)**:
- `file` (文件, **必需**): 要检测的图像或视频文件 (支持 JPG, PNG, MP4, AVI, MOV 等)。
- `record_process` (可选, bool): **仅对视频有效**。如果为 `true`，将生成并保存一个带标注的检测过程视频。默认为 `false`。
- `force_sync` (可选, bool): 如果为 `true`，强制同步处理视频，API将等待视频处理完成后再返回结果。默认为 `false`（异步处理）。

**响应示例 (图片或同步视频)**:
```json
{
  "filename": "test_image.jpg",
  "detection_type": "comprehensive",
  "status": "success",
  "results": {
    "detections": [
      {
        "class_name": "person",
        "confidence": 0.95,
        "bbox": [100, 150, 300, 450]
      }
    ],
    "behaviors": {
      "hairnet": {"status": "compliant", "confidence": 0.98},
      "handwashing": {"status": "no_action", "confidence": 0.0},
      "sanitizing": {"status": "no_action", "confidence": 0.0}
    },
    "statistics": {
      "total_persons": 1,
      "processing_time_ms": 120
    }
  },
  "processed_video_url": null
}
```

### 7.2 区域管理 (已迁移)

**注意**: 区域管理接口已迁移至第5章节 "区域管理接口"，请参考 `/api/v1/management/regions` 相关接口。

### 7.3 WebSocket 实时检测

系统通过WebSocket将实时的检测结果推送给前端。

**端点**: `WS /ws/detection`

**描述**: 建立WebSocket连接后，服务器会实时推送检测数据流。用于驱动前端的实时画面和统计更新。

## 8. 其他辅助接口

### 8.1 健康检查

**端点**: `GET /health`

**描述**: 检查API服务是否正常运行

**响应示例**:
```json
{"status": "healthy"}
```

### 8.2 文件下载

**端点**: `GET /api/v1/download/{filename}`

**描述**: 下载服务器上处理过的视频或抓拍的图片

### 8.3 性能指标

**端点**: `GET /metrics`

**描述**: 为Prometheus等监控系统提供性能指标

### 8.4 安全相关接口

- **用户登录**: `POST /api/v1/security/auth/login` - JWT认证登录（生产环境）
- **安全监控**: `GET /api/v1/security/threats` - 获取威胁检测记录
- **错误监控**: `GET /api/v1/error-monitoring/stats` - 获取错误统计和监控数据

## 9. 错误处理

API遵循标准的HTTP状态码。当发生错误时，响应体通常会包含一个`detail`字段，描述错误信息。

### 9.1 常见错误码

- **400 Bad Request**: 请求参数错误
- **401 Unauthorized**: 未授权访问
- **404 Not Found**: 资源不存在
- **422 Unprocessable Entity**: 请求格式正确但语义错误
- **500 Internal Server Error**: 服务器内部错误

### 9.2 错误响应示例

**400 Bad Request**:
```json
{
  "detail": "No file provided."
}
```

**422 Unprocessable Entity**:
```json
{
  "detail": [
    {
      "loc": ["body", "camera_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 10. 认证和授权

### 10.1 开发环境

开发环境下，大部分API接口无需认证即可访问。

### 10.2 生产环境

生产环境下，需要通过JWT令牌进行认证：

1. 通过 `/api/v1/security/auth/login` 获取JWT令牌
2. 在请求头中添加 `Authorization: Bearer <token>`

## 11. 限流和配额

### 11.1 请求限制

- 检测接口：每分钟最多60次请求
- 查询接口：每分钟最多300次请求
- WebSocket连接：每个客户端最多5个并发连接

### 11.2 文件大小限制

- 图片文件：最大10MB
- 视频文件：最大100MB

## 12. 版本更新记录

### v2.1 (2025-01-17)
- 统一API路径规范，所有接口使用 `/api/v1` 前缀
- 新增区域管理接口 `/api/v1/management/regions`
- 新增统计事件接口 `/api/v1/statistics/events`
- 完善系统接口文档
- 优化错误处理和响应格式

### v2.0 (2024-12-01)
- 重构API架构，采用模块化设计
- 新增WebSocket实时推送功能
- 增强安全认证机制
- 优化检测性能和准确性

---
*本文档已于2025-01-17根据最新API实现更新至v2.1版本。*
