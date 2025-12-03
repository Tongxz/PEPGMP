#!/bin/bash
# 清理旧的 frontend 容器

set -e

echo "========================================================================="
echo "清理旧的 frontend 容器"
echo "========================================================================="
echo ""

# 检查是否存在旧的 pepgmp-frontend-prod 容器
if docker ps -a | grep -q "pepgmp-frontend-prod"; then
    echo "[INFO] 发现旧的 pepgmp-frontend-prod 容器，准备清理..."
    
    # 停止容器（如果正在运行）
    if docker ps | grep -q "pepgmp-frontend-prod"; then
        echo "[INFO] 停止容器..."
        docker stop pepgmp-frontend-prod
    fi
    
    # 删除容器
    echo "[INFO] 删除容器..."
    docker rm pepgmp-frontend-prod
    
    echo "[OK] 旧容器已清理"
else
    echo "[INFO] 未发现旧的 pepgmp-frontend-prod 容器"
fi

echo ""
echo "========================================================================="
echo "清理完成"
echo "========================================================================="
echo ""
echo "当前容器列表："
docker ps -a | grep pepgmp || echo "无 pepgmp 相关容器"

