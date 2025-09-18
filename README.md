# 人体行为检测系统 🚀

一个基于深度学习的企业级实时人体行为检测系统，专注于工业环境中的安全合规监控。支持发网佩戴、洗手行为等智能识别与分析，具备完整的监控、告警和安全防护能力。

## ✨ 核心功能

### 🔍 智能检测
- **多目标实时检测**: 基于YOLOv8的高性能人体检测，支持GPU加速
- **多行为复合识别**: 发网佩戴、洗手、手部消毒等多种行为的复合检测
- **姿态分析**: 基于MediaPipe和YOLOv8的高精度姿态检测
- **运动分析**: 智能运动轨迹分析和行为模式识别

### 🎯 区域管理
- **可配置区域管理**: 支持自定义多边形监控区域
- **智能ROI提取**: 增强的头部ROI提取算法
- **流程合规性分析**: 内置状态机引擎，支持完整的"进入-洗手-烘干-离开"流程分析

### 🖥️ 部署模式
- **单一视频源检测**: 支持摄像头和视频文件检测
- **多摄像头集中管理**: Supervisor模式集中管理多路视频源
- **API服务模式**: 完整的REST API和Web界面
- **容器化部署**: Docker和Kubernetes支持

### 🛡️ 安全与监控
- **统一安全管理**: JWT认证、访问控制、威胁检测
- **实时监控**: 系统性能、检测指标、错误追踪
- **智能告警**: 多渠道告警通知（邮件、Webhook、日志）
- **安全中间件**: CSRF保护、内容安全策略、速率限制

### ⚡ 性能优化
- **GPU加速**: CUDA、Metal Performance Shaders (MPS) 支持
- **批处理优化**: 智能批量处理和内存管理
- **异步处理**: 高并发异步检测管道
- **智能缓存**: 多级缓存和结果优化

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI, Python 3.10+
- **AI引擎**: PyTorch, Ultralytics (YOLOv8), MediaPipe
- **数据库**: SQLite (开发), PostgreSQL (生产)
- **缓存**: Redis
- **监控**: Prometheus, Grafana
- **日志**: 结构化JSON日志

### 前端技术栈
- **核心**: Vanilla JavaScript, HTML5, CSS3
- **UI组件**: 响应式设计，现代化界面
- **实时通信**: WebSocket支持
- **可视化**: 实时图表和监控面板

### 基础设施
- **容器化**: Docker, Docker Compose
- **编排**: Kubernetes
- **CI/CD**: GitHub Actions, GitLab CI
- **安全**: TLS/SSL, 私有CA证书

## 📁 项目结构

经过全面重构的企业级项目结构：

```
.
├── main.py                      # 🚪 唯一的项目主入口
├── config/                      # ⚙️ 配置文件
│   ├── unified_params.yaml      # 主配置文件
│   ├── regions.json             # 区域配置
│   └── user_profiles/           # 用户配置
├── src/                         # 📚 核心源代码
│   ├── api/                     # 🌐 FastAPI应用
│   │   ├── routers/             # API路由
│   │   └── middleware/          # 安全中间件
│   ├── core/                    # 🧠 核心业务逻辑
│   ├── detection/               # 🔍 检测器实现
│   ├── services/                # 🔧 业务服务
│   ├── utils/                   # 🛠️ 工具模块
│   ├── monitoring/              # 📊 监控系统
│   ├── security/                # 🛡️ 安全管理
│   └── architecture/            # 🏛️ 架构组件
├── frontend/                    # 🖥️ Web前端
├── models/                      # 🤖 AI模型文件
├── scripts/                     # 📜 自动化脚本
│   ├── performance/             # 性能优化
│   ├── maintenance/             # 维护工具
│   └── deployment/              # 部署脚本
├── docs/                        # 📖 文档
├── tests/                       # 🧪 自动化测试
├── docker-compose.yml           # 🐳 容器编排
└── requirements.txt             # 📦 依赖列表
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.10+
- **系统**: macOS, Linux, Windows
- **GPU**: NVIDIA (CUDA), Apple Silicon (MPS) - 可选
- **内存**: 建议8GB+
- **存储**: 建议20GB+

### 一键安装

#### 快速开始（推荐）

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd <repository-name>

# 2. 创建虚拟环境并安装所有依赖
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装所有依赖（开发+生产）
pip install -e ".[dev,production]"

# 4. 启动服务
python main.py --mode api
```

#### 自动化安装脚本

```bash
# 1. 克隆项目
git clone <your-repository-url>
cd <repository-name>

# 2. 选择安装脚本
# macOS (Apple Silicon/Intel)
bash scripts/setup_macos_arm64.sh

# Linux/Unix
bash scripts/setup_dev.sh

# Windows (PowerShell)
./scripts/setup_windows.ps1
```

### 手动安装

#### 方式一：使用 pyproject.toml（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装基础依赖
pip install -e .

# 安装开发环境依赖（包含测试、代码质量工具）
pip install -e ".[dev]"

