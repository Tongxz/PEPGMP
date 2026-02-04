#!/usr/bin/env python3
"""诊断在线摄像头为0的问题"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径（脚本需在项目根下执行以便导入）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta, timezone  # noqa: E402

import asyncpg  # noqa: E402


async def diagnose_cameras():
    """诊断摄像头状态"""
    # 获取数据库连接
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
    )

    try:
        conn = await asyncpg.connect(database_url)

        print("=" * 60)
        print("诊断在线摄像头为0的问题")
        print("=" * 60)
        print()

        # 1. 检查所有摄像头的状态
        print("1. 检查所有摄像头的状态:")
        print("-" * 60)
        cameras = await conn.fetch(
            """
            SELECT id, name, status, is_active, created_at, updated_at
            FROM cameras
            ORDER BY name
            """
        )
        if not cameras:
            print("  ⚠️  没有找到任何摄像头")
        else:
            print(f"  找到 {len(cameras)} 个摄像头:")
            for cam in cameras:
                print(
                    f"    - {cam['name']} (ID: {cam['id']}): "
                    f"status={cam['status']}, is_active={cam['is_active']}"
                )
        print()

        # 2. 检查符合查询条件的摄像头
        print("2. 检查符合查询条件的摄像头:")
        print("-" * 60)
        active_cameras = await conn.fetch(
            """
            SELECT DISTINCT c.id, c.name, c.status, c.is_active
            FROM cameras c
            LEFT JOIN detection_records dr ON c.id::text = dr.camera_id
                AND dr.timestamp > NOW() - INTERVAL '1 hour'
            WHERE c.status IN ('active', 'online', 'running')
               OR (c.status IS NULL AND c.is_active = true)
               OR dr.id IS NOT NULL
            ORDER BY c.name
            """
        )
        print(f"  符合查询条件的摄像头数: {len(active_cameras)}")
        if active_cameras:
            for cam in active_cameras:
                print(f"    - {cam['name']} (ID: {cam['id']}): status={cam['status']}")
        else:
            print("  ⚠️  没有找到符合条件的摄像头")
        print()

        # 3. 检查最近1小时内的检测记录
        print("3. 检查最近1小时内的检测记录:")
        print("-" * 60)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_records = await conn.fetch(
            """
            SELECT DISTINCT camera_id, COUNT(*) as record_count
            FROM detection_records
            WHERE timestamp > $1
            GROUP BY camera_id
            ORDER BY record_count DESC
            """,
            one_hour_ago,
        )
        if not recent_records:
            print("  ⚠️  最近1小时内没有检测记录")
        else:
            print(f"  最近1小时内有检测记录的摄像头数: {len(recent_records)}")
            for rec in recent_records:
                print(f"    - camera_id={rec['camera_id']}: {rec['record_count']} 条记录")
        print()

        # 4. 检查各个查询条件
        print("4. 检查各个查询条件:")
        print("-" * 60)

        # 条件1: status IN ('active', 'online', 'running')
        condition1 = await conn.fetch(
            """
            SELECT COUNT(*) as count
            FROM cameras
            WHERE status IN ('active', 'online', 'running')
            """
        )
        print(
            f"  条件1 (status IN ('active', 'online', 'running')): {condition1[0]['count']} 个"
        )

        # 条件2: status IS NULL AND is_active = true
        condition2 = await conn.fetch(
            """
            SELECT COUNT(*) as count
            FROM cameras
            WHERE status IS NULL AND is_active = true
            """
        )
        print(
            f"  条件2 (status IS NULL AND is_active = true): {condition2[0]['count']} 个"
        )

        # 条件3: 最近1小时内有检测记录
        condition3 = await conn.fetch(
            """
            SELECT COUNT(DISTINCT c.id) as count
            FROM cameras c
            INNER JOIN detection_records dr ON c.id = dr.camera_id
            WHERE dr.timestamp > NOW() - INTERVAL '1 hour'
            """
        )
        print(f"  条件3 (最近1小时内有检测记录): {condition3[0]['count']} 个")
        print()

        # 5. 建议
        print("5. 建议:")
        print("-" * 60)
        if not active_cameras:
            print("  ❌ 没有找到活跃摄像头，可能的原因:")
            print("     1. 摄像头状态不是 'active', 'online', 或 'running'")
            print("     2. 最近1小时内没有检测记录")
            print("     3. is_active 字段为 false")
            print()
            print("  💡 解决方案:")
            print("     1. 更新摄像头状态为 'active':")
            print(
                "        UPDATE cameras SET status = 'active' WHERE id = 'your_camera_id';"
            )
            print("     2. 或者确保最近1小时内有检测记录")
            print("     3. 或者更新 is_active 字段:")
            print(
                "        UPDATE cameras SET is_active = true WHERE id = 'your_camera_id';"
            )
        else:
            print(f"  ✅ 找到 {len(active_cameras)} 个活跃摄像头")
            print("     如果前端仍然显示0，请检查:")
            print("     1. 后端是否已重启")
            print("     2. API响应是否正确")
            print("     3. 前端是否正确解析响应")

        await conn.close()

    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose_cameras())
