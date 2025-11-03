"""环境配置加载模块.

基于12-Factor App原则，从环境变量加载配置。
支持.env文件和环境特定配置文件。
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入python-dotenv
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    logger.warning("python-dotenv未安装，无法从.env文件加载配置")
    logger.warning("安装命令: pip install python-dotenv")


class Config:
    """应用配置类.

    从环境变量和.env文件加载配置。
    配置优先级（从高到低）：
    1. 环境变量（命令行设置）
    2. .env.local（本地覆盖，不提交）
    3. .env.{ENVIRONMENT}（环境特定）
    4. .env（默认配置）
    5. 代码中的默认值
    """

    def __init__(self, env_file: Optional[str] = None):
        """初始化配置.

        Args:
            env_file: 环境文件路径，如果为None则按优先级加载
        """
        if not HAS_DOTENV:
            logger.info("使用环境变量进行配置（未安装python-dotenv）")
            return

        if env_file:
            # 加载指定的配置文件
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"已加载配置文件: {env_file}")
            else:
                logger.warning(f"配置文件不存在: {env_file}")
        else:
            # 按优先级加载配置文件
            project_root = Path(__file__).parent.parent.parent

            # 1. 加载默认配置
            default_env = project_root / ".env"
            if default_env.exists():
                load_dotenv(default_env)
                logger.info(f"已加载默认配置: {default_env}")

            # 2. 加载环境特定配置
            environment = os.getenv("ENVIRONMENT", "development")
            env_specific = project_root / f".env.{environment}"
            if env_specific.exists():
                load_dotenv(env_specific, override=True)
                logger.info(f"已加载环境特定配置: {env_specific}")

            # 3. 加载本地覆盖配置
            local_env = project_root / ".env.local"
            if local_env.exists():
                load_dotenv(local_env, override=True)
                logger.info(f"已加载本地覆盖配置: {local_env}")

    # ==================== 应用配置 ====================

    @property
    def environment(self) -> str:
        """环境名称: development, staging, production."""
        return os.getenv("ENVIRONMENT", "development")

    @property
    def log_level(self) -> str:
        """日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL."""
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def auto_convert_tensorrt(self) -> bool:
        """是否自动转换TensorRT模型."""
        return os.getenv("AUTO_CONVERT_TENSORRT", "false").lower() == "true"

    # ==================== 数据库配置 ====================

    @property
    def database_url(self) -> str:
        """数据库连接URL.

        格式: postgresql://user:password@host:port/dbname
        """
        return os.getenv("DATABASE_URL", "")

    @property
    def database_host(self) -> str:
        """数据库主机."""
        return os.getenv("DATABASE_HOST", "localhost")

    @property
    def database_port(self) -> int:
        """数据库端口."""
        return int(os.getenv("DATABASE_PORT", "5432"))

    @property
    def database_name(self) -> str:
        """数据库名称."""
        return os.getenv("DATABASE_NAME", "pyt_development")

    @property
    def database_user(self) -> str:
        """数据库用户."""
        return os.getenv("DATABASE_USER", "pyt_dev")

    @property
    def database_password(self) -> str:
        """数据库密码."""
        return os.getenv("DATABASE_PASSWORD", "")

    # ==================== Redis配置 ====================

    @property
    def redis_url(self) -> str:
        """Redis连接URL.

        格式: redis://:password@host:port/db
        """
        return os.getenv("REDIS_URL", "")

    @property
    def redis_host(self) -> str:
        """Redis主机."""
        return os.getenv("REDIS_HOST", "localhost")

    @property
    def redis_port(self) -> int:
        """Redis端口."""
        return int(os.getenv("REDIS_PORT", "6379"))

    @property
    def redis_db(self) -> int:
        """Redis数据库编号."""
        return int(os.getenv("REDIS_DB", "0"))

    @property
    def redis_password(self) -> Optional[str]:
        """Redis密码."""
        password = os.getenv("REDIS_PASSWORD")
        return password if password else None

    # ==================== 领域服务配置 ====================

    @property
    def use_domain_service(self) -> bool:
        """是否使用领域服务."""
        return os.getenv("USE_DOMAIN_SERVICE", "false").lower() == "true"

    @property
    def rollout_percent(self) -> int:
        """灰度发布百分比（0-100）."""
        return int(os.getenv("ROLLOUT_PERCENT", "0"))

    @property
    def repository_type(self) -> str:
        """仓储类型: postgresql, redis, hybrid."""
        return os.getenv("REPOSITORY_TYPE", "postgresql")

    # ==================== API配置 ====================

    @property
    def api_host(self) -> str:
        """API服务主机."""
        return os.getenv("API_HOST", "0.0.0.0")

    @property
    def api_port(self) -> int:
        """API服务端口."""
        return int(os.getenv("API_PORT", "8000"))

    @property
    def api_reload(self) -> bool:
        """是否启用热重载（开发环境）."""
        return os.getenv("API_RELOAD", "false").lower() == "true"

    # ==================== 安全配置 ====================

    @property
    def admin_username(self) -> str:
        """管理员用户名."""
        return os.getenv("ADMIN_USERNAME", "admin")

    @property
    def admin_password(self) -> str:
        """管理员密码."""
        return os.getenv("ADMIN_PASSWORD", "")

    @property
    def secret_key(self) -> str:
        """应用密钥."""
        return os.getenv("SECRET_KEY", "")

    # ==================== 摄像头配置 ====================

    @property
    def cameras_yaml_path(self) -> str:
        """摄像头配置文件路径."""
        return os.getenv("CAMERAS_YAML_PATH", "config/cameras.yaml")

    # ==================== 可选配置 ====================

    @property
    def watchfiles_force_polling(self) -> bool:
        """是否强制使用文件轮询（Docker on Mac需要）."""
        return os.getenv("WATCHFILES_FORCE_POLLING", "false").lower() == "true"

    def validate(self) -> bool:
        """验证必需的配置项是否存在.

        Returns:
            配置是否有效

        Raises:
            ValueError: 如果缺少必需的配置项
        """
        required = [
            ("DATABASE_URL", self.database_url),
            ("REDIS_URL", self.redis_url),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(f"缺少必需的配置项: {', '.join(missing)}\n" f"请检查.env文件或环境变量设置")

        # 验证密码（生产环境）
        if self.environment == "production":
            weak_passwords = []

            if self.admin_password == "admin123":
                weak_passwords.append("ADMIN_PASSWORD")

            if self.secret_key == "dev-secret-key-change-in-production":
                weak_passwords.append("SECRET_KEY")

            if weak_passwords:
                raise ValueError(
                    f"生产环境不能使用默认密码: {', '.join(weak_passwords)}\n"
                    f"请在.env.production中设置强密码"
                )

        return True

    def __repr__(self) -> str:
        """配置的字符串表示（隐藏敏感信息）."""
        return (
            f"Config(environment={self.environment}, "
            f"database=***@{self.database_host}:{self.database_port}, "
            f"redis=***@{self.redis_host}:{self.redis_port})"
        )


# 全局配置实例
config = Config()


# 导出常用配置（用于向后兼容）
def get_config() -> Config:
    """获取全局配置实例."""
    return config
