"""
仓储工厂
使用工厂模式创建不同的仓储实现
"""

import logging
from typing import Any, Dict, List, Optional, Type

from src.interfaces.repositories.detection_repository_interface import (
    IDetectionRepository,
)

from .postgresql_detection_repository import PostgreSQLDetectionRepository
from .redis_detection_repository import RedisDetectionRepository

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """仓储工厂"""

    # 注册的仓储实现
    _repositories: Dict[str, Type[IDetectionRepository]] = {
        "postgresql": PostgreSQLDetectionRepository,
        "redis": RedisDetectionRepository,
    }

    @classmethod
    def create_repository(cls, repository_type: str, **kwargs) -> IDetectionRepository:
        """
        创建仓储实例

        Args:
            repository_type: 仓储类型
            **kwargs: 仓储参数

        Returns:
            IDetectionRepository: 仓储实例

        Raises:
            ValueError: 不支持的仓储类型
            RepositoryError: 仓储创建失败
        """
        if repository_type not in cls._repositories:
            available_types = list(cls._repositories.keys())
            raise ValueError(f"不支持的仓储类型: {repository_type}. 可用类型: {available_types}")

        try:
            repository_class = cls._repositories[repository_type]
            repository = repository_class(**kwargs)

            logger.info(f"创建仓储成功: {repository_type}")
            return repository

        except Exception as e:
            logger.error(f"创建仓储失败: {repository_type}, 错误: {e}")
            raise

    @classmethod
    def get_available_repositories(cls) -> List[str]:
        """
        获取可用的仓储列表

        Returns:
            List[str]: 可用的仓储类型列表
        """
        available = []

        for repository_type, repository_class in cls._repositories.items():
            try:
                # 尝试创建仓储实例来检查可用性
                if repository_type == "postgresql":
                    # PostgreSQL需要数据库连接
                    repository_class()
                elif repository_type == "redis":
                    # Redis需要Redis连接
                    repository_class()
                else:
                    repository_class()

                # 简单检查：如果创建成功就认为可用
                available.append(repository_type)

            except Exception as e:
                logger.debug(f"仓储 {repository_type} 不可用: {e}")
                continue

        return available

    @classmethod
    def get_repository_info(cls, repository_type: str) -> Dict[str, Any]:
        """
        获取仓储信息

        Args:
            repository_type: 仓储类型

        Returns:
            Dict[str, Any]: 仓储信息
        """
        if repository_type not in cls._repositories:
            raise ValueError(f"不支持的仓储类型: {repository_type}")

        repository_class = cls._repositories[repository_type]

        # 获取仓储类的文档字符串
        doc = repository_class.__doc__ or "无文档"

        return {
            "type": repository_type,
            "class": repository_class.__name__,
            "module": repository_class.__module__,
            "description": doc.strip(),
            "available": repository_type in cls.get_available_repositories(),
        }

    @classmethod
    def register_repository(
        cls, repository_type: str, repository_class: Type[IDetectionRepository]
    ) -> None:
        """
        注册新的仓储实现

        Args:
            repository_type: 仓储类型名称
            repository_class: 仓储类
        """
        if not issubclass(repository_class, IDetectionRepository):
            raise ValueError(f"仓储类必须实现 IDetectionRepository 接口: {repository_class}")

        cls._repositories[repository_type] = repository_class
        logger.info(f"注册仓储实现: {repository_type} -> {repository_class.__name__}")

    @classmethod
    def unregister_repository(cls, repository_type: str) -> None:
        """
        注销仓储实现

        Args:
            repository_type: 仓储类型名称
        """
        if repository_type in cls._repositories:
            del cls._repositories[repository_type]
            logger.info(f"注销仓储实现: {repository_type}")
        else:
            logger.warning(f"尝试注销不存在的仓储实现: {repository_type}")

    @classmethod
    def get_supported_repositories(cls) -> List[str]:
        """
        获取所有支持的仓储类型

        Returns:
            List[str]: 仓储类型列表
        """
        return list(cls._repositories.keys())

    @classmethod
    def validate_repository_config(
        cls, repository_type: str, config: Dict[str, Any]
    ) -> bool:
        """
        验证仓储配置

        Args:
            repository_type: 仓储类型
            config: 配置字典

        Returns:
            bool: 配置是否有效
        """
        if repository_type not in cls._repositories:
            return False

        try:
            # 尝试创建仓储实例来验证配置
            cls.create_repository(repository_type, **config)
            return True
        except Exception as e:
            logger.debug(f"仓储配置验证失败: {repository_type}, 错误: {e}")
            return False

    @classmethod
    def create_repository_from_config(
        cls, config: Dict[str, Any]
    ) -> IDetectionRepository:
        """
        从配置创建仓储

        Args:
            config: 配置字典，必须包含 'type' 字段

        Returns:
            IDetectionRepository: 仓储实例
        """
        repository_type = config.get("type")
        if not repository_type:
            raise ValueError("配置中必须包含 'type' 字段")

        # 移除 type 字段，其余作为参数
        repository_config = {k: v for k, v in config.items() if k != "type"}

        return cls.create_repository(repository_type, **repository_config)

    @classmethod
    def create_repository_from_env(cls) -> IDetectionRepository:
        """根据环境变量创建仓储实例。

        环境变量：
        - REPOSITORY_TYPE: postgresql|redis（默认: postgresql）
        - 其余连接/配置参数按需扩展
        """
        import os

        repo_type = os.getenv("REPOSITORY_TYPE", "postgresql").lower()
        # 可按需扩展参数（此处使用默认构造，配置集中到代码/配置文件）
        return cls.create_repository(repo_type)


