#!/bin/bash
# 开发环境启动脚本（快捷方式）
# Development environment startup script (shortcut)
# 调用统一启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --env dev "$@"
