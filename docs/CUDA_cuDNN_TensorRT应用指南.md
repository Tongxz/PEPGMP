# CUDA、cuDNN、TensorRT核心库应用指南

## 📊 执行摘要

本指南详细阐述如何将CUDA、cuDNN、TensorRT等核心库应用到项目中，实现**2-10倍的性能提升**。

### 核心库作用
- **CUDA**: NVIDIA GPU并行计算平台
- **cuDNN**: 深度神经网络加速库
- **TensorRT**: 高性能深度学习推理引擎
- **Torch-TensorRT**: PyTorch与TensorRT集成

---

## 🎯 一、核心库概述

### 1.1 库的作用和关系

```
应用层
  ↓
PyTorch / TensorFlow
  ↓
CUDA Runtime API
  ↓
cuDNN (深度神经网络加速)
  ↓
TensorRT (推理优化引擎)
  ↓
GPU硬件
```

### 1.2 性能提升对比

| 优化方案 | 速度提升 | 精度影响 | 实施难度 | 推荐场景 |
|----------|----------|----------|----------|----------|
| CUDA基础 | 2-3倍 | 无 | 低 | 所有GPU环境 |
| cuDNN优化 | +30-50% | 无 | 低 | 深度学习模型 |
| TensorRT FP32 | 3-5倍 | 无 | 中 | 生产推理 |
| TensorRT FP16 | 5-10倍 | ±0.1% | 中 | 实时推理 |
| TensorRT INT8 | 10-20倍 | -1-3% | 高 | 边缘设备 |

---

## ⚡ 二、CUDA应用

### 2.1 CUDA基础配置

#### 当前状态分析
**代码位置**: `src/utils/gpu_acceleration.py:135-178`

```python
def _apply_cuda_optimizations(self, device_info: Dict[str, Any]) -> list:
    """应用CUDA优化设置"""
    optimizations = []

    # 1. 环境变量优化
    cuda_env = {
        "CUDA_LAUNCH_BLOCKING": "0",  # 异步执行
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512,roundup_power2_divisions:16",
        "CUBLAS_WORKSPACE_CONFIG": ":16:8",
        "CUDA_MODULE_LOADING": "LAZY",
        "TORCH_CUDNN_V8_API_ENABLED": "1",
    }

    # 2. CuDNN优化
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False

    # 3. TF32优化 (Ampere架构)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    return optimizations
```

#### CUDA环境变量详解

```bash
# 1. CUDA_LAUNCH_BLOCKING
# 控制CUDA核函数的执行模式
export CUDA_LAUNCH_BLOCKING=0  # 异步执行，提升性能

# 2. PYTORCH_CUDA_ALLOC_CONF
# PyTorch CUDA内存分配器配置
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512,roundup_power2_divisions:16"
# - max_split_size_mb: 最大内存块大小
# - roundup_power2_divisions: 内存对齐优化

# 3. CUBLAS_WORKSPACE_CONFIG
# cuBLAS工作空间配置
export CUBLAS_WORKSPACE_CONFIG=":16:8"
# 格式: :<前向>:<后向>

# 4. CUDA_MODULE_LOADING
# CUDA模块加载策略
export CUDA_MODULE_LOADING="LAZY"  # 延迟加载，减少启动时间

# 5. TORCH_CUDNN_V8_API_ENABLED
# 启用cuDNN v8 API
export TORCH_CUDNN_V8_API_ENABLED="1"
```

### 2.2 CUDA流优化

#### 多流并行处理

```python
import torch
import torch.cuda as cuda

class CudaStreamManager:
    """CUDA流管理器"""

    def __init__(self, num_streams=4):
        self.num_streams = num_streams
        self.streams = [cuda.Stream() for _ in range(num_streams)]
        self.current_stream = 0

    def get_stream(self):
        """获取当前流"""
        stream = self.streams[self.current_stream]
        self.current_stream = (self.current_stream + 1) % self.num_streams
        return stream

    def synchronize_all(self):
        """同步所有流"""
        for stream in self.streams:
            stream.synchronize()

# 使用示例
stream_manager = CudaStreamManager(num_streams=4)

def parallel_inference(model, images):
    """并行推理"""
    results = []

    for i, image in enumerate(images):
        stream = stream_manager.get_stream()

        with cuda.stream(stream):
            # 数据移动到GPU
            image_gpu = image.cuda(non_blocking=True)

            # 推理
            with torch.no_grad():
                result = model(image_gpu)

            results.append(result.cpu())

    # 同步所有流
    stream_manager.synchronize_all()

    return results
```

