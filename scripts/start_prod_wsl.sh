#!/bin/bash
# 生产环境启动脚本（快捷方式 - WSL容器化模式）
# Production environment startup script (shortcut - WSL containerized mode)
# 调用统一启动脚本
#
# 此脚本适用于:
# - WSL2 Ubuntu 环境
# - 原生 Ubuntu/Linux 环境
# - 使用 Docker 完全容器化部署的场景

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --env prod --mode containerized "$@"
