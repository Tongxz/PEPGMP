#!/usr/bin/env python3
"""验证数据导出功能.

测试导出API接口是否正常工作.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"


async def test_export_detection_records(session: aiohttp.ClientSession):
    """测试检测记录导出."""
    print("\n" + "=" * 60)
    print("测试检测记录导出")
    print("=" * 60)

    # 测试参数
    params = {
        "camera_id": "vid1",  # 使用一个已知的摄像头ID
        "format": "csv",
        "limit": 100,  # 小数据量测试
    }

    # 添加时间范围（最近7天）
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    params["start_time"] = start_time.isoformat()
    params["end_time"] = end_time.isoformat()

    url = f"{BASE_URL}/export/detection-records"
    print(f"请求URL: {url}")
    print(f"参数: {params}")

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            print(f"状态码: {response.status}")

            if response.status == 200:
                content = await response.read()
                content_length = len(content)
                print("✅ 导出成功")
                print(f"   文件大小: {content_length} 字节")

                # 检查是否为CSV格式（包含BOM和表头）
                if content.startswith(b"\xef\xbb\xbf"):
                    print("   ✅ 包含UTF-8 BOM（Excel兼容）")
                    content = content[3:]  # 移除BOM

                content_text = content.decode("utf-8")
                lines = content_text.strip().split("\n")
                print(f"   总行数: {len(lines)}")
                if lines:
                    print(f"   表头: {lines[0][:100]}...")
                    if len(lines) > 1:
                        print(f"   首行数据: {lines[1][:100]}...")
            else:
                error_text = await response.text()
                print(f"❌ 导出失败: {error_text}")
                return False
    except asyncio.TimeoutError:
        print("❌ 请求超时（120秒）")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

    return True


async def test_export_violations(session: aiohttp.ClientSession):
    """测试违规记录导出."""
    print("\n" + "=" * 60)
    print("测试违规记录导出")
    print("=" * 60)

    params = {
        "format": "csv",
        "limit": 100,
    }

    url = f"{BASE_URL}/export/violations"
    print(f"请求URL: {url}")
    print(f"参数: {params}")

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            print(f"状态码: {response.status}")

            if response.status == 200:
                content = await response.read()
                content_length = len(content)
                print("✅ 导出成功")
                print(f"   文件大小: {content_length} 字节")

                # 检查是否为CSV格式
                if content.startswith(b"\xef\xbb\xbf"):
                    print("   ✅ 包含UTF-8 BOM（Excel兼容）")
                    content = content[3:]

                content_text = content.decode("utf-8")
                lines = content_text.strip().split("\n")
                print(f"   总行数: {len(lines)}")
                if lines:
                    print(f"   表头: {lines[0][:100]}...")
                    if len(lines) > 1:
                        print(f"   首行数据: {lines[1][:100]}...")
            elif response.status == 404:
                print("⚠️  没有找到违规记录（这是正常的，如果数据库为空）")
                return True  # 404是正常的，如果没有数据
            else:
                error_text = await response.text()
                print(f"❌ 导出失败: {error_text}")
                return False
    except asyncio.TimeoutError:
        print("❌ 请求超时（120秒）")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

    return True


async def test_export_statistics(session: aiohttp.ClientSession):
    """测试统计数据导出."""
    print("\n" + "=" * 60)
    print("测试统计数据导出")
    print("=" * 60)

    params = {
        "format": "csv",
        "days": 7,
    }

    url = f"{BASE_URL}/export/statistics"
    print(f"请求URL: {url}")
    print(f"参数: {params}")

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            print(f"状态码: {response.status}")

            if response.status == 200:
                content = await response.read()
                content_length = len(content)
                print("✅ 导出成功")
                print(f"   文件大小: {content_length} 字节")

                # 检查是否为CSV格式
                if content.startswith(b"\xef\xbb\xbf"):
                    print("   ✅ 包含UTF-8 BOM（Excel兼容）")
                    content = content[3:]

                content_text = content.decode("utf-8")
                lines = content_text.strip().split("\n")
                print(f"   总行数: {len(lines)}")
                if lines:
                    print(f"   表头: {lines[0][:100]}...")
                    if len(lines) > 1:
                        print(f"   首行数据: {lines[1][:100]}...")
            elif response.status == 404:
                print("⚠️  没有找到统计数据（这是正常的，如果数据库为空）")
                return True  # 404是正常的，如果没有数据
            else:
                error_text = await response.text()
                print(f"❌ 导出失败: {error_text}")
                return False
    except asyncio.TimeoutError:
        print("❌ 请求超时（120秒）")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

    return True


async def test_export_with_invalid_params(session: aiohttp.ClientSession):
    """测试无效参数."""
    print("\n" + "=" * 60)
    print("测试无效参数处理")
    print("=" * 60)

    # 测试1: 检测记录导出没有camera_id
    url = f"{BASE_URL}/export/detection-records"
    params = {"format": "csv", "limit": 10}

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 400:
                error_text = await response.text()
                print("✅ 正确拒绝无效请求（缺少camera_id）")
                print(f"   错误信息: {error_text[:200]}")
                return True
            else:
                print(f"⚠️  未正确处理无效请求，状态码: {response.status}")
                return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


async def main():
    """主函数."""
    print("=" * 60)
    print("数据导出功能验证")
    print("=" * 60)
    print(f"API基础URL: {BASE_URL}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    async with aiohttp.ClientSession() as session:
        # 测试检测记录导出
        results.append(("检测记录导出", await test_export_detection_records(session)))

        # 测试违规记录导出
        results.append(("违规记录导出", await test_export_violations(session)))

        # 测试统计数据导出
        results.append(("统计数据导出", await test_export_statistics(session)))

        # 测试无效参数
        results.append(("无效参数处理", await test_export_with_invalid_params(session)))

    # 打印总结
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for _, result in results if result)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if passed == total:
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n❌ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
