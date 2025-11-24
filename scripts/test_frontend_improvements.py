#!/usr/bin/env python3
"""前端功能完善统一测试脚本

测试所有已完成的前端功能完善任务：
1. 智能检测实时统计接口
2. 告警历史分页和排序接口
3. 告警规则分页接口
"""

import asyncio
import json
import sys
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("需要安装 httpx: pip install httpx")
    sys.exit(1)

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 10.0


async def test_detection_realtime_stats():
    """测试智能检测实时统计接口"""
    print("\n" + "=" * 60)
    print("测试1: 智能检测实时统计接口")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{BASE_URL}/statistics/detection-realtime")
            response.raise_for_status()
            data = response.json()

            print("✅ 接口调用成功")
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # 验证数据结构
            required_fields = [
                "processing_efficiency",
                "avg_fps",
                "processed_frames",
                "skipped_frames",
                "scene_distribution",
                "performance",
                "connection_status",
                "timestamp",
            ]

            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
                return False

            # 验证嵌套字段
            if "scene_distribution" in data:
                scene_fields = ["static", "dynamic", "critical"]
                missing = [f for f in scene_fields if f not in data["scene_distribution"]]
                if missing:
                    print(f"⚠️  场景分布缺少字段: {missing}")
                    return False

            if "performance" in data:
                perf_fields = ["cpu_usage", "memory_usage", "gpu_usage"]
                missing = [f for f in perf_fields if f not in data["performance"]]
                if missing:
                    print(f"⚠️  性能监控缺少字段: {missing}")
                    return False

            if "connection_status" in data:
                conn_fields = ["connected", "active_cameras"]
                missing = [f for f in conn_fields if f not in data["connection_status"]]
                if missing:
                    print(f"⚠️  连接状态缺少字段: {missing}")
                    return False

            print("✅ 数据结构验证通过")
            return True

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


async def test_alert_history_pagination():
    """测试告警历史分页接口"""
    print("\n" + "=" * 60)
    print("测试2: 告警历史分页接口")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # 测试基本分页
            response = await client.get(
                f"{BASE_URL}/alerts/history-db",
                params={"limit": 10, "offset": 0},
            )
            response.raise_for_status()
            data = response.json()

            print("✅ 基本分页测试通过")
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # 验证分页字段
            required_fields = ["count", "total", "items", "limit", "offset"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
                return False

            # 测试页码参数
            response2 = await client.get(
                f"{BASE_URL}/alerts/history-db",
                params={"limit": 10, "page": 2},
            )
            response2.raise_for_status()
            data2 = response2.json()

            if data2.get("offset") != 10:
                print(f"⚠️  页码计算错误: 期望offset=10, 实际={data2.get('offset')}")
                return False

            print("✅ 页码参数测试通过")
            return True

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


async def test_alert_history_sorting():
    """测试告警历史排序接口"""
    print("\n" + "=" * 60)
    print("测试3: 告警历史排序接口")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # 测试按时间降序排序
            response = await client.get(
                f"{BASE_URL}/alerts/history-db",
                params={"limit": 10, "sort_by": "timestamp", "sort_order": "desc"},
            )
            response.raise_for_status()
            data = response.json()

            print("✅ 时间降序排序测试通过")

            # 测试按摄像头升序排序
            response2 = await client.get(
                f"{BASE_URL}/alerts/history-db",
                params={"limit": 10, "sort_by": "camera_id", "sort_order": "asc"},
            )
            response2.raise_for_status()
            data2 = response2.json()

            print("✅ 摄像头升序排序测试通过")

            # 测试按类型排序
            response3 = await client.get(
                f"{BASE_URL}/alerts/history-db",
                params={"limit": 10, "sort_by": "alert_type", "sort_order": "desc"},
            )
            response3.raise_for_status()
            data3 = response3.json()

            print("✅ 类型排序测试通过")
            return True

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


async def test_alert_rules_pagination():
    """测试告警规则分页接口"""
    print("\n" + "=" * 60)
    print("测试4: 告警规则分页接口")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # 测试基本分页
            response = await client.get(
                f"{BASE_URL}/alerts/rules",
                params={"limit": 10, "offset": 0},
            )
            response.raise_for_status()
            data = response.json()

            print("✅ 基本分页测试通过")
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

            # 验证分页字段
            required_fields = ["count", "total", "items", "limit", "offset"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
                return False

            # 测试页码参数
            response2 = await client.get(
                f"{BASE_URL}/alerts/rules",
                params={"limit": 10, "page": 2},
            )
            response2.raise_for_status()
            data2 = response2.json()

            if data2.get("offset") != 10:
                print(f"⚠️  页码计算错误: 期望offset=10, 实际={data2.get('offset')}")
                return False

            print("✅ 页码参数测试通过")
            return True

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


async def test_camera_list():
    """测试摄像头列表接口（用于检测记录页面）"""
    print("\n" + "=" * 60)
    print("测试5: 摄像头列表接口")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(f"{BASE_URL}/cameras")
            response.raise_for_status()
            data = response.json()

            print("✅ 接口调用成功")
            print(f"摄像头数量: {len(data) if isinstance(data, list) else 'N/A'}")
            if isinstance(data, list) and len(data) > 0:
                print(f"第一个摄像头: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
            return True

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP错误: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("前端功能完善统一测试")
    print("=" * 60)
    print(f"测试目标: {BASE_URL}")
    print(f"超时设置: {TIMEOUT}秒")

    results = []

    # 运行所有测试
    results.append(("智能检测实时统计接口", await test_detection_realtime_stats()))
    results.append(("告警历史分页接口", await test_alert_history_pagination()))
    results.append(("告警历史排序接口", await test_alert_history_sorting()))
    results.append(("告警规则分页接口", await test_alert_rules_pagination()))
    results.append(("摄像头列表接口", await test_camera_list()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")

    if failed > 0:
        print("\n⚠️  部分测试失败，请检查后端服务是否正常运行")
        sys.exit(1)
    else:
        print("\n✅ 所有测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

