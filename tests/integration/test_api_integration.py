"""完整集成测试脚本 - 验证所有重构后的API端点."""

import os
import sys
from typing import Dict, List, Optional

import requests

# 配置
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0


class IntegrationTestSuite:
    """集成测试套件."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results: List[Dict] = []

    def test_endpoint(
        self,
        method: str,
        path: str,
        name: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        expected_status: int = 200,
        force_domain: Optional[bool] = None,
    ) -> Dict:
        """测试单个API端点.

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            path: API路径
            name: 测试名称
            params: 查询参数
            json_data: JSON请求体
            expected_status: 期望的状态码
            force_domain: 强制使用领域服务

        Returns:
            测试结果字典
        """
        if params is None:
            params = {}
        if force_domain is not None:
            params["force_domain"] = force_domain

        import time

        start_time = time.time()

        try:
            url = f"{self.base_url}{path}"

            if method == "GET":
                response = requests.get(url, params=params, timeout=TIMEOUT)
            elif method == "POST":
                response = requests.post(
                    url, params=params, json=json_data, timeout=TIMEOUT
                )
            elif method == "PUT":
                response = requests.put(
                    url, params=params, json=json_data, timeout=TIMEOUT
                )
            elif method == "DELETE":
                response = requests.delete(url, params=params, timeout=TIMEOUT)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response_time_ms = (time.time() - start_time) * 1000
            success = response.status_code == expected_status

            result = {
                "name": name,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response_time_ms": response_time_ms,
                "response_size": len(response.content),
            }

            if success:
                try:
                    data = response.json()
                    result["has_data"] = bool(data)
                    if isinstance(data, dict):
                        result["keys"] = list(data.keys())[:5]  # 前5个键
                except Exception:
                    result["has_data"] = False
                    result["response_text"] = response.text[:100]  # 前100字符
            else:
                result["error"] = (
                    response.text[:200]
                    if response.text
                    else f"HTTP {response.status_code} (无响应内容)"
                )
                result["error_type"] = "HTTPStatusError"
                result["status_code"] = response.status_code

            self.results.append(result)
            return result

        except requests.exceptions.Timeout as e:
            result = {
                "name": name,
                "method": method,
                "path": path,
                "success": False,
                "error": f"请求超时: {str(e)}",
                "error_type": "Timeout",
            }
            self.results.append(result)
            return result
        except requests.exceptions.ConnectionError as e:
            result = {
                "name": name,
                "method": method,
                "path": path,
                "success": False,
                "error": f"连接错误: {str(e)} (请确保后端服务正在运行)",
                "error_type": "ConnectionError",
            }
            self.results.append(result)
            return result
        except requests.exceptions.RequestException as e:
            result = {
                "name": name,
                "method": method,
                "path": path,
                "success": False,
                "error": f"请求错误: {str(e)}",
                "error_type": type(e).__name__,
            }
            self.results.append(result)
            return result
        except Exception as e:
            # 捕获所有其他异常，包括空字符串错误
            error_msg = str(e) if str(e) else f"{type(e).__name__} (无错误信息)"
            result = {
                "name": name,
                "method": method,
                "path": path,
                "success": False,
                "error": f"{type(e).__name__}: {error_msg}",
                "error_type": type(e).__name__,
            }
            self.results.append(result)
            return result

    def print_summary(self):
        """打印测试摘要."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("success", False))
        failed = total - passed

        print("\n" + "=" * 80)
        print("集成测试摘要")
        print("=" * 80)
        print(f"总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} {'❌' if failed > 0 else ''}")
        print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")

        if failed > 0:
            print("\n失败的测试:")
            for result in self.results:
                if not result.get("success", False):
                    print(f"  ❌ {result['name']} ({result['method']} {result['path']})")
                    if "error" in result:
                        error_msg = result["error"]
                        error_type = result.get("error_type", "Unknown")
                        print(f"     错误类型: {error_type}")
                        print(f"     错误信息: {error_msg}")
                    elif result.get("status_code") != result.get("expected_status"):
                        print(
                            f"     状态码: {result['status_code']} (期望: {result['expected_status']})"
                        )
                    else:
                        print(f"     未知错误")

            # 检查是否有连接错误
            connect_errors = [
                r for r in self.results if r.get("error_type") == "ConnectionError"
            ]
            if connect_errors:
                print(f"\n⚠️  检测到 {len(connect_errors)} 个连接错误")
                print("   提示: 请确保后端服务正在运行")
                print(f"   检查命令: curl {self.base_url}/api/v1/monitoring/health")

        # 响应时间统计
        response_times = [
            r["response_time_ms"] for r in self.results if "response_time_ms" in r
        ]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print(f"\n响应时间统计:")
            print(f"  平均: {avg_time:.2f}ms")
            print(f"  最大: {max_time:.2f}ms")

        print("=" * 80)


