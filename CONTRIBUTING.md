# 如何为本项目做出贡献

非常感谢您有兴趣为“人体行为检测系统”项目贡献您的时间和才华！您的每一行代码、每一条建议都对我们至关重要。本指南将为您提供参与项目所需的所有信息。

---

## 🚀 快速开始：您的第一次贡献

我们为首次贡献者设计了一条平滑的路径：

1.  **理解项目**: 首先，请阅读我们的 [**项目统一知识库 (INDEX.md)](./docs/INDEX.md)，对项目架构和目标有一个宏观的了解。
2.  **搭建环境**: 遵循下文的 [**开发环境搭建**](#-开发环境搭建) 指南，在您的本地机器上将项目运行起来。
3.  **认领任务**: 从 GitHub Issues 中寻找带有 `good first issue` 或 `help wanted` 标签的任务。这些是专门为新贡献者准备的。
4.  **遵循流程**: 按照 [**Git 工作流**](#-git-工作流) 和 [**代码规范**](#-代码规范) 进行开发。
5.  **提交PR**: 完成开发和测试后，提交您的 Pull Request，等待团队成员的审查。

---

## 🛠️ 开发环境搭建

我们强烈推荐使用本地环境进行开发，以便更好地利用 `pre-commit` 等代码质量工具。

**1. 准备工作**

- 安装 [Git](https://git-scm.com/)
- 安装 [Python 3.8](https://www.python.org/) 或更高版本
- (可选) 安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/) 以运行数据库等依赖服务。

**2. 克隆与安装**

```bash
# 克隆项目仓库
git clone <your-project-repository-url>
cd <project-directory>

# 创建并激活Python虚拟环境
python3 -m venv venv
source venv/bin/activate  # 在 Linux/macOS 上
# venv\Scripts\activate   # 在 Windows 上

# 安装项目依赖（包括开发依赖）
# '-e' 表示以可编辑模式安装，您的代码更改会立即生效
pip install -e .[dev]

# 安装 pre-commit 钩子 (‼️ 关键步骤)
# 这将确保您的代码在提交前自动通过质量检查
pre-commit install
```

**3. 运行依赖服务 (可选)**

如果您的开发需要连接数据库或Redis，可以单独启动它们：

```bash
docker-compose -f docker-compose.dev-db.yml up -d
```

**4. 验证环境**

运行测试是验证环境是否配置正确的最佳方式：

```bash
pytest
```

如果所有测试都通过了，恭喜您，您的开发环境已准备就绪！

### 🍏 Mac (Apple Silicon) 用户特别说明

对于使用 M1/M2/M3 系列芯片的 Mac 用户：

- **GPU加速已自动启用**: 本项目已支持通过 **Metal Performance Shaders (MPS)** 进行GPU加速。您无需任何额外配置，代码中的 `device='auto'` 设置会自动检测并启用MPS，相比纯CPU预计可获得 **2-3倍** 的性能提升。
- **TensorRT 不适用**: TensorRT 是 NVIDIA 的专属技术，无法在 Mac 上运行。MPS 是 Apple 平台上的主要加速方案。
- **追求极致性能?**: 如果您希望在Mac上获得极致的推理性能（3-5倍提升），可以考虑将模型转换为 **CoreML** 格式。相关转换脚本和指南请参考 `scripts/optimization/` 目录。

---

## 🌊 Git 工作流

我们采用经典的 **Git Flow** 模式来保证代码库的整洁和稳定。

- **`main`**: 生产分支。永远保持稳定和可部署。
- **`develop`**: 开发主分支。所有已完成的功能最终会合并到这里。
- **`feature/<feature-name>`**: 功能分支。从 `develop` 分支创建，用于开发新功能。
- **`bugfix/<issue-number>`**: Bug修复分支。从 `develop` 分支创建。
- **`hotfix/<issue-number>`**: 紧急修复分支。从 `main` 分支创建，修复后需同时合并回 `main` 和 `develop`。

**标准开发流程**:

1.  **同步最新代码**: `git checkout develop && git pull`
2.  **创建新分支**: `git checkout -b feature/my-awesome-feature`
3.  **编码与开发**: 尽情施展您的才华！
4.  **提交代码**: `git add . && git commit` (您的 commit message 会被 `pre-commit` 检查)
5.  **推送到远程**: `git push origin feature/my-awesome-feature`
6.  **创建 Pull Request**: 在 GitHub 上，创建一个从您的功能分支到 `develop` 分支的 Pull Request。

---

## ✨ 代码与提交规范

我们借助自动化工具来执行大部分规范，以减轻您的心智负担。

### 代码风格与质量

您无需手动调整代码格式。当您运行 `git commit` 时，`pre-commit` 会自动为您完成以下工作：

- **`black`**: 自动格式化您的Python代码。
- **`isort`**: 自动排序您的 `import` 语句。
- **`flake8`**: 检查代码中的潜在错误和不规范写法。
- **`mypy`**: 进行静态类型检查，确保类型安全。

如果 `pre-commit` 检查失败，它会提示错误并中止提交。您只需根据提示修正问题，然后再次 `git add .` 和 `git commit` 即可。

### Commit Message 规范

我们遵循 **[Conventional Commits](https://www.conventionalcommits.org/)** 规范。这有助于我们自动化生成版本日志，并使提交历史清晰可读。

**格式**: `<type>(<scope>): <subject>`

- **`type`**: 必须是以下之一：
    - `feat`: 引入新功能
    - `fix`: 修复 Bug
    - `docs`: 仅修改文档
    - `style`: 修改代码格式（不影响逻辑）
    - `refactor`: 代码重构
    - `perf`: 性能优化
    - `test`: 添加或修改测试
    - `chore`: 其他杂项（如构建脚本修改）
- **`scope`** (可选): 本次提交影响的范围（如 `api`, `detector`, `docs`）。
- **`subject`**: 对本次提交的简短描述。

**示例**:

```
feat(api): add endpoint for hairnet detection statistics
fix(detector): prevent crash when video source is unavailable
docs(readme): update installation instructions
```

---

## 🧪 测试要求

**质量是我们的生命线。** 任何非琐碎的贡献都应包含相应的测试。

- **位置**: 所有测试代码都应放在 `tests/` 目录下。
- **单元测试**: 针对单一函数或类的测试，应放在 `tests/unit/`。
- **集成测试**: 涉及多个组件交互的测试，应放在 `tests/integration/`。
- **运行测试**: 在提交PR前，请务必在本地完整运行一次测试：
  ```bash
  # 运行所有测试
  pytest

  # 运行测试并生成覆盖率报告
  pytest --cov=src
  ```
- **PR检查**: 您的Pull Request会自动触发CI流水线，运行所有测试。只有当所有检查都通过时，PR才可能被合并。

---

## 💬 Pull Request (PR) 流程

1.  **确保PR足够小**: 一个PR最好只做一件事，这样更易于审查。
2.  **填写PR模板**: 创建PR时，请详细填写模板中的信息，说明您“做了什么”、“为什么这么做”以及“如何测试”。
3.  **等待审查**: 团队成员会尽快审查您的代码。请耐心等待，并积极回应审查评论。
4.  **合并**: 一旦您的PR被批准且所有CI检查通过，它将被合并到 `develop` 分支。恭喜您，您已经成功为项目做出了贡献！