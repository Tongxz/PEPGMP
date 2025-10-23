# Mac环境优化方案

## 🍎 Mac环境限制

### TensorRT不支持Mac

- ❌ TensorRT仅支持NVIDIA GPU (CUDA)
- ❌ Mac使用AMD/Intel集成显卡或Apple Silicon GPU
- ❌ 无法直接使用TensorRT进行模型加速

---

## 🔄 Mac环境替代优化方案

### 方案1: 使用MPS (Metal Performance Shaders) - 推荐

Apple Silicon (M1/M2/M3) 支持MPS加速：

```python
# 自动使用MPS（已在代码中实现）
from src.detection.detector import HumanDetector

# 系统会自动检测并使用MPS
detector = HumanDetector(device='auto')  # 自动选择MPS
```

**性能提升**: 相比CPU提升 **2-3倍**

### 方案2: 使用CoreML优化

将PyTorch模型转换为CoreML格式：

```python
# scripts/optimization/convert_to_coreml.py
from ultralytics import YOLO
import coremltools as ct

def convert_to_coreml(model_path: str, output_path: str):
    """转换为CoreML格式"""

    # 加载YOLO模型
    model = YOLO(model_path)

    # 导出为CoreML
    model.export(
        format='coreml',
        imgsz=640,
        nms=True,
        simplify=True
    )

    print(f"✅ CoreML模型已生成: {output_path}")

# 转换模型
convert_to_coreml(
    'models/yolo/yolov8n.pt',
    'models/yolo/yolov8n.mlpackage'
)
```

**性能提升**: 相比CPU提升 **3-5倍**

### 方案3: 使用ONNX Runtime优化

将模型转换为ONNX并使用ONNX Runtime：

```python
# scripts/optimization/convert_to_onnx.py
from ultralytics import YOLO

def convert_to_onnx(model_path: str):
    """转换为ONNX格式"""

    # 加载YOLO模型
    model = YOLO(model_path)

    # 导出为ONNX
    model.export(
        format='onnx',
        imgsz=640,
        simplify=True,
        opset=12
    )

    print(f"✅ ONNX模型已生成")

# 转换模型
convert_to_onnx('models/yolo/yolov8n.pt')
```

**性能提升**: 相比CPU提升 **1.5-2倍**

---

## 📊 性能对比

| 方案 | Mac环境 | 性能提升 | 难度 | 推荐度 |
|------|---------|----------|------|--------|
| **MPS** | ✅ 支持 | 2-3倍 | 简单 | ⭐⭐⭐⭐⭐ |
| **CoreML** | ✅ 支持 | 3-5倍 | 中等 | ⭐⭐⭐⭐ |
| **ONNX Runtime** | ✅ 支持 | 1.5-2倍 | 简单 | ⭐⭐⭐ |
| **TensorRT** | ❌ 不支持 | 5-10倍 | - | - |

---

## 🚀 推荐实施步骤

### 步骤1: 使用MPS加速（最简单）

```bash
# 无需额外操作，代码已支持MPS
# 系统会自动检测并使用MPS

# 运行检测
python main.py --mode detection --input tests/fixtures/videos/test_video.mp4
```

### 步骤2: 转换为CoreML（最佳性能）

```bash
# 1. 安装依赖
pip install coremltools

# 2. 转换模型
python scripts/optimization/convert_to_coreml.py

# 3. 使用CoreML模型
# 修改代码以使用CoreML模型
```

### 步骤3: 转换为ONNX（备选）

```bash
# 1. 安装依赖
pip install onnx onnxruntime

# 2. 转换模型
python scripts/optimization/convert_to_onnx.py

# 3. 使用ONNX模型
# 修改代码以使用ONNX模型
```

---

## 🔧 创建Mac优化脚本

### 1. CoreML转换脚本

