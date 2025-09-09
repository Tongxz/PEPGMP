# 人体行为检测系统

一个基于深度学习的人体行为检测系统，专注于工业环境中的安全合规监控，包括发网佩戴检测、洗手行为识别等功能。

## 功能特性

### 核心功能
- **人体检测**: 基于YOLOv8的实时人体检测
- **发网检测**: 专门的CNN模型检测工作人员是否佩戴发网
- **行为识别**: 洗手、消毒等行为的智能识别
- **区域管理**: 支持多区域监控和行为合规检查
- **实时监控**: WebSocket实时数据推送
- **统计分析**: 详细的检测统计和合规率分析

### 技术特性
- **多模态输入**: 支持图像、视频和实时摄像头
- **高性能**: GPU加速推理，支持批量处理
- **可扩展**: 模块化设计，易于添加新的检测功能
- **数据管理**: SQLite数据库存储检测记录和统计信息
- **RESTful API**: 完整的API接口，支持第三方集成

## 技术栈

- **后端**: FastAPI, Python 3.10+
- **AI模型**: YOLOv8 (Ultralytics), PyTorch（支持 MPS/CUDA/CPU 自动选择）
- **数据库**: SQLite
- **前端**: HTML5, CSS3, JavaScript
- **部署**: Docker, Uvicorn
- **测试**: pytest

## 项目结构（更新）

```
.
├── main.py
├── config/
│   ├── unified_params.yaml                 # 统一配置（profiles 深合并 + 设备/流程配置）
│   ├── regions_site_20250902.json          # 站点区域配置（含 meta: 画布/背景/fit_mode）
│   └── ...
├── src/
│   ├── api/
│   │   ├── app.py                          # FastAPI 应用入口
│   │   └── routers/                        # 路由（区域管理/检测/统计等）
│   ├── core/
│   │   ├── optimized_detection_pipeline.py # 人检+发网+姿态/行为 综合管线
│   │   ├── detector.py                     # 人体检测（YOLOv8）
│   │   ├── yolo_hairnet_detector.py        # 发网检测（YOLO）
│   │   ├── pose_detector.py                # 姿态/手部
│   │   ├── region.py                       # 区域/映射（统一映射策略+热更新）
│   │   └── schemas.py                      # 数据结构骨架（UOD 等）
│   ├── services/
│   │   ├── process_engine.py               # 流程状态机 + 规则（发网/顺序/驻留）
│   │   └── region_service.py               # 区域服务（加载/映射/缓存）
│   └── utils/
│       └── logger.py
├── frontend/
│   ├── region_config.html
│   └── region_config.js                    # 保存 meta，支持后端统一映射
├── scripts/
│   └── setup_macos_arm64.sh                # Apple Silicon 一键环境配置（含 MPS）
├── models/
│   └── yolo/*.pt                           # 权重文件
├── docs/
│   └── 流程合规性检测系统方案.md
└── logs/
    └── events_record.jsonl                 # 记录模式事件输出（MVP）
```

## 🏗️ 系统架构

```
├── src/
│   ├── core/           # 核心检测模块
│   │   ├── detector.py     # 人体检测器
│   │   ├── tracker.py      # 多目标追踪
│   │   ├── behavior.py     # 行为识别
│   │   ├── data_manager.py # 数据管理器
│   │   └── region.py       # 区域管理
│   ├── config/         # 配置管理
│   ├── utils/          # 工具函数
│   └── api/            # Web API接口
├── models/             # AI模型文件
├── data/               # 数据目录（存放数据库文件等）
├── logs/               # 日志文件
├── scripts/            # 脚本工具目录
└── config/             # 配置文件
```

### 流程合规（MVP）分层

```
[视频流] → 感知层(人检/发网/姿态) → 统一目标描述(UOD) → 流程状态层(PersonState)
       → 事件判断层(发网准入/流程顺序/驻留时长) → 动作层(抓拍/日志/告警)
```

要点：
- 设备选择自动回退：mps → cuda → cpu（可被 CLI 覆盖）。
- 区域统一映射：优先使用前端 meta（canvas/background/fit），回退 ref_size/自适应。
- 流程规则：
  - 进入“洗手池区域”且未戴发网 → NO_HAIRNET_AT_SINK
  - 从“洗手池区域”直达“工作区区域”（跳过烘干）→ SKIP_DRYING
  - 离开“站立/洗手池/烘干”区域时计算驻留秒数，低于阈值 → INSUFFICIENT_DWELL_TIME
  - 站立区域且“手部关键点”落入洗手池 → HANDWASHING_ACTIVE（持续性）

