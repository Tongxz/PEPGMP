"""
迁移脚本：将 cameras 表的 id 列从 UUID 改为 VARCHAR(100)

原因：
- 代码期望使用字符串类型的摄像头ID（如 'v1', 'camera1'）
- 但数据库表使用 UUID 类型，导致类型不匹配错误
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.services.database_service import get_db_service


async def migrate_camera_id_column():
    """将 cameras 表的 id 列从 UUID 改为 VARCHAR(100)"""
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
            
            if current_type == 'uuid':
                print("检测到 UUID 类型，开始迁移...")
                
                # 0. 检查是否有未完成的迁移（id_new 列存在）
                id_new_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'cameras'
                        AND column_name = 'id_new'
                    )
                    """
                )
                
                if id_new_exists:
                    print("检测到未完成的迁移（id_new 列存在），继续迁移...")
                    # 检查是否有 id 列
                    id_exists = await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_schema = 'public'
                            AND table_name = 'cameras'
                            AND column_name = 'id'
                        )
                        """
                    )
                    if not id_exists:
                        # id 列已被删除，只需重命名 id_new
                        print("id 列已删除，重命名 id_new 为 id...")
                        await conn.execute("ALTER TABLE cameras ALTER COLUMN id_new DROP DEFAULT")
                        await conn.execute("ALTER TABLE cameras RENAME COLUMN id_new TO id")
                        await conn.execute("ALTER TABLE cameras ADD PRIMARY KEY (id)")
                        print("[OK] 迁移完成：cameras.id 列已从 UUID 改为 VARCHAR(100)")
                        return True
                    else:
                        # 清理 id_new 列，重新开始
                        print("清理未完成的迁移...")
                        await conn.execute("ALTER TABLE cameras DROP COLUMN IF EXISTS id_new")
                
                # 1. 检查是否有数据
                row_count = await conn.fetchval("SELECT COUNT(*) FROM cameras")
                print(f"当前 cameras 表中有 {row_count} 条记录")
                
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
                    table_name = ref['table_name']
                    constraint_name = ref['constraint_name']
                    print(f"  删除外键: {table_name}.{constraint_name}")
                    await conn.execute(
                        f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"
                    )
                
                # 3. 删除主键约束（使用 CASCADE 自动删除依赖）
                print("删除主键约束...")
                await conn.execute("ALTER TABLE cameras DROP CONSTRAINT IF EXISTS cameras_pkey CASCADE")
                
                # 4. 添加临时列用于存储转换后的ID
                print("添加临时列...")
                await conn.execute(
                    """
                    ALTER TABLE cameras
                    ADD COLUMN id_new VARCHAR(100)
                    """
                )
                
                # 5. 如果有数据，将 UUID 转换为字符串
                if row_count > 0:
                    print("转换现有 UUID 数据为字符串...")
                    await conn.execute(
                        """
                        UPDATE cameras
                        SET id_new = id::text
                        """
                    )
                else:
                    print("表中无数据，跳过数据转换")
                
                # 6. 删除依赖的视图（如果有）
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
                    view_name = view['viewname']
                    print(f"  删除视图: {view_name}")
                    await conn.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")
                
                # 7. 删除旧列（使用 CASCADE）
                print("删除旧的 UUID 列...")
                await conn.execute("ALTER TABLE cameras DROP COLUMN IF EXISTS id CASCADE")
                
                # 8. 重命名新列为 id
                print("重命名新列为 id...")
                await conn.execute("ALTER TABLE cameras RENAME COLUMN id_new TO id")
                
                # 9. 添加主键约束
                print("添加主键约束...")
                await conn.execute("ALTER TABLE cameras ADD PRIMARY KEY (id)")
                
                print("[OK] 迁移完成：cameras.id 列已从 UUID 改为 VARCHAR(100)")
                if row_count > 0:
                    print(f"[OK] 已保留 {row_count} 条记录（UUID 已转换为字符串）")
                return True
            elif current_type == 'character varying':
                print("[OK] cameras.id 列已经是 VARCHAR 类型，无需迁移")
                return True
            else:
                print(f"⚠️  未知的列类型: {current_type}")
                return False
                
        finally:
            await pool.release(conn)
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(migrate_camera_id_column())
    sys.exit(0 if success else 1)

