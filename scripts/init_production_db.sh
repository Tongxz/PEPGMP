#!/bin/bash
#
# 生产环境数据库初始化脚本
# 用于首次部署时初始化数据库表结构
#
# 用法:
#   ./scripts/init_production_db.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 生产环境数据库初始化"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 确保虚拟环境已激活
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "/app/venv/bin/activate" ]; then
        source /app/venv/bin/activate
    else
        echo "⚠️  警告: 虚拟环境未找到，使用系统 Python"
    fi
fi

# 1. 创建数据库扩展
echo "📦 1. 创建数据库扩展..."
python3 << 'PYTHON_EOF'
import asyncio
import os
import asyncpg

async def create_extensions():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ 错误: DATABASE_URL 未配置")
        return False

    try:
        # 去掉 ?sslmode= 后缀
        db_url = database_url.split("?")[0]
        conn = await asyncpg.connect(db_url)

        # 创建 UUID 扩展
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        print("   ✅ uuid-ossp 扩展已创建")

        await conn.close()
        return True
    except Exception as e:
        print(f"   ❌ 创建扩展失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(create_extensions())
    exit(0 if success else 1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "❌ 数据库扩展创建失败"
    exit 1
fi

# 2. 使用 Alembic 创建表结构
echo ""
echo "🗄️  2. 使用 Alembic 创建表结构..."

if command -v alembic &> /dev/null; then
    # 检查是否已有迁移记录
    if python3 -c "
import asyncio
import os
import asyncpg

async def check_alembic():
    database_url = os.getenv('DATABASE_URL', '').split('?')[0]
    try:
        conn = await asyncpg.connect(database_url)
        result = await conn.fetch(\"SELECT * FROM alembic_version LIMIT 1;\")
        await conn.close()
        return len(result) > 0
    except:
        return False

print('yes' if asyncio.run(check_alembic()) else 'no')
" | grep -q "yes"; then
        echo "   ℹ️  数据库已初始化，执行迁移升级..."
        alembic upgrade head
    else
        echo "   ℹ️  首次初始化，创建所有表..."
        alembic upgrade head
    fi

    if [ $? -eq 0 ]; then
        echo "   ✅ 表结构创建/更新成功"
    else
        echo "   ❌ 表结构创建/更新失败"
        exit 1
    fi
else
    echo "   ❌ 错误: Alembic 未安装"
    echo "   请运行: pip install alembic"
    exit 1
fi

# 3. 插入初始数据（如果需要）
echo ""
echo "📊 3. 检查初始数据..."
python3 << 'PYTHON_EOF'
import asyncio
import sys
sys.path.insert(0, "/app" if "/app/src" in str(sys.path) else ".")

from src.database.init_db import create_initial_data

async def main():
    try:
        await create_initial_data()
        print("   ✅ 初始数据检查完成")
        return True
    except Exception as e:
        print(f"   ⚠️  初始数据插入警告: {e}")
        return True  # 非关键错误，继续执行

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
PYTHON_EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 生产环境数据库初始化完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
