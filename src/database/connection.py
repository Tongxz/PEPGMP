"""
数据库连接和会话管理
提供数据库连接、会话创建和关闭功能
"""

import logging
import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# 数据库配置
_raw_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
)

# 处理 SSL 配置
# - psycopg2 (同步): 通过 connect_args={'sslmode': 'disable'}
# - asyncpg (异步): 通过 connect_args={'ssl': False}
# 注意: asyncpg 不支持 'sslmode' 参数，必须使用 'ssl'
if "?sslmode=" in _raw_database_url:
    # 从 URL 中移除 ?sslmode= 部分
    DATABASE_URL = _raw_database_url.split("?")[0]
    _sync_connect_args = {"sslmode": "disable"}
    _async_connect_args = {"ssl": False}  # asyncpg 使用 ssl=False
else:
    DATABASE_URL = _raw_database_url
    _sync_connect_args = {}
    _async_connect_args = {}

# 如果 ASYNC_DATABASE_URL 未设置，从 DATABASE_URL 自动生成
_async_db_url = os.getenv("ASYNC_DATABASE_URL")
if _async_db_url:
    # 处理用户提供的 ASYNC_DATABASE_URL，同样移除 ?sslmode=
    if "?sslmode=" in _async_db_url:
        _async_db_url = _async_db_url.split("?")[0]
    if _async_db_url.startswith("postgresql://"):
        ASYNC_DATABASE_URL = _async_db_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    else:
        ASYNC_DATABASE_URL = _async_db_url
else:
    # 从 DATABASE_URL 自动生成（已移除 ?sslmode=）
    if DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    else:
        # 如果格式不匹配，使用默认值
        ASYNC_DATABASE_URL = "postgresql+asyncpg://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development"

# 同步数据库引擎（用于Alembic迁移，psycopg2 驱动）
sync_engine = create_engine(DATABASE_URL, echo=False, connect_args=_sync_connect_args)

# 异步数据库引擎（asyncpg 驱动，使用 ssl=False 而不是 sslmode）
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_async_connect_args,
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    用于依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话错误: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """
    初始化数据库
    创建所有表
    """
    try:
        from src.database.models import Base

        # 创建所有表
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_database():
    """
    关闭数据库连接
    """
    try:
        await async_engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


def get_sync_session():
    """
    获取同步数据库会话
    用于Alembic迁移等场景
    """
    SessionLocal = sessionmaker(bind=sync_engine)
    return SessionLocal()


# 数据库健康检查
async def check_database_health() -> bool:
    """
    检查数据库连接健康状态
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False
