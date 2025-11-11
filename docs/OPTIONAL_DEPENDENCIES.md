# 可选依赖说明

## 概述

本项目采用**按需安装**的依赖策略。部分功能依赖是可选的，您可以根据实际硬件设备和功能需求选择性安装。

---

## 📦 按需依赖列表

### 1. pynvml - NVIDIA GPU监控

**依赖类型**: 按设备需求安装
**适用场景**: 仅在使用 NVIDIA GPU 进行推理时需要

#### 安装方式

```bash
# 仅在使用 NVIDIA GPU 时安装
pip install pynvml
```

#### 使用场景对照表

| 硬件设备 | 是否需要 pynvml | 说明 |
|---------|----------------|------|
| **NVIDIA GPU** | ✅ 推荐安装 | 获取详细的GPU信息和监控指标 |
| **AMD GPU** | ❌ 无需安装 | 使用 PyTorch 的 ROCm 支持 |
| **Intel GPU** | ❌ 无需安装 | 使用 PyTorch 的设备检测 |
| **Apple Silicon (M1/M2/M3/M4)** | ❌ 无需安装 | 使用 PyTorch 的 MPS 后端 |
| **CPU only** | ❌ 无需安装 | 无GPU相关功能 |

#### 功能影响

**已安装时**:
- ✅ 获取详细的GPU名称和型号
- ✅ 准确的显存使用情况
- ✅ GPU使用率监控
- ✅ 多GPU设备信息

**未安装时**:
- ✅ 系统自动回退到 PyTorch 检测
- ✅ 基本的GPU信息仍可获取
- ✅ 核心功能完全不受影响
- ℹ️  GPU监控指标可能不完整

#### 代码实现

系统在 `src/utils/hardware_probe.py` 中实现了优雅的降级机制：

```python
def _gpu_info_pynvml() -> Dict[str, Any]:
    """使用 pynvml 获取 NVIDIA GPU 详细信息（仅 NVIDIA GPU 需要）"""
    try:
        import pynvml
        # 使用 pynvml 获取详细信息...
    except ImportError:
        # pynvml 未安装（正常情况，仅 NVIDIA GPU 需要）
        pass  # 系统会自动使用 PyTorch fallback
    except Exception as e:
        # pynvml 已安装但获取失败
        print(f"pynvml failed: {e}, trying torch fallback")
```

---

### 2. XGBoost - ML分类器（洗手行为识别增强）

**依赖类型**: 按功能需求安装
**适用场景**: 需要提升洗手行为识别准确率时

**详细文档**: [XGBoost 详细分析](./XGBOOST_ANALYSIS.md) | [启用指南](./XGBOOST_ENABLE_GUIDE.md)

#### 安装方式

```bash
pip install xgboost
```

#### 使用场景

| 场景 | 是否需要 | 说明 |
|------|---------|------|
| **基础行为识别** | ❌ 无需安装 | 使用规则推理引擎 |
| **ML增强识别** | ✅ 需要安装 | 启用机器学习分类器 |
| **模型训练** | ✅ 需要安装 | 训练新的分类模型 |

#### 功能状态

⚠️  **当前状态**: 实验性功能

- 默认使用规则推理引擎（无需 XGBoost）
- ML分类器功能需要配合训练好的模型文件
- 配置文件中 `use_ml_classifier` 默认为 `false`

#### 启用方法

1. 安装 XGBoost:
```bash
pip install xgboost
```

2. 准备模型文件:
```bash
# 模型文件路径（在 config/unified_params.yaml 中配置）
models/handwash_xgb.joblib  # 或 .json / .ubj 格式
```

3. 修改配置:
```yaml
# config/unified_params.yaml
behavior_recognition:
  use_ml_classifier: true
  ml_model_path: "models/handwash_xgb.joblib"
  ml_window: 30
  ml_fusion_alpha: 0.7
```

#### 功能影响

**已安装且启用时**:
- ✅ ML分类器与规则引擎融合
- ✅ 更高的行为识别准确率
- ✅ 基于时序特征的预测

**未安装或未启用时**:
- ✅ 使用规则推理引擎
- ✅ 基于姿态和手部关键点的识别
- ✅ 核心功能完全正常

#### 代码实现

系统在 `src/core/behavior.py` 中实现了优雅的检查机制：

```python
if self.use_ml_classifier:
    # 检查XGBoost是否可用
    if xgb is None:
        logger.warning(
            "ML classifier enabled but XGBoost not installed; "
            "disabling ML fusion. Install with: pip install xgboost"
        )
        self.use_ml_classifier = False
    else:
        # 加载模型...
```

---

## 🎯 安装建议

### 使用 pyproject.toml 安装（推荐）

项目已配置可选依赖组，这是**推荐的安装方式**：

```bash
# 基础安装（最小依赖，推荐）
pip install -e .

# NVIDIA GPU 用户（推荐）
pip install -e ".[gpu-nvidia]"

# 需要 ML 增强功能
pip install -e ".[ml]"

# NVIDIA GPU + ML 组合（推荐用于 NVIDIA GPU 用户）
pip install -e ".[gpu-nvidia-ml]"

# 或组合多个依赖组
pip install -e ".[gpu-nvidia,ml]"

# 开发环境（包含所有开发工具）
pip install -e ".[dev]"

# 生产环境
pip install -e ".[production]"
```

### 快速开始（最小安装）

```bash
# 基础依赖（必需）
pip install -e .

# 或者使用 requirements.txt
pip install -r requirements.txt
```

**这个最小安装足以运行所有核心功能！**

---

### 按硬件设备安装

#### NVIDIA GPU 用户（推荐方式）

