"""Redis缓存装饰器模块.

提供通用的Redis缓存装饰器，自动处理缓存读写和降级。
"""

import functools
import hashlib
import json
import logging
import random
from typing import Any, Callable, Optional

from src.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键.

    Args:
        prefix: 缓存键前缀
        func_name: 函数名称
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        缓存键字符串

    Example:
        generate_cache_key("stats", "get_stats", (), {})
        → "stats:get_stats:v1"
    """
    # 如果没有参数，使用简单格式
    if not args and not kwargs:
        return f"{prefix}:{func_name}:v1"

    # 如果有参数，生成参数哈希
    param_str = json.dumps(
        {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
    )
    param_hash = hashlib.md5(param_str.encode(), usedforsecurity=False).hexdigest()[:8]

    return f"{prefix}:{func_name}:{param_hash}:v1"


def redis_cache(
    ttl: int = 60,
    key_prefix: str = "cache",
    key_generator: Optional[Callable] = None,
    enable_fallback: bool = True,
):
    """Redis缓存装饰器.

    自动处理缓存读写、降级和异常。

    Args:
        ttl: 缓存过期时间（秒），0表示不缓存
        key_prefix: 缓存键前缀
        key_generator: 自定义缓存键生成函数（可选）
        enable_fallback: 是否启用降级（Redis失败时执行原函数）

    Returns:
        装饰器函数

    Example:
        @redis_cache(ttl=10, key_prefix="stats:realtime")
        async def get_stats():
            return {"users": 100}

    Design:
        - 缓存命中：直接返回缓存数据
        - 缓存未命中：执行原函数，缓存结果
        - Redis失败：自动降级到原函数（如果enable_fallback=True）
        - TTL抖动：添加±2秒随机偏移，避免缓存雪崩
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # TTL=0表示不缓存，直接执行原函数
            if ttl <= 0:
                logger.debug(f"缓存已禁用（TTL=0）: {func.__name__}")
                return await func(*args, **kwargs)

            # 生成缓存键
            if key_generator:
                cache_key = key_generator(func.__name__, args, kwargs)
            else:
                cache_key = generate_cache_key(key_prefix, func.__name__, args, kwargs)

            # 尝试从Redis读取缓存
            try:
                redis = await get_redis_client()
                cached_data = await redis.get(cache_key)

                if cached_data:
                    logger.info(f"✅ 缓存命中: {cache_key}")
                    try:
                        return json.loads(cached_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"缓存数据解析失败: {e}，删除缓存")
                        await redis.delete(cache_key)
                        # 继续执行原函数
                else:
                    logger.debug(f"❌ 缓存未命中: {cache_key}")

            except Exception as e:
                logger.error(f"Redis读取失败: {e}", exc_info=True)
                if not enable_fallback:
                    raise
                logger.info("降级到直接查询（Redis读取失败）")
                # 继续执行原函数

            # 执行原函数
            result = await func(*args, **kwargs)

            # 尝试写入Redis缓存
            try:
                redis = await get_redis_client()

                # TTL抖动：添加±2秒随机偏移，避免缓存雪崩
                ttl_with_jitter = ttl + random.uniform(-2, 2)
                ttl_final = max(1, int(ttl_with_jitter))  # 至少1秒

                # 序列化并存储
                cached_value = json.dumps(result, default=str)
                await redis.setex(cache_key, ttl_final, cached_value)

                logger.debug(f"缓存已更新: {cache_key} (TTL={ttl_final}s)")

            except Exception as e:
                logger.error(f"Redis写入失败: {e}", exc_info=True)
                # 写入失败不影响返回结果

            return result

        return wrapper

    return decorator


async def clear_cache(pattern: str = "*") -> int:
    """清除匹配的缓存键.

    Args:
        pattern: 缓存键模式（支持通配符）

    Returns:
        清除的缓存数量

    Example:
        await clear_cache("stats:*")  # 清除所有统计缓存
        await clear_cache("cache:*")  # 清除所有缓存

    Warning:
        使用通配符清除大量缓存时可能影响性能
    """
    try:
        redis = await get_redis_client()

        # 查找匹配的键
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)

        # 删除键
        if keys:
            deleted_count = await redis.delete(*keys)
            logger.info(f"已清除 {deleted_count} 个缓存: {pattern}")
            return deleted_count
        else:
            logger.info(f"未找到匹配的缓存: {pattern}")
            return 0

    except Exception as e:
        logger.error(f"清除缓存失败: {e}", exc_info=True)
        raise


async def get_cache_stats(pattern: str = "*") -> dict:
    """获取缓存统计信息.

    Args:
        pattern: 缓存键模式

    Returns:
        缓存统计信息字典

    Example:
        stats = await get_cache_stats("stats:*")
        # {"total_keys": 10, "pattern": "stats:*"}
    """
    try:
        redis = await get_redis_client()

        # 统计匹配的键数量
        key_count = 0
        async for _ in redis.scan_iter(match=pattern):
            key_count += 1

        # 获取Redis内存信息
        info = await redis.info("memory")

        return {
            "total_keys": key_count,
            "pattern": pattern,
            "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "memory_peak_mb": round(info.get("used_memory_peak", 0) / 1024 / 1024, 2),
        }

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}", exc_info=True)
        return {"error": str(e)}
