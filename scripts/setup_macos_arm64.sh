#!/bin/bash

set -euo pipefail

# Apple Silicon (ARM64) macOS 快速环境搭建脚本
# - 创建 venv
# - 安装适配 MPS 的 PyTorch/torchvision/torchaudio
# - 安装项目依赖
# - 验证 MPS 可用性

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC}   $1"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC}  $1"; }

ARCH=$(uname -m || echo "")
OS=$(uname -s || echo "")
if [[ "$OS" != "Darwin" ]]; then
  err "当前脚本仅支持 macOS"
  exit 1
fi
if [[ "$ARCH" != "arm64" ]]; then
  warn "检测到架构为 $ARCH（非 Apple Silicon），脚本仍可尝试，但建议使用通用 setup_dev.sh"
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
log "项目根目录: $PROJECT_ROOT"

PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_DIR=${VENV_DIR:-venv}

log "检查 Python..."
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  err "未找到 $PYTHON_BIN"
  exit 1
fi
ok "$($PYTHON_BIN --version)"

log "创建并激活虚拟环境..."
if [[ ! -d "$VENV_DIR" ]]; then
  $PYTHON_BIN -m venv "$VENV_DIR"
  ok "已创建 venv/$VENV_DIR"
else
  warn "虚拟环境已存在，继续使用"
fi
source "$VENV_DIR/bin/activate"
ok "虚拟环境已激活"

log "升级基础构建工具..."
pip install --upgrade pip setuptools wheel

log "安装 PyTorch/torchvision/torchaudio（Apple Silicon + MPS）..."
# 优先安装稳定版（包含 MPS）；如需 CPU-only，可设置 CPU_ONLY=1
if [[ "${CPU_ONLY:-0}" == "1" ]]; then
  warn "启用 CPU_ONLY=1：从 CPU 通道安装 PyTorch（不启用 MPS）"
  if ! pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio; then
    err "CPU 通道安装失败，回退到默认 PyPI 源"
    pip install torch torchvision torchaudio
  fi
else
  if ! pip install torch torchvision torchaudio; then
    warn "PyPI 安装失败，尝试 CPU 通道"
    pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
  fi
fi
ok "PyTorch 系列安装完成"

log "安装项目依赖（requirements.txt / requirements.dev.txt）..."
# 过滤 torch/torchvision/torchaudio，避免覆盖上一步已安装版本
if [[ -f requirements.txt ]]; then
  if ! pip install -r <(grep -Ev '^(torch|torchvision|torchaudio)($|[>=<])' requirements.txt); then
    warn "requirements.txt 安装出现部分警告，可忽略或稍后重试"
  fi
  ok "requirements.txt 安装完成（已过滤 torch* 包）"
fi
if [[ -f requirements.dev.txt ]]; then
  if ! pip install -r <(grep -Ev '^(torch|torchvision|torchaudio)($|[>=<])' requirements.dev.txt); then
    warn "requirements.dev.txt 安装出现部分警告，可忽略或稍后重试"
  fi
  ok "requirements.dev.txt 处理完成（已过滤 torch* 包）"
fi

# 可选：下载 YOLO 模型（开启方式：DOWNLOAD_MODELS=1）
if [[ "${DOWNLOAD_MODELS:-0}" == "1" ]]; then
  log "检测/下载 YOLO 模型（yolov8n.pt）..."
  mkdir -p models/yolo || true
  if [[ ! -f models/yolo/yolov8n.pt ]]; then
    python - <<'PY'
import os, urllib.request
os.makedirs('models/yolo', exist_ok=True)
url = 'https://github.com/ultralytics/assets/releases/download/v0.0.0/models/yolo/yolov8n.pt'
dst = 'models/yolo/yolov8n.pt'
try:
    urllib.request.urlretrieve(url, dst)
    print('下载完成: %s' % dst)
except Exception as e:
    print('下载失败: %s' % e)
PY
    if [[ -f models/yolo/yolov8n.pt ]]; then
      ok "YOLO 模型下载完成"
    else
      warn "YOLO 模型下载失败"
    fi
  else
    ok "YOLO 模型已存在，跳过下载"
  fi
fi

log "验证关键依赖与 MPS 可用性..."
python - <<'PY'
import sys
report = []
try:
    import torch
    report.append(f"PyTorch: {torch.__version__}")
    report.append(f"CUDA available: {torch.cuda.is_available()}")
    report.append(f"MPS built: {getattr(torch.backends.mps, 'is_built', lambda: False)()}")
    report.append(f"MPS available: {getattr(torch.backends.mps, 'is_available', lambda: False)()}")
except Exception as e:
    report.append(f"PyTorch 导入失败: {e}")

for mod in ("cv2", "ultralytics", "mediapipe", "numpy", "PIL"):
    try:
        __import__(mod)
        report.append(f"{mod}: OK")
    except Exception as e:
        report.append(f"{mod}: FAIL ({e})")

print("\n".join(report))
PY

log "完成。后续建议:"
echo "- 运行 demo: source venv/bin/activate && python demo_camera_direct.py --source <视频路径>"
echo "- 如需强制 MPS，可在代码中选择 device='mps'（已自动适配则不必）"
echo "- 若 MPS 不可用，代码会回退到 CPU（速度较慢，建议缩小分辨率/帧率）"
echo "- 如遇 torchvision::nms 在 MPS 未实现，可先导出: PYTORCH_ENABLE_MPS_FALLBACK=1"

ok "环境搭建完成（macOS/ARM64）"
