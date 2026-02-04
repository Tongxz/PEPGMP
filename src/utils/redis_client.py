"""Redis客户端工具模块.

提供统一的Redis客户端获取和管理功能，支持连接池复用。
"""

import logging
from typing import Optional

from redis.asyncio import Redis, from_url

from src.config.env_config import config

logger = logging.getLogger(__name__)

# 全局Redis客户端实例（单例模式）
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """获取Redis客户端实例（单例模式）.

    Returns:
        Redis客户端实例

    Raises:
        RuntimeError: 如果Redis连接失败
    """
    global _redis_client

    if _redis_client is None:
        try:
            # 从环境配置获取Redis URL
            redis_url = config.redis_url
            if not redis_url:
                # 如果没有完整URL，从独立配置构建
                password_part = (
                    f":{config.redis_password}@" if config.redis_password else ""
                )
                redis_url = f"redis://{password_part}{config.redis_host}:{config.redis_port}/{config.redis_db}"

            # 创建Redis客户端
            _redis_client = from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,  # 自动解码为字符串
                socket_keepalive=True,
                socket_timeout=5,  # 5秒超时
                socket_connect_timeout=5,
            )

            # 测试连接
            await _redis_client.ping()
            logger.info(f"Redis客户端已连接: {config.redis_host}:{config.redis_port}")

        except Exception as e:
            logger.error(f"Redis连接失败: {e}", exc_info=True)
            _redis_client = None
            raise RuntimeError(f"Redis连接失败: {e}")

    return _redis_client


async def test_redis_connection() -> bool:
    """测试Redis连接是否可用.

    Returns:
        True if连接正常，False otherwise
    """
    try:
        client = await get_redis_client()
        await client.ping()
        logger.info("Redis连接测试成功")
        return True
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
        return False


async def close_redis_client():
    """关闭Redis客户端连接."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis客户端已关闭")


def reset_redis_client():
    """重置Redis客户端（用于测试或重新连接）."""
    global _redis_client
    _redis_client = None
    logger.info("Redis客户端已重置")