### 2.3 CUDA内存池优化

```python
class CudaMemoryPool:
    """CUDA内存池管理器"""

    def __init__(self):
        self.pool = {}

    def allocate(self, shape, dtype=torch.float32):
        """分配内存"""
        key = (shape, dtype)

        if key not in self.pool:
            self.pool[key] = torch.empty(shape, dtype=dtype, device='cuda')

        return self.pool[key]

    def clear(self):
        """清空内存池"""
        self.pool.clear()
        torch.cuda.empty_cache()

# 使用示例
memory_pool = CudaMemoryPool()

def optimized_inference(model, image):
    """优化的推理"""
    # 从内存池分配
    image_gpu = memory_pool.allocate(image.shape, image.dtype)
    image_gpu.copy_(image)

    # 推理
    with torch.no_grad():
        result = model(image_gpu)

    return result
```

---

## 🚀 三、cuDNN应用

### 3.1 cuDNN自动调优

#### 当前配置
**代码位置**: `src/utils/gpu_acceleration.py:156-159`

```python
# CuDNN优化
torch.backends.cudnn.benchmark = True
torch.backends.cudnn.deterministic = False
```

#### 深度优化

```python
def configure_cudnn_optimizations():
    """配置cuDNN优化"""
    import torch

    # 1. 启用基准测试模式
    # 自动选择最优算法，适合固定输入尺寸
    torch.backends.cudnn.benchmark = True

    # 2. 非确定性模式
    # 允许使用非确定性算法，提升性能
    torch.backends.cudnn.deterministic = False

    # 3. TF32优化 (Ampere架构)
    # 使用TensorFloat-32精度，提升性能
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # 4. 允许使用cuDNN
    torch.backends.cudnn.enabled = True

    # 5. 设置cuDNN版本
    if hasattr(torch.backends.cudnn, 'version'):
        print(f"cuDNN版本: {torch.backends.cudnn.version()}")

# 在程序启动时调用
configure_cudnn_optimizations()
```

### 3.2 cuDNN算法选择

```python
def select_optimal_cudnn_algorithm(conv_layer, input_shape):
    """选择最优cuDNN算法"""
    import torch
    import torch.nn as nn

    # 创建测试输入
    x = torch.randn(*input_shape).cuda()

    # 获取所有可用算法
    algorithms = []

    # 测试不同算法
    for algo in ['IMPLICIT_GEMM', 'IMPLICIT_PRECOMP_GEMM',
                 'GEMM', 'DIRECT', 'FFT', 'FFT_TILING',
                 'WINOGRAD', 'WINOGRAD_NONFUSED']:
        try:
            # 设置算法
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True

            # 测试性能
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)

            start.record()
            _ = conv_layer(x)
            end.record()

            torch.cuda.synchronize()
            elapsed_time = start.elapsed_time(end)

            algorithms.append((algo, elapsed_time))
        except:
            pass

    # 选择最快的算法
    best_algo = min(algorithms, key=lambda x: x[1])

    return best_algo[0]
```

### 3.3 cuDNN性能监控

