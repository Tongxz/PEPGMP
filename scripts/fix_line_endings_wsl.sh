#!/bin/bash
# Fix Windows line endings (CRLF) to Unix line endings (LF) in WSL
# Run this script in WSL: bash scripts/fix_line_endings_wsl.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Fixing script file line endings..."
echo ""

# Find all .sh files and fix them
find "$SCRIPT_DIR" -name "*.sh" -type f | while read -r script; do
    # Remove \r characters
    sed -i 's/\r$//' "$script"
    echo "Fixed: $script"
done

echo ""
echo "Done! All .sh files have been fixed."
echo ""
echo "You can now run:"
echo "  bash scripts/generate_production_config.sh"

