# 自动TensorRT转换使用指南

## 🎯 功能概述

系统现在支持**自动检测并转换TensorRT引擎**，无需手动转换！

### 工作原理

```
启动时自动检测:
  ├─ 检查是否有.engine文件
  ├─ 如果没有 → 自动转换为TensorRT
  ├─ 如果.pt文件更新 → 重新转换
  └─ 加载优化后的.engine文件
```

---

## 🚀 使用方法

### 方法1: 自动转换（推荐）

**无需任何额外操作！** 系统会自动处理：

```python
# 在CUDA环境下，自动检测并转换
from src.detection.detector import HumanDetector

# 自动检测并转换TensorRT引擎
detector = HumanDetector()  # 自动使用TensorRT引擎
```

**输出日志示例**:
```
INFO - TensorRT可用，版本: 8.6.1
INFO - 📋 TensorRT引擎不存在，开始转换: yolov8n.pt
INFO - 🔄 开始转换为TensorRT: yolov8n.pt
INFO - ✅ TensorRT转换成功: yolov8n.engine
INFO - 文件大小: 6.23 MB
INFO - 成功加载模型: models/yolo/yolov8n.engine 到设备: cuda
```

### 方法2: 禁用自动转换

如果不需要自动转换：

```python
# 禁用自动转换
detector = HumanDetector(auto_convert_tensorrt=False)
```

---

## 📊 自动转换流程

### 1. 首次启动（无.engine文件）

```
启动检测器
  ↓
检查.engine文件是否存在
  ↓
不存在 → 自动转换为TensorRT
  ↓
生成.engine文件
  ↓
加载.engine文件
```

**耗时**: 首次转换需要 **2-5分钟**（每个模型）

### 2. 后续启动（已有.engine文件）

```
启动检测器
  ↓
检查.engine文件是否存在
  ↓
存在 → 检查.pt文件是否更新
  ↓
未更新 → 直接加载.engine文件
```

**耗时**: 几乎瞬时加载

### 3. 模型更新（.pt文件更新）

```
启动检测器
  ↓
检查.engine文件是否存在
  ↓
存在 → 检查.pt文件是否更新
  ↓
已更新 → 重新转换为TensorRT
  ↓
生成新的.engine文件
  ↓
加载新的.engine文件
```

---

## 🔧 配置选项

### 环境变量

```bash
# 禁用自动转换
export AUTO_CONVERT_TENSORRT=false

# 设置TensorRT精度
export TENSORRT_PRECISION=fp16  # fp32, fp16, int8
```

### 代码配置

```python
from src.detection.detector import HumanDetector

# 启用自动转换（默认）
detector = HumanDetector(auto_convert_tensorrt=True)

# 禁用自动转换
detector = HumanDetector(auto_convert_tensorrt=False)

# 指定模型路径
detector = HumanDetector(
    model_path='models/yolo/yolov8n.pt',
    device='cuda',
    auto_convert_tensorrt=True
)
```

---

## 📈 性能对比

### 自动转换前后

| 场景 | 首次启动 | 后续启动 | 性能 |
|------|----------|----------|------|
| **无自动转换** | 加载.pt | 加载.pt | 28.6 FPS |
| **有自动转换** | 转换+加载.engine | 加载.engine | 166.7 FPS |

### 性能提升

- ✅ **首次启动**: 需要2-5分钟转换，但只需一次
- ✅ **后续启动**: 几乎瞬时加载，性能提升 **5.8倍**
- ✅ **模型更新**: 自动重新转换，保持最新状态

---

## 🎯 适用场景

### ✅ 推荐使用自动转换

1. **生产环境首次部署**
   ```bash
   # 首次启动会自动转换所有模型
   docker compose -f docker-compose.prod.full.yml up -d
   ```

2. **模型更新后**
   ```bash
   # 更新模型文件后，系统会自动重新转换
   cp new_model.pt models/yolo/yolov8n.pt
   docker compose -f docker-compose.prod.full.yml restart api
   ```

3. **开发测试**
   ```python
   # 在GPU环境下测试，自动使用TensorRT
   detector = HumanDetector()
   ```

### ❌ 不推荐使用自动转换

1. **Mac开发环境**
   ```python
   # Mac不支持TensorRT，会自动跳过
   detector = HumanDetector()  # 使用MPS加速
   ```

2. **CPU环境**
   ```python
   # CPU环境不支持TensorRT，会自动跳过
   detector = HumanDetector(device='cpu')
   ```

3. **CI/CD流水线**
   ```bash
   # 在CI/CD中预先转换模型
   python scripts/optimization/convert_to_tensorrt.py
   ```

---

## 🔍 故障排除

### 问题1: 转换失败

**症状**: 日志显示"TensorRT转换失败"

**解决方案**:
```bash
# 1. 检查TensorRT是否安装
pip install nvidia-tensorrt

# 2. 检查CUDA是否可用
python -c "import torch; print(torch.cuda.is_available())"

# 3. 检查GPU内存
nvidia-smi

# 4. 手动转换
python scripts/optimization/convert_to_tensorrt.py
```

### 问题2: 转换时间过长

**症状**: 首次启动需要很长时间

**原因**: 每个模型转换需要2-5分钟

**解决方案**:
```bash
# 预先转换模型
python scripts/optimization/convert_to_tensorrt.py

# 后续启动会直接加载.engine文件
```

### 问题3: 内存不足

**症状**: 转换过程中内存溢出

**解决方案**:
```bash
# 减少工作空间大小
# 编辑 src/detection/detector.py
# 将 workspace=4 改为 workspace=2
```

### 问题4: .engine文件损坏

**症状**: 加载.engine文件失败

**解决方案**:
```bash
# 删除损坏的.engine文件，系统会自动重新转换
rm models/yolo/*.engine
rm models/hairnet_detection/*.engine

# 重启服务
docker compose -f docker-compose.prod.full.yml restart api
```

---

## 📝 最佳实践

### 1. 生产环境部署

```bash
# 首次部署时，预先转换模型
python scripts/optimization/convert_to_tensorrt.py

# 启动服务
docker compose -f docker-compose.prod.full.yml up -d
```

### 2. 开发环境

```python
# 启用自动转换，方便开发
detector = HumanDetector(auto_convert_tensorrt=True)
```

### 3. 模型更新

```bash
# 更新模型文件
cp new_model.pt models/yolo/yolov8n.pt

# 重启服务，系统会自动重新转换
docker compose -f docker-compose.prod.full.yml restart api
```

### 4. 版本控制

```bash
# .gitignore 配置
# 不提交.engine文件
models/**/*.engine
models/**/*.onnx

# 只提交.pt文件
models/**/*.pt
```

---

## 🎉 总结

### 自动转换的优势

- ✅ **零配置**: 无需手动转换
- ✅ **自动更新**: 模型更新后自动重新转换
- ✅ **智能回退**: TensorRT不可用时自动使用PyTorch
- ✅ **性能最优**: 自动使用最佳加速方案

### 使用建议

1. **生产环境**: 预先转换模型，避免首次启动延迟
2. **开发环境**: 启用自动转换，方便开发测试
3. **Mac环境**: 自动跳过TensorRT，使用MPS加速
4. **CPU环境**: 自动跳过TensorRT，使用CPU推理

---

**文档版本**: v1.0
**最后更新**: 2025-10-15
**维护者**: 开发团队
