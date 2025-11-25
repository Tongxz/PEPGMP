"""
数据库连接和会话管理
提供数据库连接、会话创建和关闭功能
"""

import os
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development")

# 如果 ASYNC_DATABASE_URL 未设置，从 DATABASE_URL 自动生成
_async_db_url = os.getenv("ASYNC_DATABASE_URL")
if _async_db_url:
    ASYNC_DATABASE_URL = _async_db_url
else:
    # 从 DATABASE_URL 自动生成异步数据库URL
    # 将 postgresql:// 替换为 postgresql+asyncpg://
    if DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        # 如果格式不匹配，使用默认值
        ASYNC_DATABASE_URL = "postgresql+asyncpg://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development"

# 同步数据库引擎（用于Alembic迁移）
sync_engine = create_engine(DATABASE_URL, echo=False)

# 异步数据库引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
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
