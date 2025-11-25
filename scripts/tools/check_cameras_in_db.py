"""检查数据库中的摄像头数据"""
import asyncio
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import asyncpg


async def check_cameras():
    """检查数据库中的摄像头数据"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
    )
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # 检查cameras表是否存在
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
            print("[ERROR] cameras表不存在")
            await conn.close()
            return
        
        # 获取摄像头数量
        count = await conn.fetchval("SELECT COUNT(*) FROM cameras")
        print(f"[INFO] 摄像头数量: {count}")
        
        # 获取所有摄像头
        if count > 0:
            cameras = await conn.fetch("SELECT id, name, status, camera_type, location FROM cameras LIMIT 10")
            print("\n[INFO] 摄像头列表（前10个）:")
            for cam in cameras:
                print(f"  - ID: {cam['id']}, Name: {cam['name']}, Status: {cam['status']}, Type: {cam['camera_type']}, Location: {cam['location']}")
        else:
            print("[WARNING] 数据库中没有摄像头数据")
        
        await conn.close()
        
    except Exception as e:
        print(f"[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_cameras())

