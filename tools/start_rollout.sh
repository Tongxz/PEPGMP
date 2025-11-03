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
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "配置说明:"
echo "  - USE_DOMAIN_SERVICE=true"
echo "  - ROLLOUT_PERCENT=$ROLLOUT_PERCENT"
echo ""
echo -e "${YELLOW}⚠ 警告: 这将启用灰度发布，$ROLLOUT_PERCENT% 的请求将使用新实现${NC}"
echo ""
echo "发布的端点:"
echo "  - 告警规则写操作: 2个端点"
echo "  - 摄像头操作端点: 11个端点"
echo "  - 总计: 13个端点"
echo ""
read -p "是否继续? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "----------------------------------------"
echo "1. 停止当前服务"
echo "----------------------------------------"

# 查找并停止当前服务
BACKEND_PID=$(pgrep -f "uvicorn.*app:app" | head -1) || true

if [ -n "$BACKEND_PID" ]; then
    echo "找到后端进程: $BACKEND_PID"
    echo -n "停止服务 ... "
    kill "$BACKEND_PID" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✓ 已停止${NC}"
else
    echo -e "${YELLOW}⚠ 未找到运行中的后端服务${NC}"
fi

echo ""
echo "----------------------------------------"
echo "2. 配置环境变量"
echo "----------------------------------------"

# 设置环境变量
export USE_DOMAIN_SERVICE=true
export ROLLOUT_PERCENT=$ROLLOUT_PERCENT

echo "环境变量已设置:"
echo "  USE_DOMAIN_SERVICE=true"
echo "  ROLLOUT_PERCENT=$ROLLOUT_PERCENT"

# 生成启动脚本
cat > /tmp/backend_start_rollout.sh << 'EOFSCRIPT'
#!/bin/bash
cd /Users/zhou/Code/Pyt

source venv/bin/activate

export DATABASE_URL="postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development"
export REDIS_URL="redis://:pyt_dev_redis@localhost:6379/0"
export LOG_LEVEL=INFO
export AUTO_CONVERT_TENSORRT=false
export USE_DOMAIN_SERVICE=true
export ROLLOUT_PERCENT=ROLLOUT_VALUE

python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info > /tmp/backend.log 2>&1 &
EOFSCRIPT

# 替换ROLLOUT_VALUE
sed -i.bak "s/ROLLOUT_VALUE/$ROLLOUT_PERCENT/g" /tmp/backend_start_rollout.sh
chmod +x /tmp/backend_start_rollout.sh

echo ""
echo "----------------------------------------"
echo "3. 启动后端服务"
echo "----------------------------------------"

echo "启动服务 ... "
/tmp/backend_start_rollout.sh

sleep 5

echo ""
echo "----------------------------------------"
echo "4. 验证服务启动"
echo "----------------------------------------"

# 等待服务启动
MAX_RETRIES=10
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/api/ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 服务已启动${NC}"
        break
    else
        RETRY=$((RETRY + 1))
        echo "等待服务启动... ($RETRY/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ 服务启动失败，请检查日志: /tmp/backend.log${NC}"
    exit 1
fi

echo ""
echo "----------------------------------------"
echo "5. 验证灰度配置"
echo "----------------------------------------"

# 验证监控端点
echo -n "检查健康检查端点 ... "
if curl -s http://localhost:8000/api/v1/monitoring/health | grep -q "status\|healthy"; then
    echo -e "${GREEN}✓ 可用${NC}"
else
    echo -e "${YELLOW}⚠ 不可用（可能需等待）${NC}"
fi

echo -n "检查监控指标端点 ... "
if curl -s http://localhost:8000/api/v1/monitoring/metrics | grep -q "requests\|response_time"; then
    echo -e "${GREEN}✓ 可用${NC}"
else
    echo -e "${YELLOW}⚠ 不可用（可能需等待）${NC}"
fi

echo ""
echo "========================================="
echo "灰度发布启动完成"
echo "========================================="
echo ""
echo -e "${GREEN}✓ 灰度发布已启动: $ROLLOUT_PERCENT%${NC}"
echo ""
echo "环境变量:"
echo "  USE_DOMAIN_SERVICE=true"
echo "  ROLLOUT_PERCENT=$ROLLOUT_PERCENT"
echo ""
echo "监控端点:"
echo "  - 健康检查: http://localhost:8000/api/v1/monitoring/health"
echo "  - 监控指标: http://localhost:8000/api/v1/monitoring/metrics"
echo ""
echo "下一步:"
echo "  1. 观察1-2天，监控错误率和性能"
echo "  2. 验证功能正确性"
echo "  3. 如果正常，提升到25%灰度"
echo ""
echo -e "${YELLOW}⚠ 提示: 查看日志: tail -f /tmp/backend.log${NC}"
echo ""
