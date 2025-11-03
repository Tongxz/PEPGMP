#!/bin/bash
# 灰度发布启动脚本

set -e

ROLLOUT_PERCENT="${1:-10}"

if [ "$ROLLOUT_PERCENT" -lt 0 ] || [ "$ROLLOUT_PERCENT" -gt 100 ]; then
    echo "错误: ROLLOUT_PERCENT 必须在 0-100 之间"
    exit 1
fi

echo "========================================="
echo "灰度发布启动"
echo "========================================="
echo "灰度比例: $ROLLOUT_PERCENT%"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "配置说明:"
echo "  1. 设置 USE_DOMAIN_SERVICE=true"
echo "  2. 设置 ROLLOUT_PERCENT=$ROLLOUT_PERCENT"
echo "  3. 重启后端服务"
echo ""
echo "环境变量设置:"
echo "  export USE_DOMAIN_SERVICE=true"
echo "  export ROLLOUT_PERCENT=$ROLLOUT_PERCENT"
echo ""
echo -e "${YELLOW}⚠ 警告: 这将启用灰度发布，$ROLLOUT_PERCENT% 的请求将使用新实现${NC}"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "生成启动脚本..."

# 生成启动命令
cat > /tmp/rollout_start.sh << EOF
#!/bin/bash
# 灰度发布启动命令（$ROLLOUT_PERCENT%）

export USE_DOMAIN_SERVICE=true
export ROLLOUT_PERCENT=$ROLLOUT_PERCENT

echo "灰度发布已启动:"
echo "  USE_DOMAIN_SERVICE=true"
echo "  ROLLOUT_PERCENT=$ROLLOUT_PERCENT"
echo ""
echo "请重启后端服务使配置生效"
EOF

chmod +x /tmp/rollout_start.sh

echo -e "${GREEN}✓ 启动脚本已生成: /tmp/rollout_start.sh${NC}"
echo ""
echo "执行方法:"
echo "  1. 查看启动脚本: cat /tmp/rollout_start.sh"
echo "  2. 或直接执行: source /tmp/rollout_start.sh"
echo "  3. 然后重启后端服务"
echo ""
echo -e "${YELLOW}提示: 建议先在测试环境验证后再在生产环境使用${NC}"

