"""
迁移脚本：将 cameras 表的 stream_url 列改为可空

原因：
- stream_url 列当前是 NOT NULL，但代码中创建摄像头时可能不提供此值
- source 信息存储在 metadata 中，stream_url 可以作为可选项
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.services.database_service import get_db_service


async def make_stream_url_nullable():
    """将 cameras 表的 stream_url 列改为可空"""
    try:
        db_service = await get_db_service()
        if not db_service or not db_service.pool:
            print("无法获取数据库连接池")
            return False
        
        pool = db_service.pool
        conn = await pool.acquire()
        try:
            # 检查当前 stream_url 列的定义
            column_info = await conn.fetchrow(
                """
                SELECT is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'cameras'
                AND column_name = 'stream_url'
                """
            )
            
            if not column_info:
                print("stream_url 列不存在，无需迁移")
                return True
            
            is_nullable = column_info['is_nullable']
            print(f"当前 stream_url 列可空性: {is_nullable}")
            
            if is_nullable == 'NO':
                print("将 stream_url 列改为可空...")
                await conn.execute(
                    """
                    ALTER TABLE cameras
                    ALTER COLUMN stream_url DROP NOT NULL
                    """
                )
                print("[OK] stream_url 列已改为可空")
                return True
            else:
                print("[OK] stream_url 列已经是可空的，无需迁移")
                return True
                
        finally:
            await pool.release(conn)
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(make_stream_url_nullable())
    sys.exit(0 if success else 1)

