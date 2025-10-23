# =================================================================
# 第一阶段: 构建器 (Builder)
#
# 这个阶段负责安装所有编译时依赖，并构建Python依赖包。
# 它的产物将被复制到最终的生产镜像中，而它本身会被丢弃。
# =================================================================
ARG CUDA_IMAGE=nvidia/cuda:12.4.0-runtime-ubuntu22.04
FROM ${CUDA_IMAGE} AS builder

WORKDIR /app

# 安装编译时所需的系统依赖，包括Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制项目文件（requirements.txt 中有 -e . 需要 pyproject.toml）
COPY pyproject.toml requirements.txt ./
COPY src ./src

# 在一个独立的虚拟环境中构建依赖，便于后续复制
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 使用缓存安装依赖，加速后续构建
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

# =================================================================
# 第二阶段: 生产镜像 (Production Image)
#
# 这是最终的、轻量级的生产镜像。
# 它只包含运行应用所必需的依赖和代码。
# =================================================================
ARG CUDA_IMAGE=nvidia/cuda:12.4.0-runtime-ubuntu22.04
FROM ${CUDA_IMAGE}

# 安装运行时所需的系统依赖，包括Python (比构建器少得多)
# 注意: libgl1-mesa-glx 在GPU容器中通常不需要(由NVIDIA驱动提供OpenGL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    libglib2.0-0 libgomp1 curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 创建非root用户以提升安全
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 从构建器阶段复制已安装的Python依赖，并设置所有权
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# 复制项目源代码，并设置所有权
COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 设置环境变量，并激活虚拟环境
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 暴露API端口
EXPOSE 8000

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认启动命令 (运行API服务)
CMD ["python", "main.py", "--mode", "api", "--host", "0.0.0.0"]
