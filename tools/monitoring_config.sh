#!/bin/bash
# 监控配置脚本

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========================================="
echo "监控配置"
echo "========================================="
echo "BASE_URL: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "----------------------------------------"
echo "1. 监控端点验证"
echo "----------------------------------------"

# 检查健康检查端点
echo ""
echo -n "检查健康检查端点 ... "
health_response=$(curl -s "$BASE_URL/api/v1/monitoring/health" 2>&1) || true

if echo "$health_response" | grep -q "status\|healthy"; then
    echo -e "${GREEN}✓ 可用${NC}"
else
    echo -e "${RED}✗ 不可用${NC}"
    echo "  响应: $health_response"
    echo -e "${YELLOW}⚠ 提示: 可能需要重启后端服务使监控端点配置生效${NC}"
fi

# 检查监控指标端点
echo ""
echo -n "检查监控指标端点 ... "
metrics_response=$(curl -s "$BASE_URL/api/v1/monitoring/metrics" 2>&1) || true

if echo "$metrics_response" | grep -q "requests\|response_time"; then
    echo -e "${GREEN}✓ 可用${NC}"
else
    echo -e "${RED}✗ 不可用${NC}"
    echo "  响应: $metrics_response"
    echo -e "${YELLOW}⚠ 提示: 可能需要重启后端服务使监控端点配置生效${NC}"
fi

echo ""
echo "----------------------------------------"
echo "2. 监控指标配置"
echo "----------------------------------------"

echo ""
echo "监控指标说明:"
echo "  - 错误率: 目标 < 1%，阈值 > 5% 立即告警"
echo "  - 响应时间: P95延迟无明显增加，阈值 > 50% 告警"
echo "  - 成功率: 目标 > 99%，阈值 < 95% 立即告警"
echo "  - 领域服务使用率: 跟踪使用情况"
echo ""

echo "----------------------------------------"
echo "3. 告警规则配置"
echo "----------------------------------------"

echo ""
echo "告警规则（建议配置）:"
echo ""
echo "1. 错误率告警"
echo "   - 条件: 错误率 > 5%"
echo "   - 动作: 立即告警并记录"
echo "   - 优先级: 高"
echo ""
echo "2. 响应时间告警"
echo "   - 条件: P95延迟增加 > 50%"
echo "   - 动作: 记录并检查"
echo "   - 优先级: 中"
echo ""
echo "3. 成功率告警"
echo "   - 条件: 成功率 < 95%"
echo "   - 动作: 立即告警并记录"
echo "   - 优先级: 高"
echo ""
echo "4. 领域服务使用率监控"
echo "   - 目的: 跟踪灰度发布进度"
echo "   - 监控: 使用率变化趋势"
echo "   - 优先级: 低"
echo ""

echo "----------------------------------------"
echo "4. 监控仪表板配置（可选）"
echo "----------------------------------------"

echo ""
echo "建议配置的监控仪表板:"
echo ""
echo "1. 错误率趋势图"
echo "   - X轴: 时间"
echo "   - Y轴: 错误率 (%)"
echo "   - 数据源: /api/v1/monitoring/metrics"
echo ""
echo "2. 响应时间分布图"
echo "   - X轴: 时间"
echo "   - Y轴: 响应时间 (ms)"
echo "   - 指标: P50/P95/P99/平均值"
echo "   - 数据源: /api/v1/monitoring/metrics"
echo ""
echo "3. 领域服务使用率图"
echo "   - X轴: 时间"
echo "   - Y轴: 使用率 (%)"
echo "   - 数据源: /api/v1/monitoring/metrics"
echo ""
echo "4. 请求分布图"
echo "   - X轴: 状态码"
echo "   - Y轴: 请求数量"
echo "   - 数据源: /api/v1/monitoring/metrics"
echo ""

echo "----------------------------------------"
echo "5. 监控检查清单"
echo "----------------------------------------"

echo ""
echo "监控配置检查清单:"
echo "  [ ] 监控端点可用"
echo "  [ ] 监控指标正常收集"
echo "  [ ] 告警规则配置完成"
echo "  [ ] 监控仪表板配置完成（可选）"
echo "  [ ] 监控脚本准备完成"
echo "  [ ] 监控文档完善"
echo ""

echo "----------------------------------------"
echo "6. 监控脚本"
echo "----------------------------------------"

echo ""
echo "获取监控指标:"
echo "  curl $BASE_URL/api/v1/monitoring/metrics | jq"
echo ""
echo "健康检查:"
echo "  curl $BASE_URL/api/v1/monitoring/health | jq"
echo ""

echo "========================================="
echo "监控配置完成"
echo "========================================="
echo ""
echo -e "${GREEN}✓ 监控配置说明已完成${NC}"
echo ""
echo "下一步:"
echo "  1. 重启后端服务使监控端点生效（如需要）"
echo "  2. 配置告警规则（如需要）"
echo "  3. 配置监控仪表板（可选）"
echo ""