# 安装生产环境依赖（包含监控、性能优化）
pip install -e ".[production]"

# 安装所有依赖（开发+生产）
pip install -e ".[dev,production]"
```

#### 方式二：使用传统 requirements 文件

```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装基础依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements.dev.txt
```

#### 依赖说明

- **基础依赖**: 核心功能所需的最小依赖集
- **开发依赖**: 测试框架、代码质量工具、文档生成
- **生产依赖**: 监控、性能优化、安全增强功能

#### 新增功能依赖

系统已集成以下企业级功能，相关依赖已自动包含：

- **安全模块**: `PyJWT`, `cryptography`, `python-jose`, `passlib`
- **监控模块**: `prometheus-client`, `structlog`, `sentry-sdk`
- **架构组件**: 依赖注入、事件系统、插件系统
- **错误处理**: 统一错误处理和恢复机制

### 📦 依赖管理

项目采用现代化的依赖管理方式，支持多种安装模式：

#### 依赖分组

| 分组 | 命令 | 包含内容 | 适用场景 |
|------|------|----------|----------|
| **基础** | `pip install -e .` | 核心功能依赖 | 最小化部署 |
| **开发** | `pip install -e ".[dev]"` | 测试、代码质量、文档 | 开发环境 |
| **生产** | `pip install -e ".[production]"` | 监控、性能、安全 | 生产环境 |
| **全部** | `pip install -e ".[dev,production]"` | 所有功能 | 完整环境 |

#### 关键依赖版本

- **AI框架**: PyTorch 2.2+, Ultralytics 8.0+, MediaPipe 0.10+
- **Web框架**: FastAPI 0.100+, Uvicorn 0.23+
- **安全**: PyJWT 2.8+, Cryptography 41.0+
- **监控**: Prometheus Client 0.17+, Structlog 23.1+
- **数据库**: SQLAlchemy 2.0+, PostgreSQL/Redis

#### 环境变量

```bash
# 开发环境（禁用安全限制）
export ENVIRONMENT=development

# 生产环境（启用完整安全保护）
export ENVIRONMENT=production
```

## 📖 使用指南

### 🎯 检测模式

#### 基础检测
```bash
# 使用默认摄像头
python main.py --mode detection --source 0

# 视频文件检测
python main.py --mode detection --source video.mp4

# GPU加速检测
python main.py --mode detection --source 0 --gpu-optimize
```

#### 高级检测
```bash
# 自定义配置
python main.py --mode detection \
  --source 0 \
  --profile accurate \
  --gpu-optimize \
  --batch-size 4
```

### 🌐 API服务模式

#### 启动服务
```bash
# 基础启动
python main.py --mode api

# 生产环境启动
ENVIRONMENT=production python main.py --mode api --port 8000
```

#### 访问界面
- **主界面**: http://localhost:8000/frontend/index.html
- **API文档**: http://localhost:8000/docs
- **Vue开发服务器**: http://localhost:5173/ (开发模式)

### 🎛️ 多路监控

```bash
# 启动supervisor模式
python main.py --mode supervisor

# 自定义配置文件
python main.py --mode supervisor --config config/cameras.yaml
```

### 🐳 容器化部署

#### Docker Compose (推荐)
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

#### 单独Docker运行
```bash
# 构建镜像
docker build -t behavior-detection .

# 运行容器
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/data:/app/data \
  behavior-detection
```

## ⚙️ 配置管理

### 主配置文件 (`config/unified_params.yaml`)

```yaml
# 检测配置
detection:
  device: "auto"  # auto, cuda, mps, cpu
  confidence_threshold: 0.4
  iou_threshold: 0.6

# GPU优化
gpu:
  enabled: true
  batch_size: 4
  use_mixed_precision: true

# 安全配置
security:
  enable_csrf: false  # 开发环境
  jwt_secret: "your-secret-key-here"  # pragma: allowlist secret

# 监控配置
monitoring:
  enabled: true
  metrics_interval: 30
  alert_threshold: 0.8
```

### 环境变量配置

```bash
# 环境设置
export ENVIRONMENT=development  # development, testing, production
export LOG_LEVEL=INFO
export GPU_OPTIMIZE=true

# 数据库配置
export DATABASE_URL=sqlite:///./app.db
export REDIS_URL=redis://localhost:6379/0

# 安全配置
export JWT_SECRET=your-secret-key
export ENABLE_CSRF=false
```

## 🔧 开发指南

### 代码质量

项目集成了完整的代码质量保证工具：

```bash
# 代码格式化
black src/ tests/
isort src/ tests/

# 代码检查
flake8 src/ tests/
mypy src/

# 安全扫描
bandit -r src/

# 文档检查
pydocstyle src/
```

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/
pytest tests/integration/

# 测试覆盖率
pytest --cov=src/ --cov-report=html
```

### 预提交钩子

```bash
# 安装预提交钩子
pre-commit install

# 手动运行检查
pre-commit run --all-files
```