```python
class CudnnProfiler:
    """cuDNN性能分析器"""

    def __init__(self):
        self.profiles = []

    def profile_conv_layer(self, conv_layer, input_shape):
        """分析卷积层性能"""
        import torch

        # 预热
        x = torch.randn(*input_shape).cuda()
        for _ in range(10):
            _ = conv_layer(x)

        # 性能测试
        torch.cuda.synchronize()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)

        start.record()
        for _ in range(100):
            _ = conv_layer(x)
        end.record()

        torch.cuda.synchronize()
        elapsed_time = start.elapsed_time(end) / 100

        self.profiles.append({
            'layer': conv_layer,
            'input_shape': input_shape,
            'elapsed_time': elapsed_time
        })

        return elapsed_time

    def report(self):
        """生成报告"""
        total_time = sum(p['elapsed_time'] for p in self.profiles)

        print("cuDNN性能分析报告:")
        print(f"总时间: {total_time:.2f}ms")
        print("\n各层性能:")
        for i, profile in enumerate(self.profiles):
            print(f"  层{i}: {profile['elapsed_time']:.2f}ms")
```

---

## 🔥 四、TensorRT应用

### 4.1 TensorRT基础

#### 什么是TensorRT
TensorRT是NVIDIA的高性能深度学习推理引擎，可以将训练好的模型优化为高效的推理引擎。

#### 性能优势
- **速度提升**: 3-10倍
- **内存优化**: 减少50-70%
- **精度保持**: FP32几乎无损，FP16损失<0.1%

### 4.2 TensorRT安装

#### 前置条件
```bash
# 1. 检查CUDA版本
nvcc --version

# 2. 检查cuDNN版本
cat /usr/local/cuda/include/cudnn_version.h | grep CUDNN_MAJOR

# 3. 检查GPU计算能力
nvidia-smi --query-gpu=compute_cap --format=csv
```

#### 安装步骤

```bash
# 方式1: 使用pip安装
pip install nvidia-tensorrt

# 方式2: 使用torch-tensorrt (推荐)
pip install torch-tensorrt

# 方式3: 从NVIDIA官网下载
# https://developer.nvidia.com/tensorrt
```

#### 验证安装

```python
import tensorrt as trt
import torch_tensorrt

print(f"TensorRT版本: {trt.__version__}")
print(f"Torch-TensorRT版本: {torch_tensorrt.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
```

### 4.3 YOLOv8 TensorRT优化

#### 方法1: 使用YOLO原生导出

```bash
# 导出为TensorRT格式
yolo export model=yolov8s.pt format=tensorrt device=0

# 导出为TensorRT FP16
yolo export model=yolov8s.pt format=tensorrt device=0 half=True

# 导出为TensorRT INT8
yolo export model=yolov8s.pt format=tensorrt device=0 int8=True

# 指定输入尺寸
yolo export model=yolov8s.pt format=tensorrt device=0 imgsz=640
```

#### 方法2: 使用torch-tensorrt

```python
import torch
import torch_tensorrt

# 加载PyTorch模型
model = YOLO("yolov8s.pt")
model.eval()

# 准备输入
example_input = torch.randn(1, 3, 640, 640).cuda()

# 编译为TensorRT
trt_model = torch_tensorrt.compile(
    model,
    inputs=[example_input],
    enabled_precisions={torch.half},  # FP16
    workspace_size=1 << 30,  # 1GB工作空间
    min_block_size=7,
    torch_executed_ops={"torch.ops.aten.add"}  # 指定在PyTorch中执行的算子
)

# 保存TensorRT模型
torch.jit.save(trt_model, "yolov8s_trt.ts")

# 加载TensorRT模型
trt_model = torch.jit.load("yolov8s_trt.ts")
```

#### 方法3: ONNX → TensorRT

```python
# 步骤1: 导出ONNX
yolo export model=yolov8s.pt format=onnx

# 步骤2: ONNX转TensorRT
import tensorrt as trt

def onnx_to_tensorrt(onnx_path, trt_path, fp16=True):
    """ONNX转TensorRT"""
    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    )
    parser = trt.OnnxParser(network, logger)

    # 解析ONNX模型
    with open(onnx_path, 'rb') as model:
        if not parser.parse(model.read()):
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return False

    # 配置构建器
    config = builder.create_builder_config()
    config.max_workspace_size = 1 << 30  # 1GB

    if fp16:
        config.set_flag(trt.BuilderFlag.FP16)

    # 构建引擎
    engine = builder.build_engine(network, config)

    # 保存引擎
    with open(trt_path, 'wb') as f:
        f.write(engine.serialize())

    return True

# 使用
onnx_to_tensorrt("yolov8s.onnx", "yolov8s.trt", fp16=True)
```