```python
# scripts/optimization/convert_to_coreml.py
#!/usr/bin/env python
"""
CoreML模型转换脚本 - Mac优化方案
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_to_coreml(model_path: str, output_path: str = None):
    """转换为CoreML格式"""

    try:
        from ultralytics import YOLO
        import coremltools as ct

        # 检查模型文件
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"模型文件不存在: {model_path}")
            return False

        logger.info(f"开始转换为CoreML: {model_path}")

        # 加载模型
        model = YOLO(str(model_path))

        # 导出为CoreML
        model.export(
            format='coreml',
            imgsz=640,
            nms=True,
            simplify=True,
            verbose=True
        )

        logger.info(f"✅ CoreML模型转换成功")
        return True

    except Exception as e:
        logger.error(f"❌ CoreML转换失败: {e}")
        return False

def convert_all_models():
    """转换所有模型"""

    models = [
        'models/yolo/yolov8n.pt',
        'models/hairnet_detection/hairnet_detection.pt',
        'models/yolo/yolov8n-pose.pt'
    ]

    for model_path in models:
        logger.info(f"\n转换模型: {model_path}")
        convert_to_coreml(model_path)

if __name__ == '__main__':
    convert_all_models()
```

### 2. ONNX转换脚本

```python
# scripts/optimization/convert_to_onnx.py
#!/usr/bin/env python
"""
ONNX模型转换脚本 - Mac优化方案
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_to_onnx(model_path: str):
    """转换为ONNX格式"""

    try:
        from ultralytics import YOLO

        # 检查模型文件
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"模型文件不存在: {model_path}")
            return False

        logger.info(f"开始转换为ONNX: {model_path}")

        # 加载模型
        model = YOLO(str(model_path))

        # 导出为ONNX
        model.export(
            format='onnx',
            imgsz=640,
            simplify=True,
            opset=12,
            dynamic=False,
            verbose=True
        )

        logger.info(f"✅ ONNX模型转换成功")
        return True

    except Exception as e:
        logger.error(f"❌ ONNX转换失败: {e}")
        return False

def convert_all_models():
    """转换所有模型"""

    models = [
        'models/yolo/yolov8n.pt',
        'models/hairnet_detection/hairnet_detection.pt',
        'models/yolo/yolov8n-pose.pt'
    ]

    for model_path in models:
        logger.info(f"\n转换模型: {model_path}")
        convert_to_onnx(model_path)

if __name__ == '__main__':
    convert_all_models()
```

---

## 📊 Mac环境性能优化建议

### 1. 使用MPS（推荐）

```python
# 代码已自动支持MPS
# 无需修改，系统会自动选择最佳设备

from src.detection.detector import HumanDetector

# 自动选择: MPS (Apple Silicon) > CUDA > CPU
detector = HumanDetector(device='auto')
```

**性能**: 相比CPU提升 **2-3倍**

### 2. 优化推理参数

```python
# 减少输入图像大小以提高速度
detector = HumanDetector(
    model_path='models/yolo/yolov8n.pt',
    device='mps',  # 明确使用MPS
    imgsz=480      # 降低输入尺寸
)
```

### 3. 使用批处理

```python
# 批量处理图像以提高吞吐量
images = [img1, img2, img3, ...]
results = detector.detect_batch(images)
```

---

## 🎯 实际建议

### 如果您在Mac上开发，但要在GPU服务器上部署：

**工作流程**:
1. **Mac上**: 开发和测试代码
2. **Linux服务器上**: 转换TensorRT模型
3. **部署**: 使用TensorRT引擎

```bash
# 在Mac上开发
git add .
git commit -m "feat: 添加新功能"
git push

# 在Linux服务器上转换
ssh user@server
cd /path/to/project
git pull
python scripts/optimization/convert_to_tensorrt.py

# 在Mac上拉取转换后的模型
git pull
```

### 如果只在Mac上运行：

**使用MPS加速**（最简单）:
```bash
# 无需额外操作，代码已支持MPS
python main.py --mode detection --input video.mp4
```

**性能**: 相比CPU提升 **2-3倍**

---

## 📝 总结

### Mac环境优化方案

| 方案 | 性能提升 | 实施难度 | 推荐度 |
|------|----------|----------|--------|
| **MPS** | 2-3倍 | 简单 | ⭐⭐⭐⭐⭐ |
| **CoreML** | 3-5倍 | 中等 | ⭐⭐⭐⭐ |
| **ONNX Runtime** | 1.5-2倍 | 简单 | ⭐⭐⭐ |

### 推荐策略

1. **开发阶段**: 使用Mac + MPS
2. **生产部署**: 使用Linux + TensorRT
3. **性能优化**: 在Linux服务器上转换TensorRT模型

---

**文档版本**: v1.0
**最后更新**: 2025-10-15
**维护者**: 开发团队
