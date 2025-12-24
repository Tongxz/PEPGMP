# TensorRT 模型转换机制说明

## 📋 概述

系统在部署启动后会自动检查并转换 YOLO 模型为 TensorRT 格式，以优化推理性能。TensorRT 是 NVIDIA 的深度学习推理优化库，可以将模型转换为针对特定 GPU 优化的引擎格式。

---

## 🔄 转换触发时机

TensorRT 转换在以下时机自动触发：

### 1. API 服务启动时

**调用链：**
```
src/api/app.py::lifespan()
  └─> src/services/detection_service.py::initialize_detection_services()
      └─> src/detection/detector.py::HumanDetector.__init__()
          └─> _auto_convert_to_tensorrt()
```

### 2. 转换条件检查

转换只在满足以下条件时执行：

- ✅ **设备必须是 CUDA** (`device == "cuda"`)
- ✅ **TensorRT 库必须可用** (`import tensorrt` 成功)
- ✅ **CUDA 可用** (`torch.cuda.is_available()` 返回 `True`)
- ✅ **模型文件 (.pt) 必须存在**

### 3. 是否需要转换的判断

系统会检查以下条件：

| 条件 | 动作 |
|------|------|
| `.engine` 文件不存在 | ✅ 需要转换 |
| `.pt` 文件修改时间比 `.engine` 文件新 | ✅ 需要重新转换 |
| `.engine` 文件已存在且较新 | ⏭️ 跳过转换，直接使用 |

---

## ⚙️ 转换流程

### 转换逻辑位置

`src/detection/detector.py::_auto_convert_to_tensorrt()`

### 详细步骤

1. **设备检查**
   - 如果设备不是 `cuda`，直接返回原始模型路径

2. **TensorRT 可用性检查**
   ```python
   try:
       import tensorrt as trt
       logger.info(f"TensorRT可用，版本: {trt.__version__}")
   except ImportError:
       logger.info("TensorRT未安装，使用PyTorch模型")
       return model_path
   ```

3. **CUDA 可用性检查**
   ```python
   if not torch.cuda.is_available():
       logger.info("CUDA不可用，使用PyTorch模型")
       return model_path
   ```

4. **模型文件检查**
   - 检查 `.pt` 文件是否存在
   - 生成对应的 `.engine` 文件路径（同目录，扩展名改为 `.engine`）

5. **转换必要性判断**
   - 如果 `.engine` 不存在，标记需要转换
   - 如果 `.pt` 文件的 `mtime` > `.engine` 文件的 `mtime`，标记需要重新转换

6. **执行转换**（如果需要）
   ```python
   from ultralytics import YOLO
   model = YOLO(str(pt_file))
   model.export(
       format="engine",      # TensorRT engine 格式
       device=0,             # GPU 设备索引
       imgsz=640,            # 输入图像尺寸
       half=True,            # FP16 精度
       workspace=4,          # 4GB 工作空间
       simplify=True,        # 简化模型
       opset=12,             # ONNX opset 版本
       dynamic=False,        # 静态输入尺寸
       verbose=False,        # 不输出详细信息
   )
   ```

7. **转换结果验证**
   - 检查 `.engine` 文件是否生成成功
   - 记录文件大小
   - 返回引擎文件路径

---

## 🔧 配置控制

### 环境变量

**变量名：** `AUTO_CONVERT_TENSORRT`

**配置文件中的默认值：** `false`（在 `.env` 和配置生成脚本中）

**代码中的默认值：** `True`（如果环境变量完全未设置，为了向后兼容）

**取值：**
- `true` / `1` / `yes` → 启用自动转换
- `false` / `0` / `no` → 禁用自动转换
- 未设置（且没有通过 dotenv 加载配置文件）→ 使用代码默认值 `True`

**注意：**
- 在实际部署中，通常通过 `.env` 文件或配置生成脚本设置该变量为 `false`（开发环境）或 `true`（生产环境）
- 如果环境变量完全未设置（例如直接运行 Python 代码），为了向后兼容，默认启用转换

### 代码中的配置

**位置：** `src/detection/detector.py::HumanDetector.__init__()`

**参数：** `auto_convert_tensorrt: Optional[bool] = None`

**优先级：**
1. **显式参数**（如果调用时传入 `True` 或 `False`）
2. **环境变量** `AUTO_CONVERT_TENSORRT`（如果参数为 `None`）
3. **默认值** `True`（如果环境变量也未设置）

**示例：**
```python
# 方式1：从环境变量读取（推荐）
detector = HumanDetector()  # auto_convert_tensorrt=None，从环境变量读取

# 方式2：显式指定
detector = HumanDetector(auto_convert_tensorrt=True)   # 强制启用
detector = HumanDetector(auto_convert_tensorrt=False)  # 强制禁用
```

---

## 📝 日志输出

### 转换过程日志

**开始转换：**
```
📋 TensorRT引擎不存在，开始转换: yolov8s.pt
🔄 开始转换为TensorRT: yolov8s.pt
```

**转换成功：**
```
✅ TensorRT转换成功: yolov8s.engine
   文件大小: 45.23 MB
```

**跳过转换：**
```
✅ TensorRT引擎已存在: yolov8s.engine
```

**转换失败或条件不满足：**
```
TensorRT未安装，使用PyTorch模型
设备为 cpu，跳过TensorRT转换
CUDA不可用，使用PyTorch模型
TensorRT自动转换失败: <错误信息>
回退到PyTorch模型
```

---

## 🎯 使用场景

### 生产环境

**推荐配置：**
```bash
# .env 或 docker-compose.yml
AUTO_CONVERT_TENSORRT=true
```

