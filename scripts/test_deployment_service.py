"""
测试部署服务的完整功能
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.deployment.docker_service import DockerDeploymentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_list_deployments():
    """测试列出部署"""
    logger.info("=" * 60)
    logger.info("测试: 列出所有部署")
    logger.info("=" * 60)

    service = DockerDeploymentService()
    try:
        deployments = await service.list_deployments()
        logger.info(f"找到 {len(deployments)} 个部署:")
        for d in deployments:
            logger.info(
                f"  - {d.id}: {d.status} (CPU: {d.cpu_usage:.1f}%, Memory: {d.memory_usage:.1f}%)"
            )
        return len(deployments) > 0
    except Exception as e:
        logger.error(f"列出部署失败: {e}")
        return False
    finally:
        await service.close()


async def test_get_deployment_status():
    """测试获取部署状态"""
    logger.info("=" * 60)
    logger.info("测试: 获取部署状态")
    logger.info("=" * 60)

    service = DockerDeploymentService()
    try:
        # 先列出所有部署
        deployments = await service.list_deployments()
        if not deployments:
            logger.warning("没有找到部署，跳过状态测试")
            return True

        # 测试第一个部署的状态
        test_deployment = deployments[0]
        logger.info(f"测试部署: {test_deployment.id}")

        status = await service.get_deployment_status(test_deployment.id)
        logger.info(f"状态详情:")
        logger.info(f"  - ID: {status.id}")
        logger.info(f"  - 状态: {status.status}")
        logger.info(f"  - 副本数: {status.replicas}")
        logger.info(f"  - CPU使用率: {status.cpu_usage:.2f}%")
        logger.info(f"  - 内存使用率: {status.memory_usage:.2f}%")
        if status.error:
            logger.warning(f"  - 错误: {status.error}")

        return True
    except Exception as e:
        logger.error(f"获取部署状态失败: {e}")
        return False
    finally:
        await service.close()


async def test_create_deployment():
    """测试创建/查找部署"""
    logger.info("=" * 60)
    logger.info("测试: 创建/查找部署")
    logger.info("=" * 60)

    service = DockerDeploymentService()
    try:
        # 测试1: 查找现有容器
        config1 = {
            "detection_task": "hairnet_detection",
            "container_name": "pyt-postgres-dev",  # 使用已知存在的容器
        }
        logger.info(f"测试配置1: {config1}")
        deployment_id1 = await service.create_deployment(config1)
        logger.info(f"结果: {deployment_id1}")

        # 测试2: 使用检测任务名称
        config2 = {"detection_task": "human_detection"}
        logger.info(f"测试配置2: {config2}")
        deployment_id2 = await service.create_deployment(config2)
        logger.info(f"结果: {deployment_id2}")

        # 测试3: 不存在的容器
        config3 = {"container_name": "non-existent-container-12345"}
        logger.info(f"测试配置3: {config3}")
        deployment_id3 = await service.create_deployment(config3)
        logger.info(f"结果: {deployment_id3} (预期: 返回容器名，但容器不存在)")

        return True
    except Exception as e:
        logger.error(f"创建/查找部署失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await service.close()


async def test_restart_deployment():
    """测试重启部署"""
    logger.info("=" * 60)
    logger.info("测试: 重启部署")
    logger.info("=" * 60)

    service = DockerDeploymentService()
    try:
        # 获取一个存在的部署
        deployments = await service.list_deployments()
        if not deployments:
            logger.warning("没有找到部署，跳过重启测试")
            return True

        test_deployment = deployments[0]
        logger.info(f"测试重启: {test_deployment.id}")

        result = await service.restart_deployment(test_deployment.id)
        if result:
            logger.info(f"✅ 重启成功: {test_deployment.id}")
        else:
            logger.warning(f"⚠️ 重启失败: {test_deployment.id}")

        return True
    except Exception as e:
        logger.error(f"重启部署失败: {e}")
        return False
    finally:
        await service.close()


async def main():
    """运行所有测试"""
    logger.info("开始测试部署服务功能...")

    results = []

    # 测试1: 列出部署
    results.append(("列出部署", await test_list_deployments()))

    # 测试2: 获取部署状态
    results.append(("获取部署状态", await test_get_deployment_status()))

    # 测试3: 创建/查找部署
    results.append(("创建/查找部署", await test_create_deployment()))

    # 测试4: 重启部署（可选，可能会影响正在运行的容器）
    # results.append(("重启部署", await test_restart_deployment()))

    # 汇总结果
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ 所有测试通过")
    else:
        logger.warning("⚠️ 部分测试失败")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