```bash
# 使用可选依赖组（推荐）
pip install -e ".[gpu-nvidia]"

# 或手动安装
pip install -e .
pip install pynvml
```

#### NVIDIA GPU + ML 用户

```bash
# 使用组合依赖组（推荐）
pip install -e ".[gpu-nvidia-ml]"

# 或分别安装
pip install -e ".[gpu-nvidia,ml]"
```

#### AMD GPU / Intel GPU 用户

```bash
# 仅需要基础依赖
pip install -e .

# 无需额外安装
```

#### Apple Silicon (M1/M2/M3/M4) 用户

```bash
# 仅需要基础依赖
pip install -e .

# PyTorch MPS 后端会自动使用
```

#### CPU 用户

```bash
# 仅需要基础依赖
pip install -e .
```

---

### 按功能需求安装

#### 需要 ML 增强识别

```bash
# 使用可选依赖组（推荐）
pip install -e ".[ml]"

# 或手动安装
pip install -e .
pip install xgboost

# 还需要模型文件
# 请联系项目维护者获取训练好的模型
```

---

## 🔍 检查已安装的依赖

### 方法1: Python命令

```python
# 检查 pynvml
python -c "import pynvml; print('pynvml is installed')"

# 检查 xgboost
python -c "import xgboost; print('xgboost is installed')"
```

### 方法2: pip list

```bash
pip list | grep pynvml
pip list | grep xgboost
```

---

## 📊 依赖对照表

| 依赖 | 类型 | 必需性 | 适用场景 | 未安装时影响 | 安装方式 |
|------|------|--------|----------|-------------|---------|
| PyTorch | 核心 | ✅ 必需 | 所有场景 | 无法运行 | `pip install -e .` |
| FastAPI | 核心 | ✅ 必需 | API服务 | API无法启动 | `pip install -e .` |
| OpenCV | 核心 | ✅ 必需 | 视频处理 | 无法处理视频 | `pip install -e .` |
| MediaPipe | 核心 | ✅ 必需 | 姿态检测 | 姿态检测失败 | `pip install -e .` |
| greenlet | 数据库 | ✅ 需要 | 异步数据库 | 数据库错误 | `pip install -e .` |
| **pynvml** | 可选 | ⚠️  按需 | NVIDIA GPU | 回退到PyTorch | `pip install -e ".[gpu-nvidia]"` |
| **xgboost** | 可选 | ❌ 可选 | ML增强识别 | 使用规则引擎 | `pip install -e ".[ml]"` |

## 📦 可选依赖组说明

项目在 `pyproject.toml` 中定义了以下可选依赖组：

| 依赖组 | 包含依赖 | 安装命令 | 适用场景 |
|--------|---------|---------|----------|
| `gpu-nvidia` | pynvml | `pip install -e ".[gpu-nvidia]"` | NVIDIA GPU 用户 |
| `ml` | xgboost | `pip install -e ".[ml]"` | 需要 ML 增强识别 |
| `gpu-nvidia-ml` | pynvml + xgboost | `pip install -e ".[gpu-nvidia-ml]"` | NVIDIA GPU + ML 用户 |
| `dev` | 测试、代码质量工具 | `pip install -e ".[dev]"` | 开发环境 |
| `test` | 测试框架 | `pip install -e ".[test]"` | 运行测试 |
| `docs` | 文档工具 | `pip install -e ".[docs]"` | 生成文档 |
| `production` | Gunicorn、监控等 | `pip install -e ".[production]"` | 生产环境 |

**组合使用示例**：
```bash
# 组合多个依赖组
pip install -e ".[gpu-nvidia,ml]"

# 开发环境 + GPU 支持
pip install -e ".[dev,gpu-nvidia]"

# 生产环境 + GPU 支持
pip install -e ".[production,gpu-nvidia]"
```

---

## ❓ 常见问题

### Q1: 我不确定是否需要安装 pynvml？

**A**: 查看您的设备类型：

```bash
# 检查是否有 NVIDIA GPU
nvidia-smi

# 如果命令有效且显示GPU信息，推荐安装 pynvml
# 如果命令无效或报错，无需安装
```

### Q2: pynvml 未安装会影响功能吗？

**A**: 不会。系统会自动使用 PyTorch 的设备检测，核心功能完全不受影响。只是GPU监控指标可能不如 pynvml 详细。

### Q3: 如何知道 XGBoost ML分类器是否生效？

**A**: 查看启动日志：

```bash
# 如果看到这个，说明ML分类器已启用
Loaded ML handwash classifier: models/handwash_xgb.joblib

# 如果看到这个，说明使用规则引擎
ML classifier enabled but XGBoost not installed
```

### Q4: 可以在运行时切换吗？

**A**: 需要重启服务。修改配置后：

```bash
# 重启检测服务
python main.py --mode detection --source 0
```

---

## 🔄 升级建议

### 从旧版本升级

如果您从旧版本升级，建议：

```bash
# 1. 更新基础依赖
pip install --upgrade -r requirements.txt

# 2. 根据您的设备选择性安装可选依赖
# NVIDIA GPU 用户
pip install pynvml

# 需要 ML 功能
pip install xgboost
```

---

## 📝 总结

- ✅ **pynvml**: 按设备需求安装（仅 NVIDIA GPU）
- ✅ **xgboost**: 按功能需求安装（实验性功能）
- ✅ **核心功能**: 无需任何可选依赖即可完整运行
- ✅ **优雅降级**: 所有可选依赖都有自动回退机制

**推荐做法**: 先安装基础依赖，测试系统是否正常运行，再根据需要添加可选依赖。

---

**文档版本**: 1.0
**最后更新**: 2025-11-04
**维护者**: 开发团队
