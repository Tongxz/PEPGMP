"""
PostgreSQL检测记录仓储实现
使用PostgreSQL数据库存储检测记录
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.interfaces.repositories.detection_repository_interface import (
    DetectionRecord,
    IDetectionRepository,
    RepositoryError,
)

logger = logging.getLogger(__name__)


class PostgreSQLDetectionRepository(IDetectionRepository):
    """PostgreSQL检测记录仓储实现"""

    def __init__(self, connection_string: str = None):
        """
        初始化PostgreSQL仓储

        Args:
            connection_string: 数据库连接字符串
        """
        self.connection_string = connection_string or self._get_default_connection()
        self._connection = None
        self._pool = None

        logger.info("PostgreSQL检测记录仓储初始化")

    def _get_default_connection(self) -> str:
        """获取默认连接字符串"""
        import os

        return os.getenv(
            "DATABASE_URL",
            "postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development",
        )

    async def _get_connection(self):
        """获取数据库连接"""
        if self._connection is None:
            try:
                import asyncpg

                self._connection = await asyncpg.connect(self.connection_string)
                logger.info("PostgreSQL连接已建立")
            except ImportError:
                raise RepositoryError("asyncpg依赖未安装")
            except Exception as e:
                raise RepositoryError(f"PostgreSQL连接失败: {e}")

        return self._connection

    async def _ensure_table_exists(self):
        """确保表存在"""
        conn = await self._get_connection()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS detection_records (
            id VARCHAR(255) PRIMARY KEY,
            camera_id VARCHAR(255) NOT NULL,
            objects JSONB NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            confidence FLOAT NOT NULL,
            processing_time FLOAT NOT NULL,
            frame_id INTEGER,
            region_id VARCHAR(255),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_detection_records_camera_id
        ON detection_records(camera_id);

        CREATE INDEX IF NOT EXISTS idx_detection_records_timestamp
        ON detection_records(timestamp);

        CREATE INDEX IF NOT EXISTS idx_detection_records_confidence
        ON detection_records(confidence);
        """

        await conn.execute(create_table_sql)
        logger.debug("检测记录表已确保存在")

    async def save(self, record: DetectionRecord) -> str:
        """
        保存检测记录

        Args:
            record: 检测记录

        Returns:
            str: 保存的记录ID
        """
        try:
            await self._ensure_table_exists()
            conn = await self._get_connection()

            insert_sql = """
            INSERT INTO detection_records
            (id, camera_id, objects, timestamp, confidence, processing_time, frame_id, region_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                objects = EXCLUDED.objects,
                timestamp = EXCLUDED.timestamp,
                confidence = EXCLUDED.confidence,
                processing_time = EXCLUDED.processing_time,
                frame_id = EXCLUDED.frame_id,
                region_id = EXCLUDED.region_id,
                metadata = EXCLUDED.metadata
            """

            await conn.execute(
                insert_sql,
                record.id,
                record.camera_id,
                json.dumps(record.objects),
                record.timestamp,
                record.confidence,
                record.processing_time,
                record.frame_id,
                record.region_id,
                json.dumps(record.metadata) if record.metadata else None,
            )

            logger.debug(f"检测记录已保存: {record.id}")
            return record.id

        except Exception as e:
            logger.error(f"保存检测记录失败: {e}")
            raise RepositoryError(f"保存检测记录失败: {e}")

    async def find_by_id(self, record_id: str) -> Optional[DetectionRecord]:
        """
        根据ID查找记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[DetectionRecord]: 检测记录，如果不存在则返回None
        """
        try:
            conn = await self._get_connection()

            select_sql = """
            SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                   frame_id, region_id, metadata
            FROM detection_records
            WHERE id = $1
            """

            row = await conn.fetchrow(select_sql, record_id)

            if row is None:
                return None

            return self._row_to_record(row)

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

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
            conn = await self._get_connection()

            select_sql = """
            SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                   frame_id, region_id, metadata
            FROM detection_records
            WHERE camera_id = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
            """

            rows = await conn.fetch(select_sql, camera_id, limit, offset)

            return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def find_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[str] = None,
        limit: int = 100,
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
            conn = await self._get_connection()

            if camera_id:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE timestamp BETWEEN $1 AND $2 AND camera_id = $3
                ORDER BY timestamp DESC
                LIMIT $4
                """
                rows = await conn.fetch(
                    select_sql, start_time, end_time, camera_id, limit
                )
            else:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE timestamp BETWEEN $1 AND $2
                ORDER BY timestamp DESC
                LIMIT $3
                """
                rows = await conn.fetch(select_sql, start_time, end_time, limit)

            return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

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
            conn = await self._get_connection()

            if camera_id:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE confidence BETWEEN $1 AND $2 AND camera_id = $3
                ORDER BY timestamp DESC
                LIMIT $4
                """
                rows = await conn.fetch(
                    select_sql, min_confidence, max_confidence, camera_id, limit
                )
            else:
                select_sql = """
                SELECT id, camera_id, objects, timestamp, confidence, processing_time,
                       frame_id, region_id, metadata
                FROM detection_records
                WHERE confidence BETWEEN $1 AND $2
                ORDER BY timestamp DESC
                LIMIT $3
                """
                rows = await conn.fetch(
                    select_sql, min_confidence, max_confidence, limit
                )

            return [self._row_to_record(row) for row in rows]

        except Exception as e:
            logger.error(f"查找检测记录失败: {e}")
            raise RepositoryError(f"查找检测记录失败: {e}")

    async def count_by_camera_id(self, camera_id: str) -> int:
        """
        统计摄像头记录数量

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 记录数量
        """
        try:
            conn = await self._get_connection()

            count_sql = "SELECT COUNT(*) FROM detection_records WHERE camera_id = $1"
            result = await conn.fetchval(count_sql, camera_id)

            return result or 0

        except Exception as e:
            logger.error(f"统计检测记录失败: {e}")
            raise RepositoryError(f"统计检测记录失败: {e}")

    async def delete_by_id(self, record_id: str) -> bool:
        """
        根据ID删除记录

        Args:
            record_id: 记录ID

        Returns:
            bool: 删除是否成功
        """
        try:
            conn = await self._get_connection()

            delete_sql = "DELETE FROM detection_records WHERE id = $1"
            result = await conn.execute(delete_sql, record_id)

            # PostgreSQL返回格式: "DELETE 1" 或 "DELETE 0"
            deleted_count = int(result.split()[-1])
            success = deleted_count > 0

            if success:
                logger.debug(f"检测记录已删除: {record_id}")
            else:
                logger.warning(f"检测记录不存在: {record_id}")

            return success

        except Exception as e:
            logger.error(f"删除检测记录失败: {e}")
            raise RepositoryError(f"删除检测记录失败: {e}")

    async def delete_by_camera_id(self, camera_id: str) -> int:
        """
        删除摄像头的所有记录

        Args:
            camera_id: 摄像头ID

        Returns:
            int: 删除的记录数量
        """
        try:
            conn = await self._get_connection()

            delete_sql = "DELETE FROM detection_records WHERE camera_id = $1"
            result = await conn.execute(delete_sql, camera_id)

            # PostgreSQL返回格式: "DELETE N"
            deleted_count = int(result.split()[-1])

            logger.info(f"删除了 {deleted_count} 条检测记录，摄像头: {camera_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"删除检测记录失败: {e}")
            raise RepositoryError(f"删除检测记录失败: {e}")

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
            conn = await self._get_connection()

            # 构建WHERE条件
            where_conditions = []
            params = []
            param_count = 0

            if camera_id:
                param_count += 1
                where_conditions.append(f"camera_id = ${param_count}")
                params.append(camera_id)

            if start_time:
                param_count += 1
                where_conditions.append(f"timestamp >= ${param_count}")
                params.append(start_time)

            if end_time:
                param_count += 1
                where_conditions.append(f"timestamp <= ${param_count}")
                params.append(end_time)

            where_clause = (
                "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            )

            # 统计查询
            stats_sql = f"""
            SELECT
                COUNT(*) as total_records,
                AVG(confidence) as avg_confidence,
                AVG(processing_time) as avg_processing_time,
                MIN(timestamp) as earliest_record,
                MAX(timestamp) as latest_record
            FROM detection_records
            {where_clause}
            """

            result = await conn.fetchrow(stats_sql, *params)

            return {
                "total_records": result["total_records"] or 0,
                "avg_confidence": float(result["avg_confidence"])
                if result["avg_confidence"]
                else 0.0,
                "avg_processing_time": float(result["avg_processing_time"])
                if result["avg_processing_time"]
                else 0.0,
                "earliest_record": result["earliest_record"].isoformat()
                if result["earliest_record"]
                else None,
                "latest_record": result["latest_record"].isoformat()
                if result["latest_record"]
                else None,
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise RepositoryError(f"获取统计信息失败: {e}")

    def _row_to_record(self, row) -> DetectionRecord:
        """将数据库行转换为DetectionRecord对象"""
        return DetectionRecord(
            id=row["id"],
            camera_id=row["camera_id"],
            objects=json.loads(row["objects"])
            if isinstance(row["objects"], str)
            else row["objects"],
            timestamp=row["timestamp"],
            confidence=row["confidence"],
            processing_time=row["processing_time"],
            frame_id=row["frame_id"],
            region_id=row["region_id"],
            metadata=json.loads(row["metadata"])
            if row["metadata"] and isinstance(row["metadata"], str)
            else row["metadata"],
        )

    async def close(self):
        """关闭数据库连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("PostgreSQL连接已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
