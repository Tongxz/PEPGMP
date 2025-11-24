from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DeploymentStatus:
    id: str
    status: str
    replicas: int
    cpu_usage: float
    memory_usage: float
    error: Optional[str] = None


class IDeploymentService(ABC):
    """
    部署服务接口
    负责管理模型服务的部署、扩缩容和状态监控
    """

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """获取部署状态"""

    @abstractmethod
    async def list_deployments(self) -> List[DeploymentStatus]:
        """获取所有部署列表"""

    @abstractmethod
    async def create_deployment(self, config: Dict[str, Any]) -> str:
        """
        创建部署
        Args:
            config: 部署配置，包含 model_path, replicas 等
        Returns:
            deployment_id
        """

    @abstractmethod
    async def update_deployment(
        self, deployment_id: str, config: Dict[str, Any]
    ) -> bool:
        """更新部署（如更新模型路径、环境变量）"""

    @abstractmethod
    async def scale_deployment(self, deployment_id: str, replicas: int) -> bool:
        """扩缩容"""

    @abstractmethod
    async def restart_deployment(self, deployment_id: str) -> bool:
        """重启部署"""

    @abstractmethod
    async def delete_deployment(self, deployment_id: str) -> bool:
        """删除部署"""
