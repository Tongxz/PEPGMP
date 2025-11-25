# 系统配置分析文档

## 1. 配置分类概览

### 1.1 系统配置（System Configuration）
系统级配置，影响整个应用的基础运行环境。

### 1.2 检测配置（Detection Configuration）
检测相关的配置，影响检测行为的参数。

---

## 2. 详细配置清单

### 2.1 系统配置（System Configuration）

#### 2.1.1 环境变量配置（必须在系统启动时读取）

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `DATABASE_URL` | 环境变量 | `postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development` | 数据库连接字符串 | ❌ | ✅ |
| `REDIS_URL` | 环境变量 | `redis://:pepgmp_dev_redis@localhost:6379/0` | Redis连接字符串 | ❌ | ✅ |
| `REDIS_HOST` | 环境变量 | `localhost` | Redis主机 | ❌ | ✅ |
| `REDIS_PORT` | 环境变量 | `6379` | Redis端口 | ❌ | ✅ |
| `REDIS_PASSWORD` | 环境变量 | `pepgmp_dev_redis` | Redis密码 | ❌ | ✅ |
| `REDIS_DB` | 环境变量 | `0` | Redis数据库编号 | ❌ | ✅ |
| `ENVIRONMENT` | 环境变量 | `development` | 运行环境（development/staging/production） | ❌ | ✅ |
| `LOG_LEVEL` | 环境变量 | `INFO` | 日志级别 | ❌ | ✅ |
| `HBD_PROFILE` | 环境变量 | `fast` | 检测性能档位 | ❌ | ✅ |

**说明**：
- 这些配置必须在系统启动时读取，因为需要建立数据库和Redis连接
- 不建议存入数据库，因为它们是基础设施配置，需要在数据库连接之前可用

#### 2.1.2 日志配置（系统级）

| 配置项 | 来源 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|------|---------------|-----------|
| 日志目录 | 代码硬编码 | `logs/` | ❌ | ✅ |
| 日志分类 | 代码硬编码 | `detection/`, `api/`, `errors/`, `events/` | ❌ | ✅ |
| 日志轮转大小 | 代码硬编码 | 检测日志100MB，API日志50MB | ❌ | ✅ |
| 日志备份数量 | 代码硬编码 | 检测日志10个，错误日志20个 | ❌ | ✅ |

#### 2.1.3 文件路径配置（系统级）

| 配置项 | 来源 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|------|---------------|-----------|
| `regions_file` | 命令行参数/相机配置 | 区域配置文件路径（如 `config/regions.json`） | ✅ | ✅ |
| 模型文件路径 | YAML/代码默认 | `models/yolo/yolov8n.pt` | ❌ | ✅ |
| 快照存储路径 | 代码硬编码 | `output/snapshots/` | ❌ | ✅ |

---

### 2.2 检测配置（Detection Configuration）

#### 2.2.1 统一检测参数（从 `config/unified_params.yaml` 读取）

**人体检测配置（human_detection）**：

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `confidence_threshold` | YAML | `0.5` | 人体检测置信度阈值 | ✅ | ✅ |
| `iou_threshold` | YAML | `0.5` | IoU阈值 | ✅ | ✅ |
| `min_box_area` | YAML | `100` | 最小检测框面积 | ✅ | ✅ |
| `max_box_ratio` | YAML | `2.0` | 最大检测框宽高比 | ✅ | ✅ |
| `min_width` | YAML | `20` | 最小宽度 | ✅ | ✅ |
| `min_height` | YAML | `20` | 最小高度 | ✅ | ✅ |
| `nms_threshold` | YAML | `0.4` | NMS阈值 | ✅ | ✅ |
| `max_detections` | YAML | `100` | 最大检测数量 | ✅ | ✅ |
| `model_path` | YAML | `models/yolo/yolov8n.pt` | 模型文件路径 | ❌ | ✅ |
| `imgsz` | YAML/CLI | `640` | 输入图像尺寸 | ✅ | ✅ |
| `device` | YAML/CLI/环境变量 | `auto` | 计算设备（cpu/cuda/mps/auto） | ✅ | ✅ |

