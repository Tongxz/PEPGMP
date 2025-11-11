# 快速参考卡片

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install -e .

# NVIDIA GPU 用户
pip install -e ".[gpu-nvidia]"

# ML 功能
pip install -e ".[ml]"

# 组合安装
pip install -e ".[gpu-nvidia-ml]"
```

### 运行

```bash
# 检测模式
python main.py --mode detection --source 0 --camera-id test

# API服务
python main.py --mode api --port 8000
```

---

## 📦 可选依赖组

| 命令 | 说明 |
|------|------|
| `pip install -e ".[gpu-nvidia]"` | NVIDIA GPU 监控 |
| `pip install -e ".[ml]"` | XGBoost ML分类器 |
| `pip install -e ".[gpu-nvidia-ml]"` | GPU + ML 组合 |
| `pip install -e ".[dev]"` | 开发工具 |
| `pip install -e ".[production]"` | 生产环境 |

---

## ⚙️ 配置启用

### XGBoost ML分类器

```yaml
# config/unified_params.yaml
behavior_recognition:
  use_ml_classifier: true
  ml_model_path: models/handwash_xgb.json
  ml_window: 30
  ml_fusion_alpha: 0.7
```

---

## 🔍 验证命令

```bash
# 检查XGBoost
python -c "import xgboost; print('✅ XGBoost已安装')"

# 检查配置
python -c "from src.config.unified_params import get_unified_params; print(get_unified_params().behavior_recognition.use_ml_classifier)"

# 检查模型文件
ls -lh models/handwash_xgb.json
```

---

## 📚 文档链接

- [最近更新索引](./RECENT_UPDATES_INDEX.md)
- [XGBoost分析](./XGBOOST_ANALYSIS.md)
- [XGBoost启用指南](./XGBOOST_ENABLE_GUIDE.md)
- [依赖管理指南](./OPTIONAL_DEPENDENCIES.md)

---

**最后更新**: 2025-11-04
