#!/bin/bash
#
# 数据库迁移脚本
# 使用 Alembic 管理数据库表结构迁移
#
# 用法:
#   ./scripts/db_migrate.sh upgrade      # 升级到最新版本
#   ./scripts/db_migrate.sh downgrade    # 降级一个版本
#   ./scripts/db_migrate.sh current      # 查看当前版本
#   ./scripts/db_migrate.sh history      # 查看迁移历史
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 确保虚拟环境已激活
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo "❌ 错误: 虚拟环境未找到"
        exit 1
    fi
fi

# 确保 Alembic 已安装
if ! command -v alembic &> /dev/null; then
    echo "❌ 错误: Alembic 未安装"
    echo "请运行: pip install alembic"
    exit 1
fi

# 确保数据库 URL 已配置
if [ -z "$DATABASE_URL" ]; then
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo "❌ 错误: DATABASE_URL 未配置"
        exit 1
    fi
fi

ACTION="${1:-upgrade}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 数据库迁移工具（Alembic）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

case "$ACTION" in
    upgrade)
        echo "📈 升级数据库到最新版本..."
        alembic upgrade head
        echo "✅ 数据库升级完成"
        ;;
    downgrade)
        echo "📉 降级数据库一个版本..."
        alembic downgrade -1
        echo "✅ 数据库降级完成"
        ;;
    current)
        echo "📍 当前数据库版本:"
        alembic current
        ;;
    history)
        echo "📜 迁移历史:"
        alembic history
        ;;
    stamp)
        REVISION="${2:-head}"
        echo "🏷️  标记数据库版本为: $REVISION"
        alembic stamp "$REVISION"
        echo "✅ 数据库版本已标记"
        ;;
    revision)
        MESSAGE="${2:-Auto-generated migration}"
        echo "📝 创建新的迁移脚本: $MESSAGE"
        alembic revision --autogenerate -m "$MESSAGE"
        echo "✅ 迁移脚本已生成"
        ;;
    *)
        echo "❌ 错误: 未知操作 '$ACTION'"
        echo ""
        echo "用法:"
        echo "  $0 upgrade      # 升级到最新版本"
        echo "  $0 downgrade    # 降级一个版本"
        echo "  $0 current      # 查看当前版本"
        echo "  $0 history      # 查看迁移历史"
        echo "  $0 stamp [REV]  # 标记为指定版本（不执行迁移）"
        echo "  $0 revision \"MSG\"  # 生成新的迁移脚本"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