## 📊 监控与运维

### 性能监控

系统内置了完整的监控体系：

- **系统指标**: CPU、内存、磁盘使用率
- **应用指标**: 检测延迟、处理速度、错误率
- **业务指标**: 检测数量、合规率、告警次数

### 日志管理

```bash
# 查看应用日志
tail -f logs/app.log

# 查看结构化日志
cat logs/app.log | jq '.'

# 日志轮转配置
# 自动按日期和大小轮转
```

### 告警配置

支持多种告警通道：

```yaml
alerts:
  channels:
    - type: email
      smtp_server: smtp.company.com
      recipients: ["admin@company.com"]
    - type: webhook
      url: "https://hooks.slack.com/..."
    - type: log
      level: ERROR
```

## 🛡️ 安全特性

### 认证与授权
- **JWT令牌**: 无状态身份验证
- **角色控制**: 基于角色的访问控制(RBAC)
- **会话管理**: 安全的会话管理机制

### 安全防护
- **CSRF保护**: 跨站请求伪造防护
- **XSS防护**: 跨站脚本攻击防护
- **SQL注入防护**: 参数化查询和输入验证
- **速率限制**: API调用频率限制

### 数据安全
- **传输加密**: TLS/SSL加密传输
- **数据加密**: 敏感数据加密存储
- **密码安全**: PBKDF2哈希算法

## 🚀 部署方案

### 开发环境
- **本地开发**: SQLite + 文件系统
- **快速启动**: 单机部署
- **调试模式**: 详细日志输出

### 测试环境
- **容器化**: Docker Compose
- **数据隔离**: 独立数据库
- **性能测试**: GPU加速验证

### 生产环境
- **高可用**: Kubernetes集群
- **负载均衡**: Nginx + 多实例
- **监控体系**: Prometheus + Grafana
- **日志中心**: ELK Stack

### CI/CD流水线

支持多种CI/CD方案：

```yaml
# GitHub Actions
name: CI/CD Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          python -m pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.prod.yml up -d
```

## 🔍 故障排除

### 常见问题

#### GPU相关
```bash
# 检查GPU状态
python scripts/check_gpu.py

# CUDA不可用
export CUDA_VISIBLE_DEVICES=0

# MPS问题(macOS)
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

#### 依赖问题
```bash
# 重新安装依赖
pip install --force-reinstall -r requirements.txt

# 清理缓存
pip cache purge
```

#### 权限问题
```bash
# API访问被拒绝
export ENVIRONMENT=development

# 摄像头权限
sudo chmod 666 /dev/video0
```

### 日志调试

```bash
# 开启调试日志
export LOG_LEVEL=DEBUG

# 查看特定模块日志
python main.py --mode api --log-level DEBUG

# 性能分析
python -m cProfile main.py --mode detection --source 0
```

## 📚 API文档

### 核心API端点

#### 检测服务
```bash
# 启动检测
POST /api/v1/detection/start
{
  "source": "0",
  "profile": "balanced"
}

# 获取检测结果
GET /api/v1/detection/results

# 停止检测
POST /api/v1/detection/stop
```

#### 摄像头管理
```bash
# 获取摄像头列表
GET /api/v1/cameras

# 启动摄像头
POST /api/v1/cameras/{camera_id}/start

# 获取状态
GET /api/v1/cameras/{camera_id}/status
```

#### 监控API
```bash
# 系统健康检查
GET /health

# 性能指标
GET /api/v1/metrics

# 错误监控
GET /api/v1/error-monitoring/stats
```

### WebSocket API

```javascript
// 实时检测结果
const ws = new WebSocket('ws://localhost:8000/api/ws/detection');
ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  console.log('检测结果:', result);
};
```

## 🤝 贡献指南

### 贡献流程

1. **Fork项目** - 点击右上角Fork按钮
2. **创建分支** - `git checkout -b feature/amazing-feature`
3. **编写代码** - 遵循代码规范
4. **测试验证** - 运行完整测试套件
5. **提交更改** - `git commit -m 'Add amazing feature'`
6. **推送分支** - `git push origin feature/amazing-feature`
7. **创建PR** - 提交Pull Request

### 代码规范

- **Python**: 遵循PEP 8，使用black格式化
- **JavaScript**: 使用ES6+语法，保持一致性
- **文档**: 所有函数和类都需要文档字符串
- **测试**: 新功能需要对应的测试用例

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.dev.txt

# 安装预提交钩子
pre-commit install

# 运行开发服务器
python main.py --mode api --reload
```

## 📄 许可证

本项目采用 **MIT 许可证** - 详情请参阅 [LICENSE](LICENSE) 文件。

## 🆘 支持与反馈

- **问题报告**: [GitHub Issues](https://github.com/your-repo/issues)
- **功能请求**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **文档**: [项目文档](https://your-docs-site.com)
- **邮件支持**: support@yourcompany.com

## 🎉 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**
