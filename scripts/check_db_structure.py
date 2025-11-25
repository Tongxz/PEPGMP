#!/usr/bin/env python3
"""
检查数据库表结构和触发器
"""
import asyncio
import os

import asyncpg


async def check_db():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
    )
    conn = await asyncpg.connect(database_url)

    try:
        # 检查表结构
        print("=" * 60)
        print("表结构:")
        print("=" * 60)
        rows = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'detection_records'
            ORDER BY ordinal_position
        """
        )
        for row in rows:
            print(
                f"{row['column_name']:20} {row['data_type']:30} "
                f"NULL={row['is_nullable']:3} DEFAULT={row['column_default']}"
            )

        # 检查触发器
        print("\n" + "=" * 60)
        print("触发器:")
        print("=" * 60)
        triggers = await conn.fetch(
            """
            SELECT trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE event_object_table = 'detection_records'
        """
        )
        if triggers:
            for trig in triggers:
                print(f"\n触发器名: {trig['trigger_name']}")
                print(f"事件: {trig['event_manipulation']}")
                print(f"动作: {trig['action_statement']}")
        else:
            print("无触发器")

        # 检查约束
        print("\n" + "=" * 60)
        print("约束:")
        print("=" * 60)
        constraints = await conn.fetch(
            """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'detection_records'
        """
        )
        for cons in constraints:
            print(f"{cons['constraint_name']:40} {cons['constraint_type']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_db())