**优势：**
- 首次启动时自动转换，后续使用优化后的引擎
- 性能提升明显（通常 2-5 倍加速）
- 转换后的引擎文件会被缓存，不会重复转换

**注意事项：**
- 首次转换可能需要几分钟时间（取决于模型大小）
- 需要确保 TensorRT 库已正确安装
- `.engine` 文件是针对特定 GPU 架构优化的，不能跨设备使用

### 开发环境

**推荐配置：**
```bash
# .env
AUTO_CONVERT_TENSORRT=false
```

**原因：**
- 开发时经常修改模型，频繁转换浪费时间
- 开发环境可能没有 GPU 或 TensorRT
- 快速迭代，不需要极致性能

---

## 🔍 故障排查

### 问题1：转换失败

**症状：** 日志显示 "TensorRT自动转换失败"

**可能原因：**
1. TensorRT 未安装或版本不兼容
2. CUDA 版本不匹配
3. 模型文件损坏
4. 磁盘空间不足

**解决方案：**
1. 检查 TensorRT 安装：`python -c "import tensorrt; print(tensorrt.__version__)"`
2. 检查 CUDA 版本：`nvidia-smi`
3. 验证模型文件完整性
4. 检查磁盘空间：`df -h`

### 问题2：转换后性能没有提升

**可能原因：**
1. 模型太小，优化效果不明显
2. 批量大小设置不当
3. 输入尺寸不匹配

**解决方案：**
1. 使用更大的模型（如 `yolov8m.pt` 或 `yolov8l.pt`）
2. 调整 `workspace` 参数（增加到 8GB 或更大）
3. 确保输入图像尺寸与 `imgsz=640` 匹配

### 问题3：转换时间过长

**可能原因：**
1. 模型太大
2. GPU 性能不足
3. 工作空间设置过大

**解决方案：**
1. 使用更小的模型（如 `yolov8n.pt`）
2. 首次转换可以接受，后续使用缓存的引擎文件
3. 适当减小 `workspace` 参数（但不要太小，可能影响优化效果）

---

## 📊 性能对比

### 典型性能提升（RTX 3090）

| 模型 | PyTorch (ms) | TensorRT FP16 (ms) | 加速比 |
|------|--------------|-------------------|--------|
| yolov8n.pt | 8.5 | 3.2 | 2.7x |
| yolov8s.pt | 15.3 | 5.8 | 2.6x |
| yolov8m.pt | 28.7 | 10.2 | 2.8x |
| yolov8l.pt | 45.2 | 16.8 | 2.7x |

**注意：** 实际性能取决于 GPU 型号、驱动版本、TensorRT 版本等因素。

---

## 🔗 相关文件

- `src/detection/detector.py` - TensorRT 转换实现
- `src/services/detection_service.py` - 检测服务初始化
- `src/api/app.py` - API 应用生命周期
- `src/config/env_config.py` - 环境配置管理
- `.env` - 环境变量配置文件
- `scripts/docker-entrypoint.sh` - Docker 容器启动脚本

---

## 🚀 生产环境配置示例

### 启用 TensorRT 转换

**在 `.env.production` 中设置：**
```bash
# TensorRT Configuration
AUTO_CONVERT_TENSORRT=true
```

**使用配置生成脚本：**
```bash
# 使用 scripts/generate_production_config.sh 生成配置时
# 手动编辑 .env.production，将 AUTO_CONVERT_TENSORRT=false 改为 true
```

**验证配置：**
```bash
# 在容器中检查环境变量
docker exec pepgmp-api-prod env | grep AUTO_CONVERT_TENSORRT

# 查看启动日志，确认转换状态
docker logs pepgmp-api-prod | grep -i tensorrt
```

### 首次转换时间

首次启用 TensorRT 转换时，模型转换可能需要：
- **yolov8n.pt**: 约 1-2 分钟
- **yolov8s.pt**: 约 2-3 分钟
- **yolov8m.pt**: 约 3-5 分钟
- **yolov8l.pt**: 约 5-8 分钟

转换完成后，`.engine` 文件会被缓存，后续启动会直接使用，无需重新转换。

### 检查转换结果

```bash
# 检查 .engine 文件是否生成
docker exec pepgmp-api-prod ls -lh /app/models/yolo/*.engine

# 查看转换日志
docker logs pepgmp-api-prod 2>&1 | grep -A 5 "TensorRT"

# 验证模型加载
docker logs pepgmp-api-prod 2>&1 | grep "成功加载模型"
```

---

## 📚 参考资料

- [TensorRT 官方文档](https://docs.nvidia.com/deeplearning/tensorrt/)
- [Ultralytics YOLO 导出文档](https://docs.ultralytics.com/modes/export/)
- [NVIDIA TensorRT 开发者指南](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/)

---

## ✅ 总结

TensorRT 模型转换机制在 API 服务启动时自动运行，通过环境变量 `AUTO_CONVERT_TENSORRT` 控制是否启用。转换后的引擎文件会被缓存，只有在模型更新时才会重新转换。这一机制在生产环境中可以显著提升推理性能。

### NVIDIA Blackwell 架构（RTX 5070）特殊要求

对于 NVIDIA Blackwell 架构（sm_120）的显卡，需要使用：
- **CUDA**: 12.8（已在 Dockerfile.prod 中配置）
- **TensorRT**: 10.8 或更高版本（推荐使用最新版本）
- **PyTorch**: 2.7.0.dev+ 或 2.8+ 基于 CUDA 12.8 的开发版本（通过 nightly/cu128 自动获取）

这些要求已经在 Dockerfile.prod 中正确配置。