**发网检测配置（hairnet_detection）**：

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `confidence_threshold` | YAML | `0.65` | 发网检测置信度阈值 | ✅ | ✅ |
| `total_score_threshold` | YAML | `0.5` | 总分阈值 | ✅ | ✅ |
| `model_path` | YAML | `models/hairnet/yolov8_hairnet.pt` | 模型文件路径 | ❌ | ✅ |
| `roi_head_ratio` | YAML | `0.15` | ROI头部比例 | ✅ | ✅ |
| `roi_padding_height_ratio` | YAML | `0.1` | ROI高度填充比例 | ✅ | ✅ |
| `roi_padding_width_ratio` | YAML | `0.05` | ROI宽度填充比例 | ✅ | ✅ |
| `roi_min_size` | YAML | `64` | ROI最小尺寸 | ✅ | ✅ |
| `roi_detection_confidence` | YAML | `0.25` | ROI检测置信度 | ✅ | ✅ |
| `roi_min_positive_confidence` | YAML | `0.3` | ROI最小正例置信度 | ✅ | ✅ |

**行为识别配置（behavior_recognition）**：

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `confidence_threshold` | YAML | `0.6` | 行为识别置信度阈值 | ✅ | ✅ |
| `handwashing_stability_frames` | YAML | `10` | 洗手稳定性帧数 | ✅ | ✅ |
| `sanitizing_stability_frames` | YAML | `5` | 消毒稳定性帧数 | ✅ | ✅ |
| `handwashing_min_duration` | YAML | `3.0` | 洗手最短持续时间（秒） | ✅ | ✅ |
| `sanitizing_min_duration` | YAML | `1.0` | 消毒最短持续时间（秒） | ✅ | ✅ |

**姿态检测配置（pose_detection）**：

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `backend` | YAML | `auto` | 后端（yolov8/mediapipe/auto） | ✅ | ✅ |
| `device` | YAML | `auto` | 计算设备 | ✅ | ✅ |
| `confidence_threshold` | YAML | `0.5` | 姿态检测置信度阈值 | ✅ | ✅ |

**检测规则配置（detection_rules）**：

| 配置项 | 来源 | 默认值 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|--------|------|---------------|-----------|
| `horizontal_move_std` | YAML | `50.0` | 水平移动标准差阈值 | ✅ | ✅ |
| `vertical_move_std` | YAML | `30.0` | 垂直移动标准差阈值 | ✅ | ✅ |

#### 2.2.2 相机配置（Camera Configuration）

**从数据库或 `config/cameras.yaml` 读取**：

| 配置项 | 来源 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|------|---------------|-----------|
| `id` | 数据库/YAML | 相机ID | ✅ | ✅ |
| `name` | 数据库/YAML | 相机名称 | ✅ | ✅ |
| `source` | 数据库/YAML | 视频源（文件路径或摄像头索引） | ✅ | ✅ |
| `location` | 数据库/YAML | 位置信息 | ✅ | ✅ |
| `resolution` | 数据库/YAML | 分辨率 | ✅ | ✅ |
| `fps` | 数据库/YAML | 帧率 | ✅ | ✅ |
| `status` | 数据库/YAML | 状态（active/inactive） | ✅ | ✅ |
| `region_id` | 数据库/YAML | 关联的区域ID | ✅ | ✅ |
| `regions_file` | 数据库/YAML | 区域配置文件路径 | ✅ | ✅ |
| `profile` | 数据库/YAML | 性能档位（fast/balanced/accurate） | ✅ | ✅ |
| `device` | 数据库/YAML | 计算设备（cpu/cuda/mps/auto） | ✅ | ✅ |
| `imgsz` | 数据库/YAML | 输入图像尺寸 | ✅ | ✅ |
| `log_interval` | 数据库/YAML | 检测频率（每N帧检测一次） | ✅ | ✅ |
| `auto_start` | 数据库/YAML | 是否自动启动 | ✅ | ✅ |
| `auto_tune` | 数据库/YAML | 是否自动调优 | ✅ | ✅ |

