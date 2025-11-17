# 视频流配置功能实现总结

## 📋 需求描述

用户希望能够在前端配置：
1. **视频流的检测帧率**（stream_interval）
2. **实时视频是否逐帧**（frame_by_frame，即stream_interval=1）

## ✅ 实现方案

### 1. API接口实现

**文件**: `src/api/routers/video_stream.py`

**新增接口**:
- `POST /api/v1/video-stream/config/{camera_id}`: 更新视频流配置
- `GET /api/v1/video-stream/config/{camera_id}`: 获取当前视频流配置

**配置模型**:
```python
class VideoStreamConfigRequest(BaseModel):
    stream_interval: Optional[int] = Field(None, ge=1, le=30)  # 推送间隔（帧数）
    log_interval: Optional[int] = Field(None, ge=1)  # 检测间隔（帧数）
    frame_by_frame: Optional[bool] = Field(None)  # 是否逐帧模式
```

**配置存储**:
- 使用Redis存储配置（键: `video_stream:config:{camera_id}`）
- 配置过期时间: 1小时
- 检测进程每100帧检查一次配置更新

### 2. 检测循环服务更新

**文件**: `src/application/detection_loop_service.py`

**修改内容**:
- 在 `DetectionLoopConfig` 类中添加 `update_from_redis()` 方法
- 在检测循环中每100帧检查一次配置更新
- 支持运行时动态更新配置

### 3. 前端配置界面（待实现）

**文件**: `frontend/src/components/VideoStreamCard.vue`

**需要添加的功能**:
- 检测帧率配置滑块（1-30帧）
- 逐帧模式开关
- 配置保存按钮
- 实时显示当前配置

## 📝 使用说明

### 后端API使用

#### 更新配置

```bash
curl -X POST "http://localhost:8000/api/v1/video-stream/config/camera_001" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_interval": 5,
    "log_interval": 60,
    "frame_by_frame": false
  }'
```

#### 获取配置

```bash
curl "http://localhost:8000/api/v1/video-stream/config/camera_001"
```

### 配置参数说明

| 参数 | 类型 | 说明 | 默认值 | 范围 |
|------|------|------|--------|------|
| `stream_interval` | int | 视频流推送间隔（帧数） | 3 | 1-30 |
| `log_interval` | int | 检测间隔（帧数） | 120 | ≥1 |
| `frame_by_frame` | bool | 是否逐帧模式 | false | true/false |

**注意**:
- `frame_by_frame=true` 时，`stream_interval` 自动设置为 1
- `stream_interval=1` 表示逐帧推送（最高帧率）
- `log_interval` 控制检测频率，不影响视频流推送

## 🔍 配置更新机制

### 配置流程

```
前端配置界面
    ↓
POST /api/v1/video-stream/config/{camera_id}
    ↓
保存到Redis (video_stream:config:{camera_id})
    ↓
检测进程每100帧检查一次
    ↓
更新 DetectionLoopConfig
    ↓
应用新配置
```

### 配置优先级

1. **Redis配置**（最高优先级）
2. **环境变量**（`VIDEO_STREAM_INTERVAL`）
3. **默认值**（`stream_interval=3`, `log_interval=120`）

## 📚 相关文档

- [系统完善改进计划](./SYSTEM_IMPROVEMENT_PLAN.md)
- [视频流问题修复](./VIDEO_STREAM_COMPLETE_FIX.md)

## 🎯 下一步工作

1. **前端配置界面实现**
   - 添加配置组件
   - 连接API接口
   - 实现实时更新

2. **配置持久化**
   - 考虑将配置保存到数据库
   - 支持配置历史记录

3. **配置验证**
   - 添加配置有效性检查
   - 添加配置变更通知

