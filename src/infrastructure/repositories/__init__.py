"""
仓储实现
实现各种数据存储的仓储模式
"""

from .postgresql_detection_repository import PostgreSQLDetectionRepository
from .redis_detection_repository import RedisDetectionRepository
from .repository_factory import RepositoryFactory

__all__ = [
    "PostgreSQLDetectionRepository",
    "RedisDetectionRepository",
    "RepositoryFactory",
]
