#!/bin/bash
# 快速修复开发环境配置
# 将 .env 文件中的旧配置更新为新配置

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE=".env"

echo "🔄 更新开发环境配置..."
echo ""

# 检查 .env 文件是否存在
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 错误: $ENV_FILE 文件不存在"
    exit 1
fi

# 备份当前 .env 文件
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
echo "✅ 已备份 .env 文件到: $BACKUP_FILE"
echo ""

# 更新数据库配置
echo "📝 更新数据库配置..."
sed -i.bak \
    -e 's|pyt_dev:pyt_dev_password|pepgmp_dev:pepgmp_dev_password|g' \
    -e 's|pyt_development|pepgmp_development|g' \
    -e 's|pyt_dev_redis|pepgmp_dev_redis|g' \
    "$ENV_FILE"

# 清理备份文件
rm -f "${ENV_FILE}.bak"

echo "✅ 配置已更新"
echo ""

# 显示更新后的配置
echo "📋 更新后的配置:"
echo "-------------------"
grep -E "DATABASE_URL|REDIS_URL" "$ENV_FILE" || echo "未找到相关配置"
echo ""

echo "💡 提示:"
echo "  1. 如果数据库中有旧数据，可能需要迁移数据"
echo "  2. 运行 'bash scripts/start_dev.sh' 重新启动开发环境"
echo ""
