# Docker 构建缓存失效分析报告

## 📋 问题描述

即使代码和依赖文件没有任何改动，Docker 构建时仍然会重新下载所有依赖（PyTorch、Python 包等），导致构建时间过长。

---

## 🔍 根本原因分析

### 1. ⚠️ PyTorch Nightly 版本（最严重）

**位置**: `Dockerfile.prod` 第 66-68 行

```dockerfile
RUN if [ "${TORCH_INSTALL_MODE}" = "nightly" ]; then \
      python3 -m pip install --user --no-cache-dir --pre \
        torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}" ; \
```

**问题**:
- ✅ 使用了 `--pre` 参数安装 **nightly** 版本
- ❌ **没有指定版本号**，pip 每次都会尝试获取最新的 nightly 版本
- ❌ **nightly 版本每天都在更新**，即使本地有缓存，pip 也会检查远程是否有更新
- ❌ 由于没有版本锁定，Docker 层缓存无法有效工作

**影响**: 每次构建都会重新下载 PyTorch（~2-3GB），耗时 5-15 分钟

---

### 2. ⚠️ pip install --upgrade（次严重）

**位置**: `Dockerfile.prod` 第 49 行

```dockerfile
RUN python3 -m pip install --upgrade pip setuptools wheel
```

**问题**:
- ✅ `--upgrade` 会尝试将 pip、setuptools、wheel 升级到最新版本
- ❌ 即使当前版本已经是最新的，这个命令也会**重新检查远程仓库**
- ❌ Docker 缓存机制认为命令相同就复用缓存，但如果 pip 版本变化，就会失效

**影响**: 每次构建都会检查并可能重新下载 pip/setuptools/wheel（虽然体积小，但会增加网络请求）

---

### 3. ⚠️ requirements.prod.txt 文件时间戳

**位置**: `Dockerfile.prod` 第 52 行

```dockerfile
COPY requirements.prod.txt /tmp/requirements.txt
```

**问题**:
- ✅ Docker 使用文件内容校验和（checksum）来判断是否需要重新构建
- ⚠️ 但是，如果文件被 Git 检出、编辑器保存、或其他操作修改了时间戳，可能会触发重新构建
- ⚠️ **实际情况**: Docker 应该使用文件内容哈希，而不是时间戳，所以这个问题通常不是主要原因

**验证方法**:
```bash
# 检查文件哈希（应该一致）
md5 requirements.prod.txt
# 或
sha256sum requirements.prod.txt
```

---

### 4. ⚠️ ARG 参数传递

**位置**: `scripts/deploy_mixed_registry.sh` 第 251-253 行

```bash
--build-arg BASE_IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04" \
--build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
--build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
```

**问题**:
- ✅ ARG 值如果变化，会导致依赖该 ARG 的层失效
- ⚠️ 如果 `TORCH_INDEX_URL` 的值变化（即使只是格式变化），会导致 PyTorch 安装层失效
- ⚠️ **实际情况**: 这些值应该是固定的，但需要确认

---

### 5. ⚠️ 没有使用 BuildKit 缓存策略

**位置**: `scripts/deploy_mixed_registry.sh` 第 246-255 行

```bash
docker buildx build \
  --builder "${BUILDER_NAME}" \
  --platform linux/amd64 \
  --pull=false \
  -f Dockerfile.prod \
  --build-arg BASE_IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04" \
  --build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
  --build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
  -t $FULL_BACKEND_IMAGE \
  --load .
```

**问题**:
- ✅ 启用了 `DOCKER_BUILDKIT=1`
- ❌ **没有使用 `--cache-from`** 指定缓存源
- ❌ **没有使用 `--cache-to`** 导出缓存（用于后续构建）
- ❌ 缺少 BuildKit 的缓存挂载（`--mount=type=cache`）

**影响**: 虽然 Docker 会自动缓存层，但没有充分利用 BuildKit 的高级缓存功能

---

### 6. ⚠️ requirements.prod.txt 中的 TensorRT（如果启用）

