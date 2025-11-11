# pyproject.toml 可选依赖组使用指南

## 📋 概述

项目在 `pyproject.toml` 中定义了可选依赖组，允许您根据实际需求选择性安装依赖。这是**推荐的安装方式**，比手动安装更清晰、更易管理。

---

## 🎯 依赖组列表

项目定义了以下可选依赖组：

### 按设备/功能需求

| 依赖组 | 包含依赖 | 适用场景 |
|--------|---------|----------|
| `gpu-nvidia` | `pynvml>=11.5.0` | NVIDIA GPU 用户 |
| `ml` | `xgboost>=1.7.0` | ML 增强识别功能 |
| `gpu-nvidia-ml` | `pynvml + xgboost` | NVIDIA GPU + ML 用户 |

### 按环境需求

| 依赖组 | 包含依赖 | 适用场景 |
|--------|---------|----------|
| `dev` | 测试框架、代码质量工具 | 开发环境 |
| `test` | 测试框架 | 运行测试 |
| `docs` | 文档生成工具 | 生成文档 |
| `production` | Gunicorn、监控、性能优化 | 生产环境 |

---

## 📦 安装方式

### 基础安装（最小依赖）

```bash
# 仅安装核心依赖
pip install -e .
```

**包含**: 所有必需的核心依赖（PyTorch、FastAPI、OpenCV等）

**不包含**: 可选依赖（pynvml、xgboost）

---

### 按设备需求安装

#### NVIDIA GPU 用户

```bash
# 推荐方式：使用可选依赖组
pip install -e ".[gpu-nvidia]"
```

**包含**: 核心依赖 + pynvml

**说明**:
- ✅ 获取详细的GPU监控信息
- ✅ 准确的显存使用情况
- ✅ GPU使用率监控

#### AMD GPU / Intel GPU / Apple Silicon / CPU 用户

```bash
# 无需安装可选依赖
pip install -e .
```

**说明**:
- ✅ 系统会自动使用 PyTorch 的设备检测
- ✅ 核心功能完全不受影响
- ❌ 无需 pynvml（不支持这些设备）

---

### 按功能需求安装

#### ML 增强识别

```bash
# 使用可选依赖组
pip install -e ".[ml]"
```

**包含**: 核心依赖 + xgboost

**说明**:
- ⚠️  需要配合训练好的模型文件
- ⚠️  功能处于实验阶段
- ✅ 默认使用规则推理引擎（无需此依赖）

---

### 组合安装

#### NVIDIA GPU + ML 用户（推荐）

```bash
# 方式1：使用组合依赖组
pip install -e ".[gpu-nvidia-ml]"

# 方式2：组合多个依赖组（效果相同）
pip install -e ".[gpu-nvidia,ml]"
```

**包含**: 核心依赖 + pynvml + xgboost

---

### 开发/测试环境

#### 开发环境

```bash
# 包含所有开发工具
pip install -e ".[dev]"
```

**包含**: 核心依赖 + 测试框架 + 代码质量工具 + 文档工具

#### 仅运行测试

```bash
# 仅测试框架
pip install -e ".[test]"
```

#### 生成文档

```bash
# 仅文档工具
pip install -e ".[docs]"
```

---

### 生产环境

```bash
# 生产环境依赖
pip install -e ".[production]"
```

**包含**:
- Gunicorn（Web服务器）
- Sentry（错误监控）
- Prometheus（指标收集）
- 性能优化库（orjson、ujson）
- Redis hiredis（高速缓存）

**组合使用**：
```bash
# 生产环境 + GPU 支持
pip install -e ".[production,gpu-nvidia]"

# 生产环境 + GPU + ML
pip install -e ".[production,gpu-nvidia-ml]"
```

---

## 📊 使用场景对照表

### 快速参考

| 场景 | 推荐安装命令 | 说明 |
|------|-------------|------|
| **最小安装** | `pip install -e .` | 所有核心功能 |
| **NVIDIA GPU** | `pip install -e ".[gpu-nvidia]"` | GPU监控 |
| **ML功能** | `pip install -e ".[ml]"` | ML增强识别 |
| **NVIDIA + ML** | `pip install -e ".[gpu-nvidia-ml]"` | 完整功能 |
| **开发环境** | `pip install -e ".[dev]"` | 开发工具 |
| **生产环境** | `pip install -e ".[production]"` | 生产部署 |
| **测试** | `pip install -e ".[test]"` | 运行测试 |

---

## 🔍 检查已安装的依赖

### 方法1: pip list

```bash
# 检查特定依赖
pip list | grep pynvml
pip list | grep xgboost
```

### 方法2: Python检查

