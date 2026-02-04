#!/bin/bash
# 前端测试运行脚本
# 自动启动前端服务器并运行测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "🧪 前端页面自动化测试"
echo "========================================"

# 检查依赖
echo "📦 检查依赖..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 python3${NC}"
    exit 1
fi

if ! python3 -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Playwright 未安装，正在安装...${NC}"
    pip install playwright
    python3 -m playwright install chromium
fi

# 检查前端是否已经在运行
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端已在运行 (http://localhost:5173)${NC}"
    echo "直接运行测试..."
    python3 tests/frontend/test_frontend_pages.py
    exit $?
fi

# 前端未运行，使用 with_server.py 启动
echo -e "${YELLOW}📡 前端未运行，正在启动...${NC}"

cd "$(dirname "$0")/../.."  # 回到项目根目录

# 检查 with_server.py 是否存在
if [ ! -f ".claude/skills/webapp-testing/scripts/with_server.py" ]; then
    echo -e "${RED}❌ 错误: 未找到 with_server.py${NC}"
    echo "请确保已加载 webapp-testing 技能"
    exit 1
fi

# 使用 with_server.py 启动前端并运行测试
echo "🚀 启动前端服务器并运行测试..."
python3 .claude/skills/webapp-testing/scripts/with_server.py \
    --server "cd frontend && npm run dev" \
    --port 5173 \
    --timeout 60 \
    -- python3 tests/frontend/test_frontend_pages.py

exit $?
