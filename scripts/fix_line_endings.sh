#!/bin/bash
# 淇鑴氭湰鏂囦欢鐨?Windows 琛屽熬绗﹂棶棰?# Fix Windows line endings (CRLF) to Unix line endings (LF)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "淇鑴氭湰鏂囦欢鐨勮灏剧..."
echo ""

# 闇€瑕佷慨澶嶇殑鑴氭湰鏂囦欢鍒楄〃
SCRIPTS=(
    "generate_production_config.sh"
    "prepare_minimal_deploy.sh"
    "start_prod_wsl.sh"
)

for script in "${SCRIPTS[@]}"; do
    script_path="$SCRIPT_DIR/$script"
    if [ -f "$script_path" ]; then
        # 浣跨敤 sed 鍒犻櫎 \r
        sed -i 's/\r$//' "$script_path"
        echo "鉁?宸蹭慨澶? $script"
    else
        echo "鈿狅笍  鏂囦欢涓嶅瓨鍦? $script"
    fi
done

echo ""
echo "淇瀹屾垚锛?

