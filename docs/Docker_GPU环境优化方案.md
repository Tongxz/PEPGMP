# Docker + GPU环境优化方案

## 📊 执行摘要

本方案专门针对Docker+GPU生产环境，提供CUDA、cuDNN、TensorRT的完整优化配置和使用指南。

### 核心优势
- ✅ **Docker容器化**: 环境一致性和可移植性
- ✅ **GPU加速**: CUDA、cuDNN、TensorRT完整支持
- ✅ **生产就绪**: 优化的Dockerfile和配置
- ✅ **性能提升**: 5-10倍推理速度提升

---

## 🎯 一、Docker + GPU环境架构

### 1.1 环境组件

```
┌─────────────────────────────────────────────┐
│         Docker Host (Ubuntu 22.04)          │
│  ┌───────────────────────────────────────┐  │
│  │   NVIDIA Driver (≥470.57.02)         │  │
│  │   CUDA Toolkit (12.4.0)              │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│  ┌───────────▼───────────────────────────┐  │
│  │   NVIDIA Container Toolkit           │  │
│  │   - nvidia-container-runtime         │  │
│  │   - nvidia-container-cli             │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│  ┌───────────▼───────────────────────────┐  │
│  │   Docker Engine (20.10+)             │  │
│  │   - GPU Support                      │  │
│  │   - CUDA Runtime                     │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│  ┌───────────▼───────────────────────────┐  │
│  │   Application Container              │  │
│  │   - PyTorch + CUDA                   │  │
│  │   - TensorRT                         │  │
│  │   - cuDNN                            │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 1.2 核心技术栈

| 组件 | 版本 | 作用 |
|------|------|------|
| **NVIDIA Driver** | ≥470.57.02 | GPU驱动 |
| **CUDA Toolkit** | 12.4.0 | GPU计算平台 |
| **cuDNN** | 8.9.0 | 深度学习加速 |
| **TensorRT** | 8.6.0 | 推理优化引擎 |
| **PyTorch** | 2.2.0+ | 深度学习框架 |
| **Docker** | 20.10+ | 容器化平台 |
| **NVIDIA Container Toolkit** | 1.13+ | GPU容器支持 |

---

## 🐳 二、Dockerfile优化

### 2.1 基础镜像选择

#### 方案A：官方CUDA镜像（推荐）

```dockerfile
# 使用NVIDIA官方CUDA镜像
ARG CUDA_VERSION=12.4.0
ARG UBUNTU_VERSION=22.04
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

# 优势：
# - 官方维护，稳定可靠
# - 预装CUDA Runtime
# - 支持多架构（amd64, arm64）
# - 自动处理GPU设备映射
```

#### 方案B：PyTorch官方镜像

```dockerfile
# 使用PyTorch官方镜像
FROM pytorch/pytorch:2.2.0-cuda12.4-cudnn8-runtime

# 优势：
# - 预装PyTorch和CUDA
# - 包含cuDNN
# - 开箱即用
```

### 2.2 优化的Dockerfile

```dockerfile
# =================================================================
# 阶段1: 构建器 (Builder)
# =================================================================
ARG CUDA_VERSION=12.4.0
ARG UBUNTU_VERSION=22.04
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装TensorRT
RUN pip install --no-cache-dir nvidia-tensorrt

# =================================================================
# 阶段2: 运行时镜像 (Runtime)
# =================================================================
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    libpython3.10 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 从构建器复制虚拟环境
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# 复制应用代码
COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# CUDA环境变量
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# PyTorch CUDA优化
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
ENV TORCH_CUDNN_V8_API_ENABLED=1

# TensorRT优化
ENV TENSORRT_LOGGER_LEVEL=WARNING

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py", "--mode", "api", "--host", "0.0.0.0"]
```

### 2.3 多阶段构建优化

```dockerfile
# =================================================================
# 阶段1: 基础环境
# =================================================================
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 AS base

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# =================================================================
# 阶段2: 依赖构建
# =================================================================
FROM base AS dependencies

WORKDIR /app

# 创建虚拟环境
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# =================================================================
# 阶段3: TensorRT构建
# =================================================================
FROM dependencies AS tensorrt

# 安装TensorRT
RUN pip install --no-cache-dir nvidia-tensorrt && \
    pip install --no-cache-dir torch-tensorrt

# =================================================================
# 阶段4: 最终镜像
# =================================================================
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    libpython3.10 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建用户
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 复制虚拟环境
COPY --from=tensorrt --chown=appuser:appuser /opt/venv /opt/venv

# 复制应用代码
COPY --chown=appuser:appuser . .

