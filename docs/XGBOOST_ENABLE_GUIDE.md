# XGBoost 启用指南

## 📋 概述

本文档提供启用 XGBoost ML 分类器的完整步骤。XGBoost 用于洗手行为识别，与规则引擎融合以提升准确率。

---

## ✅ 启用前检查清单

在启用 XGBoost 之前，请确认：

- [ ] XGBoost 已安装（`pip install -e ".[ml]"` 或 `pip install xgboost`）
- [ ] 模型文件存在（`models/handwash_xgb.json`）
- [ ] 配置文件可访问（`config/unified_params.yaml`）
- [ ] 系统已安装基础依赖

---

## 🚀 启用步骤

### 步骤1: 安装 XGBoost

**方式1: 使用可选依赖组（推荐）**

```bash
pip install -e ".[ml]"
```

**方式2: 手动安装**

```bash
pip install xgboost>=1.7.0
```

**验证安装**:
```bash
python -c "import xgboost; print(f'✅ XGBoost {xgboost.__version__} 已安装')"
```

---

### 步骤2: 检查模型文件

**模型文件位置**:
```
models/handwash_xgb.json  # 推荐格式（XGBoost 原生）
models/handwash_xgb.joblib  # 备选格式（Python pickle）
```

**检查模型文件**:
```bash
# 检查文件是否存在
ls -lh models/handwash_xgb.json

# 验证文件完整性
python -c "import xgboost as xgb; model = xgb.Booster(); model.load_model('models/handwash_xgb.json'); print('✅ 模型文件有效')"
```

**预期输出**:
```
-rw-r--r--  1 user  staff   593K Sep 25 16:37 models/handwash_xgb.json
✅ 模型文件有效
```

---

### 步骤3: 配置启用

**配置文件**: `config/unified_params.yaml`

**修改配置**:
```yaml
behavior_recognition:
  # 启用 ML 分类器
  use_ml_classifier: true

  # 模型文件路径（推荐使用 .json 格式）
  ml_model_path: models/handwash_xgb.json

  # 时序窗口大小（帧数）
  # 建议值：20-40 帧
  ml_window: 30

  # ML 融合权重（0.0-1.0）
  # alpha = 0.7 表示 ML 权重 70%，规则权重 30%
  # 建议值：0.5-0.8
  ml_fusion_alpha: 0.7
```

**配置说明**:

| 参数 | 默认值 | 说明 | 建议值 |
|------|--------|------|--------|
| `use_ml_classifier` | `false` | 是否启用ML分类器 | `true` |
| `ml_model_path` | `models/handwash_xgb.json` | 模型文件路径 | 使用 `.json` 格式 |
| `ml_window` | `30` | 时序窗口大小（帧） | 20-40 |
| `ml_fusion_alpha` | `0.7` | ML权重 | 0.5-0.8 |

---

### 步骤4: 启动系统

**启动检测模式**:
```bash
python main.py --mode detection --source 0 --camera-id test_xgboost
```

**验证启用**:
查看启动日志，应该看到：
```
INFO - Loaded ML handwash classifier: models/handwash_xgb.json
INFO - BehaviorRecognizer initialized with unified params:
       ..., use_ml_classifier=True, ml_window=30, alpha=0.7
```

**如果看到这些日志，说明启用成功！** ✅

---

## 🔍 验证启用状态

### 方法1: 查看启动日志

```bash
python main.py --mode detection --source 0 2>&1 | grep -i "ml\|xgboost"
```

**预期输出**:
```
INFO - Loaded ML handwash classifier: models/handwash_xgb.json
INFO - ... use_ml_classifier=True, ml_window=30, alpha=0.7
```

### 方法2: Python 检查

```python
from src.config.unified_params import get_unified_params

params = get_unified_params()
print(f"ML分类器启用: {params.behavior_recognition.use_ml_classifier}")
print(f"模型路径: {params.behavior_recognition.ml_model_path}")
print(f"融合权重: {params.behavior_recognition.ml_fusion_alpha}")
```

**预期输出**:
```
ML分类器启用: True
模型路径: models/handwash_xgb.json
融合权重: 0.7
```

### 方法3: 运行时验证

在检测过程中，如果启用了ML分类器，应该看到：
- **性能提升**: 洗手行为识别准确率提升
- **日志输出**: 可能出现 `ML fusion` 相关日志（debug级别）

---

## ⚙️ 配置调优

### 1. 融合权重调优

**调整 `ml_fusion_alpha`**:

```yaml
# 更信任 ML 模型（推荐用于ML准确率高的情况）
ml_fusion_alpha: 0.8

# 平衡 ML 和规则（推荐用于一般情况）
ml_fusion_alpha: 0.7

# 更信任规则引擎（推荐用于规则更稳定的情况）
ml_fusion_alpha: 0.5
```

**调优建议**:
1. **初始值**: 从 `0.7` 开始
2. **如果ML准确率高**: 提高到 `0.8-0.9`
3. **如果规则更稳定**: 降低到 `0.5-0.6`
4. **根据实际效果**: 动态调整

### 2. 时序窗口调优

**调整 `ml_window`**:

```yaml
# 短窗口（快速响应，可能不够稳定）
ml_window: 20

# 标准窗口（推荐）
ml_window: 30

# 长窗口（更稳定，响应稍慢）
ml_window: 40
```