**说明**：
- 这些配置已经可以存入数据库（通过 `cameras` 表）
- 启动时必须读取，因为需要知道如何启动检测进程

#### 2.2.3 运行时配置（Runtime Configuration）

**检测循环配置（DetectionLoopConfig）**：

| 配置项 | 来源 | 说明 | 是否可存数据库 | 启动时必须 |
|--------|------|------|---------------|-----------|
| `log_interval` | 命令行参数/Redis | 检测频率（每N帧检测一次） | ✅ | ✅ |
| `stream_interval` | 命令行参数/Redis | 视频流推送频率 | ✅ | ✅ |
| `video_quality` | 环境变量 | 视频流质量（1-100） | ✅ | ✅ |
| `stream_width` | 环境变量 | 视频流宽度 | ✅ | ✅ |
| `stream_height` | 环境变量 | 视频流高度 | ✅ | ✅ |

**优先级**：
1. 命令行参数（从相机配置读取）
2. Redis配置（运行时动态更新）
3. 环境变量
4. 默认值

---

## 3. 配置来源和优先级

### 3.1 配置加载顺序

**系统启动时**：
1. 环境变量（`.env`, `.env.local`, `.env.{ENVIRONMENT}`）
2. `config/unified_params.yaml`（统一检测参数）
3. `config/cameras.yaml` 或数据库（相机配置）
4. 命令行参数（启动检测进程时）

**检测进程启动时**：
1. 命令行参数（从相机配置读取）
2. Redis配置（运行时动态更新，每100帧检查一次）
3. `config/unified_params.yaml`
4. 环境变量
5. 代码默认值

### 3.2 配置优先级（从高到低）

1. **命令行参数**（CLI）
2. **Redis配置**（运行时动态更新）
3. **环境变量**
4. **YAML配置文件**（`unified_params.yaml`）
5. **代码默认值**

---

## 4. 配置存储建议

### 4.1 应该存入数据库的配置

✅ **可以存入数据库**：
- 相机配置（id, name, source, location, resolution, fps, status, region_id等）
- 相机元数据（regions_file, profile, device, imgsz, log_interval, auto_start等）
- 检测参数（confidence_threshold, iou_threshold, min_box_area等）- 可作为全局默认值或按相机存储
- 区域配置（通过 `regions` 表）
- 违规规则配置（可以存储在数据库中，当前在代码中硬编码）

❌ **不应该存入数据库**：
- 数据库连接字符串（DATABASE_URL）- 需要先连接数据库
- Redis连接字符串（REDIS_URL）- 需要先连接Redis
- 日志配置（日志路径、轮转设置等）- 系统基础设施
- 模型文件路径 - 静态文件路径
- 环境变量 - 环境相关配置

### 4.2 必须在系统启动时读取的配置

✅ **必须在启动时读取**：
1. **数据库连接配置**（DATABASE_URL等）- 需要建立连接
2. **Redis连接配置**（REDIS_URL等）- 需要建立连接
3. **日志配置**（日志级别、路径等）- 启动时就需要记录日志
4. **相机配置**（source, regions_file等）- 需要知道如何启动检测进程
5. **检测参数**（模型路径、设备等）- 需要初始化检测管线

⏰ **可以延迟读取**：
- 运行时配置（log_interval, stream_interval）- 可以从Redis动态更新
- 部分检测参数 - 可以从数据库读取作为默认值，通过前端API修改

---

## 5. 配置流程图