# 切换用户
USER appuser

# 环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
ENV TORCH_CUDNN_V8_API_ENABLED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py", "--mode", "api", "--host", "0.0.0.0"]
```

---

## 🚀 三、Docker Compose配置

### 3.1 GPU支持配置

```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        CUDA_VERSION: 12.4.0
        UBUNTU_VERSION: 22.04

    # GPU支持配置
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

    # 环境变量
    environment:
      - ENVIRONMENT=production
      - CUDA_VISIBLE_DEVICES=0
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
      - TORCH_CUDNN_V8_API_ENABLED=1
      - TENSORRT_LOGGER_LEVEL=WARNING

    ports:
      - "8000:8000"

    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./output:/app/output
      - ./models:/app/models:ro

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    restart: unless-stopped
```

### 3.2 完整生产配置

```yaml
version: "3.8"

networks:
  pyt-prod-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

services:
  # PostgreSQL数据库
  database:
    image: postgres:16-alpine
    container_name: pyt-postgres-prod
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-pyt_production}
      POSTGRES_USER: ${POSTGRES_USER:-pyt_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    networks:
      - pyt-prod-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-pyt_user} -d ${POSTGRES_DB:-pyt_production}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: pyt-redis-prod
    command: >
      redis-server
      --appendonly yes
      --requirepass ${REDIS_PASSWORD:-change_me}
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    networks:
      - pyt-prod-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
    restart: unless-stopped

  # 后端API (GPU加速)
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        CUDA_VERSION: ${CUDA_VERSION:-12.4.0}
        UBUNTU_VERSION: ${UBUNTU_VERSION:-22.04}

    container_name: pyt-api-prod

    # GPU支持
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

    environment:
      # 应用配置
      - ENVIRONMENT=production
      - LOG_LEVEL=${LOG_LEVEL:-INFO}

      # 数据库配置
      - DATABASE_URL=postgresql://${POSTGRES_USER:-pyt_user}:${POSTGRES_PASSWORD:-change_me}@database:5432/${POSTGRES_DB:-pyt_production}

      # Redis配置
      - REDIS_URL=redis://:${REDIS_PASSWORD:-change_me}@redis:6379/0

      # 安全配置
      - SECRET_KEY=${SECRET_KEY:-change_me}
      - JWT_SECRET=${JWT_SECRET:-change_me}

      # CUDA配置
      - CUDA_VISIBLE_DEVICES=0
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility

      # PyTorch CUDA优化
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
      - TORCH_CUDNN_V8_API_ENABLED=1

      # TensorRT配置
      - TENSORRT_LOGGER_LEVEL=WARNING
      - TENSORRT_ENABLED=${TENSORRT_ENABLED:-true}
      - TENSORRT_PRECISION=${TENSORRT_PRECISION:-fp16}

      # 性能优化
      - BATCH_SIZE=${BATCH_SIZE:-8}
      - ENABLE_AMP=${ENABLE_AMP:-true}
      - ENABLE_TTA=${ENABLE_TTA:-false}

    ports:
      - "${API_PORT:-8000}:8000"

    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./output:/app/output
      - ./models:/app/models:ro
      - ./data:/app/data

    networks:
      - pyt-prod-network

    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    restart: unless-stopped

  # 前端
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
      args:
        VITE_API_BASE: ${VITE_API_BASE:-/api/v1}
        BASE_URL: ${BASE_URL:-/}

    container_name: pyt-frontend-prod

    ports:
      - "${FRONTEND_PORT:-8080}:80"

    networks:
      - pyt-prod-network

    depends_on:
      api:
        condition: service_healthy

    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

    restart: unless-stopped
```

---

## ⚡ 四、CUDA优化配置

### 4.1 环境变量优化

```bash
# .env 文件
# ============================================
# CUDA配置
# ============================================
CUDA_VISIBLE_DEVICES=0
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

# PyTorch CUDA优化
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,roundup_power2_divisions:16
TORCH_CUDNN_V8_API_ENABLED=1

# CUDA流优化
CUDA_LAUNCH_BLOCKING=0
CUDA_MODULE_LOADING=LAZY

# cuBLAS优化
CUBLAS_WORKSPACE_CONFIG=:16:8

# TensorRT配置
TENSORRT_LOGGER_LEVEL=WARNING
TENSORRT_ENABLED=true
TENSORRT_PRECISION=fp16
```

### 4.2 运行时优化

```python
# src/utils/gpu_acceleration.py
import torch
import os

