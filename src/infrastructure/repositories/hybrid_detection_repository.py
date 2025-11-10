"""
混合检测记录仓储实现
结合主存储和缓存，提供高性能的数据访问
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
    RepositoryError,
)

logger = logging.getLogger(__name__)


class HybridDetectionRepository(IDetectionRepository):
    """混合检测记录仓储实现"""

    def __init__(
        self,
        primary_repository: IDetectionRepository,
        cache_repository: IDetectionRepository,
    ):
        """
        初始化混合仓储

        Args:
            primary_repository: 主存储仓储（如PostgreSQL）
            cache_repository: 缓存仓储（如Redis）
        """
        self.primary = primary_repository
        self.cache = cache_repository

        logger.info("混合检测记录仓储初始化完成")

    async def save(self, record: DetectionRecord) -> str:
        """
        保存检测记录

        Args:
            record: 检测记录

        Returns:
            str: 保存的记录ID
        """
        try:
            # 同时保存到主存储和缓存
            primary_id = await self.primary.save(record)
            cache_id = await self.cache.save(record)

            # 确保ID一致
            if primary_id != cache_id:
                logger.warning(f"主存储和缓存返回的ID不一致: {primary_id} vs {cache_id}")

            logger.debug(f"检测记录已保存到混合仓储: {record.id}")
            return primary_id

        except Exception as e:
            logger.error(f"保存检测记录到混合仓储失败: {e}")
            raise RepositoryError(f"保存检测记录到混合仓储失败: {e}")

    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """
        根据ID查找记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[DetectionRecord]: 检测记录，如果不存在则返回None
        """
        try:
            # 先从缓存查找
            record = await self.cache.find_by_id(record_id)
            if record:
                logger.debug(f"从缓存获取检测记录: {record_id}")
                return record

            # 缓存未命中，从主存储查找
            record = await self.primary.find_by_id(record_id)
            if record:
                # 将记录写入缓存
                await self.cache.save(record)
                logger.debug(f"从主存储获取检测记录并写入缓存: {record_id}")
                return record

            return None

        except Exception as e:
            logger.error(f"从混合仓储查找检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储查找检测记录失败: {e}")

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
            # 对于列表查询，优先使用主存储
            records = await self.primary.find_by_camera_id(camera_id, limit, offset)

            # 将结果写入缓存
            for record in records:
                try:
                    await self.cache.save(record)
                except Exception as e:
                    logger.warning(f"写入缓存失败: {e}")

            logger.debug(f"从主存储获取检测记录列表: {camera_id}, 数量: {len(records)}")
            return records

        except Exception as e:
            logger.error(f"从混合仓储查找检测记录列表失败: {e}")
            raise RepositoryError(f"从混合仓储查找检测记录列表失败: {e}")

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
            # 对于时间范围查询，优先使用主存储
            records = await self.primary.find_by_time_range(
                start_time, end_time, camera_id, limit, offset
            )

            # 将结果写入缓存
            for record in records:
                try:
                    await self.cache.save(record)
                except Exception as e:
                    logger.warning(f"写入缓存失败: {e}")

            logger.debug(f"从主存储获取时间范围检测记录: {len(records)}条")
            return records

        except Exception as e:
            logger.error(f"从混合仓储查找时间范围检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储查找时间范围检测记录失败: {e}")

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
            # 对于置信度查询，优先使用主存储
            records = await self.primary.find_by_confidence_range(
                min_confidence, max_confidence, camera_id, limit
            )

            # 将结果写入缓存
            for record in records:
                try:
                    await self.cache.save(record)
                except Exception as e:
                    logger.warning(f"写入缓存失败: {e}")

            logger.debug(f"从主存储获取置信度范围检测记录: {len(records)}条")
            return records

        except Exception as e:
            logger.error(f"从混合仓储查找置信度范围检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储查找置信度范围检测记录失败: {e}")

    async def count_by_camera_id(self, camera_id: str) -> int:
        """
        统计摄像头记录数量

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 记录数量
        """
        try:
            # 统计查询使用主存储
            count = await self.primary.count_by_camera_id(camera_id)
            logger.debug(f"从主存储统计检测记录数量: {camera_id}, 数量: {count}")
            return count

        except Exception as e:
            logger.error(f"从混合仓储统计检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储统计检测记录失败: {e}")

    async def delete_by_id(self, record_id: str) -> bool:
        """
        根据ID删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 同时从主存储和缓存删除
            primary_result = await self.primary.delete_by_id(record_id)
            cache_result = await self.cache.delete_by_id(record_id)

            success = primary_result or cache_result  # 至少一个成功即可

            if success:
                logger.debug(f"检测记录已从混合仓储删除: {record_id}")
            else:
                logger.warning(f"检测记录不存在: {record_id}")

            return success

        except Exception as e:
            logger.error(f"从混合仓储删除检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储删除检测记录失败: {e}")

    async def delete_by_camera_id(self, camera_id: str) -> int:
        """
        删除摄像头的所有记录

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 删除的记录数量
        """
        try:
            # 同时从主存储和缓存删除
            primary_count = await self.primary.delete_by_camera_id(camera_id)
            cache_count = await self.cache.delete_by_camera_id(camera_id)

            # 返回较大的删除数量
            deleted_count = max(primary_count, cache_count)

            logger.info(f"从混合仓储删除了 {deleted_count} 条检测记录，摄像头: {camera_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"从混合仓储删除检测记录失败: {e}")
            raise RepositoryError(f"从混合仓储删除检测记录失败: {e}")

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
            # 统计查询使用主存储
            stats = await self.primary.get_statistics(camera_id, start_time, end_time)
            logger.debug(f"从主存储获取统计信息: {stats}")
            return stats

        except Exception as e:
            logger.error(f"从混合仓储获取统计信息失败: {e}")
            raise RepositoryError(f"从混合仓储获取统计信息失败: {e}")

    async def clear_cache(self) -> None:
        """清空缓存"""
        try:
            # 这里需要根据具体的缓存实现来清空
            # 对于Redis，可以删除所有相关键
            if hasattr(self.cache, "clear_all"):
                await self.cache.clear_all()
            else:
                logger.warning("缓存仓储不支持清空操作")

            logger.info("混合仓储缓存已清空")

        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    async def sync_cache(self, camera_id: str) -> int:
        """
        同步缓存（将主存储的数据同步到缓存）

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 同步的记录数量
        """
        try:
            # 从主存储获取所有记录
            records = await self.primary.find_by_camera_id(camera_id, limit=1000)

            # 写入缓存
            synced_count = 0
            for record in records:
                try:
                    await self.cache.save(record)
                    synced_count += 1
                except Exception as e:
                    logger.warning(f"同步记录到缓存失败: {e}")

            logger.info(f"缓存同步完成: {camera_id}, 同步数量: {synced_count}")
            return synced_count

        except Exception as e:
            logger.error(f"同步缓存失败: {e}")
            raise RepositoryError(f"同步缓存失败: {e}")

    async def close(self):
        """关闭仓储连接"""
        try:
            if hasattr(self.primary, "close"):
                await self.primary.close()
            if hasattr(self.cache, "close"):
                await self.cache.close()
            logger.info("混合仓储连接已关闭")
        except Exception as e:
            logger.warning(f"关闭混合仓储连接时出错: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
