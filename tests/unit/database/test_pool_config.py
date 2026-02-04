"""数据库连接池配置单元测试."""

import os
from unittest.mock import patch

import pytest

from src.database.pool_config import PoolConfig


class TestPoolConfig:
    """测试PoolConfig类."""

    def test_create_with_valid_params(self):
        """测试使用有效参数创建配置."""
        config = PoolConfig(
            min_size=2,
            max_size=10,
            command_timeout=60.0,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
        )

        assert config.min_size == 2
        assert config.max_size == 10
        assert config.command_timeout == 60.0
        assert config.max_queries == 50000
        assert config.max_inactive_connection_lifetime == 300.0

    def test_validation_min_size_negative(self):
        """测试min_size为负数时抛出异常."""
        with pytest.raises(ValueError, match="min_size必须 >= 0"):
            PoolConfig(
                min_size=-1,
                max_size=10,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
            )

    def test_validation_max_size_zero(self):
        """测试max_size为0时抛出异常."""
        with pytest.raises(ValueError, match="max_size必须 >= 1"):
            PoolConfig(
                min_size=0,
                max_size=0,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
            )

    def test_validation_min_greater_than_max(self):
        """测试min_size > max_size时抛出异常."""
        with pytest.raises(ValueError, match="min_size必须 <= max_size"):
            PoolConfig(
                min_size=20,
                max_size=10,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
            )

    def test_validation_command_timeout_zero(self):
        """测试command_timeout为0时抛出异常."""
        with pytest.raises(ValueError, match="command_timeout必须 > 0"):
            PoolConfig(
                min_size=2,
                max_size=10,
                command_timeout=0.0,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,
            )

    def test_validation_max_queries_zero(self):
        """测试max_queries为0时抛出异常."""
        with pytest.raises(ValueError, match="max_queries必须 >= 1"):
            PoolConfig(
                min_size=2,
                max_size=10,
                command_timeout=60.0,
                max_queries=0,
                max_inactive_connection_lifetime=300.0,
            )

    def test_validation_max_inactive_lifetime_negative(self):
        """测试max_inactive_connection_lifetime为负数时抛出异常."""
        with pytest.raises(ValueError, match="max_inactive_connection_lifetime必须 >= 0"):
            PoolConfig(
                min_size=2,
                max_size=10,
                command_timeout=60.0,
                max_queries=50000,
                max_inactive_connection_lifetime=-1.0,
            )

    def test_to_dict(self):
        """测试转换为字典."""
        config = PoolConfig(
            min_size=2,
            max_size=10,
            command_timeout=60.0,
            max_queries=50000,
            max_inactive_connection_lifetime=300.0,
        )

        result = config.to_dict()

        assert result == {
            "min_size": 2,
            "max_size": 10,
            "command_timeout": 60.0,
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300.0,
        }


