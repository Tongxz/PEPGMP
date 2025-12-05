"""
迁移脚本：将 cameras 表的 id 列从 VARCHAR 改回 UUID（自动生成）

设计变更：
- id: UUID PRIMARY KEY (自动生成，唯一标识)
- name: VARCHAR(100) (用户自定义，有辨识度)
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.services.database_service import get_db_service


async def revert_camera_id_to_uuid():
    """将 cameras 表的 id 列从 VARCHAR 改回 UUID"""
    try:
        db_service = await get_db_service()
        if not db_service or not db_service.pool:
            print("无法获取数据库连接池")
            return False

        pool = db_service.pool
        conn = await pool.acquire()
        try:
            # 检查当前 id 列类型
            current_type = await conn.fetchval(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'cameras'
                AND column_name = 'id'
                """
            )

            print(f"当前 cameras.id 列类型: {current_type}")

            if current_type == "character varying":
                print("检测到 VARCHAR 类型，开始迁移回 UUID...")

                # 1. 检查是否有数据
                row_count = await conn.fetchval("SELECT COUNT(*) FROM cameras")
                print(f"当前 cameras 表中有 {row_count} 条记录")

                if row_count > 0:
                    print("警告：表中已有数据，迁移将删除所有现有数据！")
                    print("如果这是生产环境，请先备份数据！")
                    response = input("是否继续？(yes/no): ")
                    if response.lower() != "yes":
                        print("迁移已取消")
                        return False

                # 2. 查找并删除所有引用 cameras.id 的外键约束
                print("查找并删除所有引用 cameras.id 的外键约束...")
                referencing_tables = await conn.fetch(
                    """
                    SELECT
                        tc.table_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.table_name = 'cameras'
                        AND ccu.column_name = 'id'
                    """
                )

                for ref in referencing_tables:
                    table_name = ref["table_name"]
                    constraint_name = ref["constraint_name"]
                    print(f"  删除外键: {table_name}.{constraint_name}")
                    await conn.execute(
                        f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"
                    )

                # 3. 删除主键约束
                print("删除主键约束...")
                await conn.execute(
                    "ALTER TABLE cameras DROP CONSTRAINT IF EXISTS cameras_pkey CASCADE"
                )

                # 4. 删除依赖的视图（如果有）
                print("查找并删除依赖的视图...")
                dependent_views = await conn.fetch(
                    """
                    SELECT viewname
                    FROM pg_views
                    WHERE schemaname = 'public'
                    AND definition LIKE '%cameras.id%'
                    """
                )

                for view in dependent_views:
                    view_name = view["viewname"]
                    print(f"  删除视图: {view_name}")
                    await conn.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")

                # 5. 删除旧列
                print("删除旧的 VARCHAR 列...")
                await conn.execute(
                    "ALTER TABLE cameras DROP COLUMN IF EXISTS id CASCADE"
                )

                # 6. 添加新的 UUID 列（自动生成）
                print("添加新的 UUID 列（自动生成）...")
                await conn.execute(
                    """
                    ALTER TABLE cameras
                    ADD COLUMN id UUID PRIMARY KEY DEFAULT uuid_generate_v4()
                    """
                )

                print("[OK] 迁移完成：cameras.id 列已从 VARCHAR 改回 UUID（自动生成）")
                return True
            elif current_type == "uuid":
                print("[OK] cameras.id 列已经是 UUID 类型，无需迁移")
                return True
            else:
                print(f"[WARNING] 未知的列类型: {current_type}")
                return False

        finally:
            await pool.release(conn)
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(revert_camera_id_to_uuid())
    sys.exit(0 if success else 1)
