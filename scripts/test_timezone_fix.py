#!/usr/bin/env python3
"""
测试时区修复
"""
import asyncio
from datetime import datetime, timezone


async def test_timezone():
    print("=" * 60)
    print("测试时区修复")
    print("=" * 60)

    # 1. 测试datetime创建
    print("\n1. 测试datetime创建:")
    dt_naive = datetime.now()
    dt_aware = datetime.now(timezone.utc)

    print(f"  Naive datetime: {dt_naive}")
    print(f"  Naive tzinfo: {dt_naive.tzinfo}")
    print(f"  Aware datetime: {dt_aware}")
    print(f"  Aware tzinfo: {dt_aware.tzinfo}")

    # 2. 测试Timestamp值对象
    print("\n2. 测试Timestamp值对象:")
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.domain.value_objects.timestamp import Timestamp

    ts = Timestamp.now()
    print(f"  Timestamp.now(): {ts.value}")
    print(f"  Timestamp tzinfo: {ts.value.tzinfo}")

    # 3. 测试数据库保存
    print("\n3. 测试数据库保存:")
    try:
        from src.services.detection_service_domain import get_detection_service_domain

        service = get_detection_service_domain()

        # 创建测试数据
        test_objects = [
            {
                "class_name": "person",
                "bbox": [100, 100, 200, 200],
                "confidence": 0.95,
                "track_id": 1,
            }
        ]

        record = await service.process_detection(
            camera_id="test_timezone",
            detected_objects=test_objects,
            processing_time=0.1,
        )

        print(f"  ✅ 记录保存成功: {record.id}")
        print(f"  记录时间戳: {record.timestamp.value}")
        print(f"  时间戳tzinfo: {record.timestamp.value.tzinfo}")

    except Exception as e:
        print(f"  ❌ 保存失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_timezone())