### 4.4 集成到项目

#### 创建TensorRT检测器

```python
# src/detection/tensorrt_detector.py
import torch
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
import numpy as np

class TensorRTDetector:
    """TensorRT检测器"""

    def __init__(self, engine_path, input_shape=(1, 3, 640, 640)):
        self.input_shape = input_shape
        self.engine = self._load_engine(engine_path)
        self.context = self.engine.create_execution_context()

        # 分配GPU内存
        self.inputs, self.outputs, self.bindings, self.stream = \
            self._allocate_buffers()

    def _load_engine(self, engine_path):
        """加载TensorRT引擎"""
        with open(engine_path, 'rb') as f:
            engine_data = f.read()

        logger = trt.Logger(trt.Logger.WARNING)
        runtime = trt.Runtime(logger)
        engine = runtime.deserialize_cuda_engine(engine_data)

        return engine

    def _allocate_buffers(self):
        """分配GPU内存"""
        inputs = []
        outputs = []
        bindings = []
        stream = cuda.Stream()

        for binding in self.engine:
            size = trt.volume(self.engine.get_binding_shape(binding)) * \
                   self.engine.max_batch_size
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))

            # 分配主机和设备内存
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)

            bindings.append(int(device_mem))

            if self.engine.binding_is_input(binding):
                inputs.append({'host': host_mem, 'device': device_mem})
            else:
                outputs.append({'host': host_mem, 'device': device_mem})

        return inputs, outputs, bindings, stream

    def detect(self, image):
        """执行检测"""
        # 预处理图像
        input_data = self._preprocess(image)

        # 复制到GPU
        np.copyto(self.inputs[0]['host'], input_data.ravel())
        cuda.memcpy_htod_async(
            self.inputs[0]['device'],
            self.inputs[0]['host'],
            self.stream
        )

        # 执行推理
        self.context.execute_async_v2(
            bindings=self.bindings,
            stream_handle=self.stream.handle
        )

        # 复制结果回CPU
        cuda.memcpy_dtoh_async(
            self.outputs[0]['host'],
            self.outputs[0]['device'],
            self.stream
        )
        self.stream.synchronize()

        # 后处理
        output = self.outputs[0]['host']
        results = self._postprocess(output)

        return results

    def _preprocess(self, image):
        """预处理图像"""
        # 实现预处理逻辑
        pass

    def _postprocess(self, output):
        """后处理输出"""
        # 实现后处理逻辑
        pass
```

#### 集成到检测管道

```python
# src/core/optimized_detection_pipeline.py
from src.detection.tensorrt_detector import TensorRTDetector

class OptimizedDetectionPipeline:
    """优化的检测管道"""

    def __init__(self, use_tensorrt=True):
        self.use_tensorrt = use_tensorrt

        if use_tensorrt:
            # 使用TensorRT检测器
            self.human_detector = TensorRTDetector(
                "models/yolo/yolov8s.trt",
                input_shape=(1, 3, 640, 640)
            )
        else:
            # 使用标准检测器
            self.human_detector = HumanDetector()

    def detect_comprehensive(self, image):
        """综合检测"""
        # 使用优化的检测器
        person_detections = self.human_detector.detect(image)

        # 后续处理...
        return result
```

### 4.5 TensorRT性能对比

#### 基准测试