def configure_cuda_optimizations():
    """配置CUDA优化"""
    if not torch.cuda.is_available():
        return

    # 1. 环境变量设置
    os.environ.setdefault("CUDA_LAUNCH_BLOCKING", "0")
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512,roundup_power2_divisions:16")
    os.environ.setdefault("TORCH_CUDNN_V8_API_ENABLED", "1")

    # 2. CuDNN优化
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False

    # 3. TF32优化 (Ampere架构)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # 4. 内存管理
    torch.cuda.empty_cache()

    print(f"✅ CUDA优化配置完成")
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA版本: {torch.version.cuda}")
    print(f"   cuDNN版本: {torch.backends.cudnn.version()}")
```

---

## 🔥 五、TensorRT集成

### 5.1 TensorRT优化器

```python
# src/optimization/tensorrt_optimizer.py
import torch
import torch_tensorrt
import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)

class TensorRTOptimizer:
    """TensorRT优化器"""

    def __init__(self, model, input_shape=(1, 3, 640, 640)):
        self.model = model
        self.input_shape = input_shape
        self.optimized_model = None
        self.enabled = os.getenv("TENSORRT_ENABLED", "false").lower() == "true"
        self.precision = os.getenv("TENSORRT_PRECISION", "fp16")

    def optimize(self, precision: Optional[str] = None, workspace_size: int = 1<<30):
        """优化模型"""
        if not self.enabled:
            logger.info("TensorRT未启用，跳过优化")
            return None

        precision = precision or self.precision
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

            logger.info(f"✅ TensorRT优化完成，精度: {precision}")
            return self.optimized_model

        except Exception as e:
            logger.error(f"TensorRT优化失败: {e}")
            return None

    def save(self, path: str):
        """保存优化后的模型"""
        if self.optimized_model is not None:
            torch.jit.save(self.optimized_model, path)
            logger.info(f"模型已保存到: {path}")
        else:
            logger.error("模型未优化，无法保存")

    def load(self, path: str):
        """加载优化后的模型"""
        self.optimized_model = torch.jit.load(path)
        logger.info(f"模型已从{path}加载")
        return self.optimized_model
```

### 5.2 集成到检测器

```python
# src/detection/detector.py
from src.optimization.tensorrt_optimizer import TensorRTOptimizer

class HumanDetector(BaseDetector):
    """人体检测器 - 支持TensorRT优化"""

    def __init__(self, model_path: Optional[str] = None, device: str = "auto"):
        super().__init__(model_path or "models/yolo/yolov8s.pt", device)

        # TensorRT优化
        self.tensorrt_optimizer = TensorRTOptimizer(
            self.model,
            input_shape=(1, 3, 640, 640)
        )

        if self.tensorrt_optimizer.enabled:
            logger.info("启用TensorRT优化")
            self.model = self.tensorrt_optimizer.optimize()

    def detect(self, image: np.ndarray) -> List[Dict]:
        """执行检测"""
        if self.model is None:
            raise RuntimeError("模型未加载")

        # 使用优化后的模型进行推理
        with torch.no_grad():
            results = self.model(image)

        # 后处理
        detections = self._postprocess(results)

        return detections
```

### 5.3 自动优化脚本

```python
# scripts/optimization/auto_tensorrt_optimization.py
import torch
from src.optimization.tensorrt_optimizer import TensorRTOptimizer
from src.detection.detector import HumanDetector
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector
import os

def auto_optimize_models():
    """自动优化所有模型"""
    print("🚀 开始自动TensorRT优化...")

    # 设置环境变量
    os.environ["TENSORRT_ENABLED"] = "true"
    os.environ["TENSORRT_PRECISION"] = "fp16"

    # 1. 优化人体检测模型
    print("\n1. 优化人体检测模型...")
    human_detector = HumanDetector()
    if human_detector.model is not None:
        optimizer = TensorRTOptimizer(
            human_detector.model,
            input_shape=(1, 3, 640, 640)
        )
        optimized_model = optimizer.optimize(precision='fp16')
        if optimized_model:
            optimizer.save("models/tensorrt/human_detection_fp16.trt")
            print("   ✅ 人体检测模型优化完成")

    # 2. 优化发网检测模型
    print("\n2. 优化发网检测模型...")
    hairnet_detector = YOLOHairnetDetector()
    if hairnet_detector.model is not None:
        optimizer = TensorRTOptimizer(
            hairnet_detector.model,
            input_shape=(1, 3, 224, 224)
        )
        optimized_model = optimizer.optimize(precision='fp16')
        if optimized_model:
            optimizer.save("models/tensorrt/hairnet_detection_fp16.trt")
            print("   ✅ 发网检测模型优化完成")

    print("\n🎉 所有模型优化完成！")

