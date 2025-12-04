import logging
from typing import Any, Dict, List, Optional

import aiodocker

from src.domain.interfaces.deployment_interface import (
    DeploymentStatus,
    IDeploymentService,
)

logger = logging.getLogger(__name__)


class DockerDeploymentService(IDeploymentService):
    """
    基于 Docker 的部署服务实现
    """

    def __init__(self, socket_path: Optional[str] = None):
        if socket_path:
            self.socket_path = socket_path
        else:
            import os

            self.socket_path = os.environ.get(
                "DOCKER_HOST", "unix:///var/run/docker.sock"
            )

        self._docker = None

    @property
    async def docker(self):
        if self._docker is None:
            self._docker = aiodocker.Docker(url=self.socket_path)
        return self._docker

    async def close(self):
        if self._docker:
            await self._docker.close()
            self._docker = None

    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        docker = await self.docker
        try:
            # 假设 deployment_id 对应 Docker 容器名或 ID
            container = await docker.containers.get(deployment_id)
            container_info = await container.show()

            # 从容器信息中获取状态
            container_state = container_info.get("State", {})
            status = container_state.get("Status", "unknown")
            running = container_state.get("Running", False)

            # 如果容器正在运行，获取统计信息
            cpu_usage = 0.0
            memory_usage = 0.0

            if running:
                try:
                    stats = await container.stats(stream=False)

                    # 计算 CPU 使用率
                    if "cpu_stats" in stats and "precpu_stats" in stats:
                        cpu_delta = (
                            stats["cpu_stats"]["cpu_usage"]["total_usage"]
                            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        )
                        system_delta = (
                            stats["cpu_stats"]["system_cpu_usage"]
                            - stats["precpu_stats"]["system_cpu_usage"]
                        )
                        if system_delta > 0:
                            cpu_usage = (cpu_delta / system_delta) * 100.0

                    # 计算内存使用率
                    if "memory_stats" in stats:
                        usage = stats["memory_stats"].get("usage", 0)
                        limit = stats["memory_stats"].get("limit", 1)
                        if limit > 0:
                            memory_usage = (usage / limit) * 100.0
                except Exception as stats_error:
                    logger.warning(f"获取容器统计信息失败: {stats_error}")

            # 标准化状态
            if status == "running" and running:
                normalized_status = "running"
            elif status in ["exited", "stopped"]:
                normalized_status = "stopped"
            elif status == "created":
                normalized_status = "created"
            else:
                normalized_status = status

            return DeploymentStatus(
                id=deployment_id,
                status=normalized_status,
                replicas=1,  # 单容器模式
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
            )
        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                logger.warning(f"容器 {deployment_id} 不存在")
                return DeploymentStatus(
                    id=deployment_id,
                    status="not_found",
                    replicas=0,
                    cpu_usage=0.0,
                    memory_usage=0.0,
                    error=f"容器不存在: {deployment_id}",
                )
            logger.error(f"获取容器 {deployment_id} 状态失败: {e}")
            return DeploymentStatus(
                id=deployment_id,
                status="error",
                replicas=0,
                cpu_usage=0.0,
                memory_usage=0.0,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"获取容器 {deployment_id} 状态失败: {e}")
            return DeploymentStatus(
                id=deployment_id,
                status="error",
                replicas=0,
                cpu_usage=0.0,
                memory_usage=0.0,
                error=str(e),
            )

    async def list_deployments(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[DeploymentStatus]:
        """
        列出所有部署（容器）

        Args:
            filters: 可选的过滤条件，例如：
                - name: 容器名模式列表，如 ["pepgmp-"]
                - label: 标签过滤，如 ["app=detection"]

        Returns:
            部署状态列表
        """
        docker = await self.docker
        results = []
        try:
            # 默认列出所有 pyt- 开头的容器
            if filters is None:
                filters = {"name": ["pyt-"]}

            containers = await docker.containers.list(filters=filters, all=True)

            for c in containers:
                try:
                    names = c._container.get("Names", [])
                    name = names[0].lstrip("/") if names else c._id[:12]

                    # 获取详细状态（使用已实现的 get_deployment_status）
                    status = await self.get_deployment_status(name)
                    results.append(status)
                except Exception as e:
                    logger.warning(f"获取容器 {c._id[:12]} 状态失败: {e}")
                    # 如果获取详细状态失败，至少返回基本信息
                    names = c._container.get("Names", [])
                    name = names[0].lstrip("/") if names else c._id[:12]
                    results.append(
                        DeploymentStatus(
                            id=name,
                            status=c._container.get("State", "unknown"),
                            replicas=1,
                            cpu_usage=0.0,
                            memory_usage=0.0,
                        )
                    )
        except Exception as e:
            logger.error(f"列出容器失败: {e}")

        return results

    async def create_deployment(self, config: Dict[str, Any]) -> str:
        """
        创建或查找部署容器

        Args:
            config: 部署配置，包含：
                - container_name: 容器名称（可选）
                - detection_task: 检测任务名称（如 "hairnet_detection"）
                - model_path: 模型路径（可选）
                - image: Docker镜像（可选，用于创建新容器）
                - labels: 容器标签（可选）

        Returns:
            deployment_id: 部署ID（容器名或ID）
        """
        docker = await self.docker

        # 优先使用 container_name，否则根据 detection_task 推断
        container_name = config.get("container_name")
        detection_task = config.get("detection_task")

        if not container_name and detection_task:
            # 根据检测任务推断容器名
            # 例如: hairnet_detection -> pepgmp-hairnet-detection 或 hairnet_detection_container
            container_name = f"pepgmp-{detection_task.replace('_', '-')}"

        if not container_name:
            # 如果没有指定容器名，尝试查找标签匹配的容器
            labels = config.get("labels", {})
            if labels:
                try:
                    filters = {"label": [f"{k}={v}" for k, v in labels.items()]}
                    containers = await docker.containers.list(filters=filters, all=True)
                    if containers:
                        names = containers[0]._container.get("Names", [])
                        container_name = (
                            names[0].lstrip("/") if names else containers[0]._id[:12]
                        )
                        logger.info(f"找到匹配标签的容器: {container_name}")
                        return container_name
                except Exception as e:
                    logger.warning(f"查找标签匹配容器失败: {e}")

            # 如果仍然没有找到，返回默认值
            logger.warning("未指定容器名且未找到匹配容器，返回默认部署ID")
            return "pepgmp-api"

        # 尝试查找现有容器
        try:
            container = await docker.containers.get(container_name)
            container_info = await container.show()
            logger.info(
                f"找到现有容器: {container_name} (状态: {container_info.get('State', {}).get('Status', 'unknown')})"
            )

            # 如果容器已停止，尝试启动
            if not container_info.get("State", {}).get("Running", False):
                try:
                    await container.start()
                    logger.info(f"已启动容器: {container_name}")
                except Exception as start_error:
                    logger.warning(f"启动容器失败: {start_error}")

            return container_name
        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                # 容器不存在，如果提供了镜像配置，可以尝试创建（这里暂时不实现）
                logger.info(f"容器 {container_name} 不存在")
                if config.get("image"):
                    logger.warning("创建新容器功能暂未实现，返回容器名供后续处理")
                return container_name
            raise
        except Exception as e:
            logger.error(f"查找容器 {container_name} 失败: {e}")
            raise

    async def update_deployment(
        self, deployment_id: str, config: Dict[str, Any]
    ) -> bool:
        """
        更新部署配置
        主要用于更新模型路径环境变量
        """
        # 注意：Docker 容器通常不能直接修改环境变量，需要重建
        # 在 Docker Compose 环境下，我们可能只是更新 .env 文件并重启
        # 或者，如果应用支持热加载配置，我们只需要通过 API 通知应用

        # 在这个阶段，我们假设应用会监听数据库配置变化，所以这里可能不需要操作 Docker
        # 但为了接口完整性，我们保留这个方法，可以用来重启容器以应用配置
        return await self.restart_deployment(deployment_id)

    async def scale_deployment(self, deployment_id: str, replicas: int) -> bool:
        # 单机 Docker 难以实现无缝扩容，除非使用 Docker Swarm 或 K8s
        # 这里的实现仅作为占位
        logger.warning("单机 Docker 环境不支持动态扩缩容")
        return False

    async def restart_deployment(self, deployment_id: str) -> bool:
        """
        重启部署容器

        Args:
            deployment_id: 容器名或ID

        Returns:
            bool: 是否成功
        """
        docker = await self.docker
        try:
            container = await docker.containers.get(deployment_id)
            await container.restart()
            logger.info(f"容器 {deployment_id} 重启成功")
            return True
        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                logger.warning(f"容器 {deployment_id} 不存在，无法重启")
            else:
                logger.error(f"重启容器 {deployment_id} 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"重启容器 {deployment_id} 失败: {e}")
            return False

    async def delete_deployment(self, deployment_id: str) -> bool:
        """
        删除部署容器

        Args:
            deployment_id: 容器名或ID

        Returns:
            bool: 是否成功
        """
        docker = await self.docker
        try:
            container = await docker.containers.get(deployment_id)
            # 先停止容器（如果正在运行）
            container_info = await container.show()
            if container_info.get("State", {}).get("Running", False):
                await container.stop()
                logger.info(f"容器 {deployment_id} 已停止")

            # 删除容器
            await container.delete(force=True)
            logger.info(f"容器 {deployment_id} 删除成功")
            return True
        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                logger.warning(f"容器 {deployment_id} 不存在，无法删除")
                return True  # 容器不存在视为成功（幂等性）
            else:
                logger.error(f"删除容器 {deployment_id} 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"删除容器 {deployment_id} 失败: {e}")
            return False