**位置**: `requirements.prod.txt` 第 61 行（已取消注释）

```txt
tensorrt>=10.8.0
```

**问题**:
- ✅ 如果启用了 TensorRT，使用了 `>=10.8.0` 版本约束
- ⚠️ 版本约束会允许安装更新的版本，可能导致每次构建安装不同的版本
- ⚠️ **建议**: 如果启用，应该固定版本号

---

## 📊 问题严重程度评估

| 问题 | 严重程度 | 影响范围 | 修复难度 |
|------|---------|---------|---------|
| PyTorch Nightly 版本 | 🔴 **严重** | 每次构建重新下载 ~2-3GB | 中等 |
| pip install --upgrade | 🟡 **中等** | 检查更新，可能下载 | 简单 |
| requirements.prod.txt 时间戳 | 🟢 **轻微** | 通常不是问题 | 无需修复 |
| ARG 参数传递 | 🟢 **轻微** | 如果值不变则无影响 | 无需修复 |
| BuildKit 缓存策略 | 🟡 **中等** | 可以加速，但不是必须 | 中等 |
| TensorRT 版本约束 | 🟡 **中等** | 如果启用会有影响 | 简单 |

---

## 💡 解决方案

### 方案 0: 使用 PyTorch 稳定版（强烈推荐 ⭐）

**背景**: 截至 2025 年 12 月，PyTorch 2.9.1 稳定版已支持 CUDA 12.8 和 sm_120 (Blackwell 架构)

**优势**:
- ✅ **完全支持 RTX 5070** (sm_120)
- ✅ **可以固定版本号**，解决缓存失效问题
- ✅ **稳定可靠**，无需使用 nightly 版本
- ✅ **更好的兼容性**，经过充分测试

**修改方法**:

**步骤 1**: 修改 `Dockerfile.prod`

```dockerfile
# 修改默认安装模式为 stable
ARG TORCH_INSTALL_MODE="stable"   # 从 "nightly" 改为 "stable"

# 更新版本号（PyTorch 2.9.1 稳定版）
# 注意：需要确认对应的 torchvision 和 torchaudio 版本号
# 可以通过 pip 安装时自动解析依赖，或参考 PyTorch 官方文档
ARG TORCH_VERSION="2.9.1"
ARG TORCHVISION_VERSION="0.20.1"  # 需要确认对应版本
ARG TORCHAUDIO_VERSION="2.9.1"    # 需要确认对应版本

# CUDA 12.8 索引（稳定版也支持 cu128）
ARG TORCH_INDEX_URL="https://download.pytorch.org/whl/cu128"

# 安装命令保持不变（stable 模式会使用固定版本）
RUN if [ "${TORCH_INSTALL_MODE}" = "nightly" ]; then \
      python3 -m pip install --user --no-cache-dir --pre \
        torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}" ; \
    else \
      python3 -m pip install --user --no-cache-dir \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        --index-url "${TORCH_INDEX_URL}" ; \
    fi
```

**步骤 2**: 修改部署脚本 `scripts/deploy_mixed_registry.sh`

```bash
# 修改默认安装模式
TORCH_INSTALL_MODE_DEFAULT="stable"  # 从 "nightly" 改为 "stable"

# CUDA 12.8 稳定版索引
TORCH_INDEX_URL_DEFAULT="https://download.pytorch.org/whl/cu128"
```

**验证方法**:

```bash
# 构建镜像后验证
docker run --rm pepgmp-backend:test python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"

# 应该输出：
# 2.9.1+cu128
# True
# NVIDIA GeForce RTX 5070
```

**优点**:
- ✅ **完全解决缓存失效问题**（固定版本号）
- ✅ **稳定可靠**，适合生产环境
- ✅ **完全支持 RTX 5070**
- ✅ **构建时间大幅减少**（后续构建使用缓存）

**注意事项**:
- ⚠️ 需要确认 `torchvision` 和 `torchaudio` 的对应版本号
- ⚠️ 首次构建仍需下载（但后续构建会使用缓存）

---

