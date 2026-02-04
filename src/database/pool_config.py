"""数据库连接池配置模块.

提供环境感知的连接池配置，支持环境变量覆盖。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PoolConfig:
    """数据库连接池配置.

    根据环境（development/production/testing）提供不同的连接池参数。
    支持通过环境变量覆盖默认配置。

    Attributes:
        min_size: 最小连接数（保持活跃）
        max_size: 最大连接数（峰值）
        command_timeout: 命令超时时间（秒）
        max_queries: 每个连接最多执行查询数（防止连接泄漏）
        max_inactive_connection_lifetime: 非活跃连接最大生存时间（秒）

    Example:
        >>> config = PoolConfig.from_env()
        >>> print(config.max_size)
        10

        >>> config = PoolConfig.from_env("production")
        >>> print(config.max_size)
        50
    """

    min_size: int
    max_size: int
    command_timeout: float
    max_queries: int
    max_inactive_connection_lifetime: float

    def __post_init__(self):
        """验证配置参数."""
        if self.min_size < 0:
            raise ValueError(f"min_size必须 >= 0，当前值: {self.min_size}")

        if self.max_size < 1:
            raise ValueError(f"max_size必须 >= 1，当前值: {self.max_size}")

        if self.min_size > self.max_size:
            raise ValueError(
                f"min_size必须 <= max_size，"
                f"当前值: min_size={self.min_size}, max_size={self.max_size}"
            )

        if self.command_timeout <= 0:
            raise ValueError(f"command_timeout必须 > 0，当前值: {self.command_timeout}")

        if self.max_queries < 1:
            raise ValueError(f"max_queries必须 >= 1，当前值: {self.max_queries}")

        if self.max_inactive_connection_lifetime < 0:
            raise ValueError(
                f"max_inactive_connection_lifetime必须 >= 0，"
                f"当前值: {self.max_inactive_connection_lifetime}"
            )

    @classmethod
    def from_env(cls, env: Optional[str] = None) -> "PoolConfig":
        """根据环境创建配置.

        优先级:
        1. 环境变量（如 DB_POOL_MAX_SIZE）- 最高优先级
        2. ENV环境变量指定的环境配置
        3. 默认配置（development）

        Args:
            env: 环境名称（development/production/testing）
                 如果为None，从ENV环境变量读取

        Returns:
            连接池配置实例

        Example:
            >>> # 使用环境变量
            >>> os.environ["ENV"] = "production"
            >>> config = PoolConfig.from_env()
            >>> config.max_size
            50

            >>> # 直接指定环境
            >>> config = PoolConfig.from_env("development")
            >>> config.max_size
            10

            >>> # 环境变量覆盖
            >>> os.environ["DB_POOL_MAX_SIZE"] = "100"
            >>> config = PoolConfig.from_env("production")
            >>> config.max_size
            100
        """
        if env is None:
            env = os.getenv("ENV", "development").lower()
        else:
            env = env.lower()

        # 预定义配置
        configs = {
            "development": cls(
                min_size=2,
                max_size=10,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,  # 5分钟
            ),
            "dev": cls(
                min_size=2,
                max_size=10,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
            ),
            "production": cls(
                min_size=10,
                max_size=50,
                command_timeout=30.0,
                max_queries=50000,
                max_inactive_connection_lifetime=600.0,  # 10分钟
            ),
            "prod": cls(
                min_size=10,
                max_size=50,
                command_timeout=30.0,
                max_queries=50000,
                max_inactive_connection_lifetime=600.0,
            ),
            "testing": cls(
                min_size=1,
                max_size=5,
                command_timeout=30.0,
                max_queries=10000,
                max_inactive_connection_lifetime=60.0,  # 1分钟
            ),
            "test": cls(
                min_size=1,
                max_size=5,
                command_timeout=30.0,
                max_queries=10000,
                max_inactive_connection_lifetime=60.0,
            ),
        }

        # 获取环境对应的配置（如果环境未知，使用development）
        base_config = configs.get(env, configs["development"])

        # 环境变量覆盖（优先级最高）
        return cls(
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", base_config.min_size)),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", base_config.max_size)),
            command_timeout=float(
                os.getenv("DB_POOL_COMMAND_TIMEOUT", base_config.command_timeout)
            ),
            max_queries=int(os.getenv("DB_POOL_MAX_QUERIES", base_config.max_queries)),
            max_inactive_connection_lifetime=float(
                os.getenv(
                    "DB_POOL_MAX_INACTIVE_LIFETIME",
                    base_config.max_inactive_connection_lifetime,
                )
            ),
        )

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            配置字典
        """
        return {
            "min_size": self.min_size,
            "max_size": self.max_size,
            "command_timeout": self.command_timeout,
            "max_queries": self.max_queries,
            "max_inactive_connection_lifetime": self.max_inactive_connection_lifetime,
        }