if __name__ == "__main__":
    auto_optimize_models()
```

---

## 📊 六、性能基准测试

### 6.1 基准测试脚本

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

    if model_trt_fp32:
        avg_time, fps = benchmark_model(model_trt_fp32, input_data)
        results['TensorRT FP32'] = {'time': avg_time, 'fps': fps}
        print(f"  延迟: {avg_time:.2f}ms, FPS: {fps:.1f}")

    # 测试4: TensorRT FP16
    print("测试 TensorRT FP16...")
    optimizer_fp16 = TensorRTOptimizer(model_fp32)
    model_trt_fp16 = optimizer_fp16.optimize(precision='fp16')

    if model_trt_fp16:
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

### 6.2 预期性能

| 优化方案 | 延迟 (ms) | FPS | 速度提升 | 精度影响 |
|----------|-----------|-----|----------|----------|
| PyTorch FP32 | 35 | 28.6 | 1.0x | 基准 |
| PyTorch FP16 | 22 | 45.5 | 1.6x | ±0.1% |
| TensorRT FP32 | 12 | 83.3 | 2.9x | 无 |
| TensorRT FP16 | 6 | 166.7 | 5.8x | ±0.1% |
| TensorRT INT8 | 4 | 250.0 | 8.7x | -1-3% |

---

## 🚀 七、部署流程

### 7.1 完整部署步骤

```bash
# 1. 检查GPU环境
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.0-runtime-ubuntu22.04 nvidia-smi

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 构建镜像
docker compose -f docker-compose.prod.full.yml build

# 4. 启动服务
docker compose -f docker-compose.prod.full.yml up -d

# 5. 查看日志
docker compose -f docker-compose.prod.full.yml logs -f api

# 6. 验证服务
curl http://localhost:8000/health

# 7. 运行基准测试
docker exec pyt-api-prod python scripts/benchmark/gpu_benchmark.py
```

### 7.2 优化模型

```bash
# 1. 进入容器
docker exec -it pyt-api-prod bash

# 2. 运行自动优化
python scripts/optimization/auto_tensorrt_optimization.py

# 3. 验证优化后的模型
python scripts/benchmark/gpu_benchmark.py

# 4. 重启服务
exit
docker compose -f docker-compose.prod.full.yml restart api
```

---

## 📈 八、监控和调优

### 8.1 GPU监控

```bash
# 实时监控GPU
watch -n 1 nvidia-smi

# Docker容器GPU使用
docker stats pyt-api-prod
```

### 8.2 性能调优

```yaml
# docker-compose.prod.full.yml
api:
  environment:
    # 批处理大小
    - BATCH_SIZE=8

    # 混合精度
    - ENABLE_AMP=true

    # TensorRT
    - TENSORRT_ENABLED=true
    - TENSORRT_PRECISION=fp16

    # 测试时增强
    - ENABLE_TTA=false
```

---

## 🎯 九、最佳实践

### 9.1 Docker镜像优化

- ✅ 使用多阶段构建
- ✅ 使用官方CUDA镜像
- ✅ 最小化镜像大小
- ✅ 使用非root用户
- ✅ 设置健康检查

### 9.2 GPU优化

- ✅ 启用cuDNN benchmark
- ✅ 使用TF32精度
- ✅ 优化内存分配
- ✅ 启用TensorRT
- ✅ 使用FP16推理

### 9.3 生产配置

- ✅ 使用环境变量配置
- ✅ 启用日志轮转
- ✅ 设置资源限制
- ✅ 配置健康检查
- ✅ 启用自动重启

---

## 🎉 总结

### 快速部署命令

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env 文件

# 2. 启动服务
docker compose -f docker-compose.prod.full.yml up -d

# 3. 优化模型
docker exec pyt-api-prod python scripts/optimization/auto_tensorrt_optimization.py

# 4. 验证性能
docker exec pyt-api-prod python scripts/benchmark/gpu_benchmark.py

# 5. 查看日志
docker compose -f docker-compose.prod.full.yml logs -f api
```

### 性能提升总结

| 优化项 | 性能提升 | 实施难度 |
|--------|----------|----------|
| CUDA基础优化 | 2-3倍 | 低 |
| cuDNN优化 | +30-50% | 低 |
| TensorRT FP16 | 5-10倍 | 中 |
| 完整优化 | 10-20倍 | 中 |

---

**文档版本**: v1.0
**最后更新**: 2025-10-15
**维护者**: 开发团队
