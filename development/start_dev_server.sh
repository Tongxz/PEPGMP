#!/bin/bash
# 开发服务器启动脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "虚拟环境已激活"
else
    echo "警告: 未找到虚拟环境，请先运行 ./setup_dev_env.sh"
fi

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export HAIRNET_MODEL_PATH="models/hairnet_detection/models/hairnet_detection/hairnet_detection.pt"

echo "启动后端API服务器..."
python src/api/app.py
