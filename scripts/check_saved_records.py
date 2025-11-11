#!/usr/bin/env python3
"""
检查保存的检测记录
"""
import asyncio
import os

import asyncpg


async def check_records():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development",
    )
    conn = await asyncpg.connect(database_url)

    try:
        # 检查最近的记录
        print("=" * 60)
        print("最近10条检测记录:")
        print("=" * 60)
        rows = await conn.fetch(
            """
            SELECT id, camera_id, timestamp, confidence, frame_id
            FROM detection_records
            WHERE camera_id LIKE 'test%'
            ORDER BY id DESC
            LIMIT 10
        """
        )
        if rows:
            for row in rows:
                print(
                    f"ID:{row['id']:5} Camera:{row['camera_id']:15} "
                    f"Time:{row['timestamp']} Conf:{row['confidence']:.2f}"
                )
            print(f"\n✅ 找到 {len(rows)} 条记录")
        else:
            print("❌ 未找到任何记录")

        # 统计
        count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM detection_records
            WHERE camera_id LIKE 'test%'
        """
        )
        print(f"\n总共{count}条测试记录")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_records())