### 方案 1: 锁定 PyTorch Nightly 版本（备选方案）

**目标**: 避免每次构建都下载最新的 nightly 版本

**方法 1.1: 固定 nightly 版本号**

修改 `Dockerfile.prod`:

```dockerfile
# 在构建时获取最新的 nightly 版本号（可选，或者手动指定）
# ARG TORCH_NIGHTLY_VERSION="2.7.0.dev20250226+cu128"

RUN if [ "${TORCH_INSTALL_MODE}" = "nightly" ]; then \
      python3 -m pip install --user --no-cache-dir --pre \
        "torch==2.7.0.dev20250226+cu128" \
        "torchvision==0.18.0.dev20250226+cu128" \
        "torchaudio==2.7.0.dev20250226+cu128" \
        --index-url "${TORCH_INDEX_URL}" ; \
```

**优点**:
- ✅ 版本固定，Docker 缓存有效
- ✅ 构建结果可重复

**缺点**:
- ⚠️ 需要定期手动更新版本号（如果要使用最新版本）

---

**方法 1.2: 使用本地 wheel 文件缓存**

在构建前先下载 PyTorch wheel 文件到本地，然后使用本地文件安装：

```dockerfile
# 在构建脚本中先下载 wheel 文件
# pip download torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Dockerfile 中使用本地文件
COPY torch-*.whl /tmp/
RUN pip install --user --no-cache-dir /tmp/torch-*.whl
```

**优点**:
- ✅ 完全离线构建
- ✅ 版本可控

**缺点**:
- ⚠️ 需要维护本地 wheel 文件
- ⚠️ 增加构建复杂度

---

**方法 1.3: 分离 PyTorch 安装层，使用缓存挂载**

使用 BuildKit 的缓存挂载功能：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "${TORCH_INSTALL_MODE}" = "nightly" ]; then \
      python3 -m pip install --user --pre \
        torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}" ; \
```

**优点**:
- ✅ 充分利用 BuildKit 缓存
- ✅ 即使版本更新，也能部分利用缓存

**缺点**:
- ⚠️ 需要 BuildKit 支持
- ⚠️ 首次构建仍然需要下载

---

### 方案 2: 优化 pip install --upgrade

**修改 `Dockerfile.prod` 第 49 行**:

```dockerfile
# 方案 2.1: 移除 --upgrade（如果基础镜像已经有较新版本）
RUN python3 -m pip install pip setuptools wheel

# 方案 2.2: 使用版本检查，只在需要时升级
RUN python3 -m pip install --upgrade pip setuptools wheel || \
    python3 -m pip install pip setuptools wheel

# 方案 2.3: 固定版本（推荐，确保一致性）
RUN python3 -m pip install --user "pip>=24.0" "setuptools>=65.0" "wheel>=0.40"
```

**推荐**: 使用方案 2.3，固定版本号

---

### 方案 3: 优化 BuildKit 缓存策略

**修改 `scripts/deploy_mixed_registry.sh`**:

```bash
# 使用缓存挂载和缓存导入/导出
docker buildx build \
  --builder "${BUILDER_NAME}" \
  --platform linux/amd64 \
  --pull=false \
  --cache-from type=local,src=/tmp/.buildx-cache \
  --cache-to type=local,dest=/tmp/.buildx-cache,mode=max \
  -f Dockerfile.prod \
  --build-arg BASE_IMAGE="nvidia/cuda:12.8.0-runtime-ubuntu22.04" \
  --build-arg TORCH_INSTALL_MODE="$TORCH_INSTALL_MODE_DEFAULT" \
  --build-arg TORCH_INDEX_URL="$TORCH_INDEX_URL_DEFAULT" \
  -t $FULL_BACKEND_IMAGE \
  --load .
```

**优点**:
- ✅ 跨构建会话共享缓存
- ✅ 加速后续构建

**缺点**:
- ⚠️ 需要管理缓存目录
- ⚠️ 缓存可能占用磁盘空间

---

### 方案 4: 固定 TensorRT 版本（如果启用）

