#!/usr/bin/env python3
"""
前端页面自动化测试脚本
测试修复后的页面是否正常工作

测试范围：
1. 区域配置页面 (RegionConfig.vue)
2. 检测记录页面 (DetectionRecords.vue)
3. 相机配置页面 (CameraConfig.vue)
"""

import sys

from playwright.sync_api import sync_playwright

# 配置
FRONTEND_URL = "http://localhost:5173"
TIMEOUT = 30000  # 30秒超时


def test_page_loads_without_errors():
    """测试页面是否能正常加载，无控制台错误"""
    with sync_playwright() as p:
        print("🚀 启动浏览器...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 收集控制台错误
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )

        # 收集页面错误
        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        print(f"📡 访问前端: {FRONTEND_URL}")
        try:
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=TIMEOUT)
            page.wait_for_timeout(2000)  # 等待2秒让Vue初始化

            # 检查页面是否加载
            print("✅ 页面加载成功")

            # 检查是否有严重错误
            critical_errors = [
                err
                for err in console_errors
                if "Invalid vnode type" in err
                or "has already been declared" in err
                or "readonly is not defined" in err
                or "Cannot find module" in err
            ]

            if critical_errors:
                print("❌ 发现严重控制台错误：")
                for err in critical_errors[:5]:  # 只显示前5个
                    print(f"   - {err}")
                return False

            if page_errors:
                print("❌ 发现页面错误：")
                for err in page_errors[:5]:
                    print(f"   - {err}")
                return False

            # 截图
            screenshot_path = "/tmp/frontend_homepage.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 截图已保存: {screenshot_path}")

            print("✅ 首页测试通过")
            return True

        except Exception as e:
            print(f"❌ 页面加载失败: {e}")
            return False
        finally:
            browser.close()


def test_region_config_page():
    """测试区域配置页面"""
    with sync_playwright() as p:
        print("\n🧪 测试区域配置页面...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 收集错误
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )

        try:
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=TIMEOUT)
            page.wait_for_timeout(1000)

            # 尝试找到区域配置相关的导航链接
            print("🔍 查找区域配置链接...")

            # 可能的链接文本
            region_link_texts = ["区域配置", "区域管理", "Region", "ROI"]

            for link_text in region_link_texts:
                try:
                    link = page.get_by_text(link_text, exact=False).first
                    if link.is_visible():
                        print(f"✅ 找到链接: {link_text}")
                        link.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 检查是否有 "handleBatchAction has already been declared" 错误
            duplicate_errors = [
                err for err in console_errors if "has already been declared" in err
            ]

            if duplicate_errors:
                print(f"❌ 发现重复声明错误: {duplicate_errors[0]}")
                return False

            # 检查是否有 v-model 错误
            vmodel_errors = [
                err
                for err in console_errors
                if "v-model cannot be used on a prop" in err
            ]

            if vmodel_errors:
                print(f"❌ 发现 v-model 错误: {vmodel_errors[0]}")
                return False

            # 截图
            screenshot_path = "/tmp/region_config_page.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 截图已保存: {screenshot_path}")

            print("✅ 区域配置页面测试通过")
            return True

        except Exception as e:
            print(f"❌ 区域配置页面测试失败: {e}")
            page.screenshot(path="/tmp/region_config_error.png", full_page=True)
            return False
        finally:
            browser.close()


def test_detection_records_page():
    """测试检测记录页面"""
    with sync_playwright() as p:
        print("\n🧪 测试检测记录页面...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 收集错误
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )

        try:
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=TIMEOUT)
            page.wait_for_timeout(1000)

            # 查找检测记录链接
            print("🔍 查找检测记录链接...")

            record_link_texts = ["检测记录", "历史记录", "Detection", "Records"]

            for link_text in record_link_texts:
                try:
                    link = page.get_by_text(link_text, exact=False).first
                    if link.is_visible():
                        print(f"✅ 找到链接: {link_text}")
                        link.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 检查是否有 "Invalid vnode type" 错误
            vnode_errors = [
                err for err in console_errors if "Invalid vnode type" in err
            ]

            if vnode_errors:
                print(f"❌ 发现 Invalid vnode type 错误: {vnode_errors[0]}")
                return False

            # 检查是否有 "readonly is not defined" 错误
            readonly_errors = [
                err for err in console_errors if "readonly is not defined" in err
            ]

            if readonly_errors:
                print(f"❌ 发现 readonly 未定义错误: {readonly_errors[0]}")
                return False

            # 截图
            screenshot_path = "/tmp/detection_records_page.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 截图已保存: {screenshot_path}")

            print("✅ 检测记录页面测试通过")
            return True

        except Exception as e:
            print(f"❌ 检测记录页面测试失败: {e}")
            page.screenshot(path="/tmp/detection_records_error.png", full_page=True)
            return False
        finally:
            browser.close()


def test_camera_config_page():
    """测试相机配置页面"""
    with sync_playwright() as p:
        print("\n🧪 测试相机配置页面...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 收集错误
        console_errors = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type == "error"
            else None,
        )

        try:
            page.goto(FRONTEND_URL, wait_until="networkidle", timeout=TIMEOUT)
            page.wait_for_timeout(1000)

            # 查找相机配置链接
            print("🔍 查找相机配置链接...")

            camera_link_texts = ["相机配置", "摄像头配置", "Camera", "摄像头"]

            for link_text in camera_link_texts:
                try:
                    link = page.get_by_text(link_text, exact=False).first
                    if link.is_visible():
                        print(f"✅ 找到链接: {link_text}")
                        link.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # 检查是否有任何控制台错误
            if console_errors:
                print(f"⚠️  发现控制台消息 ({len(console_errors)} 条):")
                for err in console_errors[:3]:  # 只显示前3条
                    print(f"   - {err}")

            # 截图
            screenshot_path = "/tmp/camera_config_page.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 截图已保存: {screenshot_path}")

            print("✅ 相机配置页面测试通过")
            return True

        except Exception as e:
            print(f"❌ 相机配置页面测试失败: {e}")
            page.screenshot(path="/tmp/camera_config_error.png", full_page=True)
            return False
        finally:
            browser.close()


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 前端页面自动化测试")
    print("=" * 60)
    print(f"测试目标: {FRONTEND_URL}")
    print(f"超时设置: {TIMEOUT/1000}秒")
    print("=" * 60)

    results = {}

    # 1. 测试首页加载
    results["首页加载"] = test_page_loads_without_errors()

    # 2. 测试区域配置页面
    results["区域配置页面"] = test_region_config_page()

    # 3. 测试检测记录页面
    results["检测记录页面"] = test_detection_records_page()

    # 4. 测试相机配置页面
    results["相机配置页面"] = test_camera_config_page()

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")

    print("=" * 60)

    # 总结
    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")

    if passed_tests == total_tests:
        print("🎉 所有测试通过！")
        return 0
    else:
        print(f"⚠️  {total_tests - passed_tests} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
