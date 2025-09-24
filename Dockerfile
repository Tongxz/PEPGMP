# =================================================================
# 第一阶段: 构建器 (Builder)
#
# 这个阶段负责安装所有编译时依赖，并构建Python依赖包。
# 它的产物将被复制到最终的生产镜像中，而它本身会被丢弃。
# =================================================================
FROM python:3.10-slim as builder

WORKDIR /app

# 安装编译时所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# 仅复制依赖定义文件
COPY requirements.txt .

# 在一个独立的虚拟环境中构建依赖，便于后续复制
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 使用缓存安装依赖，加速后续构建
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

# =================================================================
# 第二阶段: 生产镜像 (Production Image)
#
# 这是最终的、轻量级的生产镜像。
# 它只包含运行应用所必需的依赖和代码。
# =================================================================
FROM python:3.10-slim

WORKDIR /app

# 安装运行时所需的系统依赖 (比构建器少得多)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建器阶段复制已安装的Python依赖
COPY --from=builder /opt/venv /opt/venv

# 复制项目源代码
COPY . .

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
