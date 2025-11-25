"""
检查 cameras 表的结构
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.services.database_service import get_db_service


async def check_table_structure():
    """检查 cameras 表的结构"""
    try:
        db_service = await get_db_service()
        if not db_service or not db_service.pool:
            print("无法获取数据库连接池")
            return
        
        pool = db_service.pool
        
        conn = await pool.acquire()
        try:
            # 检查表是否存在
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'cameras'
                )
                """
            )
            
            if not table_exists:
                print("cameras 表不存在")
                return
            
            # 检查 id 列的类型
            id_type = await conn.fetchval(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'cameras'
                AND column_name = 'id'
                """
            )
            
            print(f"cameras.id 列类型: {id_type}")
            
            # 检查所有列
            columns = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'cameras'
                ORDER BY ordinal_position
                """
            )
            
            print("\n所有列:")
            for col in columns:
                print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")
            
        finally:
            await pool.release(conn)
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_table_structure())