class TestPoolConfigFromEnv:
    """测试PoolConfig.from_env()方法."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_env_development(self):
        """测试默认环境（无ENV变量）使用development配置."""
        config = PoolConfig.from_env()

        assert config.min_size == 2
        assert config.max_size == 10
        assert config.command_timeout == 60.0
        assert config.max_queries == 50000
        assert config.max_inactive_connection_lifetime == 300.0

    @patch.dict(os.environ, {"ENV": "development"})
    def test_development_env(self):
        """测试development环境配置."""
        config = PoolConfig.from_env()

        assert config.min_size == 2
        assert config.max_size == 10
        assert config.command_timeout == 60.0

    @patch.dict(os.environ, {"ENV": "dev"})
    def test_dev_env_alias(self):
        """测试dev环境别名."""
        config = PoolConfig.from_env()

        assert config.min_size == 2
        assert config.max_size == 10

    @patch.dict(os.environ, {"ENV": "production"})
    def test_production_env(self):
        """测试production环境配置."""
        config = PoolConfig.from_env()

        assert config.min_size == 10
        assert config.max_size == 50
        assert config.command_timeout == 30.0
        assert config.max_inactive_connection_lifetime == 600.0

    @patch.dict(os.environ, {"ENV": "prod"})
    def test_prod_env_alias(self):
        """测试prod环境别名."""
        config = PoolConfig.from_env()

        assert config.min_size == 10
        assert config.max_size == 50

    @patch.dict(os.environ, {"ENV": "testing"})
    def test_testing_env(self):
        """测试testing环境配置."""
        config = PoolConfig.from_env()

        assert config.min_size == 1
        assert config.max_size == 5
        assert config.command_timeout == 30.0
        assert config.max_queries == 10000
        assert config.max_inactive_connection_lifetime == 60.0

    @patch.dict(os.environ, {"ENV": "test"})
    def test_test_env_alias(self):
        """测试test环境别名."""
        config = PoolConfig.from_env()

        assert config.min_size == 1
        assert config.max_size == 5

    @patch.dict(os.environ, {"ENV": "unknown_env"})
    def test_unknown_env_uses_development(self):
        """测试未知环境使用development配置."""
        config = PoolConfig.from_env()

        assert config.min_size == 2
        assert config.max_size == 10

    @patch.dict(os.environ, {"ENV": "production", "DB_POOL_MAX_SIZE": "100"})
    def test_env_var_override_max_size(self):
        """测试环境变量覆盖max_size."""
        config = PoolConfig.from_env()

        assert config.max_size == 100
        # 其他参数保持production配置
        assert config.min_size == 10

    @patch.dict(os.environ, {"ENV": "development", "DB_POOL_MIN_SIZE": "5"})
    def test_env_var_override_min_size(self):
        """测试环境变量覆盖min_size."""
        config = PoolConfig.from_env()

        assert config.min_size == 5
        assert config.max_size == 10

    @patch.dict(os.environ, {"ENV": "production", "DB_POOL_COMMAND_TIMEOUT": "120.0"})
    def test_env_var_override_command_timeout(self):
        """测试环境变量覆盖command_timeout."""
        config = PoolConfig.from_env()

        assert config.command_timeout == 120.0

    @patch.dict(
        os.environ,
        {
            "ENV": "production",
            "DB_POOL_MIN_SIZE": "20",
            "DB_POOL_MAX_SIZE": "100",
            "DB_POOL_COMMAND_TIMEOUT": "45.0",
        },
    )
    def test_multiple_env_var_overrides(self):
        """测试多个环境变量同时覆盖."""
        config = PoolConfig.from_env()

        assert config.min_size == 20
        assert config.max_size == 100
        assert config.command_timeout == 45.0
        # 未覆盖的参数保持production配置
        assert config.max_queries == 50000

    def test_explicit_env_parameter(self):
        """测试显式指定环境参数."""
        config = PoolConfig.from_env("production")

        assert config.min_size == 10
        assert config.max_size == 50

    @patch.dict(os.environ, {"ENV": "development"})
    def test_explicit_env_overrides_env_var(self):
        """测试显式参数优先于ENV环境变量."""
        config = PoolConfig.from_env("production")

        # 应该使用显式指定的production，而不是ENV变量的development
        assert config.min_size == 10
        assert config.max_size == 50

    @patch.dict(os.environ, {"DB_POOL_MAX_SIZE": "100"})
    def test_env_var_override_with_explicit_env(self):
        """测试显式环境 + 环境变量覆盖."""
        config = PoolConfig.from_env("production")

        # 显式指定production配置
        assert config.min_size == 10
        # 但max_size被环境变量覆盖
        assert config.max_size == 100


class TestPoolConfigRealWorldScenarios:
    """测试真实使用场景."""

    @patch.dict(os.environ, {"ENV": "development"})
    def test_development_scenario(self):
        """测试开发环境场景."""
        config = PoolConfig.from_env()

        # 开发环境使用较小的连接池
        assert config.min_size == 2
        assert config.max_size == 10
        # 超时时间较长，便于调试
        assert config.command_timeout == 60.0

    @patch.dict(os.environ, {"ENV": "production"})
    def test_production_scenario(self):
        """测试生产环境场景."""
        config = PoolConfig.from_env()

        # 生产环境使用较大的连接池
        assert config.min_size == 10
        assert config.max_size == 50
        # 超时时间较短，快速失败
        assert config.command_timeout == 30.0
        # 连接生命周期较长
        assert config.max_inactive_connection_lifetime == 600.0

    @patch.dict(os.environ, {"ENV": "testing"})
    def test_testing_scenario(self):
        """测试测试环境场景."""
        config = PoolConfig.from_env()

        # 测试环境使用最小的连接池
        assert config.min_size == 1
        assert config.max_size == 5
        # 查询数较少
        assert config.max_queries == 10000
        # 连接生命周期较短
        assert config.max_inactive_connection_lifetime == 60.0

    @patch.dict(os.environ, {"ENV": "production", "DB_POOL_MAX_SIZE": "200"})
    def test_high_traffic_production(self):
        """测试高流量生产环境."""
        config = PoolConfig.from_env()

        # 高流量场景增加最大连接数
        assert config.max_size == 200
        assert config.min_size == 10

    @patch.dict(os.environ, {"ENV": "development", "DB_POOL_MAX_SIZE": "3"})
    def test_resource_constrained_development(self):
        """测试资源受限的开发环境."""
        config = PoolConfig.from_env()

        # 资源受限时减少连接数
        assert config.max_size == 3
        assert config.min_size == 2
