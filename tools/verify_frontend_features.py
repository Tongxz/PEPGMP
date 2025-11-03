#!/usr/bin/env python3
"""
前端功能验证脚本
验证所有MLOps功能是否在前端正常工作
"""

import time

import requests

API_BASE_URL = "http://localhost:8000/api/v1/mlops"
FRONTEND_URL = "http://localhost:5173"


def test_api_endpoints():
    """测试所有API端点"""
    print("🔍 测试API端点...")

    endpoints = [
        "/health",
        "/api/v1/mlops/datasets",
        "/api/v1/mlops/deployments",
        "/api/v1/mlops/workflows",
    ]

    results = {}

    for endpoint in endpoints:
        try:
            url = f"http://localhost:8000{endpoint}"
            response = requests.get(url, timeout=5)
            results[endpoint] = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data_length": len(response.text) if response.text else 0,
            }

            if response.status_code == 200:
                print(f"✅ {endpoint} - 正常")
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")

        except Exception as e:
            results[endpoint] = {"status_code": 0, "success": False, "error": str(e)}
            print(f"❌ {endpoint} - 错误: {e}")

    return results


def test_mlops_features():
    """测试MLOps功能"""
    print("\n🔍 测试MLOps功能...")

    features = {
        "datasets": test_datasets_feature(),
        "deployments": test_deployments_feature(),
        "workflows": test_workflows_feature(),
    }

    return features


def test_datasets_feature():
    """测试数据集功能"""
    print("  📊 测试数据集功能...")

    try:
        # 获取数据集列表
        response = requests.get(f"{API_BASE_URL}/datasets", timeout=10)
        if response.status_code == 200:
            datasets = response.json()
            print(f"    ✅ 数据集列表: {len(datasets)} 个数据集")

            # 测试获取详情
            if datasets:
                dataset_id = datasets[0]["id"]
                detail_response = requests.get(
                    f"{API_BASE_URL}/datasets/{dataset_id}", timeout=5
                )
                if detail_response.status_code == 200:
                    print(f"    ✅ 数据集详情: {dataset_id}")
                    return True
                else:
                    print(f"    ❌ 数据集详情失败: {detail_response.status_code}")
                    return False
            return True
        else:
            print(f"    ❌ 数据集列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ 数据集功能异常: {e}")
        return False


def test_deployments_feature():
    """测试部署功能"""
    print("  🚀 测试部署功能...")

    try:
        # 获取部署列表
        response = requests.get(f"{API_BASE_URL}/deployments", timeout=10)
        if response.status_code == 200:
            deployments = response.json()
            print(f"    ✅ 部署列表: {len(deployments)} 个部署")
            return True
        else:
            print(f"    ❌ 部署列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ 部署功能异常: {e}")
        return False


def test_workflows_feature():
    """测试工作流功能"""
    print("  ⚙️ 测试工作流功能...")

    try:
        # 获取工作流列表
        response = requests.get(f"{API_BASE_URL}/workflows", timeout=10)
        if response.status_code == 200:
            workflows = response.json()
            print(f"    ✅ 工作流列表: {len(workflows)} 个工作流")

            # 测试创建工作流
            new_workflow = {
                "name": f"验证测试工作流_{int(time.time())}",
                "type": "training",
                "trigger": "manual",
                "description": "前端验证测试工作流",
                "steps": [
                    {
                        "name": "数据预处理",
                        "type": "data_processing",
                        "description": "清洗和预处理数据",
                    },
                    {
                        "name": "模型训练",
                        "type": "model_training",
                        "description": "训练机器学习模型",
                    },
                ],
            }

            create_response = requests.post(
                f"{API_BASE_URL}/workflows", json=new_workflow, timeout=30
            )
            if create_response.status_code == 200:
                result = create_response.json()
                workflow_id = result.get("workflow_id")
                print(f"    ✅ 创建工作流: {workflow_id}")

                # 测试运行工作流
                run_response = requests.post(
                    f"{API_BASE_URL}/workflows/{workflow_id}/run", timeout=60
                )
                if run_response.status_code == 200:
                    print(f"    ✅ 运行工作流成功")

                    # 清理：删除测试工作流
                    delete_response = requests.delete(
                        f"{API_BASE_URL}/workflows/{workflow_id}", timeout=10
                    )
                    if delete_response.status_code == 200:
                        print(f"    ✅ 删除工作流成功")

                    return True
                else:
                    print(f"    ❌ 运行工作流失败: {run_response.status_code}")
                    return False
            else:
                print(f"    ❌ 创建工作流失败: {create_response.status_code}")
                return False
        else:
            print(f"    ❌ 工作流列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"    ❌ 工作流功能异常: {e}")
        return False


def test_frontend_access():
    """测试前端访问"""
    print("\n🌐 测试前端访问...")

    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            print("✅ 前端页面可访问")
            return True
        else:
            print(f"❌ 前端页面访问失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 前端访问异常: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始前端功能验证...")
    print("=" * 60)

    # 测试API端点
    api_results = test_api_endpoints()

    # 测试MLOps功能
    mlops_results = test_mlops_features()

    # 测试前端访问
    frontend_ok = test_frontend_access()

    # 显示结果摘要
    print("\n📋 验证结果摘要:")
    print("=" * 60)

    # API端点结果
    api_success = sum(1 for r in api_results.values() if r["success"])
    api_total = len(api_results)
    print(f"API端点: {api_success}/{api_total} 通过")

    # MLOps功能结果
    mlops_success = sum(1 for r in mlops_results.values() if r)
    mlops_total = len(mlops_results)
    print(f"MLOps功能: {mlops_success}/{mlops_total} 通过")

    # 前端访问
    print(f"前端访问: {'✅ 通过' if frontend_ok else '❌ 失败'}")

    print("\n🎯 前端验证指南:")
    print("1. 打开浏览器访问: http://localhost:5173")
    print("2. 登录系统（如果需要）")
    print("3. 导航到 'MLOps管理' 页面")
    print("4. 验证以下功能:")
    print("   - 数据集管理: 查看、创建、编辑数据集")
    print("   - 部署管理: 查看部署状态（Docker功能需要Docker环境）")
    print("   - 工作流管理: 创建、运行、管理工作流")
    print("   - 实验跟踪: 查看MLflow实验数据")
    print("   - 模型版本: 查看DVC模型版本")

    print("\n📊 详细功能状态:")
    for feature, status in mlops_results.items():
        status_text = "✅ 正常" if status else "❌ 异常"
        print(f"  {feature}: {status_text}")

    if frontend_ok and mlops_success >= 2:
        print("\n🎉 前端功能验证完成！可以正常使用MLOps功能。")
    else:
        print("\n⚠️ 部分功能异常，请检查相关服务。")


if __name__ == "__main__":
    main()