def run_integration_tests():
    """运行完整集成测试."""

    suite = IntegrationTestSuite()
    print("开始集成测试...")
    print(f"测试目标: {BASE_URL}")
    print()

    # ========== 读操作端点 ==========
    print("测试读操作端点...")

    # 1. 统计摘要
    suite.test_endpoint(
        "GET", "/api/v1/records/statistics/summary", "获取统计摘要", {"period": "7d"}
    )

    # 2. 违规记录列表
    suite.test_endpoint("GET", "/api/v1/records/violations", "获取违规记录列表", {"limit": 10})

    # 3. 违规详情
    suite.test_endpoint("GET", "/api/v1/records/violations/1", "获取违规详情")

    # 4. 摄像头统计
    suite.test_endpoint("GET", "/api/v1/records/statistics/cam0", "获取摄像头统计")

    # 5. 检测记录
    suite.test_endpoint(
        "GET", "/api/v1/records/detection-records/cam0", "获取检测记录", {"limit": 10}
    )

    # 6. 日统计
    suite.test_endpoint("GET", "/api/v1/statistics/daily", "获取日统计", {"days": 7})

    # 7. 事件历史
    suite.test_endpoint("GET", "/api/v1/statistics/events", "获取事件历史", {"limit": 10})

    # 8. 历史统计
    suite.test_endpoint("GET", "/api/v1/statistics/history", "获取历史统计", {"period": "7d"})

    # 9. 摄像头列表
    suite.test_endpoint("GET", "/api/v1/cameras", "获取摄像头列表")

    # 10. 摄像头统计详情
    suite.test_endpoint("GET", "/api/v1/cameras/cam0/stats", "获取摄像头统计详情")

    # 11. 最近事件
    suite.test_endpoint("GET", "/api/v1/events/recent", "获取最近事件", {"limit": 10})

    # 12. 实时统计
    suite.test_endpoint("GET", "/api/v1/statistics/realtime", "获取实时统计")

    # 13. 系统信息
    suite.test_endpoint("GET", "/api/v1/system/info", "获取系统信息")

    # 14. 告警历史
    suite.test_endpoint("GET", "/api/v1/alerts/history-db", "获取告警历史", {"limit": 10})

    # 15. 告警规则列表
    suite.test_endpoint("GET", "/api/v1/alerts/rules", "获取告警规则列表")

    # 16. 健康检查
    suite.test_endpoint("GET", "/api/v1/monitoring/health", "健康检查")

    # 17. 监控指标
    suite.test_endpoint("GET", "/api/v1/monitoring/metrics", "获取监控指标")

    # ========== 写操作端点 ==========
    print("\n测试写操作端点...")

    # 18. 更新违规状态
    suite.test_endpoint(
        "PUT",
        "/api/v1/records/violations/1/status",
        "更新违规状态",
        params={"status": "confirmed", "notes": "集成测试"},
        expected_status=200,
    )

    # 19. 创建摄像头
    suite.test_endpoint(
        "POST",
        "/api/v1/cameras",
        "创建摄像头",
        json_data={
            "id": "test_camera_integration",
            "name": "集成测试摄像头",
            "source": "rtsp://test.example.com/stream",
            "location": "测试位置",
            "active": True,
        },
        expected_status=200,
    )

    # 20. 更新摄像头
    suite.test_endpoint(
        "PUT",
        "/api/v1/cameras/test_camera_integration",
        "更新摄像头",
        json_data={"name": "更新后的摄像头名称"},
        expected_status=200,
    )

    # 21. 创建告警规则
    suite.test_endpoint(
        "POST",
        "/api/v1/alerts/rules",
        "创建告警规则",
        json_data={
            "name": "集成测试规则",
            "rule_type": "violation",
            "conditions": {"threshold": 5},
            "enabled": True,
        },
        expected_status=200,
    )

    # 注意：删除操作需要先创建，所以这里先跳过
    # 实际测试中可以创建一个临时资源然后删除

    # ========== 领域服务验证 ==========
    print("\n测试领域服务（force_domain=true）...")

    # 验证关键端点使用领域服务
    suite.test_endpoint(
        "GET",
        "/api/v1/records/violations",
        "违规记录列表（领域服务）",
        params={"limit": 10, "force_domain": True},
    )

    suite.test_endpoint(
        "GET",
        "/api/v1/statistics/summary",
        "统计摘要（领域服务）",
        params={"period": "7d", "force_domain": True},
    )

    suite.test_endpoint(
        "GET", "/api/v1/cameras", "摄像头列表（领域服务）", params={"force_domain": True}
    )

    # ========== 打印结果 ==========
    suite.print_summary()

    # 返回结果
    return suite.results


def main():
    """主函数."""
    try:
        results = run_integration_tests()

        # 统计
        total = len(results)
        passed = sum(1 for r in results if r.get("success", False))
        failed = total - passed

        # 退出码
        exit_code = 0 if failed == 0 else 1

        print(f"\n集成测试完成: {passed}/{total} 通过")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
