#!/bin/bash
# 生产环境启动脚本（快捷方式 - WSL容器化模式）
# Production environment startup script (shortcut - WSL containerized mode)
# 调用统一启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --env prod --mode containerized "$@"