## 🛠️ 开发环境搭建

### 依赖安装顺序（macOS/CPU 或 Apple Silicon）
1. 先安装 *PyTorch*（官方夜间 CPU 版即可满足 `ultralytics` 依赖）：
   ```bash
   pip install --pre torch torchvision torchaudio \
       --extra-index-url https://download.pytorch.org/whl/nightly/cpu
   ```
   - 如需 GPU/CUDA，请前往 [PyTorch 官网安装向导](https://pytorch.org/get-started/locally/) 选择对应 CUDA 版本。
2. **再安装其他依赖**（包含 `ultralytics`）：
   ```bash
   pip install -r requirements.dev.txt
   ```
   > 提示：若 `pip` 解析器仍报告冲突，可先执行 `pip install ultralytics --no-deps`，再单独安装 `opencv-python` 等依赖。

### 常见安装问题与解决
| 症状 | 根因 | 解决方案 |
|------|------|----------|
| `ResolutionImpossible` 与 `torch` 冲突 | 先安装的 *ultralytics* 触发了对旧版 `torch>=1.7.0` 的解析 | **先装 torch**，或使用 `--no-deps` 安装 *ultralytics* |
| 找不到 `torch` 版本 | macOS 需使用 *nightly CPU* 索引 | 添加 `--extra-index-url https://download.pytorch.org/whl/nightly/cpu` |
| MPS/GPU 不可用 | Apple Silicon 默认 CPU 版 | 升级到 macOS ≥ 12.3 并使用 `--pre` 安装，或改用 CUDA 版 |

> 完整依赖见 `requirements.dev.txt`，生产镜像仍使用根目录 `requirements.txt`。

### 环境脚本

- `scripts/setup_macos_arm64.sh`（Apple Silicon）：安装 PyTorch（MPS 兼容）及依赖，并检测 MPS 可用性。
  ```bash
  bash scripts/setup_macos_arm64.sh
  ```

- `development/start_dev.sh`：开发一键启动（可在启动前导出 `HBD_PROFILE`，脚本可透传至运行命令）
  ```bash
  export HBD_PROFILE=fast   # 或 balanced / accurate
  bash development/start_dev.sh
  ```

> 说明：截图默认保存到 `output/screenshots/`，可用 `HBD_SAVE_DIR=/some/path` 覆盖。

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- CUDA 11.0+ (可选，用于GPU加速)
- 4GB+ RAM
- 摄像头或视频文件

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd human-behavior-detection

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 自训练模型（指引）

- 训练脚本：`scripts/train_hairnet_model.py`（示例，详见训练文档）
- 数据准备：`scripts/prepare_roboflow_dataset.py`、`scripts/add_dataset.py`
- 详细流程与参数请参考：
  - `docs/README_TRAINING.md`
  - `docs/README_HAIRNET_DETECTION.md`

### 基本使用

#### 1. 实时检测模式

```bash
# 使用默认摄像头
python main.py --mode detection --source 0

# 使用视频文件
python main.py --mode detection --source path/to/video.mp4

# 启用调试模式
python main.py --mode detection --source 0 --debug
```

#### 主入口 CLI 参数参考

- `--profile fast|balanced|accurate`：档位（CLI > ENV > YAML）
- `--device cpu|cuda|mps`：指定推理设备（否则按 mps→cuda→cpu 自动选择）
- `--imgsz <int>`：YOLO 输入尺寸（覆盖配置）
- `--human-weights <path>`：YOLO 人体权重（覆盖配置）
- `--cascade-enable`：启用级联二次检测（若配置中未默认开启）
- `--log-interval <int>`：日志限流间隔（帧）

### 自适应档位与设备自适应（Profiles + Device）

> 完整原理与更详细说明见 `docs/自适应档位与设备自适应方案.md`

- 档位（profile）与设备选择优先级：`CLI > 环境变量 > YAML 配置`
  - 环境变量：`HBD_PROFILE=fast|balanced|accurate`，`HBD_DEVICE=cpu|cuda|mps`
  - 设备自动回退顺序：`mps → cuda → cpu`（可被 `--device` 或 `HBD_DEVICE` 强制覆盖）

#### 常用运行示例（CPU 当前设备）

- 快速档（fast，建议先验证链路稳定）
```bash
source venv/bin/activate
python main.py --mode detection \
  --source tests/fixtures/videos/20250724072822_175680.mp4 \
  --profile fast --device cpu --imgsz 512 \
  --human-weights models/yolo/yolov8n.pt --log-interval 120
```

- 准确档（accurate，较慢但更稳）
```bash
source venv/bin/activate
python main.py --mode detection \
  --source tests/fixtures/videos/20250724072822_175680.mp4 \
  --profile accurate --device cpu --imgsz 640 \
  --human-weights models/yolo/yolov8s.pt --log-interval 120
```

> 如迁移到 Apple Silicon（M 系列）并使用 MPS：请设置 `export PYTORCH_ENABLE_MPS_FALLBACK=1`，
> 以便 `torchvision::nms` 在 MPS 不支持时自动回退到 CPU。

### 区域与流程合规（MVP）运行

```bash
source venv/bin/activate
python main.py --mode detection \
  --source tests/fixtures/videos/20250724072708.mp4 \
  --profile accurate --imgsz 640 \
  --regions-file config/regions_site_20250902.json \
  --log-interval 60
```

- 事件输出：`logs/events_record.jsonl`
- 建议：用前端页面 `frontend/region_config.html` 标注并保存区域（自动包含 meta），后端将按帧尺寸统一映射。

#### 级联（Cascade）可选开启

- 在 `config/unified_params.yaml` 的 `profiles.accurate.cascade.enable: true` 或 CLI `--cascade-enable`
- 可通过配置控制触发条件：`cascade.trigger_confidence_range: [0.4, 0.6]`、可选 `cascade.trigger_roi`
- 运行中日志会统计：级联触发次数、细化数与累计耗时

#### 2. API服务模式

```bash
# 启动API服务器
python main.py --mode api --port 5000

# 自定义主机和端口
python main.py --mode api --host 0.0.0.0 --port 8080
```

#### 3. 演示模式

```bash
# 运行演示
python main.py --mode demo
```

## 📋 配置说明

### 系统配置

主要生效的配置文件位于 `config/` 目录：

- `unified_params.yaml`：统一参数（profiles 深合并、设备、runtime、cascade、process/region_names 等）
- `regions_site_*.json`：站点区域配置（含 meta：canvas/background/fit_mode 或 ref_size）
- （可选规划）`cameras.yaml`：摄像头配置，配合前端配置页使用（见“摄像头配置可视化”）

### 配置片段示例（仅示意，实际以 unified_params.yaml 为准）

```yaml
inference:
  profile: accurate

human_detection:
  model_path: models/yolo/yolov8s.pt
  imgsz: 640
  confidence_threshold: 0.5
  max_detections: 20

process:
  enable: true
  min_dwell_seconds:
    stand: 3
    sink: 3
    dryer: 3
  cooldown_seconds: 10
  region_names:
    entrance: "入口线"
    stand: "洗手站立区域"
    sink: "洗手水池"
    dryer: "烘干区域"
    work: "车间入口"
```

### 统一参数（unified_params.yaml）与 Profiles 深合并

- 基础 + profiles[profile] 深合并 + CLI/ENV 覆盖（优先级：CLI > ENV > YAML）
- 关键块：`inference`、`runtime`、`cascade`、`profiles`

```yaml
# --- 基础配置 ---
inference:
  profile: fast

human_detection:
  model_path: models/yolo/yolov8n.pt
  imgsz: 512
  confidence_threshold: 0.4
  max_detections: 10

runtime:
  frame_skip: 1
  osd_minimal: true
  log_interval: 120

cascade:
  enable: false
  heavy_weights: null
  trigger_confidence_range: null  # 例如 [0.4, 0.6]
  trigger_roi: null               # 例如 [[x1,y1],[x2,y2],...]

# --- 档位覆盖 ---
profiles:
  fast: {}

  balanced:
    human_detection:
      model_path: models/yolo/yolov8s.pt
      imgsz: 640
      confidence_threshold: 0.5
    runtime:
      frame_skip: 0

  accurate:
    human_detection:
      model_path: models/yolo/yolov8m.pt
      max_detections: 20
    runtime:
      osd_minimal: false
    cascade:
      enable: true
      heavy_weights: models/yolo/yolov8l.pt
      trigger_confidence_range: [0.4, 0.6]
```

### HANDWASHING_ACTIVE 参数与调优（新增）

- 判定逻辑（代码）：
  - `main.py`（检测循环）：为每个行人检测手部关键点（landmarks），统计关键点是否落入“洗手水池”多边形；生成 `hand_in_sink` 并写入 UOD。
  - `src/services/process_engine.py`：人在 `process.region_names.stand` 且 `hand_in_sink=True` 时，触发 `HANDWASHING_ACTIVE`（带冷却）。
- 关键阈值（默认）：
  - 至少 3 个关键点在池内，且比例 ≥ 0.2（`pts_inside >= 3 && pts_inside/pts_total >= 0.2`）。
  - 可在代码中快速调整：`main.py` UOD 生成处（hand_in_sink 计算）。
- 配置关联：
  - `config/unified_params.yaml.process.region_names`：`stand`（洗手站立区域）、`sink`（洗手水池）。
  - `process.cooldown_seconds`：事件冷却时间，避免频繁重复。
- 调参建议：
  - 提高召回：降低为 `pts_inside >= 2`、比例 `≥ 0.1`；或仅统计“指尖”子集。
  - 提高稳定：加入“连续 N 帧”为真再触发（在 `ProcessEngine` 内部做状态平滑）。
  - 排查调试：在日志中打印 `pts_inside/pts_total` 与区域命中名称；必要时放宽区域多边形。

### UOD 统一目标描述（已接入）

- 数据结构：`src/core/schemas.py::UODPerson`
  - `track_id: int`
  - `bbox: [x1,y1,x2,y2]`
  - `confidence: float`
  - `has_hairnet: bool`
  - `hairnet_confidence: float`
  - `hand_regions: list[dict] | None`（可能包含手部 landmarks）
  - `region: str | None`
  - `hand_in_sink: bool | None`（基于手部关键点与“洗手水池”多边形计算）
  - `ts: float | None`
- 工程用法：`main.py` 以 dataclass 生成后 `.to_dict()` 传入 `ProcessEngine`。

## 🔧 API接口

### 健康检查

```bash
GET /health
```

### 检测接口

```bash
# 上传图片检测
POST /api/v1/detection/image
Content-Type: multipart/form-data

# 实时视频流检测
WS /api/v1/detection/stream
```

### 配置与区域管理（API 路由与示例）

- 兼容路由（前端保存区域使用）
  - 保存区域（含 meta）：
    ```bash
    POST /api/regions
    Content-Type: application/json
    {
      "regions": [ { ... } ],
      "meta": { "canvas_size": {"width":800,"height":450}, "background_size": {"width":1920,"height":1080}, "fit_mode": "contain" }
    }
    ```
  - 读取区域：
    ```bash
    GET /api/regions
    ```

- 新版区域管理（建议）
  - 保存区域：
    ```bash
    POST /api/v1/management/regions
    ```
  - 更新 meta：
    ```bash
    POST /api/v1/management/regions/meta
    {"canvas_size":{...},"background_size":{...},"fit_mode":"contain","ref_size":"640x480"}
    ```
  - 列出区域：
    ```bash
    GET /api/v1/management/regions
    ```

- 综合检测（示例，具体参数以代码为准）
  ```bash
  POST /api/v1/detect/comprehensive
  Content-Type: multipart/form-data  # 支持图像/小视频
  ```

- 统计与下载
  ```bash
  GET /api/v1/statistics/summary
  GET /api/v1/download/overlay?video=...  # 叠加区域可视化（若实现）
  ```

### 统计汇总与监控（新增）

- 事件统计汇总（最近 N 分钟聚合）：
  ```bash
  GET /api/v1/statistics/summary?minutes=60&limit=1000
  ```
  - 返回字段：window_minutes、total_events、counts_by_type、samples

- Prometheus 监控端点（文本）：
  ```
  GET /metrics
  ```
  - 输出示例：
    - `hbd_events_total{type="NO_HAIRNET_AT_SINK"} 12`
    - `hbd_events_total 34`

### 事件查询（新增）

- 最近事件：
  ```bash
  GET /api/v1/events/recent?limit=100&minutes=60&etype=NO_HAIRNET_AT_SINK
  ```
  - 数据来源：`logs/events_record.jsonl`
  - 可选过滤：时间窗口（minutes）、事件类型（etype）

### WebSocket 事件推送（新增）

- 实时订阅：
  ```
  WS /ws/events?etype=NO_HAIRNET_AT_SINK  # 可选 etype 过滤
  ```
  - 消息格式：
    - 事件：`{"type":"event","data":{...}}`
    - 心跳：`{"type":"ping"}`（每 ~0.5s）
  - 数据源：尾随 `logs/events_record.jsonl`，有新事件即推送

- WebSocket（实时）
  ```bash
  WS /ws
  # 消息中可包含: 检测框、区域命中、级联统计、(未来) 事件
  ```

## 🎮 开发指南

### 项目结构

```
src/
├── core/               # 核心功能模块
│   ├── __init__.py
│   ├── detector.py     # 人体检测
│   ├── tracker.py      # 目标追踪
│   ├── behavior.py     # 行为识别
│   └── region.py       # 区域管理
├── config/             # 配置管理
│   ├── __init__.py
│   ├── unified_params.py  # 统一参数加载与深合并
│   ├── model_config.py    # 设备选择（mps→cuda→cpu）
│   └── (cameras.yaml)     # 摄像头配置（规划，可选）
├── utils/              # 工具函数
│   ├── __init__.py
│   ├── logger.py       # 日志工具
│   ├── image_utils.py  # 图像处理
│   ├── video_utils.py  # 视频处理
│   ├── math_utils.py   # 数学工具
│   └── file_utils.py   # 文件工具
└── api/                # Web API
    ├── __init__.py
    ├── app.py          # FastAPI 应用
    └── routers/        # 路由定义（FastAPI）
```

### 添加新的行为检测

1. 在 `src/core/behavior.py` 中添加新的行为类型
2. 实现对应的检测逻辑
3. 更新配置文件
4. 添加相应的测试

### 自定义检测区域

1. 使用 `RegionManager` 类管理检测区域
2. 配置区域类型和规则
3. 设置行为合规性检查

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_detector.py

# 生成覆盖率报告
pytest --cov=src tests/
```

## 🛠️ 脚本工具

项目中的脚本工具位于 `scripts/` 目录下，用于辅助开发、测试和维护工作。

### 主要脚本工具

#### 项目清理工具

```bash
# 清理项目根目录，移动脚本文件到scripts目录，移动数据库文件到data目录
python scripts/cleanup_tests.py
```

`cleanup_tests.py` 脚本用于：
- 删除已整理到tests目录的根目录测试文件
- 删除不必要的测试图像文件
- 将脚本文件从根目录移动到scripts目录
- 将数据库文件从根目录移动到data目录

#### 其他工具脚本

- `analyze_detection_parameters.py`: 分析检测参数
- `debug_detection_parameters.py`: 调试检测参数
- `enhanced_roi_visualizer.py`: 增强ROI可视化
- `improved_head_roi.py`: 改进头部ROI提取
- `view_enhanced_results.py`: 查看增强结果
- `view_improved_roi.py`: 查看改进的ROI
- `view_roi_results.py`: 查看ROI结果
- `visualize_roi.py`: ROI可视化

## 📊 性能优化

### GPU加速

确保安装了CUDA版本的PyTorch：

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 模型优化

- 使用TensorRT进行模型加速
- 调整输入分辨率平衡精度和速度
- 启用多线程处理

## 🐛 故障排除

### 常见问题

1. **摄像头无法打开**
   - 检查摄像头权限
   - 确认摄像头索引正确
   - 尝试不同的摄像头索引

2. **模型加载失败**
   - 检查模型文件路径
   - 确认模型文件完整性
   - 检查CUDA环境配置

3. **检测精度低**
   - 调整置信度阈值
   - 检查光照条件
   - 考虑重新训练模型

4. **XGBoost 无法加载（洗手 ML 分类器未启用）**
   - 症状：`libxgboost.dylib` 加载失败，提示缺少 `libomp.dylib`
   - 解决：
     - Intel Mac：
       ```bash
       brew install libomp
       export DYLD_LIBRARY_PATH="/usr/local/opt/libomp/lib:$DYLD_LIBRARY_PATH"
       ```
     - Apple Silicon：
       ```bash
       brew install libomp
       export DYLD_LIBRARY_PATH="/opt/homebrew/opt/libomp/lib:$DYLD_LIBRARY_PATH"
       ```
     - 将 `export DYLD_LIBRARY_PATH=...` 写入启动脚本或 shell 配置以持久化。

5. **MPS 上 YOLO 报错 `torchvision::nms` 未实现**
   - 说明：MPS 部分算子暂不支持，可开启 CPU 回退
   - 解决：运行前设置 `export PYTORCH_ENABLE_MPS_FALLBACK=1`

---

## 📦 部署与多路接入（新增）

### 部署方式（推荐顺序）

- 本机/边缘一体部署（建议）
  - 拓扑：1 个 API（用于前端配置/可视化）+ N 个检测进程（每路摄像头各 1 进程）
  - 启动 API（静态前端挂载 /frontend）：
    ```bash
    source venv/bin/activate
    nohup python main.py --mode api --port 8000 --log-level INFO > logs/api.log 2>&1 &
    ```
  - 启动检测进程（USB 摄像头示例）：
    ```bash
    # 摄像头1（索引 0）
    nohup python main.py --mode detection --source 0 --profile accurate --imgsz 640 \
      --regions-file config/regions_site_20250902.json --log-interval 120 \
      > logs/detect_cam0.log 2>&1 &

    # 摄像头2（索引 1）
    nohup python main.py --mode detection --source 1 --profile accurate --imgsz 640 \
      --regions-file config/regions_site_20250902.json --log-interval 120 \
      > logs/detect_cam1.log 2>&1 &
    ```
  - 启动检测进程（RTSP 摄像头）：
    ```bash
    nohup python main.py --mode detection --source rtsp://user:pass@ip:554/stream \
      --profile accurate --imgsz 640 --regions-file config/regions_site_20250902.json \
      --log-interval 120 > logs/detect_rtsp1.log 2>&1 &
    ```
  - 目录持久化：日志 `logs/`、事件记录 `logs/events_record.jsonl`；后续引入抓拍后，输出到 `output/`

- Docker / Compose（可选）
  - 结构：1 个 API 容器 + N 个检测容器（各自绑定视频源/RTSP）
  - 映射卷：`config/`、`models/`、`logs/`、`output/`
  - GPU：NVIDIA 需 `--gpus all`；Apple Silicon 建议本机运行推理（MPS）以获得更好兼容性

- systemd（长期运维）
  - 为 `api.service` 与 `detect@.service` 写单元文件，设置自动拉起、重启策略与日志轮转

### 硬件与性能建议

- 单路 720p@15–20fps（YOLOv8n：人检+发网，规则引擎）
  - Apple Silicon M1/M2 8GB+ 足够；事件抓拍建议 SSD/NVMe
- 双路 720p 或单路 1080p
  - Apple Silicon 16GB 更稳；或 x86_64 + RTX 2060/3060 级别
- 多路（≥3）
  - 推荐 GPU（RTX 3060+/A2000+）或多机分担
- 依赖环境
  - macOS（MPS）：`export PYTORCH_ENABLE_MPS_FALLBACK=1`
  - 安装 OpenCV/FFmpeg，RTSP 解码更稳定

### 两路摄像头接入（最佳实践）

- 每路“独立检测进程”最稳（互不影响、易扩缩容）
- 区域配置共用同一站点文件（`--regions-file config/regions_site_*.json`）
- 区域标注一次，多路共享；若视角不同，分别保存站点文件并在命令行指定
- API 一个端口即可；检测模式本身不占用端口

### 摄像头配置可视化（已实现-基础版）

- 前端：`frontend/camera_config.html`（列表/创建/更新/删除），直接对接后端 `cameras` 路由
- 后端：`/api/v1/cameras`（GET/POST/PUT/DELETE）
- 持久化：`config/cameras.yaml`（原子写入）
- 访问方式：启动 API 后打开 `http://127.0.0.1:8000/frontend/camera_config.html`
- 后续增强：预览与“一键拉起检测进程”（规划）

### 摄像头与运行调优

- USB（macOS）：优先 `cv2.CAP_AVFOUNDATION`，系统“隐私与安全”允许摄像头权限
- RTSP：固定分辨率/码率/帧率；弱网场景降低 fps/码率
- 性能：合理选择 `--imgsz`（512/640）、开启 `runtime.frame_skip`，选择合适 profile
- 事件排查：若无事件，多为区域未命中或未发生“离开”；在前端适度放大多边形，并用“进入又离开”的短片回放验证

---

## 🎯 跟踪器选择与切换（现状）

- 现状：默认使用 `src/core/tracker.py::MultiObjectTracker`（IoU/中心距离 + 匈牙利/贪心），遮挡/多目标下更稳。
- 指引：在综合管线之后、UOD 之前，将人检框输入 MultiObjectTracker，使用返回的稳定 `track_id` 进入区域判定与流程引擎。

---

## 📸 抓拍动作层（capture_service）规划

- 目标：对 `ProcessEngine` 产出的事件进行图片抓拍 + 短片段导出 + 元数据落盘（匿名化、冷却可共用引擎策略）。
- 现状：已实现图片+裁剪+元数据（输出 `output/captures/<event_id>/`），片段支持前段（pre_seconds），可按需开启后段与拼接。
- 建议目录结构：
```
output/
  violations/
    no_hairnet/
    skip_drying/
    insufficient_dwell/
  clips/
    <event_id>.mp4
  meta/
    <event_id>.json
```
- 元数据示例：
```json
{
  "event_id": "20250905T114437Z_000123",
  "type": "NO_HAIRNET_AT_SINK",
  "ts": 1757044477.336,
  "track_id": 7,
  "regions": ["入口线", "洗手池区域"],
  "person_bbox": [x1, y1, x2, y2],
  "has_hairnet": false,
  "dwell_seconds": 1.2,
  "uod_snapshot": {"persons": [...]},
  "source": {"video": "tests/fixtures/videos/20250724072822_175680.mp4", "frame": 348}
}
```
- 匿名化：默认对头像/面部区域进行模糊；可在 `unified_params.yaml` 增加开关与模糊强度。

---

## 🎛️ 摄像头配置可视化（接口草案）

- 目标：在前端配置 USB/RTSP 摄像头，保存到 `config/cameras.yaml`，并提供预览与进程拉起。
- 数据结构（cameras.yaml）：
```yaml
cameras:
  - id: cam0
    name: 大门口 USB0
    source: 0           # USB 索引 或 rtsp://...
    resolution: 1280x720
    fps: 20
    regions_file: config/regions_site_gate.json
  - id: cam1
    name: 洗手间 RTSP1
    source: rtsp://user:pass@ip:554/stream
    resolution: 1280x720
    fps: 20
    regions_file: config/regions_site_sink.json
```
- API（建议）：
```bash
GET  /api/v1/cameras            # 列表
POST /api/v1/cameras            # 新增
PUT  /api/v1/cameras/{id}       # 更新
DEL  /api/v1/cameras/{id}       # 删除
POST /api/v1/cameras/{id}/preview  # 可选：生成 snapshot/mjpeg
```
- 前端：`frontend/camera_config.html`（表单 + 预览 + 保存）；保存后写入 `cameras.yaml`。

---

## 🗂️ 多路摄像头与区域文件映射示例

- 不同视角需不同站点区域文件：
```bash
# 大门口摄像头（USB0）
nohup python main.py --mode detection --source 0 --profile accurate --imgsz 640 \
  --regions-file config/regions_site_gate.json --log-interval 120 \
  > logs/detect_gate.log 2>&1 &

# 洗手池摄像头（RTSP）
nohup python main.py --mode detection --source rtsp://user:pass@ip:554/stream \
  --profile accurate --imgsz 640 \
  --regions-file config/regions_site_sink.json --log-interval 120 \
  > logs/detect_sink.log 2>&1 &
```

---

## 🔁 RTSP 健壮性与重连建议

- 固定编码参数：分辨率/码率/帧率，避免动态变化导致解析失败。
- 解码库：安装 FFmpeg/OpenCV 完整编解码支持。
- 重连策略（建议在代码中实现）：
  - 超时失败 → 指数退避（1s, 2s, 4s, ... 上限 30s）
  - 连续失败 N 次后告警并降级（降低 fps/分辨率）。
- 缓冲调优：根据网络质量调整接收缓冲区与读帧超时。

---

## 🧩 systemd 与 docker-compose 模板

### systemd（示例）

`/etc/systemd/system/hbd-api.service`
```
[Unit]
Description=HBD API Service
After=network.target

[Service]
WorkingDirectory=/opt/hbd
Environment=PYTORCH_ENABLE_MPS_FALLBACK=1
ExecStart=/opt/hbd/venv/bin/python main.py --mode api --port 8000 --log-level INFO
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/hbd-detect@.service`
```
[Unit]
Description=HBD Detect Service (%i)
After=network.target

[Service]
WorkingDirectory=/opt/hbd
Environment=PYTORCH_ENABLE_MPS_FALLBACK=1
ExecStart=/opt/hbd/venv/bin/python main.py --mode detection --source %i --profile accurate --imgsz 640 --regions-file /opt/hbd/config/regions_site_20250902.json --log-interval 120
Restart=always

[Install]
WantedBy=multi-user.target
```

### docker-compose（简化示例）

```yaml
version: "3.8"
services:
  api:
    image: hbd:latest
    command: ["python","main.py","--mode","api","--port","8000"]
    ports: ["8000:8000"]
    volumes:
      - ./config:/app/config
      - ./models:/app/models
      - ./logs:/app/logs
      - ./frontend:/app/frontend
  detect_cam0:
    image: hbd:latest
    command: ["python","main.py","--mode","detection","--source","0","--profile","accurate","--imgsz","640","--regions-file","config/regions_site_20250902.json"]
    volumes:
      - ./config:/app/config
      - ./models:/app/models
      - ./logs:/app/logs
```

---

## 📈 监控与 KPI 建议

- 性能指标：
  - 人检/发网/后处理耗时、端到端 FPS、缓存命中率、级联触发/细化次数
- 业务指标：
  - 事件数量/类型、重复率、无效率（误报/漏报估计）
- 采集方式：
  - 日志 JSON 行（jsonl）或 Prometheus 导出（可选）
  - 周期性汇总脚本：统计 `events_record.jsonl` 并输出日报

---

## 🔒 隐私与数据治理

- 匿名化：抓拍默认对人脸或上部区域模糊处理；配置项在 `unified_params.yaml`（建议新增）。
- 数据保留：
  - 事件图片/片段保留周期（如 30/90 天），周期性清理脚本
  - 元数据最小化存储（仅保留必要字段）
- 访问控制：限制输出目录权限；脱敏数据用于训练/评测。

### 清理脚本（新增）

```bash
# 预览将删除的内容（早于 30 天）
python scripts/cleanup_output.py --days 30 --dry-run

# 实际执行删除（早于 14 天）
python scripts/cleanup_output.py --days 14 --yes

# 自定义清理路径
python scripts/cleanup_output.py --days 7 --yes --paths output/captures logs
```

## 📝 更新日志

---

## ✅ 方案对照与完成度

- 感知与设备
  - 设备选择 mps→cuda→cpu 自动回退（CLI 可覆盖）：已完成
  - 人体检测/发网检测/姿态模块接入与综合管线：已完成（姿态为可选）
  - 级联策略（低置信度触发重检）：已完成（可按配置开启）

- 区域与映射
  - 前端区域标注并保存 meta（canvas/background/fit）：已完成
  - 统一坐标映射（meta 优先→ref_size→自适应）与热更新：已完成
  - 区域命中优化（AABB 预过滤 + 中心点优先）：已完成

- 流程合规（MVP）
  - 状态机/规则引擎骨架（`ProcessEngine/PersonState`）：已完成
  - 规则1 发网准入（进入洗手池未戴发网即违规）：已完成
  - 规则2 流程顺序（洗手→烘干→工作区，跳过烘干即违规）：已完成
  - 规则3 驻留时长（站立/洗手池/烘干离开时计算，不足即违规）：已完成
  - 事件冷却/进入-离开-驻留日志：已完成
  - 记录模式（jsonl 输出）：已完成

- 跟踪与 UOD
  - 简易中心点最近邻分配 `track_id`：已完成（临时方案）
  - 切换 `MultiObjectTracker` 稳定跟踪：已完成
  - UOD dataclass 强类型化（替代 dict）：已完成

- 动作层与事件输出
  - 抓拍服务 `capture_service`（图片+片段+meta，匿名化+冷却）：已完成（输出至 `output/captures/`）
  - 事件查询 API `/api/v1/events/recent` 与 WS 推送 `events`：已完成

- 配置与可视化
  - 统一配置 `unified_params.yaml`（profiles 深合并/设备/流程）：已完成
  - 站点区域文件 `regions_site_*.json` 并通过 `--regions-file` 注入：已完成
  - 摄像头配置可视化（`camera_config.html` + `cameras.yaml` + CRUD）：已完成（基础版）

- 部署与运维
  - 一机多进程（1×API + N×检测）部署指引：已完成
  - systemd/docker-compose 模板（文档）：已完成（示例已提供）
  - RTSP 健壮性与重连策略：已完成（已实现指数退避重连）
  - 监控与 KPI（性能/业务指标采集与看板）：未完成（README 已提供建议）
  - 隐私与数据治理（匿名化、保留与清理脚本）：未完成（README 已提供建议）

- 测试
  - 流程规则单元/集成/端到端用例：未完成

> 说明：标注“未完成”的项均已在 README 给出落地指引/接口草案，可按优先级 P0→P1→P2 逐步实现。

### v1.0.0 (2024-01-XX)

- ✨ 初始版本发布
- 🎯 基础人体检测功能
- 🔄 多目标追踪系统
- 🎭 行为识别模块
- 🌐 Web API接口
- 📊 实时监控界面

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目链接: [GitHub Repository]
- 问题反馈: [GitHub Issues]
- 邮箱: [your-email@example.com]

## 🙏 致谢

- [YOLOv8](https://github.com/ultralytics/ultralytics) - 目标检测框架
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [PyTorch](https://pytorch.org/) - 深度学习框架
