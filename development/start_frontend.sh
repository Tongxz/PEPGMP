#!/bin/bash
# 前端服务器启动脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "启动前端服务器..."
cd frontend && python -m http.server 8080
