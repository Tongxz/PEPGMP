#!/bin/bash
# 服务状态检查脚本

set -e

echo "=========================================="
echo "前后端服务状态检查"
echo "=========================================="
echo ""

# 检查后端服务
echo "1. 检查后端服务状态..."
BACKEND_PORT=8000
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "   ✅ 后端服务正在运行 (端口 $BACKEND_PORT)"
    PROCESS=$(lsof -i :$BACKEND_PORT | grep LISTEN | awk '{print $2}' | head -n1)
    if [ ! -z "$PROCESS" ]; then
        echo "   PID: $PROCESS"
        ps -p $PROCESS -o command= | head -n1
    fi
else
    echo "   ❌ 后端服务未运行 (端口 $BACKEND_PORT)"
fi

# 检查后端健康端点
echo ""
echo "2. 检查后端健康端点..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:$BACKEND_PORT/api/v1/monitoring/health 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ 健康检查通过 (状态码: $HTTP_CODE)"
    echo "   响应: $(echo "$BODY" | head -c 200)"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "   ❌ 无法连接到后端服务"
    echo "   错误: 连接被拒绝"
else
    echo "   ⚠️  健康检查失败 (状态码: $HTTP_CODE)"
    echo "   响应: $(echo "$BODY" | head -c 200)"
fi

# 检查前端服务
echo ""
echo "3. 检查前端服务状态..."
FRONTEND_PORT=5173  # Vite默认端口
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo "   ✅ 前端服务正在运行 (端口 $FRONTEND_PORT)"
    PROCESS=$(lsof -i :$FRONTEND_PORT | grep LISTEN | awk '{print $2}' | head -n1)
    if [ ! -z "$PROCESS" ]; then
        echo "   PID: $PROCESS"
        ps -p $PROCESS -o command= | head -n1
    fi
else
    echo "   ⚠️  前端服务未运行 (端口 $FRONTEND_PORT)"
    echo "   注意: 前端服务是可选的，不影响API测试"
fi

# 检查日志文件
echo ""
echo "4. 检查日志文件..."
if [ -f "logs/app.log" ]; then
    echo "   ✅ 日志文件存在: logs/app.log"
    echo "   最后10行日志:"
    tail -n 10 logs/app.log | sed 's/^/      /'
else
    echo "   ⚠️  日志文件不存在: logs/app.log"
fi

# 检查数据库连接
echo ""
echo "5. 检查数据库连接..."
if [ ! -z "$DATABASE_URL" ]; then
    echo "   DATABASE_URL已设置: ${DATABASE_URL%%@*}"
else
    echo "   ⚠️  DATABASE_URL未设置"
fi

# 检查Redis连接
echo ""
echo "6. 检查Redis连接..."
if [ ! -z "$REDIS_URL" ]; then
    echo "   REDIS_URL已设置: ${REDIS_URL%%@*}"
else
    echo "   ⚠️  REDIS_URL未设置"
fi

# 总结
echo ""
echo "=========================================="
echo "检查总结"
echo "=========================================="

if lsof -i :$BACKEND_PORT > /dev/null 2>&1 && [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 后端服务运行正常"
    echo ""
    echo "建议: 可以运行集成测试"
    echo "  export API_BASE_URL=http://localhost:8000"
    echo "  python tests/integration/test_api_integration.py"
elif lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "⚠️  后端服务运行但健康检查失败"
    echo ""
    echo "建议: 检查日志文件 logs/app.log"
else
    echo "❌ 后端服务未运行"
    echo ""
    echo "建议: 启动后端服务"
    echo "  cd /Users/zhou/Code/Pyt"
    echo "  source venv/bin/activate"
    echo "  export DATABASE_URL=\"postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development\""
    echo "  export REDIS_URL=\"redis://:pyt_dev_redis@localhost:6379/0\""
    echo "  export USE_DOMAIN_SERVICE=true"
    echo "  export ROLLOUT_PERCENT=100"
    echo "  python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload"
fi

echo "=========================================="