```python
# 检查 pynvml
try:
    import pynvml
    print("✅ pynvml 已安装")
except ImportError:
    print("❌ pynvml 未安装")

# 检查 xgboost
try:
    import xgboost
    print("✅ xgboost 已安装")
except ImportError:
    print("❌ xgboost 未安装")
```

### 方法3: 查看安装的包

```bash
# 查看所有已安装的包
pip list

# 查看项目相关包
pip show human-behavior-detection
```

---

## 🔄 更新依赖

### 添加依赖组

```bash
# 如果之前只安装了基础版本，现在想添加GPU支持
pip install -e ".[gpu-nvidia]"

# 这会自动添加 pynvml，不会影响已安装的其他依赖
```

### 移除依赖组

```bash
# 注意：pip 无法直接"卸载"依赖组
# 需要手动卸载特定包
pip uninstall pynvml
pip uninstall xgboost
```

---

## 📝 配置说明

### pyproject.toml 结构

```toml
[project.optional-dependencies]
# 按设备需求
gpu-nvidia = [
    "pynvml>=11.5.0",
]

# 按功能需求
ml = [
    "xgboost>=1.7.0",
]

# 组合选项
gpu-nvidia-ml = [
    "pynvml>=11.5.0",
    "xgboost>=1.7.0",
]

# 开发环境
dev = [
    "pytest>=7.4.0",
    # ... 其他开发工具
]

# 生产环境
production = [
    "gunicorn>=21.2.0",
    # ... 其他生产工具
]
```

---

## ❓ 常见问题

### Q1: 我已经安装了基础版本，如何添加可选依赖？

**A**: 直接安装依赖组即可：

```bash
# 之前：pip install -e .
# 现在添加 GPU 支持：
pip install -e ".[gpu-nvidia]"
```

pip 会自动添加缺失的依赖，不会影响已安装的包。

---

### Q2: 可以同时安装多个依赖组吗？

**A**: 可以，使用逗号分隔：

```bash
pip install -e ".[gpu-nvidia,ml]"
pip install -e ".[dev,test]"
pip install -e ".[production,gpu-nvidia]"
```

---

### Q3: 依赖组和手动安装有什么区别？

**A**:

**使用依赖组（推荐）**:
- ✅ 版本统一管理
- ✅ 清晰明确
- ✅ 易于维护
- ✅ 符合 Python 标准

**手动安装**:
- ⚠️  需要记住每个包名
- ⚠️  版本可能不一致
- ⚠️  难以管理

**推荐**: 始终使用依赖组安装。

---

### Q4: 如何查看所有可用的依赖组？

**A**: 查看 `pyproject.toml` 文件：

```bash
cat pyproject.toml | grep -A 20 "\[project.optional-dependencies\]"
```

或者查看项目文档。

---

### Q5: 生产环境应该安装哪些依赖组？

**A**: 根据您的需求：

```bash
# 最小生产环境
pip install -e ".[production]"

# 生产环境 + GPU（如果使用NVIDIA GPU）
pip install -e ".[production,gpu-nvidia]"

# 生产环境 + GPU + ML
pip install -e ".[production,gpu-nvidia-ml]"
```

---

## 🎯 最佳实践

### 1. 最小化安装
- ✅ 仅安装实际需要的依赖组
- ✅ 避免不必要的依赖
- ✅ 减少安装时间和包大小

### 2. 使用依赖组
- ✅ 优先使用 `pip install -e ".[group]"` 而不是手动安装
- ✅ 组合多个依赖组时使用逗号分隔
- ✅ 保持版本一致性

### 3. 文档化
- ✅ 在 README 中记录使用的依赖组
- ✅ 在部署文档中说明安装命令
- ✅ 在团队中统一使用方式

### 4. 版本控制
- ✅ 将 `pyproject.toml` 提交到版本控制
- ✅ 定期更新依赖版本
- ✅ 使用版本范围而非固定版本

---

## 📚 相关文档

- [可选依赖详细说明](./OPTIONAL_DEPENDENCIES.md) - 依赖的详细说明
- [依赖改进总结](./DEPENDENCY_IMPROVEMENTS_SUMMARY.md) - 依赖管理改进
- [README.md](../README.md) - 项目主文档

---

## 🎉 总结

通过使用 `pyproject.toml` 的可选依赖组：

- ✅ **更清晰** - 明确知道安装了哪些依赖
- ✅ **更易管理** - 版本统一管理
- ✅ **更灵活** - 按需组合安装
- ✅ **更标准** - 符合 Python 打包标准

**推荐所有用户使用依赖组方式安装！**

---

**文档版本**: 1.0
**最后更新**: 2025-11-04
**维护者**: 开发团队