```
系统启动（API服务）
├── 1. 读取环境变量（.env文件）
│   ├── DATABASE_URL
│   ├── REDIS_URL
│   ├── LOG_LEVEL
│   └── ENVIRONMENT
│
├── 2. 初始化数据库连接
│   └── 读取相机配置（从数据库或cameras.yaml）
│
├── 3. 初始化Redis连接
│   └── 读取运行时配置（可选）
│
└── 4. 初始化检测服务（可选）
    └── 读取 unified_params.yaml

检测进程启动
├── 1. 读取命令行参数（从相机配置）
│   ├── --source (视频源)
│   ├── --camera-id (相机ID)
│   ├── --log-interval (检测频率)
│   ├── --regions-file (区域文件)
│   ├── --profile (性能档位)
│   └── --device (计算设备)
│
├── 2. 读取 unified_params.yaml
│   ├── human_detection
│   ├── hairnet_detection
│   ├── behavior_recognition
│   └── pose_detection
│
├── 3. 从Redis读取运行时配置（启动时和每100帧）
│   └── video_stream:config:{camera_id}
│
└── 4. 初始化检测管线
    └── 使用合并后的配置
```

---

## 6. 当前配置存储状态

### 6.1 已存入数据库
- ✅ 相机配置（`cameras` 表）
- ✅ 区域配置（`regions` 表）
- ✅ 检测记录（`detection_records` 表）
- ✅ 违规记录（`violation_events` 表）

### 6.2 存储在YAML文件
- ✅ 统一检测参数（`config/unified_params.yaml`）
- ✅ 相机配置（`config/cameras.yaml`）- 作为回退

### 6.3 存储在环境变量
- ✅ 数据库连接配置
- ✅ Redis连接配置
- ✅ 日志配置
- ✅ 视频流配置（VIDEO_STREAM_INTERVAL等）

### 6.4 存储在Redis
- ✅ 运行时配置（`video_stream:config:{camera_id}`）
  - `log_interval`
  - `stream_interval`

---

## 7. 优化建议

### 7.1 可以存入数据库的配置
1. **检测参数配置表**：
   - 创建 `detection_configs` 表
   - 存储 `confidence_threshold`, `iou_threshold`, `min_box_area` 等
   - 支持全局默认值和按相机覆盖

2. **违规规则配置表**：
   - 将当前硬编码的违规规则移至数据库
   - 支持动态启用/禁用规则
   - 支持规则优先级配置

### 7.2 不应存入数据库的配置
- 基础设施配置（数据库连接、Redis连接、日志路径等）
- 模型文件路径（静态文件路径）
- 代码默认值（应该在代码中维护）

---

## 8. 配置读取时机总结

| 配置类型 | 读取时机 | 存储位置 | 是否可动态更新 |
|---------|---------|---------|--------------|
| 数据库连接 | API启动时 | 环境变量 | ❌ |
| Redis连接 | API启动时/检测进程启动时 | 环境变量 | ❌ |
| 日志配置 | 系统启动时 | 环境变量/代码 | ❌ |
| 相机配置 | API启动时/检测进程启动时 | 数据库/YAML | ✅（通过API） |
| 统一检测参数 | 检测进程启动时 | YAML | ✅（通过前端API） |
| 运行时配置 | 检测进程运行时 | Redis | ✅（每100帧更新） |
| 区域配置 | 检测进程启动时 | 数据库/JSON文件 | ✅（通过API） |

---

## 9. 关键配置项速查

### 9.1 系统配置（启动时必须）
- `DATABASE_URL` - 数据库连接
- `REDIS_URL` - Redis连接
- `LOG_LEVEL` - 日志级别
- `ENVIRONMENT` - 运行环境

### 9.2 检测配置（启动时必须）
- `source` - 视频源（相机配置）
- `regions_file` - 区域文件（相机配置）
- `log_interval` - 检测频率（相机配置）
- `model_path` - 模型文件路径（unified_params.yaml）
- `device` - 计算设备（相机配置/unified_params.yaml）

### 9.3 检测参数（可以动态调整）
- `confidence_threshold` - 置信度阈值（unified_params.yaml/前端API）
- `iou_threshold` - IoU阈值（unified_params.yaml/前端API）
- `log_interval` - 检测频率（相机配置/Redis）