**调优建议**:
- **快速洗手**: 使用较短窗口（20-25帧）
- **标准洗手**: 使用标准窗口（30帧）
- **慢速洗手**: 使用较长窗口（35-40帧）

---

## 🐛 常见问题

### Q1: 启动时没有看到 "Loaded ML handwash classifier" 日志

**可能原因**:
1. XGBoost 未安装
2. 配置文件未启用
3. 模型文件不存在

**解决方法**:
```bash
# 1. 检查 XGBoost
python -c "import xgboost; print('✅ XGBoost已安装')"

# 2. 检查配置
grep "use_ml_classifier" config/unified_params.yaml

# 3. 检查模型文件
ls -lh models/handwash_xgb.json
```

### Q2: 看到 "Failed to load ML classifier" 错误

**可能原因**:
1. 模型文件格式不匹配
2. 模型文件损坏
3. XGBoost 版本不兼容（最常见）

**常见错误**:
```
Invalid cast, from Integer to Number
```

**原因**: XGBoost 3.0+ 版本与旧版本训练的模型文件格式不兼容

**解决方法**:

**方法1: 使用joblib格式（推荐）**
```yaml
# config/unified_params.yaml
behavior_recognition:
  ml_model_path: models/handwash_xgb.joblib  # 使用joblib格式
```

**方法2: 重新训练模型**
```python
# 使用当前XGBoost版本重新训练模型
import xgboost as xgb

# 训练代码...
model.save_model('models/handwash_xgb.json')  # 保存为新的JSON格式
```

**方法3: 降级XGBoost版本（不推荐）**
```bash
# 降级到与模型兼容的版本（需确认模型使用的版本）
pip install xgboost==2.0.0  # 示例版本
```

**验证方法**:
```bash
# 检查 XGBoost 版本
python -c "import xgboost as xgb; print(f'XGBoost版本: {xgb.__version__}')"

# 尝试加载模型（会显示具体错误）
python -c "import xgboost as xgb; model = xgb.Booster(); model.load_model('models/handwash_xgb.json')"
```

### Q3: ML分类器启用但性能没有提升

**可能原因**:
1. 融合权重设置不当
2. 模型准确率不够高
3. 规则引擎已经足够准确

**解决方法**:
1. **调整融合权重**: 尝试不同的 `ml_fusion_alpha` 值
2. **检查模型质量**: 验证模型在测试集上的准确率
3. **收集数据**: 如果规则引擎已经>95%准确率，ML提升可能有限

### Q4: 推理速度变慢

**可能原因**:
1. XGBoost 预测本身很慢（不应该）
2. 特征提取变慢（更可能）

**解决方法**:
```bash
# 检查是否是特征提取问题
# 主要时间消耗在 MediaPipe 手部检测，而不是 XGBoost
# XGBoost 预测通常在 <1ms
```

---

## 📊 性能监控

### 启用后的性能指标

**预期性能**:
- **推理时间**: +<1ms（XGBoost预测）
- **内存占用**: +<100MB（模型+缓冲区）
- **准确率提升**: +5-15%（取决于模型质量）

### 监控方法

**查看日志**:
```bash
# 查看ML相关日志
python main.py --mode detection --source 0 2>&1 | grep -i "ml\|fusion"
```

**性能测试**:
```python
import time
from src.core.behavior import BehaviorRecognizer

# 测试ML分类器推理时间
start = time.time()
# ... 调用识别方法 ...
end = time.time()
print(f"推理时间: {(end - start) * 1000:.2f}ms")
```

---

## 🎯 最佳实践

### 1. 模型文件格式

**推荐**: 使用 `.json` 格式
- ✅ XGBoost 原生格式
- ✅ 跨平台兼容
- ✅ 加载速度快

**备选**: `.joblib` 格式
- ⚠️ Python pickle 格式
- ⚠️ 可能有版本兼容问题

### 2. 配置管理

**推荐**: 在 `config/unified_params.yaml` 中配置
- ✅ 集中管理
- ✅ 易于修改
- ✅ 版本控制友好

### 3. 权重调优

**推荐流程**:
1. 从默认值 `0.7` 开始
2. 收集测试数据
3. 对比不同权重效果
4. 选择最优权重

### 4. 版本管理

**推荐**: 使用依赖组安装
```bash
pip install -e ".[ml]"
```

**不推荐**: 手动安装
```bash
pip install xgboost  # 可能版本不一致
```

---

## 📚 相关文档

- [XGBoost 详细分析](./XGBOOST_ANALYSIS.md) - 技术原理和选择理由
- [可选依赖说明](./OPTIONAL_DEPENDENCIES.md) - 依赖安装指南
- [行为识别代码](../src/core/behavior.py) - 实现代码

---

## ✅ 启用检查清单

完成以下步骤后，XGBoost 已成功启用：

- [ ] ✅ XGBoost 已安装并验证
- [ ] ✅ 模型文件存在且有效
- [ ] ✅ 配置文件已更新（`use_ml_classifier: true`）
- [ ] ✅ 启动日志显示 "Loaded ML handwash classifier"
- [ ] ✅ 系统运行正常，无错误
- [ ] ✅ 洗手识别准确率有所提升（可选验证）

---

**文档版本**: 1.0
**创建日期**: 2025-11-04
**维护者**: 开发团队
