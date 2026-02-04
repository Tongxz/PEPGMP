"""统一应用配置模块.

使用Pydantic提供类型安全的配置管理。
支持从环境变量、.env文件加载配置。
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """数据库配置."""

    url: str = Field(
        ..., description="数据库连接URL (postgresql://user:password@host:port/dbname)"
    )
    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, ge=1, le=65535, description="数据库端口")
    name: str = Field(default="pepgmp_development", description="数据库名称")
    user: str = Field(default="pepgmp_dev", description="数据库用户")
    password: str = Field(default="", description="数据库密码")

    # 连接池配置
    pool_min_size: int = Field(default=2, ge=0, description="连接池最小连接数")
    pool_max_size: int = Field(default=10, ge=1, description="连接池最大连接数")
    pool_command_timeout: float = Field(default=60.0, gt=0, description="命令超时时间（秒）")
    pool_max_queries: int = Field(default=50000, ge=1, description="每个连接最多执行查询数")
    pool_max_inactive_lifetime: float = Field(
        default=300.0, ge=0, description="非活跃连接最大生存时间（秒）"
    )

    @field_validator("url", mode="before")
    @classmethod
    def build_url_from_parts(cls, v, info):
        """如果URL为空，从各个部分构建URL."""
        if v:
            return v

        # 从环境变量获取各个部分
        host = os.getenv("DATABASE_HOST", "localhost")
        port = int(os.getenv("DATABASE_PORT", "5432"))
        name = os.getenv("DATABASE_NAME", "pepgmp_development")
        user = os.getenv("DATABASE_USER", "pepgmp_dev")
        password = os.getenv("DATABASE_PASSWORD", "")

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{name}"
        else:
            return f"postgresql://{user}@{host}:{port}/{name}"


class RedisConfig(BaseModel):
    """Redis配置."""

    url: str = Field(..., description="Redis连接URL (redis://:password@host:port/db)")
    host: str = Field(default="localhost", description="Redis主机")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis端口")
    db: int = Field(default=0, ge=0, description="Redis数据库编号")
    password: Optional[str] = Field(default=None, description="Redis密码")

    @field_validator("url", mode="before")
    @classmethod
    def build_url_from_parts(cls, v, info):
        """如果URL为空，从各个部分构建URL."""
        if v:
            return v

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        password = os.getenv("REDIS_PASSWORD")

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"


class AppConfig(BaseSettings):
    """统一应用配置.

    配置优先级（从高到低）：
    1. 环境变量（命令行设置）
    2. .env.local（本地覆盖，不提交）
    3. .env.{ENVIRONMENT}（环境特定）
    4. .env（默认配置）
    5. 代码中的默认值
    """

    # ==================== 应用配置 ====================
    environment: str = Field(
        default="development", description="环境名称: development, staging, production"
    )
    log_level: str = Field(
        default="INFO", description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    auto_convert_tensorrt: bool = Field(default=False, description="是否自动转换TensorRT模型")

    # ==================== 数据库配置 ====================
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="数据库配置"
    )

    # ==================== Redis配置 ====================
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis配置")

    # ==================== 领域服务配置 ====================
    use_domain_service: bool = Field(default=False, description="是否使用领域服务")
    rollout_percent: int = Field(default=0, ge=0, le=100, description="灰度发布百分比（0-100）")
    repository_type: str = Field(
        default="postgresql", description="仓储类型: postgresql, redis, hybrid"
    )

    # ==================== API配置 ====================
    api_host: str = Field(default="0.0.0.0", description="API服务主机")  # nosec B104
    api_port: int = Field(default=8000, ge=1, le=65535, description="API服务端口")
    api_reload: bool = Field(default=False, description="是否启用热重载（开发环境）")

    # ==================== 安全配置 ====================
    admin_username: str = Field(default="admin", description="管理员用户名")
    admin_password: str = Field(default="", description="管理员密码")
    secret_key: str = Field(default="", description="应用密钥")

    # ==================== 摄像头配置 ====================
    cameras_yaml_path: str = Field(
        default="config/cameras.yaml", description="摄像头配置文件路径"
    )

    # ==================== 可选配置 ====================
    watchfiles_force_polling: bool = Field(
        default=False, description="是否强制使用文件轮询（Docker on Mac需要）"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # 支持 DATABASE__URL 格式
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的字段
    )

    @classmethod
    def load_from_env_files(cls, project_root: Optional[Path] = None) -> "AppConfig":
        """按优先级加载配置文件.

        Args:
            project_root: 项目根目录，如果为None则自动检测

        Returns:
            配置实例
        """
        if project_root is None:
            # 自动检测项目根目录（向上查找包含 .env 或 pyproject.toml 的目录）
            current = Path(__file__).parent
            while current != current.parent:
                if (current / ".env").exists() or (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()

        # 按优先级加载配置文件
        env_files = []

        # 1. 默认配置
        default_env = project_root / ".env"
        if default_env.exists():
            env_files.append(default_env)

        # 2. 环境特定配置
        environment = os.getenv("ENVIRONMENT", "development")
        env_specific = project_root / f".env.{environment}"
        if env_specific.exists():
            env_files.append(env_specific)

        # 3. 本地覆盖配置
        local_env = project_root / ".env.local"
        if local_env.exists():
            env_files.append(local_env)

        # 使用最后一个文件（最高优先级）作为env_file
        env_file = env_files[-1] if env_files else None

        return cls(_env_file=env_file)

    def validate_required(self) -> None:
        """验证必需的配置项.

        Raises:
            ValueError: 如果缺少必需的配置项
        """
        missing = []

        if not self.database.url:
            missing.append("DATABASE_URL")

        if not self.redis.url:
            missing.append("REDIS_URL")

        if missing:
            raise ValueError(f"缺少必需的配置项: {', '.join(missing)}\n" f"请检查.env文件或环境变量设置")

        # 验证密码（生产环境）
        if self.environment == "production":
            weak_passwords = []

            if self.admin_password == "admin123" or not self.admin_password:
                weak_passwords.append("ADMIN_PASSWORD")

            if (
                self.secret_key == "dev-secret-key-change-in-production"
                or not self.secret_key
            ):
                weak_passwords.append("SECRET_KEY")

            if weak_passwords:
                raise ValueError(
                    f"生产环境不能使用默认密码: {', '.join(weak_passwords)}\n"
                    f"请在.env.production中设置强密码"
                )

    def __repr__(self) -> str:
        """配置的字符串表示（隐藏敏感信息）."""
        return (
            f"AppConfig(environment={self.environment}, "
            f"database=***@{self.database.host}:{self.database.port}, "
            f"redis=***@{self.redis.host}:{self.redis.port})"
        )
