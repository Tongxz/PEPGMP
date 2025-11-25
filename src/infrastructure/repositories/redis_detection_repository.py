"""
Redis检测记录仓储实现
使用Redis存储检测记录，适合缓存和临时存储
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
    RepositoryError,
)

logger = logging.getLogger(__name__)


class RedisDetectionRepository(IDetectionRepository):
    """Redis检测记录仓储实现"""

    def __init__(self, connection_string: str = None, default_ttl: int = 3600):
        """
        初始化Redis仓储

        Args:
            connection_string: Redis连接字符串
            default_ttl: 默认TTL（秒）
        """
        self.connection_string = connection_string or self._get_default_connection()
        self.default_ttl = default_ttl
        self._redis = None

        logger.info("Redis检测记录仓储初始化")

    def _get_default_connection(self) -> str:
        """获取默认连接字符串"""
        import os

        return os.getenv("REDIS_URL", "redis://:pepgmp_dev_redis@localhost:6379/0")

    async def _get_redis(self):
        """获取Redis连接"""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = await redis.from_url(
                    self.connection_string, encoding="utf-8", decode_responses=True
                )
                logger.info("Redis连接已建立")
            except ImportError:
                raise RepositoryError("redis依赖未安装")
            except Exception as e:
                raise RepositoryError(f"Redis连接失败: {e}")

        return self._redis

    def _get_record_key(self, record_id: str) -> str:
        """获取记录键"""
        return f"detection_record:{record_id}"

    def _get_camera_key(self, camera_id: str) -> str:
        """获取摄像头键"""
        return f"camera_records:{camera_id}"

    def _get_timestamp_key(self, timestamp: datetime) -> str:
        """获取时间戳键"""
        return f"timestamp_records:{timestamp.strftime('%Y%m%d%H%M%S')}"

    async def save(self, record: DetectionRecord) -> str:
        """
        保存检测记录

        Args:
            record: 检测记录

        Returns:
            str: 保存的记录ID
        """
        try:
            redis = await self._get_redis()

            # 序列化记录
            record_data = json.dumps(record.to_dict(), default=str)

            # 保存记录
            record_key = self._get_record_key(record.id)
            await redis.setex(record_key, self.default_ttl, record_data)

            # 添加到摄像头索引
            camera_key = self._get_camera_key(record.camera_id)
            await redis.zadd(camera_key, {record.id: record.timestamp.timestamp()})
            await redis.expire(camera_key, self.default_ttl)

            # 添加到时间戳索引
            timestamp_key = self._get_timestamp_key(record.timestamp)
            await redis.zadd(timestamp_key, {record.id: record.timestamp.timestamp()})
            await redis.expire(timestamp_key, self.default_ttl)

            logger.debug(f"检测记录已保存到Redis: {record.id}")
            return record.id

        except Exception as e:
            logger.error(f"保存检测记录到Redis失败: {e}")
            raise RepositoryError(f"保存检测记录到Redis失败: {e}")

    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """
        根据ID查找记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[DetectionRecord]: 检测记录，如果不存在则返回None
        """
        try:
            redis = await self._get_redis()

            record_key = self._get_record_key(record_id)
            record_data = await redis.get(record_key)

            if record_data is None:
                return None

            record_dict = json.loads(record_data)
            return DetectionRecord.from_dict(record_dict)

        except Exception as e:
            logger.error(f"从Redis查找检测记录失败: {e}")
            raise RepositoryError(f"从Redis查找检测记录失败: {e}")

    async def find_by_camera_id(
        self, camera_id: str, limit: int = 100, offset: int = 0
    ) -> List[DetectionRecord]:
        """
        根据摄像头ID查找记录

        Args:
            camera_id: 摄像头ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """
        try:
            redis = await self._get_redis()

            camera_key = self._get_camera_key(camera_id)

            # 获取记录ID列表（按时间戳降序）
            record_ids = await redis.zrevrange(camera_key, offset, offset + limit - 1)

            if not record_ids:
                return []

            # 批量获取记录
            records = []
            for record_id in record_ids:
                record = await self.find_by_id(record_id)
                if record:
                    records.append(record)

            return records

        except Exception as e:
            logger.error(f"从Redis查找检测记录失败: {e}")
            raise RepositoryError(f"从Redis查找检测记录失败: {e}")

    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DetectionRecord]:
        """
        根据时间范围查找记录

        Args:
            start_time: 开始时间
            end_time: 结束时间
            camera_id: 摄像头ID（可选）
            limit: 限制数量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """
        try:
            redis = await self._get_redis()

            # 获取所有可能的记录ID
            all_record_ids = set()

            # 遍历时间范围内的所有分钟
            current_time = start_time.replace(second=0, microsecond=0)
            while current_time <= end_time:
                timestamp_key = self._get_timestamp_key(current_time)
                record_ids = await redis.zrange(timestamp_key, 0, -1)
                all_record_ids.update(record_ids)
                current_time += timedelta(minutes=1)

            # 过滤记录
            records = []
            for record_id in list(all_record_ids)[:limit]:
                record = await self.find_by_id(record_id)
                if record and start_time <= record.timestamp <= end_time:
                    if camera_id is None or record.camera_id == camera_id:
                        records.append(record)

            # 按时间戳排序
            records.sort(key=lambda x: x.timestamp, reverse=True)
            return records[:limit]

        except Exception as e:
            logger.error(f"从Redis查找检测记录失败: {e}")
            raise RepositoryError(f"从Redis查找检测记录失败: {e}")

    async def find_by_confidence_range(
        self,
        min_confidence: float,
        max_confidence: float,
        camera_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DetectionRecord]:
        """
        根据置信度范围查找记录

        Args:
            min_confidence: 最小置信度
            max_confidence: 最大置信度
            camera_id: 摄像头ID（可选）
            limit: 限制数量

        Returns:
            List[DetectionRecord]: 检测记录列表
        """
        try:
            redis = await self._get_redis()

            # 获取所有记录键
            pattern = "detection_record:*"
            record_keys = await redis.keys(pattern)

            records = []
            for key in record_keys[: limit * 2]:  # 获取更多以过滤
                record_data = await redis.get(key)
                if record_data:
                    record_dict = json.loads(record_data)
                    record = DetectionRecord.from_dict(record_dict)

                    if min_confidence <= record.confidence <= max_confidence:
                        if camera_id is None or record.camera_id == camera_id:
                            records.append(record)

            # 按时间戳排序
            records.sort(key=lambda x: x.timestamp, reverse=True)
            return records[:limit]

        except Exception as e:
            logger.error(f"从Redis查找检测记录失败: {e}")
            raise RepositoryError(f"从Redis查找检测记录失败: {e}")

    async def count_by_camera_id(self, camera_id: str) -> int:
        """
        统计摄像头记录数量

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 记录数量
        """
        try:
            redis = await self._get_redis()

            camera_key = self._get_camera_key(camera_id)
            count = await redis.zcard(camera_key)

            return count or 0

        except Exception as e:
            logger.error(f"从Redis统计检测记录失败: {e}")
            raise RepositoryError(f"从Redis统计检测记录失败: {e}")

    async def delete_by_id(self, record_id: str) -> bool:
        """
        根据ID删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 删除是否成功
        """
        try:
            redis = await self._get_redis()

            # 先获取记录以获取摄像头ID和时间戳
            record = await self.find_by_id(record_id)
            if not record:
                return False

            # 删除记录
            record_key = self._get_record_key(record_id)
            result = await redis.delete(record_key)

            # 从索引中删除
            camera_key = self._get_camera_key(record.camera_id)
            await redis.zrem(camera_key, record_id)

            timestamp_key = self._get_timestamp_key(record.timestamp)
            await redis.zrem(timestamp_key, record_id)

            success = result > 0
            if success:
                logger.debug(f"检测记录已从Redis删除: {record_id}")
            else:
                logger.warning(f"检测记录不存在: {record_id}")

            return success

        except Exception as e:
            logger.error(f"从Redis删除检测记录失败: {e}")
            raise RepositoryError(f"从Redis删除检测记录失败: {e}")

    async def delete_by_camera_id(self, camera_id: str) -> int:
        """
        删除摄像头的所有记录

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 删除的记录数量
        """
        try:
            redis = await self._get_redis()

            camera_key = self._get_camera_key(camera_id)
            record_ids = await redis.zrange(camera_key, 0, -1)

            deleted_count = 0
            for record_id in record_ids:
                if await self.delete_by_id(record_id):
                    deleted_count += 1

            logger.info(f"从Redis删除了 {deleted_count} 条检测记录，摄像头: {camera_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"从Redis删除检测记录失败: {e}")
            raise RepositoryError(f"从Redis删除检测记录失败: {e}")

    async def get_statistics(
        self,
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            camera_id: 摄像头ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            redis = await self._get_redis()

            # 获取所有记录键
            pattern = "detection_record:*"
            record_keys = await redis.keys(pattern)

            total_records = 0
            total_confidence = 0.0
            total_processing_time = 0.0
            earliest_record = None
            latest_record = None

            for key in record_keys:
                record_data = await redis.get(key)
                if record_data:
                    record_dict = json.loads(record_data)
                    record = DetectionRecord.from_dict(record_dict)

                    # 应用过滤条件
                    if camera_id and record.camera_id != camera_id:
                        continue
                    if start_time and record.timestamp < start_time:
                        continue
                    if end_time and record.timestamp > end_time:
                        continue

                    total_records += 1
                    total_confidence += record.confidence
                    total_processing_time += record.processing_time

                    if earliest_record is None or record.timestamp < earliest_record:
                        earliest_record = record.timestamp
                    if latest_record is None or record.timestamp > latest_record:
                        latest_record = record.timestamp

            return {
                "total_records": total_records,
                "avg_confidence": total_confidence / total_records
                if total_records > 0
                else 0.0,
                "avg_processing_time": total_processing_time / total_records
                if total_records > 0
                else 0.0,
                "earliest_record": earliest_record.isoformat()
                if earliest_record
                else None,
                "latest_record": latest_record.isoformat() if latest_record else None,
            }

        except Exception as e:
            logger.error(f"从Redis获取统计信息失败: {e}")
            raise RepositoryError(f"从Redis获取统计信息失败: {e}")

    async def close(self):
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis连接已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
