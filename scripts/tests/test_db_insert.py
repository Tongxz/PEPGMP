#!/usr/bin/env python3
"""
直接测试数据库插入，排查时区问题
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_db_insert():
    print("=" * 60)
    print("测试数据库直接插入")
    print("=" * 60)

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
    )
    conn = await asyncpg.connect(database_url)

    try:
        camera_id = "test_direct"
        objects = [{"class_name": "person", "confidence": 0.95}]

        print("\n测试1: 使用带时区的datetime")
        timestamp_aware = datetime.now(timezone.utc)
        print(f"  Timestamp: {timestamp_aware}")
        print(f"  TZ Info: {timestamp_aware.tzinfo}")

        try:
            result = await conn.fetchval(
                """
                INSERT INTO detection_records
                (camera_id, objects, timestamp, confidence, processing_time, frame_id, region_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                camera_id,
                json.dumps(objects),
                timestamp_aware,
                0.95,
                0.1,
                1,
                None,
                None,
            )
            print(f"  ✅ 插入成功，ID: {result}")
        except Exception as e:
            print(f"  ❌ 插入失败: {e}")

        print("\n测试2: 使用无时区的datetime")
        timestamp_naive = datetime.now()
        print(f"  Timestamp: {timestamp_naive}")
        print(f"  TZ Info: {timestamp_naive.tzinfo}")

        try:
            result = await conn.fetchval(
                """
                INSERT INTO detection_records
                (camera_id, objects, timestamp, confidence, processing_time, frame_id, region_id, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                f"{camera_id}2",
                json.dumps(objects),
                timestamp_naive,
                0.95,
                0.1,
                2,
                None,
                None,
            )
            print(f"  ✅ 插入成功，ID: {result}")
        except Exception as e:
            print(f"  ❌ 插入失败: {e}")

        print("\n检查数据库中的记录:")
        rows = await conn.fetch(
            """
            SELECT id, camera_id, timestamp
            FROM detection_records
            WHERE camera_id LIKE 'test_direct%'
            ORDER BY id DESC
            LIMIT 5
            """
        )
        for row in rows:
            print(
                f"  ID: {row['id']}, Camera: {row['camera_id']}, Timestamp: {row['timestamp']}"
            )

    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_db_insert())
