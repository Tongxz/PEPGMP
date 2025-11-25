#!/bin/bash
# 视频流状态检查脚本

echo "=== 视频流状态检查 ==="
echo ""

echo "1. 检查Redis容器状态:"
docker ps | grep redis
echo ""

echo "2. 检查Redis连接:"
docker exec pyt-redis-dev redis-cli -a pepgmp_dev_redis ping 2>&1 | grep -v "Warning"
echo ""

echo "3. 检查Redis频道订阅数:"
docker exec pyt-redis-dev redis-cli -a pepgmp_dev_redis PUBSUB NUMSUB video:vid1 2>&1 | grep -v "Warning" | tail -1
echo ""

echo "4. 检查检测进程:"
ps aux | grep -E "python.*main.py.*detection.*vid1" | grep -v grep | head -1
echo ""

echo "5. 检查检测进程日志（最近20行）:"
tail -20 logs/detect_vid1.log 2>/dev/null | grep -E "视频|推送|Redis|stream|初始化" | tail -5
echo ""

echo "6. 检查API服务器进程:"
ps aux | grep -E "uvicorn|python.*app" | grep -v grep | head -1
echo ""

echo "=== 检查完成 ==="