def create_repository_from_config(config: Dict[str, Any]) -> IDetectionRepository:
    """
    从配置创建仓储的便捷函数

    Args:
        config: 配置字典，必须包含 'type' 字段

    Returns:
        IDetectionRepository: 仓储实例
    """
    return RepositoryFactory.create_repository_from_config(config)


def get_repository_recommendations() -> Dict[str, Any]:
    """
    获取仓储推荐信息

    Returns:
        Dict[str, Any]: 推荐信息
    """
    available = RepositoryFactory.get_available_repositories()

    recommendations = {
        "postgresql": {
            "description": "PostgreSQL - 关系型数据库，适合持久化存储",
            "best_for": ["持久化存储", "复杂查询", "事务支持", "数据一致性"],
            "performance": "高",
            "resource_usage": "中等",
            "scalability": "高",
            "available": "postgresql" in available,
        },
        "redis": {
            "description": "Redis - 内存数据库，适合缓存和临时存储",
            "best_for": ["缓存", "临时存储", "快速访问", "会话存储"],
            "performance": "极高",
            "resource_usage": "高（内存）",
            "scalability": "中等",
            "available": "redis" in available,
        },
    }

    return recommendations


def get_repository_for_use_case(use_case: str) -> Optional[str]:
    """
    根据使用场景推荐仓储类型

    Args:
        use_case: 使用场景

    Returns:
        Optional[str]: 推荐的仓储类型
    """
    recommendations = {
        "persistent_storage": "postgresql",
        "caching": "redis",
        "temporary_storage": "redis",
        "complex_queries": "postgresql",
        "high_performance": "redis",
        "data_consistency": "postgresql",
        "session_storage": "redis",
        "analytics": "postgresql",
    }

    return recommendations.get(use_case)


def create_hybrid_repository(
    primary_type: str = "postgresql", cache_type: str = "redis", **configs
) -> IDetectionRepository:
    """
    创建混合仓储（主存储 + 缓存）

    Args:
        primary_type: 主存储类型
        cache_type: 缓存类型
        **configs: 配置参数

    Returns:
        IDetectionRepository: 混合仓储实例
    """
    from .hybrid_detection_repository import HybridDetectionRepository

    primary_config = configs.get("primary_config", {})
    cache_config = configs.get("cache_config", {})

    primary_repo = RepositoryFactory.create_repository(primary_type, **primary_config)
    cache_repo = RepositoryFactory.create_repository(cache_type, **cache_config)

    return HybridDetectionRepository(primary_repo, cache_repo)