**修改 `requirements.prod.txt`**:

```diff
- tensorrt>=10.8.0
+ tensorrt==10.8.0  # 固定版本，确保构建可重复
```

---

## 🎯 推荐的综合解决方案

### 优先级 0: 使用 PyTorch 稳定版（强烈推荐 ⭐⭐⭐）

**推荐理由**: PyTorch 2.9.1 稳定版已支持 CUDA 12.8 和 sm_120，可以完全替代 nightly 版本

**实施步骤**:
1. 将 `TORCH_INSTALL_MODE` 改为 `"stable"`
2. 固定版本号为 `2.9.1`（torch/torchvision/torchaudio）
3. 使用稳定版索引 `https://download.pytorch.org/whl/cu128`

**预期效果**:
- ✅ 解决缓存失效问题（固定版本号）
- ✅ 后续构建时间减少 80-90%
- ✅ 生产环境更稳定可靠

---

### 优先级 1: 锁定 PyTorch Nightly 版本（如果必须使用 nightly）

**建议**: 使用方案 1.1，但通过 ARG 参数化版本号，方便更新

```dockerfile
ARG TORCH_NIGHTLY_VERSION="2.7.0.dev20250226+cu128"
ARG TORCHVISION_NIGHTLY_VERSION="0.18.0.dev20250226+cu128"
ARG TORCHAUDIO_NIGHTLY_VERSION="2.7.0.dev20250226+cu128"

RUN if [ "${TORCH_INSTALL_MODE}" = "nightly" ]; then \
      python3 -m pip install --user --no-cache-dir --pre \
        "torch==${TORCH_NIGHTLY_VERSION}" \
        "torchvision==${TORCHVISION_NIGHTLY_VERSION}" \
        "torchaudio==${TORCHAUDIO_NIGHTLY_VERSION}" \
        --index-url "${TORCH_INDEX_URL}" ; \
```

### 优先级 2: 固定 pip/setuptools/wheel 版本（推荐）

```dockerfile
RUN python3 -m pip install --user \
    "pip>=24.0,<25.0" \
    "setuptools>=65.0,<66.0" \
    "wheel>=0.40,<1.0"
```

### 优先级 3: 使用 BuildKit 缓存挂载（可选，但推荐）

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install --user --no-cache-dir -r /tmp/requirements.txt
```

### 优先级 4: 固定 TensorRT 版本（如果启用）

```txt
tensorrt==10.8.0  # 固定版本
```

---

## 📋 实施检查清单

- [ ] 锁定 PyTorch nightly 版本号
- [ ] 固定 pip/setuptools/wheel 版本
- [ ] 添加 BuildKit 缓存挂载（可选）
- [ ] 固定 TensorRT 版本（如果启用）
- [ ] 更新部署脚本传递版本参数
- [ ] 测试构建缓存是否生效

---

## 🔍 验证方法

### 1. 验证构建缓存

```bash
# 第一次构建（应该下载所有依赖）
docker build -f Dockerfile.prod -t pepgmp-backend:test1 .

# 第二次构建（应该使用缓存，不下载依赖）
docker build -f Dockerfile.prod -t pepgmp-backend:test2 .

# 查看构建日志，应该看到 "CACHED" 标记
```

### 2. 检查 PyTorch 版本

```bash
docker run --rm pepgmp-backend:test python -c "import torch; print(torch.__version__)"
```

### 3. 检查构建时间

```bash
time docker build -f Dockerfile.prod -t pepgmp-backend:test .
```

---

## 📝 总结

**主要原因**: PyTorch nightly 版本没有锁定，导致每次构建都重新下载。

**推荐方案**:
1. 锁定 PyTorch nightly 版本号（通过 ARG 参数化）
2. 固定 pip/setuptools/wheel 版本
3. 使用 BuildKit 缓存挂载优化 pip 缓存

**预期效果**:
- 首次构建时间: 不变（仍需下载）
- 后续构建时间: **减少 80-90%**（从 15 分钟减少到 2-3 分钟）