```python
import time

def benchmark_model(model, input_shape, num_iterations=100):
    """基准测试"""
    import torch

    # 准备输入
    input_data = torch.randn(*input_shape).cuda()

    # 预热
    for _ in range(10):
        _ = model(input_data)

    torch.cuda.synchronize()

    # 测试
    start = time.time()
    for _ in range(num_iterations):
        _ = model(input_data)
    torch.cuda.synchronize()
    end = time.time()

    avg_time = (end - start) / num_iterations * 1000  # ms
    fps = 1000 / avg_time

    return avg_time, fps

# 测试不同模型
models = {
    'PyTorch FP32': pytorch_model_fp32,
    'PyTorch FP16': pytorch_model_fp16,
    'TensorRT FP32': trt_model_fp32,
    'TensorRT FP16': trt_model_fp16,
    'TensorRT INT8': trt_model_int8,
}

for name, model in models.items():
    avg_time, fps = benchmark_model(model, (1, 3, 640, 640))
    print(f"{name}: {avg_time:.2f}ms ({fps:.1f} FPS)")
```

#### 预期性能

| 模型 | 延迟 (ms) | FPS | 速度提升 |
|------|-----------|-----|----------|
| PyTorch FP32 | 30-40 | 25-33 | 1x |
| PyTorch FP16 | 20-25 | 40-50 | 1.5x |
| TensorRT FP32 | 10-15 | 67-100 | 3x |
| TensorRT FP16 | 5-8 | 125-200 | 6x |
| TensorRT INT8 | 3-5 | 200-333 | 10x |

---

## 🎯 五、完整集成方案

### 5.1 创建TensorRT优化模块

```python
# src/optimization/tensorrt_optimizer.py
import torch
import torch_tensorrt
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TensorRTOptimizer:
    """TensorRT优化器"""

    def __init__(self, model, input_shape=(1, 3, 640, 640)):
        self.model = model
        self.input_shape = input_shape
        self.optimized_model = None

    def optimize(self, precision='fp16', workspace_size=1<<30):
        """优化模型"""
        logger.info(f"开始TensorRT优化，精度: {precision}")

        try:
            # 准备示例输入
            example_input = torch.randn(*self.input_shape).cuda()

            # 编译配置
            enabled_precisions = set()
            if precision == 'fp16':
                enabled_precisions = {torch.half}
            elif precision == 'int8':
                enabled_precisions = {torch.int8}

            # 编译模型
            self.optimized_model = torch_tensorrt.compile(
                self.model,
                inputs=[example_input],
                enabled_precisions=enabled_precisions,
                workspace_size=workspace_size,
                min_block_size=7,
                truncate_long_and_double=True,
            )

            logger.info("TensorRT优化完成")
            return self.optimized_model

        except Exception as e:
            logger.error(f"TensorRT优化失败: {e}")
            return None

    def save(self, path):
        """保存优化后的模型"""
        if self.optimized_model is not None:
            torch.jit.save(self.optimized_model, path)
            logger.info(f"模型已保存到: {path}")
        else:
            logger.error("模型未优化，无法保存")

    def load(self, path):
        """加载优化后的模型"""
        self.optimized_model = torch.jit.load(path)
        logger.info(f"模型已从{path}加载")
        return self.optimized_model
```

### 5.2 集成到GPU管理器

```python
# src/utils/gpu_acceleration.py
from src.optimization.tensorrt_optimizer import TensorRTOptimizer

class GPUAccelerationManager:
    """GPU加速管理器"""

    def __init__(self):
        self.device = "cpu"
        self.gpu_info = {}
        self.optimization_applied = False
        self.performance_config = {}
        self.tensorrt_optimizer = None

    def initialize_tensorrt(self, model, precision='fp16'):
        """初始化TensorRT"""
        if not torch.cuda.is_available():
            logger.warning("CUDA不可用，无法使用TensorRT")
            return None

        # 创建TensorRT优化器
        self.tensorrt_optimizer = TensorRTOptimizer(model)

        # 优化模型
        optimized_model = self.tensorrt_optimizer.optimize(precision=precision)

        return optimized_model

    def get_optimized_model(self, model_type='yolo'):
        """获取优化的模型"""
        if self.tensorrt_optimizer is not None:
            return self.tensorrt_optimizer.optimized_model
        return None
```

### 5.3 配置管理

