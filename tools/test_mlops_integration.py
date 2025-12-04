#!/usr/bin/env python3
"""
MLOps集成功能测试
测试数据库集成、Docker部署、工作流引擎等完整功能
"""

import logging
from datetime import datetime

import requests

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000/api/v1/mlops"


class MLOpsIntegrationTester:
    """MLOps集成测试器"""

    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.test_results = {}

    def test_api_health(self):
        """测试API健康状态"""
        logger.info("🔍 测试API健康状态...")

        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API健康检查通过")
                return True
            else:
                logger.error(f"❌ API健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API健康检查异常: {e}")
            return False

    def test_datasets_api(self):
        """测试数据集API"""
        logger.info("🔍 测试数据集API...")

        try:
            # 获取数据集列表
            response = requests.get(f"{self.api_base_url}/datasets", timeout=10)
            if response.status_code == 200:
                datasets = response.json()
                logger.info(f"✅ 获取数据集列表成功: {len(datasets)} 个数据集")

                # 测试获取特定数据集
                if datasets:
                    dataset_id = datasets[0]["id"]
                    detail_response = requests.get(
                        f"{self.api_base_url}/datasets/{dataset_id}", timeout=5
                    )
                    if detail_response.status_code == 200:
                        logger.info(f"✅ 获取数据集详情成功: {dataset_id}")
                        return True
                    else:
                        logger.error(f"❌ 获取数据集详情失败: {detail_response.status_code}")
                        return False
                else:
                    logger.warning("⚠️ 没有数据集可供测试")
                    return True
            else:
                logger.error(f"❌ 获取数据集列表失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 数据集API测试异常: {e}")
            return False

    def test_deployments_api(self):
        """测试部署API"""
        logger.info("🔍 测试部署API...")

        try:
            # 获取部署列表
            response = requests.get(f"{self.api_base_url}/deployments", timeout=10)
            if response.status_code == 200:
                deployments = response.json()
                logger.info(f"✅ 获取部署列表成功: {len(deployments)} 个部署")

                # 测试创建新部署
                new_deployment = {
                    "name": f"test_deployment_{int(datetime.utcnow().timestamp())}",
                    "model_version": "test_v1.0",
                    "environment": "testing",
                    "replicas": 1,
                    "image": "pepgmp-backend:latest",
                    "environment_variables": {
                        "TEST_MODE": "true",
                        "LOG_LEVEL": "DEBUG",
                    },
                    "ports": [{"container": 8000, "host": 8001}],
                    "cpu_limit": "0.5",
                    "memory_limit": "1Gi",
                }

                create_response = requests.post(
                    f"{self.api_base_url}/deployments", json=new_deployment, timeout=30
                )

                if create_response.status_code == 200:
                    result = create_response.json()
                    logger.info(f"✅ 创建部署成功: {result.get('deployment_id')}")

                    # 测试扩缩容
                    scale_response = requests.put(
                        f"{self.api_base_url}/deployments/{result['deployment_id']}/scale?replicas=2",
                        timeout=10,
                    )

                    if scale_response.status_code == 200:
                        logger.info("✅ 部署扩缩容成功")

                        # 测试删除部署
                        delete_response = requests.delete(
                            f"{self.api_base_url}/deployments/{result['deployment_id']}",
                            timeout=10,
                        )

                        if delete_response.status_code == 200:
                            logger.info("✅ 删除部署成功")
                            return True
                        else:
                            logger.error(f"❌ 删除部署失败: {delete_response.status_code}")
                            return False
                    else:
                        logger.error(f"❌ 部署扩缩容失败: {scale_response.status_code}")
                        return False
                else:
                    logger.error(f"❌ 创建部署失败: {create_response.status_code}")
                    logger.error(f"错误详情: {create_response.text}")
                    return False
            else:
                logger.error(f"❌ 获取部署列表失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 部署API测试异常: {e}")
            return False

    def test_workflows_api(self):
        """测试工作流API"""
        logger.info("🔍 测试工作流API...")

        try:
            # 获取工作流列表
            response = requests.get(f"{self.api_base_url}/workflows", timeout=10)
            if response.status_code == 200:
                workflows = response.json()
                logger.info(f"✅ 获取工作流列表成功: {len(workflows)} 个工作流")

                # 测试创建新工作流
                new_workflow = {
                    "name": f"测试工作流_{int(datetime.utcnow().timestamp())}",
                    "type": "training",
                    "trigger": "manual",
                    "description": "这是一个测试工作流",
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
                        {
                            "name": "模型评估",
                            "type": "model_evaluation",
                            "description": "评估模型性能",
                        },
                    ],
                }

                create_response = requests.post(
                    f"{self.api_base_url}/workflows", json=new_workflow, timeout=30
                )

                if create_response.status_code == 200:
                    result = create_response.json()
                    workflow_id = result.get("workflow_id")
                    logger.info(f"✅ 创建工作流成功: {workflow_id}")

                    # 测试运行工作流
                    run_response = requests.post(
                        f"{self.api_base_url}/workflows/{workflow_id}/run",
                        timeout=60,  # 工作流运行可能需要更长时间
                    )

                    if run_response.status_code == 200:
                        run_result = run_response.json()
                        logger.info(f"✅ 运行工作流成功: {run_result.get('run_id')}")

                        # 测试删除工作流
                        delete_response = requests.delete(
                            f"{self.api_base_url}/workflows/{workflow_id}", timeout=10
                        )

                        if delete_response.status_code == 200:
                            logger.info("✅ 删除工作流成功")
                            return True
                        else:
                            logger.error(f"❌ 删除工作流失败: {delete_response.status_code}")
                            return False
                    else:
                        logger.error(f"❌ 运行工作流失败: {run_response.status_code}")
                        logger.error(f"错误详情: {run_response.text}")
                        return False
                else:
                    logger.error(f"❌ 创建工作流失败: {create_response.status_code}")
                    logger.error(f"错误详情: {create_response.text}")
                    return False
            else:
                logger.error(f"❌ 获取工作流列表失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 工作流API测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始MLOps集成功能测试...")

        # 运行各项测试
        self.test_results = {
            "api_health": self.test_api_health(),
            "datasets_api": self.test_datasets_api(),
            "deployments_api": self.test_deployments_api(),
            "workflows_api": self.test_workflows_api(),
        }

        # 显示测试结果
        logger.info("\n📋 测试结果摘要:")
        logger.info("=" * 50)

        passed_tests = 0
        total_tests = len(self.test_results)

        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name.ljust(20)} : {status}")
            if result:
                passed_tests += 1

        logger.info("=" * 50)
        logger.info(f"总计: {passed_tests}/{total_tests} 测试通过")

        if passed_tests == total_tests:
            logger.info("🎉 所有测试通过！MLOps集成功能运行正常。")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} 个测试失败，请检查相关功能。")

        return self.test_results


def main():
    """主函数"""
    tester = MLOpsIntegrationTester()
    results = tester.run_all_tests()

    # 返回适当的退出码
    if all(results.values()):
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()
