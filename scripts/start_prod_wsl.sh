#!/bin/bash
# 鐢熶骇鐜鍚姩鑴氭湰锛堝揩鎹锋柟寮?- WSL瀹瑰櫒鍖栨ā寮忥級
# Production environment startup script (shortcut - WSL containerized mode)
# 璋冪敤缁熶竴鍚姩鑴氭湰

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start.sh" --env prod --mode containerized "$@"
