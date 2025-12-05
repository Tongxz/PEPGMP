"""测试数据库服务."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.database_service import DatabaseService


async def test_database():
    """测试数据库连接和基本操作."""
    print("=" * 60)
    print("测试数据库服务")
    print("=" * 60)

    # 1. 初始化
    print("\n1. 初始化数据库连接...")
    db = DatabaseService()
    await db.init()
    print("✅ 数据库连接成功！")

    # 2. 测试保存检测记录
    print("\n2. 测试保存检测记录...")

    # 创建模拟的检测结果
    class MockDetectionResult:
        def __init__(self):
            self.person_detections = [
                {"bbox": [100, 100, 200, 300], "confidence": 0.95}
            ]
            self.hairnet_results = [
                {
                    "has_hairnet": False,
                    "confidence": 0.85,
                    "bbox": [120, 100, 180, 150],
                }
            ]
            self.handwash_results = []
            self.sanitize_results = []
            self.processing_times = {
                "person_detection": 0.05,
                "hairnet_detection": 0.03,
            }

    result = MockDetectionResult()

    record_id = await db.save_detection_record(
        camera_id="test_camera_1", frame_number=1, result=result, fps=25.5
    )
    print(f"✅ 保存检测记录成功！record_id={record_id}")

    # 3. 测试保存违规事件
    print("\n3. 测试保存违规事件...")
    violation_id = await db.save_violation_event(
        detection_id=record_id,
        camera_id="test_camera_1",
        violation_type="no_hairnet",
        track_id=1,
        confidence=0.85,
        bbox={"x": 120, "y": 100, "width": 60, "height": 50},
    )
    print(f"✅ 保存违规事件成功！violation_id={violation_id}")

    # 4. 测试查询违规事件
    print("\n4. 测试查询违规事件...")
    violations = await db.get_recent_violations(camera_id="test_camera_1", limit=10)
    print(f"✅ 查询到 {len(violations)} 条违规记录")
    if violations:
        print(f"   最新违规: {violations[0]}")

    # 5. 测试更新小时统计
    print("\n5. 测试更新小时统计...")
    hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
    stats = {
        "frames": 100,
        "persons": 50,
        "hairnet_violations": 5,
        "handwash_events": 10,
        "sanitize_events": 8,
        "fps": 25.5,
        "processing_time": 0.04,
    }
    await db.update_hourly_statistics("test_camera_1", hour_start, stats)
    print("✅ 更新小时统计成功！")

    # 6. 测试查询统计数据
    print("\n6. 测试查询统计数据...")
    from datetime import timedelta

    start_time = hour_start - timedelta(hours=1)
    end_time = hour_start + timedelta(hours=1)
    statistics = await db.get_statistics("test_camera_1", start_time, end_time)
    print(f"✅ 统计数据: {statistics}")

    # 7. 关闭连接
    print("\n7. 关闭数据库连接...")
    await db.close()
    print("✅ 数据库连接已关闭")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_database())
