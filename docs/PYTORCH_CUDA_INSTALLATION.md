# PyTorch CUDA 版本安装指南

## 问题说明

`pyproject.toml` 中的依赖声明 `torch>=2.2.0` 默认会从 PyPI 安装 **CPU 版本**的 PyTorch，而不是 CUDA 版本。

这是因为：
1. PyPI 上的 `torch` 包默认是 CPU 版本
2. CUDA 版本的 PyTorch 需要从 PyTorch 官方索引安装
3. `pyproject.toml` 无法直接指定 PyTorch 的 CUDA 版本（因为需要额外的索引 URL）

## 解决方案

### 方案1：手动安装 CUDA 版本（推荐）

在安装项目依赖后，手动安装 CUDA 版本的 PyTorch：

```bash
# 1. 先安装基础依赖（会安装 CPU 版本的 PyTorch）
pip install -e .

# 2. 卸载 CPU 版本的 PyTorch
pip uninstall -y torch torchvision torchaudio

# 3. 安装 CUDA 版本的 PyTorch（CUDA 12.1）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 方案2：使用安装脚本

项目提供了自动安装脚本（如果存在）：

```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts\install_pytorch_cuda.ps1

# Linux/Mac
bash scripts/install_pytorch_cuda.sh
```

### 方案3：修改安装顺序

在安装项目依赖之前，先安装 CUDA 版本的 PyTorch：

```bash
# 1. 先安装 CUDA 版本的 PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 2. 然后安装项目依赖（pip 会检测到已安装的 PyTorch，不会重新安装）
pip install -e .
```

## 验证安装

安装完成后，验证 CUDA 是否可用：

```python
import torch
print(f"PyTorch 版本: {torch.__version__}")
print(f"CUDA 可用: {torch.cuda.is_available()}")
print(f"CUDA 版本: {torch.version.cuda if hasattr(torch.version, 'cuda') and torch.version.cuda else 'N/A'}")
```

预期输出：
```
PyTorch 版本: 2.5.1+cu121
CUDA 可用: True
CUDA 版本: 12.1
```

## 不同 CUDA 版本的安装命令

根据你的系统 CUDA 版本，选择合适的安装命令：

| CUDA 版本 | 安装命令 |
|-----------|----------|
| CUDA 12.1 | `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121` |
| CUDA 11.8 | `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118` |
| CUDA 11.7 | `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117` |

## 常见问题

### Q: 为什么 `pyproject.toml` 不能直接指定 CUDA 版本？

A: 因为 PyTorch 的 CUDA 版本需要从 PyTorch 官方索引安装，而不是 PyPI。`pyproject.toml` 的依赖声明无法指定额外的索引 URL。

### Q: 安装 CUDA 版本后，`pip install -e .` 会重新安装 CPU 版本吗？

A: 不会。如果已经安装了 CUDA 版本的 PyTorch，pip 会检测到已满足 `torch>=2.2.0` 的要求，不会重新安装。

### Q: 如何检查当前安装的是 CPU 还是 CUDA 版本？

A: 运行以下命令：
```python
import torch
print(torch.__version__)  # CPU 版本显示为 "2.x.x"，CUDA 版本显示为 "2.x.x+cu121"
print(torch.cuda.is_available())  # CUDA 版本返回 True，CPU 版本返回 False
```

## 参考

- [PyTorch 官方安装指南](https://pytorch.org/get-started/locally/)
- [CUDA 版本兼容性说明](docs/CUDA_VERSION_MISMATCH_SOLUTION.md)