```yaml
# config/unified_params.yaml
tensorrt:
  enabled: true
  precision: fp16  # fp32, fp16, int8
  workspace_size: 1073741824  # 1GB
  min_block_size: 7
  save_path: models/tensorrt/

  # 模型配置
  models:
    human_detection:
      enabled: true
      input_shape: [1, 3, 640, 640]
      precision: fp16
    hairnet_detection:
      enabled: true
      input_shape: [1, 3, 224, 224]
      precision: fp16
    pose_detection:
      enabled: false
      input_shape: [1, 3, 640, 640]
      precision: fp16
```

### 5.4 自动优化脚本

```python
# scripts/optimization/auto_tensorrt_optimization.py
import torch
from src.optimization.tensorrt_optimizer import TensorRTOptimizer
from src.detection.detector import HumanDetector
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector
from config.unified_params import get_unified_params

def auto_optimize_models():
    """自动优化所有模型"""
    params = get_unified_params()

    # 1. 优化人体检测模型
    if params.tensorrt.models.human_detection.enabled:
        print("优化人体检测模型...")
        human_detector = HumanDetector()
        optimizer = TensorRTOptimizer(
            human_detector.model,
            input_shape=params.tensorrt.models.human_detection.input_shape
        )
        optimizer.optimize(precision=params.tensorrt.models.human_detection.precision)
        optimizer.save(f"{params.tensorrt.save_path}/human_detection.trt")

    # 2. 优化发网检测模型
    if params.tensorrt.models.hairnet_detection.enabled:
        print("优化发网检测模型...")
        hairnet_detector = YOLOHairnetDetector()
        optimizer = TensorRTOptimizer(
            hairnet_detector.model,
            input_shape=params.tensorrt.models.hairnet_detection.input_shape
        )
        optimizer.optimize(precision=params.tensorrt.models.hairnet_detection.precision)
        optimizer.save(f"{params.tensorrt.save_path}/hairnet_detection.trt")

    print("所有模型优化完成！")

if __name__ == "__main__":
    auto_optimize_models()
```

---

## 📊 六、性能对比

### 6.1 完整基准测试

```python
# scripts/benchmark/gpu_benchmark.py
import time
import torch
from src.utils.gpu_acceleration import initialize_gpu_acceleration
from src.detection.detector import HumanDetector
from src.optimization.tensorrt_optimizer import TensorRTOptimizer

def benchmark_all():
    """全面基准测试"""
    results = {}

    # 初始化GPU
    gpu_info = initialize_gpu_acceleration()
    print(f"GPU: {gpu_info['gpu_name']}")
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"cuDNN版本: {torch.backends.cudnn.version()}")
    print()

    # 准备输入
    input_shape = (1, 3, 640, 640)
    input_data = torch.randn(*input_shape).cuda()

    # 测试1: PyTorch FP32
    print("测试 PyTorch FP32...")
    model_fp32 = HumanDetector().model.cuda()
    model_fp32.eval()

    avg_time, fps = benchmark_model(model_fp32, input_data)
    results['PyTorch FP32'] = {'time': avg_time, 'fps': fps}
    print(f"  延迟: {avg_time:.2f}ms, FPS: {fps:.1f}")

    # 测试2: PyTorch FP16
    print("测试 PyTorch FP16...")
    model_fp16 = model_fp32.half()

    avg_time, fps = benchmark_model(model_fp16, input_data.half())
    results['PyTorch FP16'] = {'time': avg_time, 'fps': fps}
    print(f"  延迟: {avg_time:.2f}ms, FPS: {fps:.1f}")

    # 测试3: TensorRT FP32
    print("测试 TensorRT FP32...")
    optimizer_fp32 = TensorRTOptimizer(model_fp32)
    model_trt_fp32 = optimizer_fp32.optimize(precision='fp32')

    avg_time, fps = benchmark_model(model_trt_fp32, input_data)
    results['TensorRT FP32'] = {'time': avg_time, 'fps': fps}
    print(f"  延迟: {avg_time:.2f}ms, FPS: {fps:.1f}")

    # 测试4: TensorRT FP16
    print("测试 TensorRT FP16...")
    optimizer_fp16 = TensorRTOptimizer(model_fp32)
    model_trt_fp16 = optimizer_fp16.optimize(precision='fp16')

    avg_time, fps = benchmark_model(model_trt_fp16, input_data)
    results['TensorRT FP16'] = {'time': avg_time, 'fps': fps}
    print(f"  延迟: {avg_time:.2f}ms, FPS: {fps:.1f}")

    # 生成报告
    print("\n性能对比报告:")
    print("-" * 60)
    print(f"{'模型':<20} {'延迟(ms)':<15} {'FPS':<15} {'速度提升':<15}")
    print("-" * 60)

    baseline_fps = results['PyTorch FP32']['fps']
    for name, metrics in results.items():
        speedup = metrics['fps'] / baseline_fps
        print(f"{name:<20} {metrics['time']:<15.2f} {metrics['fps']:<15.1f} {speedup:<15.2f}x")

    return results

def benchmark_model(model, input_data, num_iterations=100):
    """基准测试模型"""
    # 预热
    for _ in range(10):
        with torch.no_grad():
            _ = model(input_data)

    torch.cuda.synchronize()

    # 测试
    start = time.time()
    for _ in range(num_iterations):
        with torch.no_grad():
            _ = model(input_data)
    torch.cuda.synchronize()
    end = time.time()

    avg_time = (end - start) / num_iterations * 1000  # ms
    fps = 1000 / avg_time

    return avg_time, fps

if __name__ == "__main__":
    results = benchmark_all()
```

