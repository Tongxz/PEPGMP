# 人体行为检测系统

一个基于深度学习的实时人体行为检测系统，专注于工业环境中的安全合规监控，包括发网佩戴、洗手等行为的智能识别与分析。

## 核心功能

- **多目标实时检测**: 基于YOLOv8的高性能人体检测。
- **多行为复合识别**: 支持发网佩戴、洗手、手部消毒等多种行为的复合检测。
- **可配置区域管理**: 支持自定义多边形监控区域，并对区域内的目标进行独立分析。
- **流程合规性分析**: 内置状态机引擎，可对“进入-洗手-烘干-离开”等流程进行合规性判断。
- **灵活的部署模式**: 支持单一视频源检测、多摄像头集中管理的 Supervisor 模式以及提供完整能力的 API 服务模式。
- **Web 可视化界面**: 提供用于实时监控、统计分析和系统配置的Web前端界面。

## 技术栈

- **后端**: FastAPI, Python 3.10+
- **AI 框架**: PyTorch, Ultralytics (YOLOv8)
- **API 服务**: Uvicorn
- **前端**: Vanilla JavaScript, HTML5, CSS
- **测试**: Pytest

## 项目结构

经过重构后，项目采用了更清晰、模块化的目录结构：

```
.
├── main.py                   # 唯一的项目主入口
├── config/
│   └── unified_params.yaml   # 用户的主要配置文件
├── data/                     # 存放原始数据 (视频, 标注等)
├── docs/
│   └── reference/            # 存放参考配置文件
├── examples/                 # 存放如何使用核心模块的示例代码
├── frontend/                 # 核心前端应用
│   ├── index.html
│   └── dev/                  # 前端开发者调试工具
├── models/                   # 存放模型权重文件
├── scripts/                  # 存放所有辅助脚本
│   ├── ci/
│   ├── data/
│   ├── development/
│   ├── maintenance/
│   ├── optimization/
│   └── training/
├── src/                      # 核心源代码
│   ├── api/                  # FastAPI 应用与路由
│   ├── config/               # 配置加载与解析逻辑
│   ├── core/                 # 核心业务逻辑 (管线, 追踪器, 状态机等)
│   ├── detection/            # 所有具体的检测器实现
│   ├── services/             # 高层业务服务
│   └── utils/                # 通用工具模块
└── tests/                    # 自动化测试
```

## 快速开始

### 1. 环境准备

- Python 3.10+
- `git`

### 2. 安装与设置

我们提供了自动化脚本来完成所有环境设置和依赖安装。

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd <repository-name>

# 2. 运行设置脚本 (二选一)

# 对于 macOS (Apple Silicon 或 Intel)
bash scripts/setup_macos_arm64.sh

# 对于 Linux 或其他环境
bash scripts/setup_dev.sh
```
该脚本会自动创建Python虚拟环境 (`venv/`) 并安装所有必要的依赖。

### 3. 激活环境

安装完成后，激活虚拟环境以使用项目依赖：
```bash
source venv/bin/activate
```

## 如何运行

项目通过唯一的入口文件 `main.py` 启动，并通过 `--mode` 参数选择不同的运行模式。

### 模式一：视频/摄像头检测

直接对视频文件或摄像头进行检测，并在窗口中实时显示结果。

```bash
# 使用默认摄像头 (索引为0)
python main.py --mode detection --source 0

# 使用视频文件
python main.py --mode detection --source path/to/your/video.mp4

# 使用不同的性能档位 (fast, balanced, accurate)
python main.py --mode detection --source 0 --profile accurate
```

### 模式二：API 服务

启动后端API服务，并提供Web前端界面。

```bash
# 启动API服务器 (默认在 8000 端口)
python main.py --mode api

# 启动后，在浏览器中打开以下地址:
# - 主界面: http://127.0.0.1:8000/frontend/index.html
# - 摄像头配置: http://127.0.0.1:8000/frontend/camera_config.html
# - API 文档: http://127.0.0.1:8000/docs
```

### 模式三：多路摄像头监控

此模式会读取 `config/cameras.yaml` 文件，并为其中定义的每一路视频源启动一个独立的检测进程。

```bash
# 启动 supervisor 来管理所有摄像头
python main.py --mode supervisor
```

## 配置管理

项目的核心配置由 `config/unified_params.yaml` 文件管理。系统采用**代码默认值 + YAML文件覆盖**的模式，您只需在此文件中修改需要调整的参数即可。

## 运行测试

我们使用 `pytest` 进行自动化测试。在激活虚拟环境后，运行以下命令来验证项目在重构后是否功能完好：

```bash
pytest
```

## 贡献指南

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 `LICENSE` 文件。