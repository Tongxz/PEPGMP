# API 接口文档 (v2.0)

## 1. 概述

人体行为检测系统提供了一套完整的 RESTful API 接口和 WebSocket 服务，支持图像/视频的综合检测、区域管理、实时统计等功能。本文档详细介绍了所有可用的 API 端点。

- **基础URL**: `http://localhost:8000`
- **API版本**: v1

## 2. 核心端点

### 2.1 综合检测

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

### 2.2 区域管理

用于获取和管理检测区域的配置。

**端点**: `GET /api/v1/management/regions`

**描述**: 获取所有已配置的检测区域列表。

**响应示例**:
```json
[
  {
    "id": "handwash_zone",
    "name": "洗手区域",
    "type": "handwash",
    "points": [[100, 100], [500, 100], [500, 400], [100, 400]],
    "rules": {"require_handwashing": true, "min_duration": 20}
  }
]
```

### 2.3 实时 WebSocket

系统通过WebSocket将实时的检测结果推送给前端。

**端点**: `WS /ws/detection`

**描述**: 建立WebSocket连接后，服务器会实时推送检测数据流。用于驱动前端的实时画面和统计更新。

## 3. 其他辅助端点

| 方法 | 端点 | 描述 |
|---|---|---|
| `GET` | `/health` | **健康检查**：检查API服务是否正常运行。返回 `{"status": "healthy"}`。 |
| `GET` | `/api/v1/statistics/realtime` | **实时统计**：获取系统的实时检测统计信息。 |
| `GET` | `/api/v1/statistics/history` | **历史统计**：获取指定时间范围内的历史统计数据。 |
| `GET` | `/api/v1/events/recent` | **近期事件**：获取最近发生的违规或关键事件列表。 |
| `GET` | `/api/v1/download/{filename}` | **文件下载**：下载服务器上处理过的视频或抓拍的图片。 |
| `GET` | `/api/v1/cameras` | **相机列表**：获取已配置的摄像头列表。 |
| `GET` | `/api/v1/system/info` | **系统信息**：获取系统硬件、软件和配置信息。 |
| `GET` | `/metrics` | **性能指标**：为Prometheus等监控系统提供性能指标。 |
| `GET` | `/health` | **健康检查**：检查系统健康状态，包括GPU、数据库等组件。 |
| `GET` | `/api/v1/error-monitoring/stats` | **错误监控**：获取错误统计和监控数据。 |
| `POST` | `/api/v1/security/auth/login` | **用户登录**：JWT认证登录（生产环境）。 |
| `GET` | `/api/v1/security/threats` | **安全监控**：获取威胁检测记录。 |

## 4. 错误处理

API遵循标准的HTTP状态码。当发生错误时，响应体通常会包含一个`detail`字段，描述错误信息。

**示例 (400 Bad Request)**:
```json
{
  "detail": "No file provided."
}
```

---
*本文档已于2025-09-15根据 `src/api/app.py` 的最新实现更新。*