### 6.2 预期性能提升

| 优化方案 | 延迟 (ms) | FPS | 速度提升 | 精度影响 |
|----------|-----------|-----|----------|----------|
| PyTorch FP32 | 35 | 28.6 | 1.0x | 基准 |
| PyTorch FP16 | 22 | 45.5 | 1.6x | ±0.1% |
| TensorRT FP32 | 12 | 83.3 | 2.9x | 无 |
| TensorRT FP16 | 6 | 166.7 | 5.8x | ±0.1% |
| TensorRT INT8 | 4 | 250.0 | 8.7x | -1-3% |

---

## 🎯 七、实施路线图

### 7.1 阶段一：基础CUDA优化 (1周)

#### 任务清单
- [ ] 验证CUDA环境
- [ ] 配置CUDA环境变量
- [ ] 启用cuDNN优化
- [ ] 测试性能提升

#### 预期效果
- 速度提升: 2-3倍
- 精度影响: 无

### 7.2 阶段二：TensorRT集成 (2-3周)

#### 任务清单
- [ ] 安装TensorRT
- [ ] 创建TensorRT优化器
- [ ] 优化人体检测模型
- [ ] 优化发网检测模型
- [ ] 集成到检测管道

#### 预期效果
- 速度提升: 5-10倍
- 精度影响: ±0.1%

### 7.3 阶段三：高级优化 (3-4周)

#### 任务清单
- [ ] CUDA流优化
- [ ] 内存池管理
- [ ] 多GPU并行
- [ ] 动态批处理

#### 预期效果
- 速度提升: 10-20倍
- 精度影响: 无

---

## 📝 八、总结

### 8.1 核心要点

1. **CUDA**: 基础GPU加速，2-3倍提升
2. **cuDNN**: 深度神经网络优化，+30-50%提升
3. **TensorRT**: 高性能推理引擎，5-10倍提升
4. **组合使用**: 可实现10-20倍性能提升

### 8.2 推荐配置

```yaml
# 生产环境推荐
tensorrt:
  enabled: true
  precision: fp16
  workspace_size: 1073741824

cuda:
  streams: 4
  memory_pool: true
  benchmark: true

cudnn:
  benchmark: true
  deterministic: false
  tf32: true
```

### 8.3 实施建议

1. **立即开始**: 启用CUDA和cuDNN优化 (1天)
2. **第一周**: 集成TensorRT (2-3天)
3. **第二周**: 优化所有模型 (3-4天)
4. **第三周**: 高级优化和测试 (5-7天)

---

**文档版本**: v1.0
**最后更新**: 2025-10-15
**维护者**: 开发团队
